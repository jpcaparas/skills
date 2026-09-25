# Output Packet

Use this file when you need the folder layout, command flow, or formatting rules.

## Packet Contract

The packet always lives under the caller's current working directory unless the user provides an explicit visible destination.

Each packet contains:

- `work-item.md` - the main draft intended to be pasted into Azure DevOps
- `context.md` - the extracted source context, codebase investigation notes, and supporting snippets that informed the draft
- `sources.md` - the official Microsoft Learn links used for type guidance
- `metadata.json` - machine-readable packet metadata

## Workflow

1. Read the source context and choose one primary type using supplied or observed process evidence. Use `Product Backlog Item` as the fallback when neither type nor process is known.
2. Run `python3 scripts/create_work_item_packet.py --title "<title>"` from the current working directory for the default PBI.
3. Pass `--type <type>` and `--process <process>` when the project process is known; the process option records metadata but does not infer type. Report unsupported types rather than inventing helper options.
4. Add `--context-file /path/to/file.md` when the source notes already exist on disk.
5. If the packet is being drafted inside a repository, inspect the codebase before replacing placeholders.
6. Open the generated `work-item.md` and replace the placeholders with a final audience-safe draft.
7. Keep spillover notes, raw reproduction details, design scraps, code snippets, or open questions in `context.md`.

## Recommended Command Patterns

| Need | Command |
| --- | --- |
| Create the default PBI packet beside the command | `python3 scripts/create_work_item_packet.py --title "Add billing status to account summary"` |
| Seed the packet from saved notes | `python3 scripts/create_work_item_packet.py --type bug --title "CSV export fails for long date ranges" --context-file ./notes/csv-export-bug.md` |
| Save to an explicit visible folder | `python3 scripts/create_work_item_packet.py --type issue --title "Vendor certificate blocks go-live" --save-root ./work-items` |

## Writing Contract

- Apply the style precedence and field-level rules in `references/writing-style.md`. Azure Boards semantics, the exact packet schema, project terminology, requested locale, and exact literals override generic style preferences.
- The labels and order below are the helper's default packaging contract, not a prose template; change that shape only when the user explicitly requests it. Adapt wording and detail within sections freely while preserving facts and type semantics.
- Do not use `#`, `##`, or `###` headings in `work-item.md` outside a detailed manual QA `Test Scenario` block.
- Use bold section labels in `work-item.md`.
- Use these exact labels for non-bug drafts, in this order:
  1. `**Title**`
  2. `**Problem**`
  3. `**Action**`
  4. `**Outcome**`
  5. `**Acceptance Criteria**`
  6. `**Developer Notes**`
  7. `**Test Scenario**`
- For `Bug`, add `**Reproduction Steps**` between `**Problem**` and `**Action**`.
- Prefer short paragraphs, bullets, and numbered lists.
- Use sentence case for the free-form title and QA scenario titles when local style permits. Keep the exact bold section labels as a deliberate schema exception.
- Write for technical and non-technical readers at the same time. The first paragraph should make sense without product or codebase trivia.
- In `Problem`, name the affected role, workflow, service, or component; distinguish observed facts from suspected causes.
- Put prerequisites and conditions before the actions that depend on them.
- Make acceptance criteria observable and testable, but add only conditions supported by the source, repository evidence, or an explicit user decision. Use `must` for requirements, `can` for capabilities, and `might` for possibilities; avoid ambiguous `should` in pass-or-fail criteria.
- Use backticks for code identifiers, file paths, commands, configuration keys, and API elements. Use descriptive Markdown link text when the renderer supports it.
- Use supplied or observed process evidence before the `Product Backlog Item` fallback; a known Agile backlog request uses `User Story` even without an explicit type name.
- Keep `Feature` drafts outcome-focused, with enough high-level actions to describe the capability without becoming an implementation diary.
- `Bug` drafts must include simple numbered `**Reproduction Steps**` that QA, product, or developers can follow without interpreting dense prose.
- `User Story` drafts should describe who needs what and why before implementation notes.
- `Task` drafts should stay execution-focused and should not masquerade as user-facing value.
- `Developer Notes` is for implementation constraints, dependencies, rollout notes, environment notes, and known unknowns. Bullets often help, but choose the clearest form.
- `Test Scenario` is for QA-facing validation notes. If it contains manual QA scenarios, use the Manual QA Scenario Contract below instead of generic bullets.

## Manual QA Scenario Contract

Use this contract whenever `**Test Scenario**` contains manual QA scenarios. The output should read like a thoughtful senior tester chose the checks, not like a generated permutation matrix.

For `work-item.md`, keep the existing `**Test Scenario**` section label and start the content with `Test environment notes:`. For a standalone QA-only response, include a top heading such as `# <Ticket> - <Change summary>: Manual QA Scenarios`.

Rules:

1. Choose risk-based scenarios: cover the happy path and the material defects, guards, or regressions introduced by the change. Use the number needed for that coverage, with no minimum, maximum, or filler. Ask or record a gap only when missing evidence prevents a meaningful check, not because a count is low.
2. Match steps to the surface under test. Use plain UI actions for browser flows, and documented requests, commands, jobs, or inspectable state for API/backend work. Technical identifiers are useful when the tester needs them; do not invent a UI path for headless behaviour.
3. Make scenario titles state the behaviour being protected in sentence case. Use "Double-clicking Pay does not charge twice", not "Payment flow test 2".
4. Make actions and expected results distinct; `**Steps:**` and `**Expected:**` lists are a useful default. Expected outcomes must be observable, such as a UI state, response, persisted record, documented log, dashboard entry, or email. Highlight the decisive signal when helpful.
5. Put verification aids first. Start with a short `Test environment notes:` block containing known prerequisites, safe test data, and available verification surfaces. Mark missing essentials rather than inventing test infrastructure.
6. Mark `(needs dev support)` only when a tester genuinely needs developer help to stage a state. Explain the supported setup before the dependent steps and include a counter-check where relevant. Do not prescribe arbitrary mocks or staged failures merely to fill a section.
7. Call out non-obvious verification traps. If pass and fail look identical on screen, tell QA where the real signal is.
8. Use only supplied or repository-backed verification surfaces. Do not invent an admin page, dashboard, log view, test clock, dependency failure, or recovery path. Mark the missing verification mechanism and request it when needed.
9. Use plain Markdown that pastes cleanly into Azure DevOps. `##` scenario headings, separators, numbered steps, and bulleted expectations are a useful pattern, not required prose styling. Do not use HTML or nested tables.
10. Use NZ English by default, including behaviour, authorised, cancelled, and enrolment where appropriate. Follow the user's or project's locale when specified; preserve exact UI labels and literals regardless of spelling.

Trimmed UI example; adapt the number of scenarios, test surface, and prose to the actual change:

```markdown
# <Ticket> - <Change summary>: Manual QA Scenarios

Test environment notes:
- Use <system> test mode. Useful test data: <test account>, <gateway test card>, and <known failing card>.
- Keep <dashboard/logs> open in another tab to confirm what actually happened.

---

## Scenario 1 - Normal <flow> still works (happy path)
**Steps:**
1. Log in as <persona> and open <page>.
2. Complete the normal <flow>.
3. Confirm the page moves to the success state.

**Expected:**
- The customer sees the normal success message.
- Exactly **one** <side effect> appears in <dashboard>.

---

## Scenario 2 - <Risk the change guards against, phrased as behaviour>
**Steps:**
1. Start <flow>.
2. Trigger the risky user action before the screen changes.

**Expected:**
- The customer is not blocked or charged twice.
- Exactly **one** <side effect> appears in <dashboard>.

---

## Scenario 3 - <Edge case> (needs dev support)
This simulates <failure>. Ask a developer to stage it: <one-sentence staging note>.

**Steps:**
1. Open the staged <record or page>.
2. Try the customer action again.

**Expected:**
- The customer sees a clear recovery or retry path.
- No duplicate <side effect> appears in <dashboard>.
- Also verify the guard still allows a fresh, non-stale <flow>.
```

## Codebase Investigation

When run inside a project or repository, investigate the structure before finalizing the draft:

1. Check repo state and shape: `git status --short`, `rg --files`, manifests, app entry points, routes, services, tests, migrations, and configuration.
2. Search for terms from the title, user flow, error text, entity names, API names, UI labels, and likely module names.
3. Read the smallest relevant files needed to identify likely ownership and implementation surfaces.
4. Add concise file references and short snippets to `**Developer Notes**` only when they help the implementer or reviewer. Use the useful number, including zero; do not add evidence-shaped filler.
5. Put longer code excerpts, search notes, dead ends, and assumptions in `context.md` under `**Codebase investigation**`.
6. If no relevant code is found, state that in `context.md`; do not invent a code path.

## What Goes Where

Put these in `work-item.md`:

- the concise title
- the audience-safe problem statement
- reproduction steps for bugs
- the high-level action
- the intended outcome
- acceptance criteria
- developer notes that materially guide delivery, including concise code references or snippets when useful
- QA-specific test scenario notes, including targeted manual QA scenarios when relevant

Put these in `context.md`:

- raw notes or copied source text
- assumptions and missing details
- implementation specifics that would distract from the main work item
- long reproduction notes, logs, or supporting details
- codebase investigation notes, relevant snippets, and searched paths

Put these in `metadata.json`:

- the chosen type and process assumption
- the title and slug
- the packet path
- the official sources used to guide the draft
