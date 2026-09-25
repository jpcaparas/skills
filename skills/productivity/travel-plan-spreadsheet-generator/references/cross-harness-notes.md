# Cross-Harness Notes

Keep the skill portable.

## Spreadsheet Runtime Guidance

- Discover an available spreadsheet skill or local spreadsheet guidance through the harness and load it before spreadsheet work. Do not assume a vendor-specific installation path.
- If no equivalent guidance is available, use this package's documented builder and validator, reporting any unavailable optional verification.
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
