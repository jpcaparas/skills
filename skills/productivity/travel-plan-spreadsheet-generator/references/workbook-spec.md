# Workbook Spec

This file describes the deterministic workbook contract. `scripts/build_workbook.py` is the runtime source of truth, and `templates/workbook_template_spec.yaml` is the human-readable mirror.

## Non-Negotiable Deterministic Rules

- Output `.xlsx`.
- Default filename: `<PrimaryDestination>_Travel_Itinerary_<Month>_<Year>.xlsx`.
- If there is no clear primary destination: `Travel_Itinerary_<Month>_<Year>.xlsx`.
- Save to `/mnt/data` when that directory exists and no explicit output path was provided. Otherwise save in the current working directory.
- Hide gridlines on all sheets.
- Do not add frozen panes, Excel tables, or auto-filters unless the user explicitly asked for them.
- Use Calibri throughout.
- Use wrapped text heavily for prose cells.
- Keep cross-sheet formulas dynamic. Do not hardcode row counts that depend on generated list sizes.

## Sheet Order

1. `Overview`
2. `Bookings`
3. `Daily Plan`
4. `<PrimaryDestination> Options`
5. `Prep & Compliance`
6. `Pack List`
7. `Buy List`
8. `Sources`

Naming rule for sheet 4:

- `Tokyo Options` when the primary destination is Tokyo.
- `<PrimaryDestination> Options` for a non-Tokyo single-base trip.
- `Destination Options` when there is no clear primary base.

## Colour Language

Use these semantic colours:

- Header navy: `#1F4E78`
- Header teal: `#0F766E`
- Static label fill: `#F3F4F6`
- Zebra fills: `#FAFAFA` and `#F4F7FB`
- Control fill: `#F3E8FF`
- Metric fill: `#E6FFFB`
- Soft caution fill: `#FFF4E5`
- Caution chip fill: `#FED7AA`
- Soft error fill: `#FDECEC`
- Success fill: `#DCFCE7`
- Info fill: `#DBEAFE`
- Purple work or in-destination buy fill: `#E9D5FF`
- Recovery fill: `#CCFBF1`

Text colours:

- White: `#FFFFFF`
- Static grey: `#6B7280`
- Editable blue: `#1D4ED8`
- Imported green: `#15803D`
- Formula black: `#000000`
- Minor slate: `#334155`
- Caution orange: `#C2410C`
- Error red: `#B91C1C`

## Typography and Borders

- Title rows: 16 pt bold white text on navy fill.
- Subtitle rows: 10 pt white text on teal fill.
- Section headers: 11 pt bold white text on navy fill with a medium bottom border.
- Column headers: 10 pt bold white text on teal fill with a medium top border and thin bottom border.
- Standard data rows: 10 pt with thin bottom borders.
- Minor notes: 9 pt slate text.
- Dates, counts, statuses, and short enums stay centered.
- Prose stays left/top aligned.

## Key Formulas

- `planner_start_date = departure_date - 1 day`
- `planner_end_date = final_home_arrival_date + 1 day`
- `hotel_nights = stay_end_date - stay_start_date`
- `planner_days = planner_end_date - planner_start_date + 1`
- `planned_adults = count of included travellers`
- Bookings gap: `MAX(planned_adults - covered_adults, 0)`
- Overview snapshot counters point to generated row ranges, not fixed row numbers

## Daily Plan Contract

- Exactly three rows per day: `AM`, `PM`, `Eve`.
- The planner window runs from one day before outbound departure through one day after final home arrival by default.
- Use phase fills for the entire row:
  - Pre-departure -> light grey
  - Travel or transit -> light blue
  - In-destination sightseeing -> light green
  - Conference or fixed work -> light purple
  - Return -> light orange
  - Recovery -> light teal
- Status validation: `Locked`, `Flexible`, `Weather watch`, `Done`

## Review-Flag Visibility

Traveller-count or coverage contradictions must stay visible in:

- `Overview`
- `Bookings`
- `Prep & Compliance`
- `Daily Plan` when the contradiction changes what the group can actually do

## Source Logging

Every source actually used goes into `Sources`.

- Keep user files separate from screenshots, official sources, and planner-generated fallbacks.
- Use plain-text URLs in workbook cells.
- Record `Last checked` for official sources.
- Record file note or issue date for uploaded files when available.
