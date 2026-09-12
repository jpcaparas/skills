# Trip Model

Build a canonical trip model before generating the workbook.

Use `templates/trip_model_schema.json` as the field contract. The builder script will normalize missing optional lists, derive planner-window dates, and apply workbook defaults, but it should not have to guess the whole trip from scratch.

## Minimum Required Fields

- `trip_title`
- `primary_destination`
- `destinations[]`
- `travellers[]`
- `stay_start_date`
- `stay_end_date`
- `departure_date`
- `final_home_arrival_date`
- `bookings[]`
- `daily_rows[]`
- `prep_tasks[]`
- `pack_items[]`
- `buy_items[]`
- `sources[]`
- `review_flags[]`

## Required Derived Fields

The normalized model should also carry:

- `planner_start_date`
- `planner_end_date`
- `options_bank[]`
- `fixed_events[]`
- `assumptions[]`
- `shopping_objectives[]`
- `notes_raw[]`
- `notes_normalised[]`
- `timezones[]`

## Field Notes

### `travellers[]`

Each traveller should include:

- `name`
- `role`
- `included_in_day_plans`
- `notes`

The builder uses this list to compute `planned_adults`.

### `bookings[]`

Each booking should include:

- `type`
- `item`
- `date`
- `time_local`
- `area_route`
- `booking_ref`
- `covered_adults`
- `status`
- `action_needed`
- `notes_source`
- optional `why_it_matters`

### `daily_rows[]`

Each row represents one block in the planner window:

- `date`
- `block` (`AM`, `PM`, `Eve`)
- `phase`
- `primary_plan`
- `fallback_option_1`
- `fallback_split_plan`
- `area_base`
- `shopping_focus`
- `fixed_booking_time`
- `pace`
- `status`
- `notes`

The builder enforces exactly three rows per day. If the supplied list is incomplete, the builder fills the gaps with placeholder rows so the workbook remains structurally valid.

### `review_flags[]`

Store clear, user-facing flags. Strings are acceptable for simple cases. Richer entries may include:

- `message`
- `severity`
- `sheet_targets`
- `source_refs`

### `sources[]`

Store only sources actually used. Each source should include:

- `type`
- `source_name`
- `url_or_file_note`
- `used_for`
- `last_checked_or_file_date`
- `notes`

## Notes Normalization

Preserve both the raw notes and the normalized interpretation.

- Put the original phrasing in `notes_raw[]`.
- Put the cleaned, calendar-normalized, or conflict-resolved version in `notes_normalised[]`.
- If normalization changes meaning or confidence, add a review flag.
