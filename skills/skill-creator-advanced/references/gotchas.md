# Gotchas — Common Mistakes & Tribal Knowledge

> **This file is self-improving.** When user feedback reveals a new generalizable mistake,
> append it to the appropriate category with a date stamp. Prefix new entries with `[NEW]`.
> Remove the `[NEW]` prefix after the rule has been validated across multiple skills.

---

## Structural Mistakes

- Putting everything in SKILL.md instead of using references -- SKILL.md should be a router
  and quick reference, not an encyclopedia. If it exceeds 300 lines, start moving content out.
- Making SKILL.md too short (just a paragraph) -- it needs decision trees, a quick reference
  table, a gotchas section, and pointers to references. A bare paragraph is not a skill, it is
  a description.
- Missing frontmatter fields -- `name` and `description` are required. Skills without them
  silently fail to trigger on most platforms.
- Directory name not matching skill name -- the `name` field in frontmatter must exactly match
  the directory name. `stripe-api/SKILL.md` with `name: stripe` will confuse harnesses.
- Nested cross-references (A -> B -> C) -- reference chains deeper than one hop mean the agent
  has to read three files to answer one question. Flatten: SKILL.md -> B and SKILL.md -> C.
- Missing evals directory -- every production skill should have `evals/evals.json`, even if it
  starts with just one smoke test.
- Forgetting .gitkeep in empty directories -- empty directories are not tracked by git without
  a placeholder file. Use `.gitkeep` and remove it when real files are added.
- Using README.md at the skill root instead of SKILL.md -- SKILL.md IS the readme for agent
  consumption. A separate README.md is redundant and may confuse harnesses.

## Content Mistakes

- Pseudocode instead of working examples -- every code example should be syntactically valid
  and ideally tested. Agents copy code; pseudocode becomes real bugs.
- Outdated API versions or endpoints -- always verify endpoints against current docs before
  writing. Pin the API version explicitly. Never use "latest" as a version.
- Missing gotchas section -- gotchas are the highest-value content in most skills. They encode
  the things that are hard to discover from official documentation alone. Include at least 3.
- Explaining things the agent already knows -- do not restate how HTTP requests work, what JSON
  is, or how to use pip. Add knowledge the agent lacks: API-specific quirks, undocumented
  behaviors, version gotchas.
- Using MUST/NEVER instead of explaining reasoning -- agents respond better to understanding why
  something matters than to rigid directives. "Explain the why" means writing "Use POST for
  creation because the API returns 405 for PUT on the create endpoint" instead of "MUST use POST".
- Hallucinating endpoints or flags -- never write an endpoint or CLI flag from memory. Verify
  by fetching docs, running --help, or testing a real call.
- Incomplete auth documentation -- auth is the first thing that breaks. Always include: the
  exact header format, where to get credentials, and a tested example.
- Mixing SDK versions -- if showing SDK examples, pin the SDK version and ensure all examples
  use the same version's API surface.

## Disclosure Mistakes

- Loading all references upfront instead of on demand -- SKILL.md should tell the agent WHEN
  to read each reference, not load them all at trigger time. Use conditional pointers:
  "Read references/auth.md when setting up authentication."
- No reading guide (agent does not know which file to read) -- include a task-to-file mapping
  table in SKILL.md so the agent can route directly to the right reference.
- Reference files without TOC when over 300 lines -- long reference files without a table of
  contents force the agent to scan the entire file. Add a TOC at the top with anchor links.
- Duplicating content between SKILL.md and references -- information should live in ONE place.
  SKILL.md summarizes; references elaborate. If you find yourself copying a paragraph, replace
  the copy with a pointer.
- Over-granular references -- splitting content into 20 tiny files (one per endpoint) creates
  navigation overhead. Group by domain or function: one file per endpoint group, not one per
  endpoint.
- Under-granular references -- one massive 2000-line reference file defeats progressive
  disclosure. Split by the 5-file structure (README, api, patterns, configuration, gotchas)
  when a domain exceeds 500 lines.

## Verification Mistakes

- Examples that do not actually work -- the most common complaint. Before shipping, execute
  every code example (or at minimum, syntax-check it).
- CLI commands with wrong flag syntax -- flag syntax changes between tool versions. Always
  verify against `tool --help` for the pinned version.
- API endpoints that return errors -- test at least one real API call per endpoint group.
  Document the exact request format that succeeds.
- Missing auth in example commands -- every curl or API example must include the auth header.
  Users will copy-paste; omitting auth means the first thing they try fails.
- Incorrect HTTP methods -- some APIs use PATCH for partial updates, PUT for full replacement.
  Do not guess; check the docs.
- Untested pagination examples -- pagination loops are a common source of bugs (off-by-one,
  infinite loops, wrong termination condition). Test with real data.
- Assuming environment variables exist -- if a script or command references an env var, document
  where to set it and what happens if it is missing.

## Style Mistakes

- Passive voice instead of imperative -- "The command should be run" is weaker than "Run the
  command." Skills are instructions; use the imperative form.
- Over-explaining general programming concepts -- do not include a tutorial on REST APIs or
  JSON parsing. The agent already knows this. Focus on what is unique to this skill's domain.
- Inconsistent heading levels -- use strict hierarchy: # for title, ## for sections, ### for
  subsections. Never skip a level (# -> ### without ##).
- No "See Also" cross-references in reference files -- every reference file should end with
  a "See Also" section linking to related files. This aids navigation when the agent needs
  adjacent information.
- Overly verbose descriptions -- the frontmatter description should be a dense, keyword-rich
  paragraph, not a marketing essay. Every word should help with triggering.
- Inconsistent example formatting -- pick one style for code examples (curl, SDK, or both)
  and use it consistently throughout all reference files.
