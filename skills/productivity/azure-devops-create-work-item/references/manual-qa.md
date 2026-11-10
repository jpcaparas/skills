# Manual QA scenarios

Use this contract whenever `**Test Scenario**` contains manual QA scenarios. The output should read like a thoughtful senior tester chose the checks, not like a generated permutation matrix.

In `work-item.md`, keep the existing `**Test Scenario**` section label and start the content with `Test environment notes:`. For a standalone QA-only response, include a top heading such as `# <Ticket> - <Change summary>: Manual QA Scenarios`.

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
