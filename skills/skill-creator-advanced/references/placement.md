# Placement & Destination Selection

## Table of Contents

- [Goal](#goal)
- [Decision Order](#decision-order)
- [Recognized Skill Roots](#recognized-skill-roots)
- [Scoring Heuristics](#scoring-heuristics)
- [Default Fallbacks](#default-fallbacks)
- [How to Present the Recommendation](#how-to-present-the-recommendation)

---

## Goal

Do not assume the current working directory is the right place for a new skill.

When creating a skill, choose the destination that best matches how the user already organizes skills:

- repo-local if the current repository already stores skills there
- same-family sibling root if this skill is already installed in a known skills directory
- global root with the most existing skills when the user's library already lives there

If the user explicitly gives a destination, that overrides every heuristic.

---

## Decision Order

Use this order every time:

1. **Explicit user target wins**
   - If the user says "put it in `/path/...`" or names the exact repo/folder, use that.

2. **Existing project root wins**
   - If the current git repo already contains a recognized skills root with one or more skills, create the new skill there.
   - Prefer the project root with the most existing skills.

3. **Current installation family wins next**
   - If this skill is currently running from a recognized skills root, prefer that sibling root when the repo itself does not already have an established skills location.

4. **Established global library wins after that**
   - Scan common global skill roots and choose the one with the most existing skills.

5. **Only then fall back**
   - Inside a git repo: default to `<repo-root>/.agents/skills/`.
   - In a public skills repo that already uses `skills/<skill-name>/`: default to `<repo-root>/skills/`.
   - Outside a repo: default to the current harness's global root if you can infer it, otherwise `~/.agents/skills/`.

---

## Recognized Skill Roots

These are the common roots worth checking first because they line up with the `skills` CLI conventions and common agent installs.

### Public repo roots

- `skills/`
- `skills/.curated/`
- `skills/.experimental/`
- `skills/.system/`

### Project roots

- `.agents/skills/`
- `.codex/skills/`
- `.claude/skills/`
- `.cursor/skills/`
- `.gemini/skills/`
- `.opencode/skills/`
- `.continue/skills/`
- `.goose/skills/`

### Global roots

- `$CODEX_HOME/skills/` when `CODEX_HOME` exists
- `~/.codex/skills/`
- `~/.claude/skills/`
- `~/.agents/skills/`
- `~/.cursor/skills/`
- `~/.gemini/skills/`
- `~/.config/opencode/skills/`
- `~/.continue/skills/`
- `~/.config/goose/skills/`

When checking a root, count immediate child directories that contain `SKILL.md`. That tells you whether the location is already "home" for the user's skills.

---

## Scoring Heuristics

Use these heuristics when several roots are plausible:

- Prefer **project scope** over **global scope** when the project already has skills there.
- Prefer the root with the **highest existing skill count** within the same scope.
- Prefer the **current install family** when this skill is already being run from a known skills root.
- Prefer `skills/` in a repository that is clearly a public skills source.
- Prefer `.agents/skills/` as the shared cross-agent project fallback when no project root exists yet.

### Good examples

| Situation | Recommended root | Why |
|-----------|------------------|-----|
| Repo already has `.agents/skills/` with 4 skills | `<repo>/.agents/skills/` | Existing project convention is clear |
| Public repo already has `skills/skill-creator-advanced/` | `<repo>/skills/` | Keep installable repo layout consistent |
| No repo-local skills, but `~/.codex/skills/` has 12 skills | `~/.codex/skills/` | Global library is already established there |
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

1. `$CODEX_HOME/skills/<skill-name>` if `CODEX_HOME` is set
2. `~/.codex/skills/<skill-name>` if Codex-style installs appear established
3. `~/.agents/skills/<skill-name>` as the generic fallback

---

## How to Present the Recommendation

Always tell the user what you inferred before creating files.

Use this format:

```text
Recommended destination: /absolute/path/to/skills-root/<skill-name>
Reason: this repo already keeps 3 installable skills under .agents/skills
Alternative: ~/.codex/skills/<skill-name>
```

This is conversational guidance for the author before scaffolding. Do not write this block into the generated skill files or repository wrappers.

Then proceed unless the user overrides the destination.
