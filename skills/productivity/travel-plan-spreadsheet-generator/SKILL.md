---
name: travel-plan-spreadsheet-generator
description: "Builds an editable .xlsx travel workbook (bookings, daily plan, options, prep, pack and buy lists, sources) from messy trip inputs such as PDFs, screenshots or booking notes. Not for prose itineraries, recommendation chat or calendar-only scheduling."
compatibility: "Requires python3 with openpyxl. Optional - a spreadsheet renderer (for example @oai/artifact-tool) for a visual check."
---

# Travel plan workbook

The layout is deterministic and lives in code; the planning judgment is yours. Never improvise sheet order, merges, widths, formulas, validations or styling by hand: build with the script. If the user wants a layout or feature the builder does not support, say so and propose a scoped extension; do not invent flags or claim the validator certifies a different shape.

Read first, ask second. Extract everything from the user's PDFs, screenshots, notes and bookings before asking anything, and if the harness offers a spreadsheet skill, load it before spreadsheet work.

## Workflow

1. Extract facts, then split what is missing into blockers and non-blockers. Blockers make the workbook materially wrong: no usable dates, no destination or base, no way to determine the traveller set when booking coverage depends on it, a route or commitment conflict that makes the daily plan nonsense, a missing departure or return boundary. Ask for blockers in one short batch, stating what you already inferred so the user can correct it. Do not re-ask answered questions, and do not guess a critical fact to avoid asking. Follow up later only for a materially new safety or correctness issue (e.g. a transit visa that appears mid-research). Budgets, restaurant choices, flexible-day lean and per-person attraction coverage are not blockers: proceed with explicit assumptions and visible review flags.
2. Verify volatile facts that affect this trip (see Research), then build the trip model as JSON following `templates/trip_model_schema.json`, with assumptions, sources, review flags and shopping objectives recorded. Read `references/trip-model.md` for fields and normalisation.
3. Build: `python3 scripts/build_workbook.py --trip-model model.json [--output path.xlsx]`. `scripts/example_trip_model.json` is a complete sample.
4. Validate: `python3 scripts/validate_workbook.py out.xlsx --trip-model model.json`. Use a renderer for a visual pass if one exists; otherwise `python3 scripts/render_check.py out.xlsx` flags likely clipping and spillover.
5. Hand over the workbook with a short summary of open flags, assumptions and what the user still has to confirm.

Read `references/workbook-spec.md` for the exact sheet architecture, filename rule and formulas, and `references/mapping-rules.md` for what belongs on which sheet.

## Planning judgment

- Assume the whole group travels together unless evidence says otherwise. When only part of the group is booked, build split fallbacks and flags rather than pretending coverage exists.
- Never silently flatten contradictions (hotel says 3 adults but plan assumes 4, flight covers 2 travellers, tickets cover part of the group, pasted weekdays from another year). Make them review flags, repeated in Overview, Bookings, Prep & Compliance and the Daily Plan when they change the day.
- Shopping stays visible in the Daily Plan, the destination options bank and the Buy List, not buried in a notes field. Pack List is what physically travels; Buy List is what is still to be bought or watched.
- Keep days geographically sane: one or two neighbourhood clusters a day, light arrival and return days, no cross-city zig-zags.
- Prep & Compliance holds only tasks that matter for this route, passports, medicines and commitments. No generic health scares or filler admin.
- The architecture is general; adapt destination-specific text and status labels instead of assuming Tokyo.

## Research

For current or future trips, verify what the plan depends on: visa and entry rules by passport, transit requirements, customs or immigration tooling, airline check-in windows, baggage and dangerous-goods rules (medicines, batteries, power banks), health guidance, medicine import rules, and conference or event dates. Use official sources first (government, border, airline, official event and venue pages); a secondary source only points you to the official one. Use exact dates in notes, and load `temporal-awareness` if available. Every source that influenced the workbook goes in the Sources sheet with type, name, plain-text URL or file note, what it was used for, last-checked date and a practical note.
