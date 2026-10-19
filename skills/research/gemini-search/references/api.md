# Gemini search API contract

Official sources: [Grounding with Google Search](https://ai.google.dev/gemini-api/docs/google-search), [generateContent variant](https://ai.google.dev/gemini-api/docs/generate-content/google-search), [URL context](https://ai.google.dev/gemini-api/docs/url-context), [Pricing](https://ai.google.dev/gemini-api/docs/pricing), [Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits). "Live" notes are from the 2026-10-19 spike in `references/evidence.md`.

## Hosts and authentication

| Item | Value |
| --- | --- |
| Base URL | `https://generativelanguage.googleapis.com/v1beta` (the helper honours `GEMINI_API_ROOT` for tests) |
| Header | `x-goog-api-key: $GEMINI_API_KEY` |
| generateContent | `POST /models/{model}:generateContent` (stream: `:streamGenerateContent?alt=sse`) |
| Interactions | `POST /interactions`, `GET /interactions/{id}`, `DELETE /interactions/{id}` |

Google now recommends the Interactions API. The helper uses generateContent for search and read because it stores nothing and returns per-segment grounding data; use Interactions for structured output and agents.

## Tools

| Tool | generateContent | Interactions | Notes |
| --- | --- | --- | --- |
| Google Search | `{"google_search": {}}` | `{"type": "google_search"}` | Model decides whether and how often to search |
| URL context | `{"url_context": {}}` | `{"type": "url_context"}` | Up to 20 URLs in the prompt; 34 MB per URL |
| Both | list both | list both | The model may search and still not read the page; call `read` explicitly |

`google_search` accepts an undocumented `timeRangeFilter` without error but it had no observable effect; `excludeDomains` is rejected with `400 Unknown name`. `toolConfig.retrievalConfig` (`latLng`, `languageCode`) did not change web results; it targets Maps grounding. Older models used `google_search_retrieval`; current models reject it.

## generateContent grounding response

`candidates[0].groundingMetadata`:

| Field | Live notes |
| --- | --- |
| `webSearchQueries[]` | The queries run. Billing counts unique non-empty queries. Empty or missing means no search ran |
| `groundingChunks[].web` | `uri` is a `vertexaisearch.cloud.google.com/grounding-api-redirect/...` link; `title` is only the domain. Chunks repeat. A `HEAD` without following redirects returns the real URL in `Location`; links still resolved after an hour |
| `groundingSupports[]` | `segment.startIndex`/`endIndex` are **UTF-8 byte offsets** (character slicing fails on non-ASCII text); `groundingChunkIndices` link to chunks |
| `searchEntryPoint.renderedContent` | About 5 KB of HTML and CSS for Search Suggestions. Apps that show grounded results to end users must display it under the Gemini API terms |

`candidates[0].urlContextMetadata.urlMetadata[]` has `retrievedUrl` and `urlRetrievalStatus` (`URL_RETRIEVAL_STATUS_SUCCESS`, `..._ERROR`, `..._UNSAFE`). `usageMetadata.toolUsePromptTokenCount` counts page tokens from URL context. `modelVersion` names the model that actually ran (useful for `-latest` aliases).

## Interactions grounding response

`steps[]` contains `google_search_call` (`arguments.queries`), `google_search_result` (`search_suggestions` HTML), `thought`, and `model_output` with text `annotations` of type `url_citation` (`url`, `title`, `start_index`, `end_index`). URLs were redirect links here too, despite the docs example. `usage.grounding_tool_count: [{"type": "google_search", "count": N}]` reports billable searches directly.

Interactions are stored by default (`store: true`); pass `store: false` for one-off calls (no `id` is returned). Agents with `background: true` require `store: true`; delete them with `DELETE /interactions/{id}` after reading.

## Models (2026-10-19)

| Model | Search | URL context | USD per 1M tokens, Standard paid (input / output incl. thinking) | Live latency, one grounded answer |
| --- | --- | --- | --- | --- |
| `gemini-3.1-flash-lite` (default) | Yes | Yes | 0.25 / 1.50 | 2-5 s |
| `gemini-3.5-flash-lite` | Yes | Yes | 0.30 / 2.50 | 2-5 s |
| `gemini-3.8-flash`, `gemini-3.6-flash` | Yes | Yes | 0.75 / 3.75 until 2026-12-31, then 1.50 / 7.50 | 7-18 s |
| `gemini-3.1-pro-preview` (gated) | Yes | Yes | 2 / 12 (4 / 18 above 200k prompt tokens) | 18 s |
| `gemini-4-argon` (gated) | Yes | Yes | 2 / 10 until 2026-11-30, then 4 / 20; paid tier only | 15 s |
| `gemini-2.5-*` | 404 "no longer available to new users" | | | |

Aliases resolved live: `gemini-flash-lite-latest` → `gemini-3.5-flash-lite`, `gemini-flash-latest` → `gemini-3.8-flash`, `gemini-pro-latest` → `gemini-3.1-pro-preview`. Pin exact names.

`thinkingConfig.thinkingLevel`: Flash-Lite accepts `low`, `medium`, `high`; 3.8 Flash rejects `minimal`. Higher thinking on Flash-Lite made it skip search (see `references/gotchas.md`).

## Billing

- **Search (Gemini 3 and newer):** each executed query; 5,000 free per month shared across all Gemini 3+ models in the project, then $14 per 1,000. Not available on the free tier for most models.
- **Search content:** not billed as tokens (a grounded call reported 24 prompt tokens).
- **URL context:** no per-call fee; retrieved content bills as input tokens (one PostgreSQL release page was about 11,000 tokens; RFC 9110 was 91,622; 20 Wikipedia pages were 164,912).
- **Deep Research:** model tokens at list rates plus each search; see `references/expensive-routes.md`.
- The API does not return spend; check AI Studio usage. The helper's estimates use list prices.

## Rate limits

Limits are per project, by usage tier, visible in AI Studio. Paid tiers also have rolling 10-minute spend caps ($10 on Tier 1, $50 Tier 2, $200 Tier 3), returned as `429 RESOURCE_EXHAUSTED`. Live on this project: 250 simultaneous Flash-Lite requests and 30 simultaneous grounded calls all succeeded, so the test project sits on a high tier; lower tiers will throttle much sooner. Retry 429 and 5xx with backoff; never retry 400 or 404 unchanged.

## Errors seen

| Status | Example message | Meaning |
| --- | --- | --- |
| 400 | `Invalid JSON payload received. Unknown name "excludeDomains"` | Unsupported field |
| 400 | `Thinking level MINIMAL is not supported for this model` | Model-specific setting |
| 400 | `The value 'json_schema' is not supported for 'type' at 'response_format'` | Interactions `response_format` takes a plain JSON Schema |
| 404 | `This model models/gemini-2.5-flash is no longer available to new users` | Retired for new projects |
| 404 | `models/... is not found for API version v1beta` | Typo or unknown model |
| 429 | `RESOURCE_EXHAUSTED` | RPM, TPM, RPD, or spend limit |
