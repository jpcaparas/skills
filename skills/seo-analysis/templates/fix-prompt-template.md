# SEO Fix Session Prompt

You are working in the repository at `{{REPO_PATH}}`.

## Objective

{{OBJECTIVE}}

## Repository Context

- Stack: `{{STACK}}`
- Pages/templates inspected:
  - {{PAGES_OR_TEMPLATES}}

## Confirmed Findings

{{CONFIRMED_FINDINGS}}

## Implementation Constraints

- Preserve intentional `noindex` behavior for utility, auth, account, cart, checkout, preview, and internal search routes unless a confirmed finding says otherwise.
- Prefer shared abstraction fixes over one-off page edits.
- Keep search metadata, social metadata, canonical logic, and schema aligned per page type.
- Do not remove valid existing schema unless it is wrong, duplicated, or contradictory.
- Keep changes minimal, testable, and localized.
- {{EXTRA_CONSTRAINTS}}

## Work Items

{{WORK_ITEMS}}

## Acceptance Criteria

{{ACCEPTANCE_CRITERIA}}

## Verification

Run the relevant checks after making changes:

{{VERIFICATION_COMMANDS}}

When you finish, summarize the code changes, note any assumptions, and call out anything still requiring runtime or search-console verification.
