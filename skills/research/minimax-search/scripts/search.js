#!/usr/bin/env node
// Zero-dependency helper for MiniMax's Token Plan web search (POST /v1/coding_plan/search)
// and its quota endpoint (GET /v1/api/openplatform/coding_plan/remains).
// Limits and quirks enforced here are documented in references/api.md.

const BASE_URL = (process.env.MINIMAX_API_HOST || "https://api.minimax.io").replace(/\/+$/, "");
const REQUEST_TIMEOUT_MS = 30_000;

// The backend searches only the first 32 whitespace-separated words; later words,
// including trailing site: operators, are silently dropped.
const MAX_EFFECTIVE_WORDS = 32;
// More than 2,048 characters returns base_resp 1033 "system error".
const MAX_QUERY_CHARS = 2048;
// Throttles (1002 RPM, 2062 plan rate limit) are free and clear within about a minute.
const THROTTLE_CODES = new Set([1002, 2062]);
const DEFAULT_RETRIES = 3;
const RETRY_DELAYS_MS = [5_000, 15_000, 30_000];

function usage() {
  console.log(`MiniMax web search helper

Usage:
  node scripts/search.js "query"
  node scripts/search.js search "query"
  node scripts/search.js quota [--json]

Search flags:
  --site <domain>          Restrict to one domain (adds site:<domain>; MiniMax honours only one)
  --exclude-site <domain>  Exclude a domain (adds -site:<domain>; repeatable)
  --compact                Print JSON with title, link, date, snippet, and related searches
  --json                   Print the raw API response
  --urls                   Print one URL per line
  -n, --limit <n>          Max results to print (display only; the API returns up to 10)
  --retries <n>            Retries after a free rate-limit response (default: ${DEFAULT_RETRIES})
  -h, --help               Show help

Examples:
  node scripts/search.js "rust tokio select cancellation safety"
  node scripts/search.js --site github.com "tokio select cancellation"
  node scripts/search.js --compact "\\"cancel safety\\" tokio after:2026-01-01"
  node scripts/search.js quota
`);
}

class UsageError extends Error {}

class ApiError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

function takeValue(args, index, flag) {
  const value = args[index + 1];
  if (value === undefined || value.startsWith("--")) {
    throw new UsageError(`${flag} requires a value.`);
  }
  return value;
}

function parseCount(value, flag, { allowZero = false } = {}) {
  if (!/^\d+$/.test(value) || (!allowZero && Number(value) === 0)) {
    throw new UsageError(`${flag} must be a ${allowZero ? "non-negative" : "positive"} integer.`);
  }
  return Number(value);
}

function parseDomain(value, flag) {
  if (/\s/.test(value) || value.includes(":")) {
    throw new UsageError(`${flag} expects a bare domain such as github.com.`);
  }
  return value;
}

function parseSearchArgs(args) {
  const options = { output: "readable", limit: 10, site: undefined, excludedSites: [], retries: DEFAULT_RETRIES };
  const queryParts = [];

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    switch (arg) {
      case "--compact":
        options.output = "compact";
        break;
      case "--json":
        options.output = "json";
        break;
      case "--urls":
        options.output = "urls";
        break;
      case "-n":
      case "--limit":
        options.limit = parseCount(takeValue(args, index, arg), arg);
        index += 1;
        break;
      case "--retries":
        options.retries = parseCount(takeValue(args, index, arg), arg, { allowZero: true });
        index += 1;
        break;
      case "--site":
        if (options.site) {
          throw new UsageError("MiniMax honours only the first site: operator. Run one search per site instead.");
        }
        options.site = parseDomain(takeValue(args, index, arg), arg);
        index += 1;
        break;
      case "--exclude-site":
        options.excludedSites.push(parseDomain(takeValue(args, index, arg), arg));
        index += 1;
        break;
      default:
        if (arg.startsWith("--")) {
          throw new UsageError(`Unknown flag: ${arg}`);
        }
        queryParts.push(arg);
    }
  }

  const baseQuery = queryParts.join(" ").trim();
  if (!baseQuery) {
    // "" returns 1033 and whitespace returns unrelated pages, so reject both locally.
    throw new UsageError("search query is required and must contain non-whitespace text.");
  }
  const operators = [
    ...(options.site ? [`site:${options.site}`] : []),
    ...options.excludedSites.map((site) => `-site:${site}`),
  ];
  const query = [baseQuery, ...operators].join(" ");
  const characters = [...query].length;
  if (characters > MAX_QUERY_CHARS) {
    throw new UsageError(`query is ${characters} characters; MiniMax rejects more than ${MAX_QUERY_CHARS}.`);
  }
  const words = query.split(/\s+/).filter(Boolean).length;
  if (words > MAX_EFFECTIVE_WORDS) {
    throw new UsageError(
      `query has ${words} words; MiniMax searches only the first ${MAX_EFFECTIVE_WORDS} and silently drops the rest, including operators. Shorten it.`,
    );
  }
  return { query, options };
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function describeBaseResp(code, message) {
  switch (code) {
    case 1004:
    case 2049:
      return `${message}. Check MINIMAX_API_KEY and that MINIMAX_API_HOST matches its region (global keys use https://api.minimax.io).`;
    case 1002:
    case 2062:
      return `${message}. The plan allows roughly 50 searches per minute; wait about a minute.`;
    case 1033:
      return `${message}. MiniMax returns this for empty or over-${MAX_QUERY_CHARS}-character queries.`;
    case 2056:
      return `${message}. The 5-hour usage window is spent; run \`node scripts/search.js quota\`.`;
    default:
      return message;
  }
}

async function request(path, { method = "GET", body } = {}) {
  const apiKey = process.env.MINIMAX_API_KEY;
  if (!apiKey) {
    throw new UsageError("MINIMAX_API_KEY environment variable is required.");
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
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new ApiError(undefined, `MiniMax returned HTTP ${response.status} with a non-JSON body: ${text.slice(0, 200)}`);
  }
  // MiniMax reports most failures as HTTP 200 with a nonzero base_resp.status_code.
  const code = data.base_resp?.status_code;
  if (code !== undefined && code !== 0) {
    throw new ApiError(code, `MiniMax error ${code}: ${describeBaseResp(code, data.base_resp.status_msg)}`);
  }
  if (!response.ok) {
    throw new ApiError(undefined, `MiniMax returned HTTP ${response.status}: ${text.slice(0, 200)}`);
  }
  return data;
}

async function searchWithRetries(query, retries) {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await request("/v1/coding_plan/search", { method: "POST", body: { q: query } });
    } catch (error) {
      // 1027 is how MiniMax reports a search with no results.
      if (error instanceof ApiError && error.code === 1027) {
        return { organic: [], related_searches: [], noResults: true };
      }
      if (error instanceof ApiError && THROTTLE_CODES.has(error.code) && attempt < retries) {
        const delay = RETRY_DELAYS_MS[Math.min(attempt, RETRY_DELAYS_MS.length - 1)];
        console.error(`Rate limited (${error.code}); retrying in ${delay / 1000}s...`);
        await sleep(delay);
        continue;
      }
      throw error;
    }
  }
}

function printReadable(results, related) {
  results.forEach((result, index) => {
    console.log(`--- Result ${index + 1} ---`);
    console.log(`Title: ${result.title || "(no title)"}`);
    console.log(`URL: ${result.link || "(no url)"}`);
    if (result.date) console.log(`Date: ${result.date}`);
    console.log(`Snippet: ${result.snippet || "(none returned)"}`);
    console.log("");
  });
  if (related.length > 0) {
    console.log(`Related searches: ${related.join(" | ")}`);
  }
}

async function runSearch(args) {
  const { query, options } = parseSearchArgs(args);
  const data = await searchWithRetries(query, options.retries);

  if (options.output === "json") {
    console.log(JSON.stringify(data, null, 2));
    return;
  }
  const results = (Array.isArray(data.organic) ? data.organic : []).slice(0, options.limit);
  const related = (Array.isArray(data.related_searches) ? data.related_searches : []).map((item) => item.query).filter(Boolean);

  if (options.output === "compact") {
    const compact = results.map(({ title, link, date, snippet }) => ({ title, link, date: date || null, snippet }));
    console.log(JSON.stringify({ query, results: compact, related_searches: related }, null, 2));
    return;
  }
  if (results.length === 0) {
    console.error("No results returned (MiniMax reports this as error 1027).");
    return;
  }
  if (options.output === "urls") {
    results.forEach((result) => result.link && console.log(result.link));
    return;
  }
  printReadable(results, related);
}

function formatDuration(ms) {
  const minutes = Math.max(0, Math.round(ms / 60_000));
  return minutes >= 60 ? `${Math.floor(minutes / 60)}h ${minutes % 60}m` : `${minutes}m`;
}

async function runQuota(args) {
  const data = await request("/v1/api/openplatform/coding_plan/remains");
  if (args.includes("--json")) {
    console.log(JSON.stringify(data, null, 2));
    return;
  }
  const general = (data.model_remains || []).find((entry) => entry.model_name === "general");
  if (!general) {
    console.log("No 'general' usage bucket returned; this key may not have a Token Plan. Use --json to inspect.");
    return;
  }
  console.log("MiniMax Token Plan quota (web search draws from the 'general' bucket)");
  console.log(
    `5-hour window: ${general.current_interval_remaining_percent}% remaining, resets in ${formatDuration(general.remains_time)} (${new Date(general.end_time).toISOString()})`,
  );
  console.log(
    `Weekly window: ${general.current_weekly_remaining_percent}% remaining, resets in ${formatDuration(general.weekly_remains_time)}`,
  );
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 0 || args.includes("-h") || args.includes("--help")) {
    usage();
    return;
  }
  const [command, ...rest] = args;
  if (command === "quota" || command === "quotas") {
    await runQuota(rest);
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
