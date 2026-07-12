# {{TOOL_NAME}} Evidenced Gotchas

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

Repeat the entry only for distinct gotchas. Create categories such as version,
platform, quoting, output parsing, identity, or safety only when the tool has
evidenced entries in that category.

## See Also

- `references/commands.md` -- command and outcome contracts
- `references/configuration.md` -- installation and identity setup
- `references/patterns.md` -- supported workflows

## Release Gate

Replace every template token and delete this entry skeleton if no evidenced
gotcha exists. Do not release speculative warnings, empty categories, or filler.
