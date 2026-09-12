# {{API_NAME}} Evidenced Gotchas

Capture only non-obvious behavior supported by current evidence. Merge repeated
feedback into one canonical entry and remove superseded wording instead of
appending a history log.

## {{GOTCHA_TITLE}}

- **Applies when:** {{GOTCHA_SCOPE}}
- **Evidence:** {{GOTCHA_EVIDENCE}}
- **Failure mode:** {{GOTCHA_FAILURE_MODE}}
- **Required rule:** {{GOTCHA_RULE}}
- **Verification:** {{GOTCHA_VERIFICATION}}
- **Supersedes:** {{SUPERSEDED_ENTRY_OR_NONE}}

Repeat the entry only for distinct gotchas. Create categories such as identity,
request encoding, event delivery, quotas, versioning, or client behavior only
when the API actually has evidenced entries in that category.

## See Also

- `references/api.md` -- operation and failure contracts
- `references/patterns.md` -- supported workflows and recovery rules
- `references/configuration.md` -- access and client setup

## Release Gate

Replace every template token and delete this entry skeleton if no evidenced
gotcha exists. Do not release speculative warnings, empty categories, or filler.
