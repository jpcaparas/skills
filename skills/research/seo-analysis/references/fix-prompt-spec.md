# Fix Prompt Specification

Use this file when the user requests an implementation handoff or it would help within the requested scope. Neither a handoff nor the helper is required for an audit answer.

## Goal

Produce a prompt that avoids redundant discovery while requiring revalidation of relevant findings against the current checkout, deployment, and official requirements before edits.

## Required Sections

1. **Objective**
   - One paragraph on the business and search outcome.
2. **Repository Context**
   - Repo path
   - stack or likely stack
   - pages or templates inspected
3. **Confirmed Findings**
   - severity
   - category
   - scope
   - evidence
   - desired end state
4. **Implementation Constraints**
   - preserve existing design system or routing behavior
   - do not break non-indexable utility pages intentionally set to `noindex`
   - keep changes minimal and centralized when the bug comes from shared abstractions
5. **Work Items**
   - ordered fixes, grouped by root cause
6. **Acceptance Criteria**
   - exact things to verify in rendered HTML, routing behavior, or generated files
7. **Verification Commands**
   - build/test/lint commands if known

## Prompt Quality Rules

- reference actual files and abstractions
- include only evidence-backed issues as confirmed findings; keep unknowns and unverified hypotheses separate
- be explicit about what not to touch
- prefer centralized fixes over page-by-page band-aids
- include page types affected
- include metadata fields and schema fields to emit
- include canonical/indexing behavior expectations

## Findings JSON Shape

The optional builder accepts `--input findings.json`; set `repo` in the JSON, not as a command-line flag. It renders a draft, not a validated audit. Review every finding, constraint, and acceptance criterion before handoff: missing evidence produces placeholder text, not confirmation. Supply custom constraints in the `extra_constraints` string; a `constraints` array is not consumed by this helper.

```json
{
  "objective": "Improve technical SEO and preview quality for core landing pages.",
  "repo": "/abs/path/to/repo",
  "stack": "Unknown or detected stack",
  "extra_constraints": "Preserve intentional noindex rules for account and checkout routes.",
  "verification_commands": [
    "pnpm test",
    "pnpm build"
  ],
  "findings": [
    {
      "severity": "high",
      "category": "metadata",
      "scope": "all marketing pages",
      "evidence": "Shared metadata helper emits the same title and description for every route.",
      "fix_direction": "Move title/description generation to route-aware metadata and keep brand suffix logic centralized."
    }
  ]
}
```

## Recommended Output Style

The handoff prompt should sound like an implementation brief, not an essay:

- concrete
- ordered
- evidence-backed
- safe for direct execution

Use `templates/fix-prompt-template.md` when writing manually.
