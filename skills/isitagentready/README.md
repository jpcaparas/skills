# isitagentready

Portable production skill for auditing a repository against Cloudflare's agent-readiness signals and writing a local markdown report packet.

## What It Covers

- the Cloudflare `isitagentready.com` signal inventory and score boundaries
- browser-first live-site verification when a production URL and browser tooling exist
- repository inspection for `.well-known` documents, headers, robots rules, markdown negotiation, OAuth discovery, MCP or A2A discovery, WebMCP, and optional commerce signals
- deterministic report-packet creation with `agent-readiness-report.md`, `sources.md`, and `metadata.json`
- optional retrieval of the official live scan JSON for the deployed site

## Key Files

- `SKILL.md` for the authoritative instructions
- `references/methodology.md` for the end-to-end audit order
- `references/signal-map.md` for the full Cloudflare signal inventory
- `references/runtime-and-browser.md` for the production URL and browser-first flow
- `references/repo-search-playbook.md` for surgical repo search heuristics
- `references/report-format.md` for the report contract
- `templates/agent-readiness-report.md` for the report shell
- `scripts/create_report_packet.py` to scaffold the local report folder
- `scripts/scan_site.py` to fetch the official live scan JSON
