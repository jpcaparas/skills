---
name: travel-plan-spreadsheet-generator
description: "Generate a polished `.xlsx` travel itinerary workbook when the user wants a travel itinerary spreadsheet, trip planner workbook, travel planner xlsx, trip spreadsheet, itinerary workbook, travel prep spreadsheet, travel shopping tracker, holiday itinerary spreadsheet, conference travel spreadsheet, or messy travel docs turned into a workbook. Use when the output must be an editable Excel workbook with bookings, daily plans, prep/compliance, packing, buying, and sources. Triggers on: 'travel-plan-generator', 'travel itinerary spreadsheet', 'travel planner xlsx', 'trip spreadsheet', 'itinerary workbook', 'travel prep spreadsheet', 'travel shopping tracker', 'holiday itinerary spreadsheet', 'conference travel spreadsheet'. Do NOT trigger for plain prose itineraries, simple travel recommendations, casual things-to-do chat, or calendar scheduling without workbook generation."
compatibility: "Requires: python3 with openpyxl. Optional: @oai/artifact-tool or an equivalent spreadsheet renderer for visual verification."
references:
  - workbook-spec
  - intake-protocol
  - research-policy
  - trip-model
  - mapping-rules
  - gotchas
  - cross-harness-notes
---

# travel-plan-spreadsheet-generator

Turn messy travel inputs into a calm, editable `.xlsx` workbook with deterministic structure and pragmatic trip-planning judgment.

## Decision Tree

What did the user actually ask for?

- The user wants an editable workbook, spreadsheet, tracker, or `.xlsx`
  Use this skill.

- The user gave PDFs, screenshots, notes, bookings, shopping asks, or conference constraints
  Extract everything you can first. Do not ask questions that the attachments already answer.

- The request is missing material facts that would make the workbook wrong
  Ask exactly one consolidated intake batch. Group it as `Required to proceed`, `Useful but optional`, and `Documents or screenshots that would improve accuracy`. Read `references/intake-protocol.md`.

- The request has non-blocking ambiguity
  Proceed with explicit assumptions and visible review flags. Do not stop the build just to perfect every detail.

- The user only wants prose, lightweight recommendations, or a casual itinerary chat
  Do not use this skill as the primary tool.

- You are in an OpenAI or Codex-style environment and `/home/oai/skills/spreadsheets/SKILL.md` exists
  Read that file before spreadsheet work, then continue with this skill's workbook-specific rules.

## Quick Reference

| Need | Read or run | Why |
| --- | --- | --- |
| One-batch intake discipline | `references/intake-protocol.md` | Prevent drip-fed questioning |
| Deterministic workbook contract | `references/workbook-spec.md` | Sheet order, widths, merges, formulas, palette |
| Canonical trip model fields | `references/trip-model.md` | Build the internal model before writing cells |
| Field-to-sheet mapping | `references/mapping-rules.md` | Keep Pack vs Buy vs Prep clean |
| Volatile travel research rules | `references/research-policy.md` | Verify visas, transit, medicine, conference dates, and other unstable facts |
| Build the workbook | `python3 scripts/build_workbook.py --trip-model /path/to/model.json` | Generate the `.xlsx` artifact |
| Validate the workbook | `python3 scripts/validate_workbook.py /path/to/output.xlsx --trip-model /path/to/model.json` | Check structure, formulas, validations, and row patterns |
| Visual-risk scan | `python3 scripts/render_check.py /path/to/output.xlsx` | Catch likely clipping or spillover when a renderer is unavailable |
| Review packaging and sample build | `python3 scripts/test_skill.py /path/to/skill` | Run the local functional smoke test |

## Operating Rules

1. Start with extraction, not interrogation. Read the user's PDFs, screenshots, pasted notes, flight details, hotel confirmations, shopping asks, and fixed commitments before asking anything.
2. Separate blockers from non-blockers. If essential trip facts are still missing, ask one consolidated clarification batch and only one batch unless the user later changes scope.
3. Build a canonical trip model before touching the workbook. Use `templates/trip_model_schema.json` and `references/trip-model.md`.
4. Keep the deterministic and heuristic layers separate:
   - Use `scripts/build_workbook.py` for filename strategy, sheet order, merges, widths, formulas, validations, fills, fonts, borders, and fixed row patterns.
   - Use judgment for extracting messy facts, reconciling contradictions, deciding pace, keeping shopping visible, pruning absurd plans, and deciding when split plans are required.
5. Default to the whole group staying together unless the evidence clearly says otherwise. When only part of the group is booked, create split fallbacks and visible review flags instead of pretending coverage exists.
6. Keep shopping visible across the workbook. It belongs in Daily Plan, the destination options bank, and Buy List when relevant.
7. Research only what matters for this trip. Verify future or current entry rules, transit constraints, medicine rules, airline check-in windows, and event dates from official sources when they materially affect the plan.
8. Do not silently flatten contradictions. A mismatch between traveller count and booking coverage must surface in Overview, Bookings, Prep & Compliance, and the Daily Plan when it changes the day's shape.
9. Treat the workbook as the deliverable. After building it, run `scripts/validate_workbook.py`. If a renderer such as `@oai/artifact-tool` is available, do a visual pass before hand-off.

## Intake Protocol

Ask nothing if the message and attachments already cover the essentials.

If a clarification batch is necessary, use this exact grouping and keep it short:

```text
Required to proceed
- ...

Useful but optional
- ...

Documents or screenshots that would improve accuracy
- ...
```

Cover these only when relevant and still missing: trip name or destination, start/end dates, departure and final home arrival, cities or bases, traveller list and roles, passport nationalities when immigration matters, flights and transit, accommodation, fixed bookings, conference or family commitments, budget sensitivity, pace, mobility constraints, dietary constraints, shopping goals and requesters, group split patterns, pre-departure and recovery-day preference, official prep tasks, and preferred output filename.

Read `references/intake-protocol.md` for the full checklist, blocker logic, and wording rules.

## Build Workflow

1. Extract facts from the user's files and notes.
2. Run only the one required clarification batch if blockers remain.
3. Build the canonical trip model and record assumptions, sources, review flags, and shopping objectives explicitly.
4. Verify volatile facts that matter. Read `references/research-policy.md`.
5. Run `scripts/build_workbook.py` to generate the workbook.
6. Run `scripts/validate_workbook.py` on the generated `.xlsx`.
7. If `@oai/artifact-tool` or another renderer is available, render each sheet for a quick visual check. Otherwise run `scripts/render_check.py` for a structural visual-risk pass.
8. Hand over the workbook with a short summary of open flags, assumptions, and anything the user still needs to confirm.

## Deterministic vs Heuristic Boundary

| Deterministic builder responsibilities | Heuristic planner responsibilities |
| --- | --- |
| Workbook filename strategy | Extract facts from messy PDFs, screenshots, and notes |
| Sheet order and naming | Decide when contradictory evidence becomes a blocker |
| Merged ranges, widths, row heights, fills, borders, fonts | Reconcile conflicting traveller counts or date references |
| Column headers and validation lists | Choose realistic neighbourhood clusters and fallbacks |
| Formula generation and cross-sheet references | Protect conference or work anchors without wrecking the family plan |
| Status vocab and chip styling | Decide when split plans are necessary because coverage is partial |
| Source logging structure | Decide what belongs in Prep vs Pack vs Buy |
| One-day-before and one-day-after planner window | Prune absurd routes, overpacked days, or cross-city zig-zags |

Do not improvise the deterministic layer in prose. Use the builder script.

## Reading Guide

| Task | Read |
| --- | --- |
| Exact workbook architecture, merges, counters, naming rules | `references/workbook-spec.md` |
| Intake questions, blockers, and one-batch discipline | `references/intake-protocol.md` |
| Source verification, official-source priority, and what to research | `references/research-policy.md` |
| Canonical model fields and normalization rules | `references/trip-model.md` |
| Sheet-mapping and categorization rules | `references/mapping-rules.md` |
| Failure modes and anti-patterns | `references/gotchas.md` |
| Portability and spreadsheet-runtime notes | `references/cross-harness-notes.md` |

## Gotchas

1. Do not ask a second or third round of "just one more thing" questions. Either ask the full blocker batch once or proceed with assumptions.
2. Do not bury shopping in a note field. If shopping matters, surface it in Daily Plan, the options bank, and Buy List.
3. Do not turn Pack List into Buy List. Pack is what physically travels. Buy is the purchase tracker.
4. Do not silently accept partial coverage. When flights, hotel rooms, or attraction tickets cover fewer people than the plan assumes, keep the mismatch visible.
5. Do not over-research. Only add prep or compliance tasks that actually matter for this route, these passports, these medicines, and these commitments.

## Helper Files

- `scripts/build_workbook.py` builds the workbook from a canonical model.
- `scripts/validate_workbook.py` checks structure, formulas, data validations, widths, merges, and Daily Plan row patterns.
- `scripts/render_check.py` performs a lightweight visual-risk scan when a richer renderer is unavailable.
- `templates/trip_model_schema.json` defines the canonical trip-model contract.
- `templates/workbook_template_spec.yaml` mirrors the deterministic layout contract for human review.
