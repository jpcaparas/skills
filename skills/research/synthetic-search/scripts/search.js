#!/usr/bin/env node

const BASE_URL = "https://api.synthetic.new/v2";

function usage() {
  console.log(`Synthetic Search helper

Usage:
  node scripts/search.js "query"
  node scripts/search.js search "query"
  node scripts/search.js quotas

Search flags:
  --content           Include truncated content blocks
  --chars <n>         Max characters for --content output (default: 5000)
  -n, --limit <n>     Max results to display locally (default: 5)
  --json              Print raw JSON response
  --urls              Print one URL per line
  --titles            Print title and URL separated by a tab
  -h, --help          Show help

Quota flags:
  --json              Print raw quota JSON

Examples:
  node scripts/search.js "rust async await"
  node scripts/search.js --content --limit 3 --chars 1200 "rust async await"
  node scripts/search.js --urls "nix flake tutorial"
  node scripts/search.js quotas --json
`);
}

function ensureApiKey() {
  const apiKey = process.env.SYNTHETIC_API_KEY;
  if (!apiKey) {
    console.error("ERROR: SYNTHETIC_API_KEY environment variable is required.");
    process.exit(1);
  }
  return apiKey;
}

function takeValue(args, index, flag) {
  if (!args[index + 1]) {
    console.error(`ERROR: ${flag} requires a value.`);
    process.exit(1);
  }
  return args[index + 1];
}

function parsePositiveInt(value, flag) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    console.error(`ERROR: ${flag} must be a positive integer.`);
    process.exit(1);
  }
  return parsed;
}

async function requestJson(path, { method = "GET", body } = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${ensureApiKey()}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

  const text = await response.text();
  if (!response.ok) {
    console.error(`Synthetic API error: ${response.status} ${response.statusText}`);
    if (text) {
      console.error(text);
    } else {
      console.error("(empty response body)");
    }
    process.exit(1);
  }

  return text ? JSON.parse(text) : {};
}

function printSearchResults(results, options) {
  if (options.urls) {
    for (const result of results) {
      if (result.url) {
        console.log(result.url);
      }
    }
    return;
  }

  if (options.titles) {
    for (const result of results) {
      console.log(`${result.title || "(no title)"}\t${result.url || ""}`);
    }
    return;
  }

  for (let index = 0; index < results.length; index += 1) {
    const result = results[index];
    const text = (result.text || "").replace(/\s+/g, " ").trim();
    const snippet = text.slice(0, 300);

    console.log(`--- Result ${index + 1} ---`);
    console.log(`Title: ${result.title || "(no title)"}`);
    console.log(`URL: ${result.url || "(no url)"}`);
    console.log(`Published: ${result.published || "(not returned by API)"}`);
    console.log(`Snippet: ${snippet}${text.length > 300 ? "..." : ""}`);

    if (options.content && text) {
      const content = text.slice(0, options.maxChars);
      console.log(`Content:\n${content}${text.length > options.maxChars ? "\n...(truncated)" : ""}`);
    }

    console.log("");
  }
}

async function runSearch(args) {
  const options = {
    content: false,
    json: false,
    urls: false,
    titles: false,
    maxChars: 5000,
    limit: 5,
  };
  const queryParts = [];

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    switch (arg) {
      case "--content":
        options.content = true;
        break;
      case "--json":
        options.json = true;
        break;
      case "--urls":
        options.urls = true;
        break;
      case "--titles":
        options.titles = true;
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
      case "-h":
      case "--help":
        usage();
        process.exit(0);
        break;
      default:
        queryParts.push(arg);
        break;
    }
  }

  const query = queryParts.join(" ").trim();
  if (!query) {
    console.error("ERROR: search query is required.");
    usage();
    process.exit(1);
  }

  const data = await requestJson("/search", {
    method: "POST",
    body: { query },
  });

  if (options.json) {
    console.log(JSON.stringify(data, null, 2));
    return;
  }

  const results = Array.isArray(data.results) ? data.results.slice(0, options.limit) : [];
  if (results.length === 0) {
    console.error("No results found.");
    return;
  }

  printSearchResults(results, options);
}

function formatQuotaLine(label, used, limit, renewsAt) {
  return `${label}: ${used}/${limit}${renewsAt ? ` (renews ${renewsAt})` : ""}`;
}

async function runQuotas(args) {
  const jsonMode = args.includes("--json");
  if (args.includes("-h") || args.includes("--help")) {
    usage();
    process.exit(0);
  }

  const data = await requestJson("/quotas");
  if (jsonMode) {
    console.log(JSON.stringify(data, null, 2));
    return;
  }

  const subscription = data.subscription || {};
  const hourly = data.search?.hourly || {};
  const weekly = data.weeklyTokenLimit || {};
  const rolling = data.rollingFiveHourLimit || {};

  console.log("Synthetic quota summary");
  console.log(formatQuotaLine("Subscription", subscription.requests ?? "?", subscription.limit ?? "?", subscription.renewsAt));
  console.log(formatQuotaLine("Search hourly", hourly.requests ?? "?", hourly.limit ?? "?", hourly.renewsAt));
  console.log(`Rolling five-hour: ${rolling.remaining ?? "?"}/${rolling.max ?? "?"}${rolling.limited === true ? " (limited)" : ""}`);
  if (weekly.remainingCredits || weekly.maxCredits) {
    console.log(`Weekly credits: ${weekly.remainingCredits || "?"}/${weekly.maxCredits || "?"}`);
  }
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 0 || args.includes("-h") || args.includes("--help")) {
    usage();
    return;
  }

  const [maybeCommand, ...rest] = args;
  if (maybeCommand === "quotas") {
    await runQuotas(rest);
    return;
  }
  if (maybeCommand === "search") {
    await runSearch(rest);
    return;
  }

  await runSearch(args);
}

main().catch((error) => {
  console.error(`Error: ${error.message}`);
  process.exit(1);
});
