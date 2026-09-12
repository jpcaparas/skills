# Fix Prompt Specification

Use this file after the audit is done and the user wants a prompt for another session to implement fixes.

## Goal

Produce a prompt that lets another session edit code immediately without redoing discovery.

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
- be explicit about what not to touch
- prefer centralized fixes over page-by-page band-aids
- include page types affected
- include metadata fields and schema fields to emit
- include canonical/indexing behavior expectations

## Findings JSON Shape

The builder script accepts this shape:

```json
{
  "objective": "Improve technical SEO and preview quality for core landing pages.",
  "repo": "/abs/path/to/repo",
  "stack": "Unknown or detected stack",
  "constraints": [
    "Preserve intentional noindex rules for account and checkout routes."
  ],
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
