# Placement & Destination Selection

## Table of Contents

- [Goal](#goal)
- [Decision Order](#decision-order)
- [Recognized Skill Roots](#recognized-skill-roots)
- [Harness Compatibility](#harness-compatibility)
- [Scoring Heuristics](#scoring-heuristics)
- [Default Fallbacks](#default-fallbacks)
- [How to Present the Recommendation](#how-to-present-the-recommendation)

---

## Goal

Do not assume the current working directory is the right place for a new skill.

When creating a skill, choose the destination that best matches how the user already organizes skills:

- repo-local if the current repository already stores skills there
- same-family sibling root if this skill is already installed in a known skills directory
- an established global root that the target harness can discover

If the user explicitly gives a destination, that overrides every heuristic.

Do not compare skill counts across incompatible harness families. A large library is not useful if the active agent cannot discover it.

---

## Decision Order

Use this order every time:

1. **Explicit user target wins**
   - If the user names the exact repository or destination folder, use that.

2. **Resolve the target harness when it matters**
   - Pass `--target-harness <harness>` when the user or environment identifies the consumer.
   - If no target was supplied, infer one only from a recognized global root containing this running skill.
   - A source checkout outside the inspected repository is not an installation-family signal.

3. **Existing compatible project root wins**
   - If the current git repo already contains a recognized root that the target harness can discover, create the new skill there.
   - Compare counts only among compatible roots. Without a target, prefer portable roots or roots with a common compatible harness.

4. **Current installation family wins next**
   - If this skill is currently running from a recognized global skills root, prefer that sibling root when the repo itself does not already have an established skills location.
   - Preserve lexical invocation ancestry so a symlinked installation still identifies its harness family.
   - Do not treat an unrelated source checkout merely containing this creator as the user's installation family.

5. **Established compatible global library wins after that**
   - With a target harness, compare only roots that harness can discover.
   - Without a target or current family, prefer the shared global root instead of guessing from unrelated vendor libraries.

6. **Only then fall back**
   - Inside a git repo: default to `<repo-root>/.agents/skills/`.
   - In a public skills repo that already uses `skills/<skill-name>/`: default to `<repo-root>/skills/`.
   - Outside a repo: default to the selected harness's global root, otherwise `~/.agents/skills/`.

---

## Recognized Skill Roots

These are the common roots worth checking first because they line up with the `skills` CLI conventions and common agent installs.

### Public repo roots

- `skills/`

Lifecycle lanes are explicit policy destinations, not ordinary inference candidates:

- `skills/.curated/`
- `skills/.experimental/`
- `skills/.system/`

Use one of those lanes only when repository policy or an explicit user target assigns the skill's lifecycle state. A populated experimental or system lane must not pull an ordinary new skill into that lane.

### Project roots

- `.agents/skills/`
- `.github/skills/`
- `.codex/skills/`
- `.claude/skills/`
- `.cursor/skills/`
- `.gemini/skills/`
- `.opencode/skills/`
- `.continue/skills/`
- `.goose/skills/`

### Global roots

- `$CODEX_HOME/skills/` when `CODEX_HOME` exists
- `~/.agents/skills/`
- `~/.copilot/skills/`
- `~/.codex/skills/`
- `~/.claude/skills/`
- `~/.cursor/skills/`
- `~/.gemini/skills/`
- `~/.config/opencode/skills/`
- `~/.continue/skills/`
- `~/.config/goose/skills/`

When checking a root, count immediate child directories that contain `SKILL.md`. That tells you whether the location is already "home" for the user's skills.

GitHub documents `.github/skills/`, `.claude/skills/`, and `.agents/skills/` as project locations for Copilot, plus `~/.copilot/skills/` and `~/.agents/skills/` as personal locations. Verify unstable path claims against the current [GitHub Copilot skill-location documentation](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference#skill-locations).

---

## Harness Compatibility

Use the helper when the consumer is known:

```bash
python3 scripts/infer_destination.py --cwd <working-directory> \
  --target-harness copilot --skill-name <skill-name> --format text
```

Supported target values are `agents`, `codex`, `copilot`, `gemini`, and `opencode`. These built-ins have repository evidence, observed installed behavior, or current primary documentation; do not add another target mapping from convention alone. The Codex mapping is an observed-environment heuristic rather than a portable format guarantee: confirm the active installation's discovery output, especially for repo-local roots, before relying on it for a write.

The helper requires an existing directory for `--cwd`. When `--skill-name` is supplied, it enforces the portable 1–64 character lowercase, digit, and single-hyphen name contract before composing a destination.

The scaffold helper does not forward `--target-harness`. When scaffolding, infer first and pass the result explicitly:

```bash
bash scripts/scaffold.sh <skill-name> --output-root <recommended-root>
```

Compatibility is a discovery contract, not a branding guess:

- `skills/` publication lanes are repository source layouts, not claims that every harness discovers them directly.
- `.agents/skills/` is a neutral fallback only for targets whose current contract supports it.
- A harness-specific project or global root is eligible only for a compatible target.
- Copilot project selection includes `.github/skills/`, `.claude/skills/`, and `.agents/skills/`; personal selection includes `~/.copilot/skills/` and `~/.agents/skills/`.
- The exact recognized global root containing this creator outranks other global libraries when no compatible project convention already exists.
- If neither a target nor a current family resolves compatibility, recommend a shared root and present only neutral alternatives.
- Other recognized roots may be retained as an existing repository convention or exact current installation family, but the helper does not infer cross-family compatibility for them.

The compatibility table was checked on 2026-07-12 against primary documentation for [GitHub Copilot](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference#skill-locations), [Gemini CLI](https://geminicli.com/docs/cli/creating-skills/), and [OpenCode](https://opencode.ai/docs/skills/#place-files), plus the current installed Codex environment for its local mapping. Re-check the target harness before expanding it.

---

## Scoring Heuristics

Use these heuristics when several roots are plausible:

- Prefer **project scope** over **global scope** when the project already has skills there.
- Prefer the root with the **highest existing skill count** within the same scope.
- Prefer the **current install family** when this skill is already being run from a known skills root.
- Prefer `skills/` only when child skills or the exact current root prove that the repository is a public skills source; an empty directory alone is not evidence.
- Prefer `.agents/skills/` as the shared cross-agent project fallback when no project root exists yet.
- For equal counts, preserve a public source layout when present, then use normalized path order so selection is deterministic and no vendor receives a hidden tie preference.
- Rank alternatives with the same compatibility filter as the recommendation.

### Good examples

| Situation | Recommended root | Why |
|-----------|------------------|-----|
| Repo already has `.agents/skills/` with 4 skills | `<repo>/.agents/skills/` | Existing project convention is clear |
| Public repo already has `skills/skill-creator-advanced/` | `<repo>/skills/` | Keep installable repo layout consistent |
| Target is Copilot and `.github/skills/` has 4 skills | `<repo>/.github/skills/` | Existing project root is compatible with the target |
| Creator runs from `~/.codex/skills/`; unrelated `~/.claude/skills/` is larger | `~/.codex/skills/` | Current installation family wins before other global libraries |
| Target is Copilot; `~/.copilot/skills/` has 3 skills and `~/.codex/skills/` has 20 | `~/.copilot/skills/` | Skill counts are compared only across Copilot-compatible roots |
| No established roots anywhere, inside git repo | `<repo>/.agents/skills/` | Best shared project default |

---

## Default Fallbacks

Use these only when the earlier checks produce no clear winner:

### Inside a normal git repo

```text
<repo-root>/.agents/skills/<skill-name>
```

### Inside a public skills repository

```text
<repo-root>/skills/<skill-name>
```

### Outside a repo

1. Use the target harness's documented global root when `--target-harness` is supplied.
2. Use the recognized global root containing this creator when it establishes the current family.
3. Use `~/.agents/skills/<skill-name>` when neither signal is available.

For Codex, `$CODEX_HOME/skills/` is the target-specific fallback when `CODEX_HOME` is set. For Copilot, use `~/.copilot/skills/`. The other supported target values map to the verified roots listed above.

---

## How to Present the Recommendation

Always tell the user what you inferred before creating files.

Use this format:

```text
Recommended destination: /absolute/path/to/skills-root/<skill-name>
Reason: this repo already keeps 3 installable skills under .agents/skills
Alternative: /compatible/skills-root/<skill-name>
```

This is conversational guidance for the author before scaffolding. Do not write this block into the generated skill files or repository wrappers.

Then proceed unless the user overrides the destination.

Placement is complete when the chosen root follows an explicit user target or the strongest compatible repository convention, incompatible library counts cannot affect the result, the recommendation is stated before writes, and fresh skill discovery can see the resulting path.

## See Also

- `references/curation.md` — lifecycle state and publication surfaces affected by a move or rename
- `references/anatomy.md` — package layout inside the chosen root
- `references/cross-harness.md` — platform discovery paths and portability constraints
