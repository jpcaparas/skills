# Cross-Harness Notes

Keep the skill portable.

## Spreadsheet Runtime Guidance

- In OpenAI or Codex-style environments, if `/home/oai/skills/spreadsheets/SKILL.md` exists, read it before spreadsheet work.
- If that file does not exist, use the harness-equivalent spreadsheet skill or local spreadsheet guidance.
- The deterministic workbook builder for this skill is `scripts/build_workbook.py`, which uses `openpyxl` for portability.

## Python Runtime

- The builder and workbook validator require `python3` with `openpyxl`.
- If the default `python3` lacks `openpyxl`, use a bundled workspace runtime or another Python interpreter that has it installed.
- `scripts/test_skill.py` tries to locate such an interpreter automatically for the local smoke test.

## Optional Rendering

- If `@oai/artifact-tool` or an equivalent renderer is available, use it after workbook creation for recalculation, cached formula checks, and sheet rendering.
- `scripts/render_check.py` is the fallback structural visual-risk scan when a richer renderer is unavailable.

## File Paths and Output

- Detect `/mnt/data` and use it when present and no explicit output path was supplied.
- Otherwise write to the working directory or the user-provided path.
- Do not hard-code machine-specific save locations in the skill instructions.

## First-Class References

- Use symbolic skill references such as `{{ skill:temporal-awareness }}` when another installed skill helps with live verification.
- Keep file-path references for local support files inside this skill.
