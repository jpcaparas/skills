#!/usr/bin/env node
// Zero-dependency helper for DeepSeek's Search and Fetch APIs (POST /v1/tools/search and
// /v1/tools/fetch). Both bill $0.75 per 1,000 successful requests; empty searches and failed
// fetches are free. It validates input locally, normalises dates and duplicate URLs, paces
// batches under the 5 QPS account limit, and retries 408, 429, and 5xx. See references/api.md.

const API_ROOT = (process.env.DEEPSEEK_API_ROOT || "https://api.deepseek.com").replace(/\/+$/, "");
const REQUEST_TIMEOUT_MS = 90_000;
const MAX_QUERY_CODE_POINTS = 128;
const MAX_COUNT = 50;
const MAX_FETCH_URL_CHARS = 8192;
const DEFAULT_SUMMARY_CHARS = 600;
const DEFAULT_FETCH_CHARS = 20_000;
// The documented retry set: wait and retry 408, 429, and 5xx; never retry other 4xx unchanged.
const RETRYABLE_STATUSES = new Set([408, 429, 500, 502, 503, 504]);
const RETRY_DELAYS_MS = [1_000, 2_500, 5_000];
// Search and Fetch each allow 5 requests per second per account, across all keys.
const BATCH_START_INTERVAL_MS = 250;
// Non-null `date` values arrive as midnight Beijing time written in UTC (T16:00:00Z the day before).
const BEIJING_OFFSET_MS = 8 * 60 * 60 * 1000;
const PRICE_PER_REQUEST = { USD: 0.00075, CNY: 0.005 };

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function usage() {
  console.log(`DeepSeek Search and Fetch helper

Usage:
  node scripts/deepseek_search.js search "query" [flags]      One search ($0.00075 if it returns results)
  node scripts/deepseek_search.js batch "q1" "q2" ... [flags] Several searches, paced and deduplicated
  node scripts/deepseek_search.js fetch <url> [flags]         One page as Markdown ($0.00075 if it returns content)
  node scripts/deepseek_search.js balance                     Account balance (free)

Search and batch flags:
  -c, --count <n>        Results per query, 1-${MAX_COUNT} (default 10; price is per request, not per result)
  --site <domain[/path]> Restrict to a site; repeat for several (joined with OR)
  --exclude-site <dom>   Exclude a site; repeatable
  --lang <codes>         Language codes such as en or zh,en (unknown codes return nothing)
  --after <date>         YYYY-MM-DD, or YYYY meaning from 1 January of that year
  --before <date>        YYYY-MM-DD, or YYYY meaning before 1 January of that year
  --question <text>      The user's original question (ori_question), 1-128 characters
  --loc <ip>             Localise results for an IPv4 or IPv6 address
  --content              Ask for page content too (about 3x larger responses)
  --summary-chars <n>    Summary and snippet characters to print (default ${DEFAULT_SUMMARY_CHARS})
  --compact | --json | --urls   Output mode (default: readable; --json is the raw API response)
  -n, --limit <n>        Max results to print (display only)
  --save <file>          Write the full raw API response(s) as JSON
  --file <path>          batch only: read additional queries from a file, one per line

Fetch flags:
  --chars <n>            Max characters to print (default ${DEFAULT_FETCH_CHARS}); use --save for the full page
  --save <file>          Write the full page to <file>
  --raw                  Keep DeepSeek's backslash escapes instead of unescaping them

Examples:
  node scripts/deepseek_search.js search --compact "postgresql 18 logical replication changes"
  node scripts/deepseek_search.js search --site github.com/tokio-rs --after 2026 "select cancellation"
  node scripts/deepseek_search.js batch --compact -c 5 "vite 8 release" "rolldown vite benchmark"
  node scripts/deepseek_search.js fetch --save /tmp/page.md https://www.postgresql.org/docs/18/release-18-6.html
`);
}

class UsageError extends Error {}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function apiKey() {
  const key = process.env.DEEPSEEK_API_KEY;
  if (!key) throw new UsageError("DEEPSEEK_API_KEY environment variable is required.");
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
    } else if (spec.values.includes(name) || spec.repeatable?.includes(name)) {
      const value = args[index + 1];
      if (value === undefined || value.startsWith("--")) throw new UsageError(`${arg} requires a value.`);
      if (spec.repeatable?.includes(name)) {
        flags[name] = [...(flags[name] ?? []), value];
      } else {
        flags[name] = value;
      }
      index += 1;
    } else {
      throw new UsageError(`Unknown flag: ${arg}`);
    }
  }
  return { flags, positional };
}

function parseIntInRange(value, flag, min, max) {
  if (!/^\d+$/.test(value) || Number(value) < min || (max !== undefined && Number(value) > max)) {
    throw new UsageError(`${flag} must be an integer from ${min}${max !== undefined ? ` to ${max}` : ""}.`);
  }
  return Number(value);
}

// The API counts Unicode code points: 128 emoji pass, 129 ASCII or CJK characters fail.
const codePoints = (text) => [...text].length;

function validDomain(value, flag) {
  if (!/^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+(\/[^\s]*)?$/i.test(value)) {
    throw new UsageError(`${flag} expects a bare domain or domain/path such as github.com or github.com/tokio-rs, not "${value}".`);
  }
  return value;
}

function isRealDate(text) {
  const parsed = new Date(`${text}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().startsWith(text);
}

// The API reads a bare year in after: as "after the end of that year" (after:2026 returned
// nothing in October 2026), so the helper expands years to explicit 1 January dates.
function dateOperand(value, flag) {
  if (/^\d{4}$/.test(value)) return `${value}-01-01`;
  if (/^\d{4}-\d{2}-\d{2}$/.test(value) && isRealDate(value)) return value;
  throw new UsageError(`${flag} must be YYYY or a real YYYY-MM-DD date, not "${value}".`);
}

function buildSearchBody(baseQuery, flags) {
  const base = baseQuery.trim();
  if (!base) throw new UsageError("search query is required and must contain non-whitespace text.");
  const parts = [base];
  const sites = (flags["--site"] ?? []).map((site) => validDomain(site, "--site"));
  if (sites.length) parts.push(sites.map((site) => `site:${site}`).join(" OR "));
  for (const site of flags["--exclude-site"] ?? []) parts.push(`-site:${validDomain(site, "--exclude-site")}`);
  if (flags["--lang"]) {
    if (!/^[a-z]{2}(,[a-z]{2})*$/.test(flags["--lang"])) throw new UsageError("--lang expects two-letter codes such as en or zh,en.");
    parts.push(`lang:${flags["--lang"]}`);
  }
  if (flags["--after"]) parts.push(`after:${dateOperand(flags["--after"], "--after")}`);
  if (flags["--before"]) parts.push(`before:${dateOperand(flags["--before"], "--before")}`);
  const query = parts.join(" ");
  const length = codePoints(query);
  if (length > MAX_QUERY_CODE_POINTS) {
    throw new UsageError(
      `query is ${length} characters including operators; DeepSeek allows ${MAX_QUERY_CODE_POINTS}. Shorten it or split it into several searches.`,
    );
  }

  const body = { query, count: flags["--count"] ? parseIntInRange(flags["--count"], "--count", 1, MAX_COUNT) : 10 };
  if (flags["--question"] !== undefined) {
    const question = flags["--question"].trim();
    if (!question || codePoints(question) > MAX_QUERY_CODE_POINTS) throw new UsageError("--question must be 1-128 characters.");
    body.ori_question = question;
  }
  if (flags["--loc"] !== undefined) {
    if (isIP(flags["--loc"]) === 0) throw new UsageError("--loc expects an IPv4 or IPv6 address.");
    body.localization = flags["--loc"];
  }
  if (flags["--content"]) body.need_content = true;
  return body;
}

function errorHint(status, path) {
  switch (status) {
    case 401:
      return "\nHint: DEEPSEEK_API_KEY is missing or invalid.";
    case 402:
      return "\nHint: the DeepSeek balance is empty. Top up at platform.deepseek.com; run `balance` to check.";
    case 403:
      return "\nHint: DeepSeek's security policy rejected this URL (private, internal, or blocked hosts).";
    case 404:
      return path.endsWith("/fetch")
        ? "\nHint: DeepSeek could not extract this page. PDFs, images, error pages, dead hosts, and some JavaScript apps fail. Failed fetches are not billed; try another source."
        : "";
    case 429:
      return "\nHint: the account allows 5 Search and 5 Fetch requests per second across all keys; pace parallel calls.";
    default:
      return "";
  }
}

async function request(method, path, body) {
  for (let attempt = 0; ; attempt += 1) {
    const response = await fetch(`${API_ROOT}${path}`, {
      method,
      headers: { Authorization: `Bearer ${apiKey()}`, ...(body ? { "Content-Type": "application/json" } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    const text = await response.text();
    let data;
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = undefined;
    }
    if (response.ok && data) return data;
    if (RETRYABLE_STATUSES.has(response.status) && attempt < RETRY_DELAYS_MS.length) {
      const delay = RETRY_DELAYS_MS[attempt] + Math.floor(Math.random() * 250);
      console.error(`DeepSeek HTTP ${response.status} on ${path}; retrying in ${(delay / 1000).toFixed(1)}s...`);
      await sleep(delay);
      continue;
    }
    const message = data?.error?.message ?? (text.slice(0, 200) || response.statusText);
    throw new ApiError(`DeepSeek ${path} HTTP ${response.status}: ${message}${errorHint(response.status, path)}`, response.status);
  }
}

function publishedDate(raw) {
  if (!raw) return null;
  const time = Date.parse(raw);
  if (Number.isNaN(time)) return null;
  return new Date(time + BEIJING_OFFSET_MS).toISOString().slice(0, 10);
}

function withoutFragment(url) {
  try {
    const parsed = new URL(url);
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return url;
  }
}

function clip(text, max) {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

function normaliseResult(item, summaryChars) {
  return {
    title: item.title || null,
    url: item.url || null,
    site: item.site_name || null,
    published: publishedDate(item.date),
    score: typeof item.rerank_score === "number" ? Number(item.rerank_score.toFixed(2)) : null,
    authority: item.authority ?? null,
    // Documented as 100-200 characters, but live snippets reached about 2,000.
    snippet: clip(item.snippet, summaryChars),
    summary: clip(item.summary, summaryChars),
    ...(item.content ? { content_chars: item.content.length } : {}),
  };
}

// Results often repeat one page under several #fragments; keep the first occurrence of each page.
function dedupe(items, seen = new Set()) {
  const kept = [];
  let removed = 0;
  for (const item of items) {
    const key = item.url ? withoutFragment(item.url) : `${item.title}`;
    if (seen.has(key)) {
      removed += 1;
      continue;
    }
    seen.add(key);
    kept.push(item);
  }
  return { kept, removed };
}

async function writeFile(path, text) {
  const { writeFileSync } = await import("node:fs");
  writeFileSync(path, text);
}

const SEARCH_SPEC = {
  booleans: ["--compact", "--json", "--urls", "--content"],
  values: ["--count", "--lang", "--after", "--before", "--question", "--loc", "--summary-chars", "--limit", "--save", "--file"],
  repeatable: ["--site", "--exclude-site"],
  aliases: { "-n": "--limit", "-c": "--count" },
};

function printReadable(items) {
  items.forEach((item, index) => {
    console.log(`--- Result ${index + 1} ---`);
    console.log(`Title: ${item.title ?? "(no title)"}`);
    console.log(`URL: ${item.url ?? "(no url)"}`);
    if (item.site) console.log(`Site: ${item.site}`);
    if (item.published) console.log(`Published: ${item.published}`);
    console.log(`Score: ${item.score ?? "?"}  Authority: ${item.authority ?? "?"}`);
    console.log(`Summary: ${item.summary || item.snippet || "(none)"}`);
    console.log("");
  });
}

function emptyResultHint(flags) {
  const hints = ["No results (empty searches are not billed)."];
  if (flags["--lang"]) hints.push("Unknown lang: codes return nothing; check --lang.");
  if (flags["--after"] || flags["--before"]) hints.push("The date window may exclude everything.");
  if ((flags["--site"] ?? []).length) hints.push("The site may not be indexed; try a broader --site or none.");
  return hints.join(" ");
}

async function runSearch(args) {
  const { flags, positional } = parseFlags(args, SEARCH_SPEC);
  if (flags["--file"]) throw new UsageError("--file is only valid with batch.");
  const body = buildSearchBody(positional.join(" "), flags);
  const summaryChars = flags["--summary-chars"] ? parseIntInRange(flags["--summary-chars"], "--summary-chars", 0) : DEFAULT_SUMMARY_CHARS;
  const limit = flags["--limit"] ? parseIntInRange(flags["--limit"], "--limit", 1) : Infinity;
  const raw = await request("POST", "/v1/tools/search", body);
  if (flags["--save"]) {
    await writeFile(flags["--save"], JSON.stringify(raw, null, 2));
    console.error(`Saved the raw response to ${flags["--save"]}`);
  }
  if (flags["--json"]) {
    console.log(JSON.stringify(raw, null, 2));
    return;
  }
  const returned = (raw.results ?? []).map((item) => normaliseResult(item, summaryChars));
  const { kept, removed } = dedupe(returned);
  if (removed) console.error(`Merged ${removed} duplicate result(s) that differed only by #fragment.`);
  const items = kept.slice(0, limit);
  if (flags["--compact"]) {
    console.log(JSON.stringify({ query: body.query, returned: returned.length, results: items }, null, 2));
    if (returned.length === 0) console.error(emptyResultHint(flags));
    return;
  }
  if (items.length === 0) {
    console.error(emptyResultHint(flags));
    return;
  }
  if (flags["--urls"]) {
    items.forEach((item) => item.url && console.log(item.url));
    return;
  }
  printReadable(items);
}

async function readQueryFile(path) {
  const { readFileSync } = await import("node:fs");
  return readFileSync(path, "utf8").split("\n").map((line) => line.trim()).filter(Boolean);
}

async function runBatch(args) {
  const { flags, positional } = parseFlags(args, SEARCH_SPEC);
  if (flags["--json"] || flags["--urls"]) throw new UsageError("batch prints compact JSON; use --save for raw responses.");
  const queries = [...positional, ...(flags["--file"] ? await readQueryFile(flags["--file"]) : [])];
  if (queries.length === 0) throw new UsageError("batch needs at least one query.");
  // Validate every query before the first request so a bad one cannot strand a half-spent batch.
  const bodies = queries.map((query) => buildSearchBody(query, flags));
  const summaryChars = flags["--summary-chars"] ? parseIntInRange(flags["--summary-chars"], "--summary-chars", 0) : DEFAULT_SUMMARY_CHARS;
  const limit = flags["--limit"] ? parseIntInRange(flags["--limit"], "--limit", 1) : Infinity;

  const pending = [];
  for (const [index, body] of bodies.entries()) {
    if (index > 0) await sleep(BATCH_START_INTERVAL_MS);
    pending.push(
      request("POST", "/v1/tools/search", body).then(
        (raw) => ({ body, raw }),
        (error) => ({ body, error }),
      ),
    );
  }
  const settled = await Promise.all(pending);
  if (flags["--save"]) {
    await writeFile(flags["--save"], JSON.stringify(settled.map(({ body, raw, error }) => ({ query: body.query, response: raw ?? null, error: error?.message ?? null })), null, 2));
    console.error(`Saved the raw responses to ${flags["--save"]}`);
  }

  const seen = new Set();
  let duplicates = 0;
  let billable = 0;
  const runs = settled.map(({ body, raw, error }) => {
    if (error) return { query: body.query, error: error.message };
    const returned = (raw.results ?? []).map((item) => normaliseResult(item, summaryChars));
    if (returned.length) billable += 1;
    const { kept, removed } = dedupe(returned, seen);
    duplicates += removed;
    return { query: body.query, returned: returned.length, results: kept.slice(0, limit) };
  });
  console.log(JSON.stringify({ runs, unique_urls: seen.size, duplicates_removed: duplicates, billable_requests: billable }, null, 2));
  console.error(`${billable} billable search(es), about $${(billable * PRICE_PER_REQUEST.USD).toFixed(5)} at list price.`);
  const failed = runs.filter((run) => run.error).length;
  if (failed) {
    console.error(`${failed} of ${runs.length} queries failed; see their "error" fields.`);
    process.exitCode = 1;
  }
}

// DeepSeek escapes Markdown punctuation everywhere (\- \. \: \{ \"), which breaks quotes,
// code, and URLs copied from the page. Undo CommonMark backslash escapes of ASCII punctuation.
function unescapeMarkdown(text) {
  return text.replace(/\\([!-/:-@[-`{-~])/g, "$1");
}

function validateFetchUrl(url) {
  if (!url) throw new UsageError("fetch needs a URL.");
  if (url.length > MAX_FETCH_URL_CHARS) throw new UsageError(`fetch URLs must be at most ${MAX_FETCH_URL_CHARS} characters.`);
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    throw new UsageError(`fetch needs an absolute http(s) URL, not "${url}".`);
  }
  if (!["http:", "https:"].includes(parsed.protocol) || !parsed.hostname || /^https?:\/\/\//i.test(url)) {
    throw new UsageError("fetch needs an http(s) URL with a host.");
  }
  if (parsed.username || parsed.password) throw new UsageError("fetch URLs must not contain a username or password.");
}

async function runFetch(args) {
  const { flags, positional } = parseFlags(args, { booleans: ["--raw"], values: ["--chars", "--save"] });
  const [url] = positional;
  validateFetchUrl(url);
  const maxChars = flags["--chars"] ? parseIntInRange(flags["--chars"], "--chars", 1) : DEFAULT_FETCH_CHARS;
  const page = await request("POST", "/v1/tools/fetch", { url });
  const content = flags["--raw"] ? page.content ?? "" : unescapeMarkdown(page.content ?? "");
  const text = `# ${page.title || "(untitled)"}\nSource: ${url}\n\n${content}`;
  if (flags["--save"]) {
    await writeFile(flags["--save"], text);
    console.error(`Saved ${text.length} characters to ${flags["--save"]}`);
  }
  console.log(text.length > maxChars ? `${text.slice(0, maxChars)}\n...(truncated at ${maxChars} of ${text.length} characters; use --save for the full page)` : text);
}

async function runBalance(args) {
  const data = await request("GET", "/user/balance");
  if (args.includes("--json")) {
    console.log(JSON.stringify(data, null, 2));
    return;
  }
  console.log(`API available: ${data.is_available ? "yes" : "no (top up before calling paid endpoints)"}`);
  for (const info of data.balance_infos ?? []) {
    const total = Number(info.total_balance);
    const price = PRICE_PER_REQUEST[info.currency];
    // Integer micro-units: 2.61 / 0.00075 is 3479.999... in floating point.
    const requests = price ? Math.floor(Math.round(total * 1e6) / Math.round(price * 1e6)) : 0;
    const capacity = price ? `, about ${requests.toLocaleString("en-US")} Search or Fetch requests` : "";
    console.log(`${info.currency} ${total.toFixed(2)} (topped up ${info.topped_up_balance}, granted ${info.granted_balance})${capacity}`);
  }
}

// Loaded with import() so the script runs whether the installing project is CommonJS or ESM.
let isIP;

async function main() {
  ({ isIP } = await import("node:net"));
  const [command, ...rest] = process.argv.slice(2);
  if (!command || command === "-h" || command === "--help" || rest.includes("--help")) {
    usage();
    return;
  }
  switch (command) {
    case "search":
      return runSearch(rest);
    case "batch":
      return runBatch(rest);
    case "fetch":
      return runFetch(rest);
    case "balance":
      return runBalance(rest);
    default:
      throw new UsageError(`Unknown command: ${command}. Run with --help.`);
  }
}

main().catch((error) => {
  console.error(error instanceof UsageError ? `ERROR: ${error.message}` : error.message);
  process.exit(error instanceof UsageError ? 2 : 1);
});
