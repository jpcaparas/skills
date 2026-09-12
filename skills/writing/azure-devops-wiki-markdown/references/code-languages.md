# Code Fence Languages

Use this file when the user asks which language tag to put after triple backticks in Azure DevOps Markdown.

Primary sources:

- Microsoft Learn, "Markdown syntax for files, widgets, wikis - Azure DevOps," current as checked on April 9, 2026
- Highlight.js supported-language table from the official Highlight.js repository, checked on April 9, 2026

## What the Docs Actually Promise

Azure DevOps documentation says fenced code blocks accept a language identifier and points readers to Highlight.js for supported languages.

Important nuance:

- Highlight.js supports many languages upstream, but its default minified web build includes only about 40 popular languages.
- Some upstream entries are third-party packages rather than core bundled languages.
- Highlight.js also documents alias overlaps such as `ls` and `ml`.
- Azure DevOps does not publish the exact Highlight.js bundle used by every Azure DevOps surface.

Inference from those sources:

- Treat common aliases as safe defaults.
- Treat uncommon or third-party aliases as "verify before promising."
- Do not treat Mermaid as a code-fence language identifier. In Azure DevOps wiki pages, Mermaid is a separate `::: mermaid` block type.

## Recommended Aliases

| Use case | Preferred tag | Also seen upstream | Notes |
| --- | --- | --- | --- |
| Plain text | `plaintext` | `text`, `txt` | Safest fallback when highlighting is uncertain. |
| Bash or shell | `bash` | `sh`, `zsh` | |
| PowerShell | `powershell` | `ps`, `ps1` | |
| JSON | `json` | `jsonc`, `json5` | |
| YAML | `yml` | `yaml` | Both exist upstream. |
| TOML / INI | `toml` | `ini` | Highlight.js groups these together. |
| HTML / XML / SVG | `html` | `xml`, `svg` | |
| CSS | `css` |  | |
| JavaScript | `js` | `javascript`, `jsx` | |
| TypeScript | `ts` | `typescript`, `tsx`, `mts`, `cts` | |
| Python | `python` | `py` | |
| C# | `csharp` | `cs` | |
| C++ | `cpp` | `cxx`, `cc`, `c++` | |
| SQL | `sql` |  | |
| Diff / patch | `diff` | `patch` | Useful in PR and README discussions. |
| Markdown | `md` | `markdown` | |
| Bicep | `bicep` |  | Upstream marks this as a third-party package. Verify before relying on it. |

## Ambiguous Aliases

Highlight.js explicitly documents alias overlaps. Prefer the full language name when these come up:

| Alias | Overlap | Guidance |
| --- | --- | --- |
| `ls` | Lasso, LiveScript | Use `lasso` or `livescript` instead of `ls`. |
| `ml` | OCaml, SML | Use `ocaml` or `sml` instead of `ml`. |

## Azure-Relevant Edge Cases

| Query | Current upstream status | Guidance |
| --- | --- | --- |
| `mermaid` | not in the current Highlight.js table | Use `::: mermaid` blocks instead of a code-fence tag. |
| `kusto` or `kql` | not found in the current upstream table | Prefer `sql` or `plaintext` unless the user has confirmed a working renderer in their environment. |
| `KaTeX` | documented in Azure DevOps examples for formula syntax | Use `$...$` or `$$...$$` for rendered math. Do not treat `katex` as your default code-fence recommendation. |
| obscure alias | unknown | Run the helper script and show the result before claiming support. |

## Verify an Alias

Run the helper script from this skill directory:

```bash
python3 scripts/find_code_language.py typescript
python3 scripts/find_code_language.py bicep
python3 scripts/find_code_language.py ls
python3 scripts/find_code_language.py mermaid
python3 scripts/find_code_language.py --refresh typescript
```

The script:

- checks the shipped cache first
- can refresh from the live Highlight.js table
- falls back to a built-in safe alias set if the network is unavailable
- flags ambiguous aliases and third-party packages

## Routing Rules

- If the task is a normal wiki page, combine this file with `references/syntax.md`.
- If the user wants Mermaid, read `references/mermaid.md`.
- If the user is debugging unexpected rendering, read `references/gotchas.md`.

## See Also

- `references/syntax.md`
- `references/mermaid.md`
- `references/gotchas.md`
- `scripts/find_code_language.py`

