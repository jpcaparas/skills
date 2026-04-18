# Mapping Rules

Map the canonical trip model into the workbook predictably.

## Overview

- Show the planner window and headline counters.
- Surface the most important review flags, especially traveller-count or ticket-coverage contradictions.
- Display up to four traveller rows in the Overview panel. If the trip has more travellers, summarize the remainder in the notes while keeping `planned_adults` accurate.
- Pull the fixed-anchor summary from bookings and fixed events.

## Bookings

- One row per anchor booking, ticket, hotel, flight, or fixed event.
- Link `Planned adults` back to `Overview`.
- Calculate `Gap` as `MAX(planned - covered, 0)`.
- Derive `Coverage flag` as `OK` or `Needs review`.
- Use `Action needed` for the practical next step, not vague filler.

## Daily Plan

- Keep exactly three rows per day.
- Arrival and return blocks should stay light by default.
- When only part of the group is ticketed for a paid activity, use `Fallback / split plan` to keep the non-ticketed travellers covered.
- Keep to one or two coherent neighbourhood clusters per day unless the user clearly wants a packed route.

## Options Bank

- Keep overflow ideas here so the Daily Plan stays readable.
- Preserve user-requested must-sees and must-buys even if they did not make the final daily route.
- Keep shopping relevance explicit.

## Prep & Compliance

- Use this sheet for travel admin, coverage, transit, immigration, tickets, health, medicines, and insurance.
- Only add tasks that matter for this route and these travellers.
- When a contradiction affects compliance or booking validity, repeat the review signal here.

## Pack List vs Buy List

Use this split consistently:

- `Pack List`: what physically needs to travel
- `Buy List`: what still needs to be purchased, watched, skipped, or bought in-destination

Examples:

- eSIM -> `Buy List`
- passport -> `Pack List`
- prescribed medicine legality check -> `Prep & Compliance`
- prescribed medicine itself -> `Pack List`
- spare glasses -> `Pack List`, possibly also `Buy List` if missing

## Sources

- Distinguish user files, user screenshots, official sources, and planner-generated fallbacks.
- Use plain-text URLs.
- Record only sources that actually influenced the workbook.
