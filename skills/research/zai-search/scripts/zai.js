#!/usr/bin/env node
// Zero-dependency helper for Z.ai's search tools: web search, web reader, and Zread
// (GitHub repository search). Default calls go through Z.ai's MCP endpoints, which draw on
// the GLM Coding Plan's monthly tool quota. `search --rest` uses the pay-as-you-go
// REST API, which bills the account's cash balance. Details live in references/api.md.

const API_ROOT = (process.env.ZAI_API_ROOT || "https://api.z.ai/api").replace(/\/+$/, "");
const REQUEST_TIMEOUT_MS = 90_000;
const MCP_SERVERS = { search: "web_search_prime", reader: "web_reader", zread: "zread" };
const RECENCY_VALUES = ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"];
const REST_ENGINES = ["search-prime", "search_std", "search_pro", "search_pro_sogou", "search_pro_quark", "search_pro_jina"];
const DEFAULT_READ_CHARS = 20_000;
// MCP throttling (1302) is free and short-lived; 8 or more concurrent calls trigger it.
const THROTTLE_RETRY_DELAYS_MS = [3_000, 8_000, 15_000];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function usage() {
  console.log(`Z.ai search helper

Usage:
  node scripts/zai.js search "query" [flags]       Web search (Coding Plan tool quota)
  node scripts/zai.js read <url> [flags]           Fetch a page as Markdown (Coding Plan tool quota)
  node scripts/zai.js repo-search owner/repo "question"   Search a GitHub repo's docs, issues, commits
  node scripts/zai.js repo-tree owner/repo [dir]   List a GitHub repo directory
  node scripts/zai.js repo-file owner/repo path    Read a file from a GitHub repo
  node scripts/zai.js quota [--json]               Plan tool quota and cash balance (free)

Search flags:
  --site <domain>        Restrict to a domain: appends site:<domain>, then drops off-domain results
  --recency <window>     ${RECENCY_VALUES.join(" | ")}
  --location <us|cn>     Result region (default: us; Z.ai's own default is cn)
  --rest                 Use the billed REST API instead of plan quota (adds --engine, --count, dates)
  --engine <name>        REST engine: ${REST_ENGINES.join(", ")} (default: search-prime)
  --count <n>            REST result count, 1-50 (search-prime returns at most about 10)
  --compact | --json | --urls    Output mode (default: readable)
  -n, --limit <n>        Max results to print (display only)

Read flags:
  --chars <n>            Max characters to print (default: ${DEFAULT_READ_CHARS}); use --save for the full page
  --save <file>          Write the full Markdown content to <file>
  --fresh                Ask Z.ai to bypass its page cache

Examples:
  node scripts/zai.js search --compact "tokio select cancellation safety"
  node scripts/zai.js search --site docs.rs --recency oneYear "select! cancel safety"
  node scripts/zai.js read --save /tmp/page.md https://docs.python.org/3/library/asyncio-task.html
  node scripts/zai.js repo-search vitejs/vite "how does HMR propagate updates"
  node scripts/zai.js quota
`);
}

class UsageError extends Error {}

function apiKey() {
  const key = process.env.Z_AI_API_KEY || process.env.ZAI_API_KEY;
  if (!key) {
    throw new UsageError("Z_AI_API_KEY (or ZAI_API_KEY) environment variable is required.");
  }
  return key;
}

function parseFlags(args, spec) {
  const flags = {};
  const positional = [];
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (!arg.startsWith("-") || arg === "-") {
      positional.push(arg);
      continue;
    }
    const name = spec.aliases?.[arg] ?? arg;
    if (spec.booleans.includes(name)) {
      flags[name] = true;
    } else if (spec.values.includes(name)) {
      const value = args[index + 1];
      if (value === undefined || value.startsWith("--")) throw new UsageError(`${arg} requires a value.`);
      flags[name] = value;
      index += 1;
    } else {
      throw new UsageError(`Unknown flag: ${arg}`);
    }
  }
  return { flags, positional };
}

function parsePositiveInt(value, flag, max) {
  if (!/^\d+$/.test(value) || Number(value) < 1 || (max && Number(value) > max)) {
    throw new UsageError(`${flag} must be an integer from 1${max ? ` to ${max}` : ""}.`);
  }
  return Number(value);
}

function oneOf(value, allowed, flag) {
  if (!allowed.includes(value)) throw new UsageError(`${flag} must be one of: ${allowed.join(", ")}.`);
  return value;
}

async function httpJson(url, { method = "GET", body, headers = {} } = {}) {
  const response = await fetch(url, {
    method,
    headers: { Authorization: `Bearer ${apiKey()}`, ...(body ? { "Content-Type": "application/json" } : {}), ...headers },
    ...(body ? { body: JSON.stringify(body) } : {}),
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`Z.ai returned HTTP ${response.status} with a non-JSON body: ${text.slice(0, 200)}`);
  }
  if (!response.ok || data.error) {
    const code = data.error?.code ?? data.code;
    const message = data.error?.message ?? data.msg ?? text.slice(0, 200);
    throw new Error(`Z.ai HTTP ${response.status}${code ? ` error ${code}` : ""}: ${message}${errorHint(String(code))}`);
  }
  return { data, headers: response.headers };
}

function errorHint(code) {
  switch (code) {
    case "1000":
    case "1001":
    case "1002":
      return "\nHint: check Z_AI_API_KEY.";
    case "1113":
      return "\nHint: the cash balance is empty; REST search is pay-as-you-go. Drop --rest to use plan quota.";
    case "1302":
    case "1305":
      return "\nHint: rate limited or overloaded; retry shortly.";
    case "1308":
    case "1310":
      return "\nHint: the plan's tool quota is spent; run `node scripts/zai.js quota` for the reset time.";
    default:
      return "";
  }
}

// Z.ai's MCP servers speak streamable HTTP and reject tool calls without an initialized session.
async function callMcpTool(server, tool, args) {
  const url = `${API_ROOT}/mcp/${server}/mcp`;
  let sessionId;
  let nextId = 1;

  async function send(payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey()}`,
        "Content-Type": "application/json",
        Accept: "application/json, text/event-stream",
        ...(sessionId ? { "Mcp-Session-Id": sessionId } : {}),
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    sessionId = response.headers.get("mcp-session-id") ?? sessionId;
    const text = await response.text();
    if (!response.ok) throw new Error(`Z.ai MCP ${server} HTTP ${response.status}: ${text.slice(0, 200)}`);
    if (payload.id === undefined) return undefined;
    const messages = text.trim().startsWith("{")
      ? [JSON.parse(text)]
      : text.split("\n").filter((line) => line.startsWith("data:")).map((line) => JSON.parse(line.slice(5)));
    const reply = messages.find((message) => message.id === payload.id);
    if (!reply) throw new Error(`Z.ai MCP ${server} returned no reply: ${text.slice(0, 200)}`);
    if (reply.error) throw new Error(`Z.ai MCP ${server} error ${reply.error.code}: ${reply.error.message}`);
    return reply.result;
  }

  await send({
    jsonrpc: "2.0",
    id: nextId++,
    method: "initialize",
    params: { protocolVersion: "2025-03-26", capabilities: {}, clientInfo: { name: "zai-search-skill", version: "1.0.0" } },
  });
  await send({ jsonrpc: "2.0", method: "notifications/initialized" });
  for (let attempt = 0; ; attempt += 1) {
    const result = await send({ jsonrpc: "2.0", id: nextId++, method: "tools/call", params: { name: tool, arguments: args } });
    const text = (result.content ?? []).filter((block) => block.type === "text").map((block) => block.text).join("");
    if (!result.isError) return decodeToolText(text);
    if (text.includes('"1302"') && attempt < THROTTLE_RETRY_DELAYS_MS.length) {
      console.error(`Rate limited (1302); retrying in ${THROTTLE_RETRY_DELAYS_MS[attempt] / 1000}s...`);
      await sleep(THROTTLE_RETRY_DELAYS_MS[attempt]);
      continue;
    }
    throw new Error(`Z.ai ${tool} failed: ${text}${toolErrorHint(text)}`);
  }
}

function toolErrorHint(text) {
  if (text.includes("repo not found")) {
    return "\nHint: Zread only covers repositories indexed on zread.ai. Read this repository through GitHub instead.";
  }
  if (text.includes('"1302"')) return errorHint("1302");
  if (text.includes('"1234"')) return "\nHint: Z.ai could not fetch the page (it reports 404s and dead hosts as network error 1234).";
  if (text.includes('"1301"')) return "\nHint: Z.ai's content filter rejected the query; rephrase it.";
  if (/quota|limit reached|exhausted/i.test(text)) return errorHint("1310");
  return "";
}

// Search, reader, and Zread tools wrap their payload in an extra layer of JSON string encoding.
function decodeToolText(text) {
  if (!text.startsWith('"')) return text;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function decodeSearchText(text) {
  const value = JSON.parse(text);
  if (!Array.isArray(value)) throw new Error(`Unexpected search payload: ${text.slice(0, 200)}`);
  return value;
}

function normaliseResult(item) {
  return {
    title: item.title || null,
    url: item.link || null,
    site: item.media || null,
    published: item.publish_date || null,
    summary: item.content || "",
  };
}

// Z.ai's search ranks site: matches higher but still returns other hosts, so --site filters locally.
function isOnSite(url, domain) {
  try {
    const host = new URL(url).hostname.toLowerCase();
    const wanted = domain.toLowerCase().replace(/^www\./, "");
    return host === wanted || host.endsWith(`.${wanted}`);
  } catch {
    return false;
  }
}

async function runSearch(args) {
  const { flags, positional } = parseFlags(args, {
    booleans: ["--compact", "--json", "--urls", "--rest"],
    values: ["--site", "--recency", "--location", "--engine", "--count", "--limit"],
    aliases: { "-n": "--limit" },
  });
  const baseQuery = positional.join(" ").trim();
  if (!baseQuery) throw new UsageError("search query is required and must contain non-whitespace text.");
  if (flags["--site"] && (/\s/.test(flags["--site"]) || flags["--site"].includes(":"))) {
    throw new UsageError("--site expects a bare domain such as github.com.");
  }
  const query = flags["--site"] ? `${baseQuery} site:${flags["--site"]}` : baseQuery;
  const recency = flags["--recency"] && oneOf(flags["--recency"], RECENCY_VALUES, "--recency");
  const location = flags["--location"] ? oneOf(flags["--location"], ["us", "cn"], "--location") : "us";
  const limit = flags["--limit"] ? parsePositiveInt(flags["--limit"], "--limit") : Infinity;
  if (!flags["--rest"] && (flags["--engine"] || flags["--count"])) {
    throw new UsageError("--engine and --count require --rest (the billed REST API).");
  }

  let raw;
  if (flags["--rest"]) {
    const body = {
      search_engine: flags["--engine"] ? oneOf(flags["--engine"], REST_ENGINES, "--engine") : "search-prime",
      search_query: query,
      count: flags["--count"] ? parsePositiveInt(flags["--count"], "--count", 50) : 10,
      ...(recency ? { search_recency_filter: recency } : {}),
    };
    const { data } = await httpJson(`${API_ROOT}/paas/v4/web_search`, { method: "POST", body });
    raw = data;
  } else {
    const text = await callMcpTool(MCP_SERVERS.search, "web_search_prime", {
      search_query: query,
      location,
      ...(recency ? { search_recency_filter: recency } : {}),
    });
    raw = decodeSearchText(text);
  }

  if (flags["--json"]) {
    console.log(JSON.stringify(raw, null, 2));
    return;
  }
  const returned = (Array.isArray(raw) ? raw : raw.search_result ?? []).map(normaliseResult);
  const onSite = flags["--site"] ? returned.filter((item) => isOnSite(item.url, flags["--site"])) : returned;
  if (flags["--site"] && onSite.length < returned.length) {
    console.error(`Dropped ${returned.length - onSite.length} of ${returned.length} results outside ${flags["--site"]} (Z.ai treats site: as a hint).`);
  }
  const items = onSite.slice(0, limit);
  if (flags["--compact"]) {
    console.log(JSON.stringify({ query, route: flags["--rest"] ? "rest" : "mcp", results: items }, null, 2));
    return;
  }
  if (items.length === 0) {
    console.error("No results returned.");
    return;
  }
  if (flags["--urls"]) {
    items.forEach((item) => item.url && console.log(item.url));
    return;
  }
  items.forEach((item, index) => {
    console.log(`--- Result ${index + 1} ---`);
    console.log(`Title: ${item.title ?? "(no title)"}`);
    console.log(`URL: ${item.url ?? "(no url)"}`);
    if (item.published) console.log(`Published: ${item.published}`);
    console.log(`Summary: ${item.summary || "(none)"}`);
    console.log("");
  });
}

async function runRead(args) {
  const { flags, positional } = parseFlags(args, {
    booleans: ["--fresh"],
    values: ["--chars", "--save"],
  });
  const [url] = positional;
  if (!url || !/^https?:\/\//i.test(url)) throw new UsageError("read needs an http(s) URL.");
  const maxChars = flags["--chars"] ? parsePositiveInt(flags["--chars"], "--chars") : DEFAULT_READ_CHARS;
  const payload = await callMcpTool(MCP_SERVERS.reader, "webReader", { url, ...(flags["--fresh"] ? { no_cache: true } : {}) });
  const page = JSON.parse(payload);
  const header = [`# ${page.title ?? "(untitled)"}`, `Source: ${page.url ?? url}`];
  if (page.description) header.push(`Description: ${page.description}`);
  const text = `${header.join("\n")}\n\n${page.content ?? ""}`;
  if (flags["--save"]) {
    const { writeFileSync } = await import("node:fs");
    writeFileSync(flags["--save"], text);
    console.error(`Saved ${text.length} characters to ${flags["--save"]}`);
  }
  console.log(text.length > maxChars ? `${text.slice(0, maxChars)}\n...(truncated at ${maxChars} of ${text.length} characters)` : text);
}

function requireRepo(value) {
  if (!value || !/^[\w.-]+\/[\w.-]+$/.test(value)) throw new UsageError("Expected a GitHub repository as owner/repo.");
  return value;
}

async function runRepo(command, args) {
  const { positional } = parseFlags(args, { booleans: [], values: [] });
  const repo = requireRepo(positional[0]);
  if (command === "repo-search") {
    const query = positional.slice(1).join(" ").trim();
    if (!query) throw new UsageError("repo-search needs a question after owner/repo.");
    const text = await callMcpTool(MCP_SERVERS.zread, "search_doc", { repo_name: repo, query, language: "en" });
    console.log(text);
    // Indexed repos can still return only a header and a zread.ai link when nothing matches.
    if (!text.includes("[1]:")) console.error("No matches in Zread's index; rephrase, or browse with repo-tree and repo-file.");
  } else if (command === "repo-tree") {
    console.log(await callMcpTool(MCP_SERVERS.zread, "get_repo_structure", { repo_name: repo, ...(positional[1] ? { dir_path: positional[1] } : {}) }));
  } else {
    if (!positional[1]) throw new UsageError("repo-file needs a file path after owner/repo.");
    console.log(await callMcpTool(MCP_SERVERS.zread, "read_file", { repo_name: repo, file_path: positional[1] }));
  }
}

async function runQuota(args) {
  const [{ data: quota }, balance] = await Promise.all([
    httpJson(`${API_ROOT}/monitor/usage/quota/limit`),
    httpJson(`${API_ROOT}/biz/account/query-customer-account-report`).then(({ data }) => data.data).catch(() => undefined),
  ]);
  if (args.includes("--json")) {
    console.log(JSON.stringify({ quota: quota.data, balance }, null, 2));
    return;
  }
  const limits = quota.data?.limits ?? [];
  if (!quota.success || limits.length === 0) {
    console.log("No Coding Plan quota returned; this key may be pay-as-you-go only, so MCP tools are unavailable.");
  } else {
    console.log(`Z.ai Coding Plan (${quota.data.level ?? "unknown level"})`);
    for (const limit of limits) {
      const resets = limit.nextResetTime ? ` (resets ${new Date(limit.nextResetTime).toISOString()})` : "";
      if (limit.type === "TIME_LIMIT") {
        const details = (limit.usageDetails ?? []).map((detail) => `${detail.modelCode} ${detail.usage}`).join(", ");
        console.log(`Tool calls this month: ${limit.currentValue}/${limit.usage} used, ${limit.remaining} left${resets}${details ? ` [${details}]` : ""}`);
      } else {
        console.log(`${limit.type} (${limit.number}-unit window): ${limit.percentage}% used${resets}`);
      }
    }
  }
  if (balance) console.log(`Cash balance for --rest calls: $${Number(balance.availableBalance).toFixed(2)}`);
}

async function main() {
  const [command, ...rest] = process.argv.slice(2);
  if (!command || command === "-h" || command === "--help" || rest.includes("--help")) {
    usage();
    return;
  }
  switch (command) {
    case "search":
      return runSearch(rest);
    case "read":
      return runRead(rest);
    case "repo-search":
    case "repo-tree":
    case "repo-file":
      return runRepo(command, rest);
    case "quota":
    case "quotas":
      return runQuota(rest);
    default:
      throw new UsageError(`Unknown command: ${command}. Run with --help.`);
  }
}

main().catch((error) => {
  console.error(error instanceof UsageError ? `ERROR: ${error.message}` : error.message);
  process.exit(error instanceof UsageError ? 2 : 1);
});
