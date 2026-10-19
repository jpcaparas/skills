#!/usr/bin/env node
// Zero-dependency helper for Gemini's Google Search grounding, URL context, and the Deep
// Research agent. Defaults are the cheapest reliable configuration measured on 2026-10-19:
// gemini-3.1-flash-lite, forced grounding, and a soft cap of 3 search queries per call.
// Expensive routes (Pro and Argon models, larger caps, Deep Research) refuse to run without
// an explicit flag. Prices and limits are documented in references/api.md.

const API_ROOT = (process.env.GEMINI_API_ROOT || "https://generativelanguage.googleapis.com/v1beta").replace(/\/+$/, "");
const REQUEST_TIMEOUT_MS = 180_000;
const DEFAULT_MODEL = "gemini-3.1-flash-lite";
// Paid Standard tier, USD per 1M tokens, valid through 2026 (3.6 and 3.8 Flash double on 2027-01-01).
const CHEAP_MODELS = {
  "gemini-3.1-flash-lite": { input: 0.25, output: 1.5 },
  "gemini-3.5-flash-lite": { input: 0.3, output: 2.5 },
  "gemini-3.8-flash": { input: 0.75, output: 3.75 },
};
const GATED_MODELS = {
  "gemini-3.1-pro-preview": { input: 2.0, output: 12.0 },
  "gemini-4-argon": { input: 2.0, output: 10.0 },
};
// Gemini 3 and newer bill each search query the model runs, after 5,000 free per month per project.
const SEARCH_QUERY_USD = 0.014;
const DEFAULT_MAX_QUERIES = 3;
const UNGATED_MAX_QUERIES = 5;
// More than 20 URLs does not error: every URL silently fails and the model guesses.
const MAX_READ_URLS = 20;
const LOW_COVERAGE = 0.5;
const RETRYABLE = new Set([429, 500, 502, 503, 504]);
const RETRY_DELAYS_MS = [2_000, 5_000, 10_000];
const RESEARCH_AGENTS = { standard: "deep-research-preview-04-2026", max: "deep-research-max-preview-04-2026" };
const RESEARCH_POLL_MS = Number(process.env.GEMINI_RESEARCH_POLL_MS || 10_000);
const RESEARCH_TIMEOUT_MS = 65 * 60 * 1000;
const EXIT = { usage: 2, ungrounded: 3, unread: 4 };

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function usage() {
  console.log(`Gemini search helper

Usage:
  node scripts/gemini_search.js search "question" [flags]        Grounded answer with sources
  node scripts/gemini_search.js read <url>... [--ask "question"]  Answer from up to ${MAX_READ_URLS} URLs (no search fee)
  node scripts/gemini_search.js research "brief" --confirm-cost  Deep Research agent (about $1+ per task)

Search flags:
  --model <name>         ${Object.keys(CHEAP_MODELS).join(" | ")} (default ${DEFAULT_MODEL})
  --max-queries <n>      Soft cap on search queries, 1-${UNGATED_MAX_QUERIES} (default ${DEFAULT_MAX_QUERIES}); each costs $${SEARCH_QUERY_USD} after the free 5,000/month
  --site <domain>        Ask for sources from one site and flag sources outside it
  --no-resolve           Keep Google's redirect links instead of resolving them
  --json                 Print a machine-readable summary
  --allow-expensive      Permit gated models (${Object.keys(GATED_MODELS).join(", ")}, others) and caps above ${UNGATED_MAX_QUERIES}

Read flags:
  --ask <question>       What to extract (default: summarise each page)
  --model <name>         As for search
  --json                 Print a machine-readable summary

Research flags:
  --confirm-cost         Required. Deep Research bills model tokens plus every search it runs
  --max                  Use Deep Research Max (documented $3-7 per task)
  --keep                 Keep the stored interaction (deleted after retrieval by default)

Exit codes: 0 ok, 1 API error, 2 usage or refused, 3 answer not grounded, 4 no URL could be read.
`);
}

class UsageError extends Error {}

function apiKey() {
  const key = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (!key) throw new UsageError("GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is required.");
  return key;
}

function parseFlags(args, spec) {
  const flags = {};
  const positional = [];
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (!arg.startsWith("--")) {
      positional.push(arg);
    } else if (spec.booleans.includes(arg)) {
      flags[arg] = true;
    } else if (spec.values.includes(arg)) {
      const value = args[index + 1];
      if (value === undefined || value.startsWith("--")) throw new UsageError(`${arg} requires a value.`);
      flags[arg] = value;
      index += 1;
    } else {
      throw new UsageError(`Unknown flag: ${arg}`);
    }
  }
  return { flags, positional };
}

function chooseModel(flags) {
  const model = flags["--model"] ?? DEFAULT_MODEL;
  if (model in CHEAP_MODELS) return model;
  if (!flags["--allow-expensive"]) {
    const price = GATED_MODELS[model];
    throw new UsageError(
      `${model} is gated${price ? ` ($${price.input}/$${price.output} per 1M tokens)` : " (unknown or unpinned model)"}. ` +
        "Get the user's explicit permission, then pass --allow-expensive.",
    );
  }
  return model;
}

async function request(method, path, body) {
  for (let attempt = 0; ; attempt += 1) {
    const response = await fetch(`${API_ROOT}${path}`, {
      method,
      headers: { "x-goog-api-key": apiKey(), ...(body ? { "Content-Type": "application/json" } : {}) },
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
    if (RETRYABLE.has(response.status) && attempt < RETRY_DELAYS_MS.length) {
      console.error(`Gemini HTTP ${response.status}; retrying in ${RETRY_DELAYS_MS[attempt] / 1000}s...`);
      await sleep(RETRY_DELAYS_MS[attempt]);
      continue;
    }
    const message = data?.error?.message ?? (text.slice(0, 300) || response.statusText);
    const hint = response.status === 429 ? "\nHint: rate or spend limit (per project, rolling 10 minutes); slow down." : "";
    throw new Error(`Gemini ${method} ${path.split("?")[0]} HTTP ${response.status}: ${message}${hint}`);
  }
}

// Google returns vertexaisearch.cloud.google.com redirect links titled only by domain.
// A HEAD request without following the redirect reveals the real URL in Location.
async function resolveRedirect(url) {
  try {
    const response = await fetch(url, { method: "HEAD", redirect: "manual", signal: AbortSignal.timeout(10_000) });
    return response.headers.get("location") || url;
  } catch {
    return url;
  }
}

async function mapLimited(items, limit, fn) {
  const results = new Array(items.length);
  let next = 0;
  await Promise.all(
    Array.from({ length: Math.min(limit, items.length) }, async () => {
      while (next < items.length) {
        const index = next++;
        results[index] = await fn(items[index]);
      }
    }),
  );
  return results;
}

function hostOf(url) {
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    return "";
  }
}

function onSite(url, domain) {
  const host = hostOf(url);
  const wanted = domain.toLowerCase().replace(/^www\./, "");
  return host === wanted || host.endsWith(`.${wanted}`);
}

function answerText(candidate) {
  return (candidate?.content?.parts ?? []).filter((part) => !part.thought && part.text).map((part) => part.text).join("");
}

// groundingSupports offsets are UTF-8 byte offsets, not character indices.
function groundingCoverage(text, supports) {
  const length = Buffer.byteLength(text);
  if (!length) return 0;
  const covered = new Uint8Array(length);
  for (const support of supports ?? []) {
    const start = support.segment?.startIndex ?? 0;
    const end = Math.min(support.segment?.endIndex ?? 0, length);
    covered.fill(1, Math.max(0, start), Math.max(start, end));
  }
  return covered.reduce((sum, byte) => sum + byte, 0) / length;
}

function tokenCost(model, usage) {
  const price = CHEAP_MODELS[model] ?? GATED_MODELS[model];
  if (!price || !usage) return null;
  const input = (usage.promptTokenCount ?? 0) + (usage.toolUsePromptTokenCount ?? 0);
  const output = (usage.candidatesTokenCount ?? 0) + (usage.thoughtsTokenCount ?? 0);
  return (input * price.input + output * price.output) / 1e6;
}

const money = (value) => (value === null ? "unknown" : `$${value.toFixed(4)}`);

function groundingInstruction(maxQueries, site) {
  return [
    "Ground every answer in Google Search results: always search before answering, even if you think you know.",
    `Use at most ${maxQueries} search ${maxQueries === 1 ? "query" : "queries"}; batch related facts into one query.`,
    site ? `Use only sources from site:${site}.` : "",
    "If the results do not support an answer, say so instead of guessing.",
  ]
    .filter(Boolean)
    .join(" ");
}

async function runSearch(args) {
  const { flags, positional } = parseFlags(args, {
    booleans: ["--json", "--no-resolve", "--allow-expensive"],
    values: ["--model", "--max-queries", "--site"],
  });
  const question = positional.join(" ").trim();
  if (!question) throw new UsageError("search needs a question.");
  const model = chooseModel(flags);
  const maxQueries = flags["--max-queries"] === undefined ? DEFAULT_MAX_QUERIES : Number(flags["--max-queries"]);
  if (!Number.isInteger(maxQueries) || maxQueries < 1) throw new UsageError("--max-queries must be a positive integer.");
  if (maxQueries > UNGATED_MAX_QUERIES && !flags["--allow-expensive"]) {
    throw new UsageError(
      `--max-queries ${maxQueries} can cost up to $${(maxQueries * SEARCH_QUERY_USD).toFixed(3)} per call. ` +
        `Split the question into calls of ${UNGATED_MAX_QUERIES} or fewer, or get permission and pass --allow-expensive.`,
    );
  }
  const site = flags["--site"];
  if (site !== undefined && !/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(site)) throw new UsageError("--site expects a bare domain such as docs.rs.");

  const data = await request("POST", `/models/${model}:generateContent`, {
    systemInstruction: { parts: [{ text: groundingInstruction(maxQueries, site) }] },
    contents: [{ role: "user", parts: [{ text: question }] }],
    tools: [{ google_search: {} }],
  });
  const candidate = data.candidates?.[0];
  const metadata = candidate?.groundingMetadata ?? {};
  const text = answerText(candidate);
  const queries = [...new Set((metadata.webSearchQueries ?? []).filter((query) => query.trim()))];
  const chunkUris = [...new Set((metadata.groundingChunks ?? []).map((chunk) => chunk.web?.uri).filter(Boolean))];
  const resolved = flags["--no-resolve"] ? chunkUris : await mapLimited(chunkUris, 8, resolveRedirect);
  const sources = [...new Set(resolved)].map((url) => ({ url, offSite: site ? !onSite(url, site) : false }));
  const coverage = groundingCoverage(text, metadata.groundingSupports);
  const tokens = tokenCost(model, data.usageMetadata);
  const summary = {
    model: data.modelVersion ?? model,
    grounded: queries.length > 0,
    queries,
    billable_queries: queries.length,
    coverage: Number(coverage.toFixed(2)),
    estimated_cost_usd: {
      search_after_free_tier: Number((queries.length * SEARCH_QUERY_USD).toFixed(4)),
      tokens: tokens === null ? null : Number(tokens.toFixed(5)),
    },
    finish_reason: candidate?.finishReason ?? null,
    answer: text,
    sources,
  };

  if (flags["--json"]) {
    console.log(JSON.stringify(summary, null, 2));
  } else {
    console.log(text || "(no answer text)");
    if (sources.length) {
      console.log("\nSources:");
      sources.forEach((source, index) => console.log(`  [${index + 1}] ${source.url}${source.offSite ? `  (outside ${site})` : ""}`));
    }
    console.log(`\n${summary.model} · ${queries.length} search ${queries.length === 1 ? "query" : "queries"}: ${queries.map((query) => JSON.stringify(query)).join(", ") || "none"}`);
    console.log(`Grounded text: ${Math.round(coverage * 100)}% · est. search ${money(queries.length * SEARCH_QUERY_USD)} after the free tier · tokens ${money(tokens)}`);
  }
  if (queries.length > maxQueries) console.error(`Warning: the model ran ${queries.length} queries despite the cap of ${maxQueries}.`);
  if (site && sources.some((source) => source.offSite)) console.error(`Warning: some sources are outside ${site}.`);
  if (!summary.grounded) {
    console.error("UNGROUNDED: the model answered from memory without searching. Do not cite this answer; rephrase or retry.");
    process.exitCode = EXIT.ungrounded;
  } else if (coverage < LOW_COVERAGE) {
    console.error(`Warning: only ${Math.round(coverage * 100)}% of the answer is tied to sources; the rest may come from memory.`);
  }
}

function validateUrls(urls) {
  if (urls.length === 0) throw new UsageError("read needs at least one URL.");
  if (urls.length > MAX_READ_URLS) {
    throw new UsageError(`read accepts at most ${MAX_READ_URLS} URLs; with more, Gemini silently fails every URL. Split into batches.`);
  }
  for (const url of urls) {
    let parsed;
    try {
      parsed = new URL(url);
    } catch {
      throw new UsageError(`Not an absolute URL: ${url}`);
    }
    if (!["http:", "https:"].includes(parsed.protocol)) throw new UsageError(`Only http(s) URLs can be read: ${url}`);
  }
}

async function runRead(args) {
  const { flags, positional } = parseFlags(args, { booleans: ["--json", "--allow-expensive"], values: ["--ask", "--model"] });
  validateUrls(positional);
  const model = chooseModel(flags);
  const ask = flags["--ask"]?.trim() || "Summarise each page's main content, one section per URL.";
  const data = await request("POST", `/models/${model}:generateContent`, {
    systemInstruction: {
      parts: [{ text: "Answer only from the content of the provided URLs. If a URL could not be retrieved, say so explicitly; never fill gaps from memory." }],
    },
    contents: [{ role: "user", parts: [{ text: `${ask}\n\nURLs:\n${positional.join("\n")}` }] }],
    tools: [{ url_context: {} }],
  });
  const candidate = data.candidates?.[0];
  const statuses = (candidate?.urlContextMetadata?.urlMetadata ?? []).map((entry) => ({
    url: entry.retrievedUrl,
    status: (entry.urlRetrievalStatus ?? "UNKNOWN").replace("URL_RETRIEVAL_STATUS_", ""),
  }));
  const failed = statuses.filter((entry) => entry.status !== "SUCCESS");
  const tokens = tokenCost(model, data.usageMetadata);
  const summary = {
    model: data.modelVersion ?? model,
    urls: statuses,
    page_tokens: data.usageMetadata?.toolUsePromptTokenCount ?? 0,
    estimated_cost_usd: tokens === null ? null : Number(tokens.toFixed(5)),
    answer: answerText(candidate),
  };
  if (flags["--json"]) {
    console.log(JSON.stringify(summary, null, 2));
  } else {
    console.log(summary.answer || "(no answer text)");
    console.log(`\n${summary.model} · ${summary.page_tokens} page tokens · est. ${money(tokens)}`);
    statuses.forEach((entry) => console.log(`  ${entry.status.padEnd(7)} ${entry.url}`));
  }
  if (statuses.length === 0 || failed.length === statuses.length) {
    console.error("No URL could be read; the answer is not based on the pages.");
    process.exitCode = EXIT.unread;
  } else if (failed.length) {
    console.error(`Warning: ${failed.length} of ${statuses.length} URLs failed (${failed.map((entry) => entry.status).join(", ")}).`);
  }
}

async function runResearch(args) {
  const { flags, positional } = parseFlags(args, { booleans: ["--confirm-cost", "--max", "--keep", "--json"], values: [] });
  const brief = positional.join(" ").trim();
  if (!brief) throw new UsageError("research needs a brief.");
  if (!flags["--confirm-cost"]) {
    throw new UsageError(
      "Deep Research costs about $1 per task (measured) and up to $3 per task (documented); Max is documented at $3-7. " +
        "Get the user's explicit permission, then pass --confirm-cost.",
    );
  }
  const agent = flags["--max"] ? RESEARCH_AGENTS.max : RESEARCH_AGENTS.standard;
  // Background agent runs require store: true; the helper deletes the record after reading it.
  const started = await request("POST", "/interactions", { agent, input: brief, background: true, store: true });
  console.error(`Started ${agent} (${started.id}); polling every ${RESEARCH_POLL_MS / 1000}s...`);
  const deadline = Date.now() + RESEARCH_TIMEOUT_MS;
  let interaction = started;
  while (!["completed", "failed", "cancelled"].includes(interaction.status)) {
    if (Date.now() > deadline) throw new Error(`Deep Research did not finish within an hour; interaction ${started.id} was kept.`);
    await sleep(RESEARCH_POLL_MS);
    interaction = await request("GET", `/interactions/${started.id}`);
  }
  const report = (interaction.steps ?? [])
    .filter((step) => step.type === "model_output")
    .flatMap((step) => step.content ?? [])
    .filter((block) => block.type === "text")
    .map((block) => block.text)
    .join("\n");
  const usage = interaction.usage ?? {};
  const searches = (usage.grounding_tool_count ?? []).reduce((sum, tool) => sum + (tool.count ?? 0), 0);
  const summary = { agent, status: interaction.status, searches, usage, report };
  if (flags["--json"]) console.log(JSON.stringify(summary, null, 2));
  else {
    console.log(report || "(no report text)");
    console.log(`\n${agent} · ${interaction.status} · ${searches} searches · ${usage.total_input_tokens ?? "?"} input, ${usage.total_output_tokens ?? "?"} output, ${usage.total_thought_tokens ?? "?"} thinking tokens`);
  }
  if (!flags["--keep"]) await request("DELETE", `/interactions/${started.id}`);
  if (interaction.status !== "completed") process.exitCode = 1;
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
    case "research":
      return runResearch(rest);
    default:
      throw new UsageError(`Unknown command: ${command}. Run with --help.`);
  }
}

main().catch((error) => {
  console.error(error instanceof UsageError ? `ERROR: ${error.message}` : error.message);
  process.exit(error instanceof UsageError ? EXIT.usage : 1);
});
