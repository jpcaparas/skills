# Gemini search gotchas

Each item was observed live on 2026-10-19 unless marked as documented only.

## The model may not search at all

Grounding is a tool the model may decline. Flash-Lite skipped search on 1 of 5 identical runs, on every trivial prompt ("What is 17*23?"), and on a 50-country central-bank question, where it answered all 50 lines from memory with confident 2026 dates. No error is raised: `webSearchQueries` is simply missing.

Always check the query count. The helper's forcing system instruction ("always search before answering") fixed every skip in testing, and exit code 3 flags any that remain.

## More thinking can mean less searching

On `gemini-3.1-flash-lite`, `thinkingLevel: high` skipped search (0 queries) in all three runs, including with "Search the web before answering" in the prompt and with a forcing system instruction. `low` also skipped once; `medium` searched. Leave thinking at the model default for grounded calls.

## Large lists fan out or go ungrounded

| Request | Model | Queries | Result |
| --- | --- | --- | --- |
| 20 projects' latest versions | 3.1 Flash-Lite | 20 | All grounded; one date wrong; $0.28 in queries |
| Same | 3.8 Flash | 25 | More precise, 58 s |
| 50 countries' rates, no forcing | 3.1 Flash-Lite | 0 | Entirely from memory |
| Same, forced | 3.5 Flash-Lite / 3.8 Flash / 3.1 Flash-Lite | 32 / 29 / 1 | The last found one aggregate page |
| 100 npm packages, forced | 3.5 Flash-Lite | 15 | 15 of 100 lines grounded; rest guessed ("vitest: 3.x") |

Split list questions into calls of about five items, and check coverage.

## Caps are suggestions

A system instruction capping queries is respected most of the time (23 of 24 capped runs; 3.1 Flash-Lite went from 4 queries to 1 with a cap of 1), but 3.8 Flash ignored a cap of 1. There is no hard limit parameter. The helper warns when the cap was exceeded.

## JSON mode hides grounding on generateContent

With `responseMimeType: application/json` and a `responseSchema`, Flash-Lite still searched (its answer cited a page published that day) but returned **no** `groundingMetadata`, so queries, billing, and sources are invisible. Use the Interactions API with `response_format` set to a plain JSON Schema instead: it returned search steps and `grounding_tool_count`. Expect more queries there (6 on two uncapped runs for a one-fact question that took 2 in prose). Or ask for prose first and extract fields locally.

## 21 URLs fail every URL silently

URL context documents a 20-URL limit. With 21, the call returned HTTP 200, every URL showed `URL_RETRIEVAL_STATUS_ERROR`, and the model wrote "approximate" figures from memory. The helper refuses more than 20.

## Failed URLs still return 200

404 pages, localhost, and dead hosts come back as `ERROR` statuses inside a successful response; the answer text may explain or may guess. Check `urlMetadata`. Even within 20 URLs, one Wikipedia page failed intermittently.

## YouTube "succeeds" without the video

A YouTube URL returned `SUCCESS` and a plausible summary from about 1,500 tokens of page metadata. The docs say video content is unsupported; use video understanding instead.

## Combining search and URL context does not guarantee reading

With both tools enabled and "read it" in the prompt, the model searched but never used URL context. Find URLs with `search`, then pass the chosen ones to `read`.

## Sources are redirect links titled by domain

`groundingChunks[].web.uri` and Interactions `url_citation.url` are `vertexaisearch.cloud.google.com/grounding-api-redirect/...` links with titles such as `python.org`. Resolve with a `HEAD` request that does not follow redirects; the helper does this and deduplicates (chunks repeat).

## Support offsets are bytes

`groundingSupports[].segment` offsets are UTF-8 byte offsets. Slicing the answer string by them misplaces citations after any non-ASCII character (2 of 2 segments matched as bytes, 0 of 2 as characters, in a text with ü and €).

## Location and date filters do nothing visible

`toolConfig.retrievalConfig.latLng` (Auckland, Berlin) and `languageCode: de-DE` left savings-rate answers US-centric. `timeRangeFilter` is accepted but a 2020-only window still returned 2025 pages. Put the region and date window in the question ("in New Zealand", "published since 2026-10-12, today is 2026-10-19").

## `site:` works from the prompt

There is no domain parameter (`excludeDomains` is rejected), but "Use only sources from site:docs.rs" made the model write `site:` queries, and every resolved source was on docs.rs. The helper adds the instruction with `--site` and flags off-site sources.

## Deep Research reports can carry stale facts

The measured Deep Research report listed Gemini 2.5 grounding pricing as a current option, but those models return 404 for new users. Verify consequential claims in agent reports.

## Interactions are stored unless told otherwise

`POST /interactions` stores the interaction by default and returns an `id` you can fetch later. Pass `store: false` for one-off calls; background agents require storage, so delete them after reading.
