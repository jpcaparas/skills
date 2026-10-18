#!/usr/bin/env node
// Zero-dependency helper for Synthetic's /v2/search and /v2/quotas endpoints.
// Limits and quirks enforced here are documented in references/api.md.

const BASE_URL = (process.env.SYNTHETIC_API_BASE_URL || "https://api.synthetic.new/v2").replace(/\/+$/, "");
const REQUEST_TIMEOUT_MS = 30_000;

// Synthetic silently ignores everything after the first 4,096 characters of `query`,
// including trailing site: operators, so longer queries are rejected locally.
const MAX_EFFECTIVE_QUERY_CHARS = 4096;
const DEFAULT_HIGHLIGHT_CHARS = 1200;
const DEFAULT_TEXT_CHARS = 5000;

function usage() {
  console.log(`Synthetic Search helper

Usage:
  node scripts/search.js "query"
  node scripts/search.js search "query"
  node scripts/search.js quotas [--json]

Search flags:
  --site <domain>          Restrict results (adds site:<domain>; repeat for a union)
  --exclude-site <domain>  Exclude a domain or path (adds -site:<domain>; repeatable)
  --compact                Print JSON with url, title, published, highlights only
  --text, --content        Include each page's full text, truncated to --chars
  --chars <n>              Max characters per highlight/text block (default: ${DEFAULT_HIGHLIGHT_CHARS} / ${DEFAULT_TEXT_CHARS})
  -n, --limit <n>          Max results to print (display only; the API always returns 5)
  --json                   Print the raw API response (often 50-600 KB)
  --urls                   Print one URL per line
  --titles                 Print title and URL separated by a tab
  --save <file>            Also write the raw API response to <file>
  -h, --help               Show help

Examples:
  node scripts/search.js "rust tokio select cancellation safety"
  node scripts/search.js --site docs.rs --site github.com "tokio select cancellation"
  node scripts/search.js --compact --save /tmp/results.json "httpx retry transport"
  node scripts/search.js quotas
`);
}

class UsageError extends Error {}

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function takeValue(args, index, flag) {
  const value = args[index + 1];
  if (value === undefined || value.startsWith("--")) {
    throw new UsageError(`${flag} requires a value.`);
  }
  return value;
}

function parsePositiveInt(value, flag) {
  if (!/^\d+$/.test(value) || Number(value) <= 0) {
    throw new UsageError(`${flag} must be a positive integer.`);
  }
  return Number(value);
}

function parseDomain(value, flag) {
  if (/\s/.test(value) || value.includes(":")) {
    throw new UsageError(`${flag} expects a bare domain or domain/path, such as github.com or github.com/tokio-rs.`);
  }
  return value;
}

function parseSearchArgs(args) {
  const options = {
    output: "readable",
    includeText: false,
    maxChars: undefined,
    limit: 5,
    sites: [],
    excludedSites: [],
    savePath: undefined,
  };
  const queryParts = [];

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    switch (arg) {
      case "--text":
      case "--content":
        options.includeText = true;
        break;
      case "--json":
        options.output = "json";
        break;
      case "--compact":
        options.output = "compact";
        break;
      case "--urls":
        options.output = "urls";
        break;
      case "--titles":
        options.output = "titles";
        break;
      case "--chars":
        options.maxChars = parsePositiveInt(takeValue(args, index, arg), arg);
        index += 1;
        break;
      case "-n":
      case "--limit":
        options.limit = parsePositiveInt(takeValue(args, index, arg), arg);
        index += 1;
        break;
      case "--site":
        options.sites.push(parseDomain(takeValue(args, index, arg), arg));
        index += 1;
        break;
      case "--exclude-site":
        options.excludedSites.push(parseDomain(takeValue(args, index, arg), arg));
        index += 1;
        break;
      case "--save":
        options.savePath = takeValue(args, index, arg);
        index += 1;
        break;
      default:
        if (arg.startsWith("--")) {
          throw new UsageError(`Unknown flag: ${arg}`);
        }
        queryParts.push(arg);
        break;
    }
  }

  const operators = [
    ...options.sites.map((site) => `site:${site}`),
    ...options.excludedSites.map((site) => `-site:${site}`),
  ];
  const baseQuery = queryParts.join(" ").trim();
  if (!baseQuery) {
    // Synthetic answers "" with a blank 500 and whitespace with unrelated news; both cost quota.
    throw new UsageError("search query is required and must contain non-whitespace text.");
  }
  const query = [baseQuery, ...operators].join(" ");
  if (query.length > MAX_EFFECTIVE_QUERY_CHARS) {
    throw new UsageError(
      `query is ${query.length} characters; Synthetic ignores everything after ${MAX_EFFECTIVE_QUERY_CHARS}. Shorten it or split it into several searches.`,
    );
  }
  return { query, options };
}

function errorHint(status, text) {
  if (status === 401) {
    return "Check that SYNTHETIC_API_KEY is valid and sent as 'Authorization: Bearer <key>'.";
  }
  if (status === 429) {
    return "The hourly search quota is spent. Stop searching until it renews; retries will keep failing.";
  }
  if (status >= 500 && !text) {
    return "Synthetic returns blank 500s for empty or oversized queries and invalid JSON; these still count against the hourly search quota.";
  }
  return undefined;
}

async function requestJson(path, { method = "GET", body } = {}) {
  const apiKey = process.env.SYNTHETIC_API_KEY;
  if (!apiKey) {
    throw new UsageError("SYNTHETIC_API_KEY environment variable is required.");
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${apiKey}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });

  const text = await response.text();
  if (!response.ok) {
    const lines = [`Synthetic API error: HTTP ${response.status}`, text || "(empty response body)"];
    const hint = errorHint(response.status, text);
    if (hint) lines.push(`Hint: ${hint}`);
    throw new ApiError(response.status, lines.join("\n"));
  }

  return { data: text ? JSON.parse(text) : {}, rawText: text };
}

function truncate(text, maxChars) {
  return text.length > maxChars ? `${text.slice(0, maxChars)}...(truncated)` : text;
}

function compactResult(result) {
  return {
    url: result.url,
    title: result.title || null,
    published: result.published || null,
    highlights: Array.isArray(result.highlights) ? result.highlights : [],
  };
}

function printReadable(results, options) {
  const highlightChars = options.maxChars ?? DEFAULT_HIGHLIGHT_CHARS;
  const textChars = options.maxChars ?? DEFAULT_TEXT_CHARS;

  results.forEach((result, index) => {
    console.log(`--- Result ${index + 1} ---`);
    console.log(`Title: ${result.title || "(no title)"}`);
    console.log(`URL: ${result.url || "(no url)"}`);
    if (result.published) {
      console.log(`Published: ${result.published}`);
    }
    const highlight = (Array.isArray(result.highlights) ? result.highlights.join("\n...\n") : "").trim();
    console.log(`Highlight:\n${highlight ? truncate(highlight, highlightChars) : "(none returned)"}`);
    if (options.includeText) {
      const text = (result.text || "").trim();
      console.log(`Text (${text.length} chars):\n${truncate(text, textChars)}`);
    }
    console.log("");
  });
}

// Synthetic sends no Retry-After header, so look up the renewal time from the free /quotas call.
async function explainQuotaExhaustion(error) {
  if (error instanceof ApiError && error.status === 429) {
    const renewsAt = await requestJson("/quotas")
      .then(({ data }) => data.search?.hourly?.renewsAt)
      .catch(() => undefined);
    if (renewsAt) error.message += `\nSearch quota renews at ${renewsAt}.`;
  }
  throw error;
}

async function runSearch(args) {
  const { query, options } = parseSearchArgs(args);
  const { data, rawText } = await requestJson("/search", { method: "POST", body: { query } }).catch(
    explainQuotaExhaustion,
  );

  if (options.savePath) {
    const { writeFileSync } = await import("node:fs");
    writeFileSync(options.savePath, rawText);
    console.error(`Saved raw response to ${options.savePath}`);
  }

  if (options.output === "json") {
    console.log(JSON.stringify(data, null, 2));
    return;
  }

  const results = (Array.isArray(data.results) ? data.results : []).slice(0, options.limit);
  if (results.length === 0) {
    console.error("No results returned.");
    return;
  }

  switch (options.output) {
    case "compact":
      console.log(JSON.stringify({ query, results: results.map(compactResult) }, null, 2));
      break;
    case "urls":
      results.forEach((result) => result.url && console.log(result.url));
      break;
    case "titles":
      results.forEach((result) => console.log(`${result.title || "(no title)"}\t${result.url || ""}`));
      break;
    default:
      printReadable(results, options);
  }
}

function formatWindow(label, bucket) {
  if (!bucket) return `${label}: (not returned)`;
  const renews = bucket.renewsAt ? ` (renews ${bucket.renewsAt})` : "";
  return `${label}: ${bucket.requests ?? "?"}/${bucket.limit ?? "?"} used${renews}`;
}

async function runQuotas(args) {
  const { data } = await requestJson("/quotas");
  if (args.includes("--json")) {
    console.log(JSON.stringify(data, null, 2));
    return;
  }

  const rolling = data.rollingFiveHourLimit;
  const weekly = data.weeklyTokenLimit;
  console.log("Synthetic quota summary");
  console.log(formatWindow("Search (hourly)", data.search?.hourly));
  console.log(formatWindow("Subscription requests", data.subscription));
  if (rolling) {
    console.log(`Rolling five-hour: ${rolling.remaining ?? "?"}/${rolling.max ?? "?"} remaining${rolling.limited ? " (limited)" : ""}`);
  }
  if (weekly) {
    console.log(`Weekly credits: ${weekly.remainingCredits ?? "?"} of ${weekly.maxCredits ?? "?"} remaining`);
  }
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 0 || args.includes("-h") || args.includes("--help")) {
    usage();
    return;
  }

  const [command, ...rest] = args;
  if (command === "quotas") {
    await runQuotas(rest);
  } else if (command === "search") {
    await runSearch(rest);
  } else {
    await runSearch(args);
  }
}

main().catch((error) => {
  console.error(error instanceof UsageError ? `ERROR: ${error.message}` : error.message);
  process.exit(error instanceof UsageError ? 2 : 1);
});
