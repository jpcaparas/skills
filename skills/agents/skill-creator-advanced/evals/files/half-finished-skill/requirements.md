# Package Checker Requirements

The finished `half-finished-skill` must provide a read-only package checker.

- Input: one explicit skill-directory path.
- Required checks: `SKILL.md` exists, begins with a delimited frontmatter block, and `evals/evals.json` exists and parses as a JSON object.
- Output: one deterministic line per failed check, otherwise `PASS: package structure is readable`.
- Exit status: `0` when all required checks pass, `1` for validation failures, and `2` for invalid CLI usage.
- Safety: do not modify the target package, follow symlinks outside it, install dependencies, or use network access.

The script may use only the target environment's standard library.
