# Maintainability Principles

Use these principles when the SKILL.md gate is not enough.

## Prime Directive

Maintainable code is code a future maintainer can understand, verify, and change with bounded risk. It is not code that merely looks tidy.

Favor code that makes domain behavior obvious over code that hides domain behavior behind clever generic machinery.

## Practical Defaults

1. Local consistency beats imported taste.
   Apply the repository's existing architecture, naming, formatting, error handling, and testing shape unless it is actively causing the problem.

2. Explicit beats implicit for domain policy.
   Business rules, permission checks, data transformations, retries, and error mappings should be named and testable. Avoid policy hidden in callbacks, magic strings, reflection, or incidental config.

3. Strong types are maintenance tools.
   When the language supports it, prefer typed inputs, typed outputs, discriminated states, enums, and narrow interfaces. Avoid `any`, dictionary bags, and stringly typed modes unless the boundary truly requires them.

4. Simple control flow beats clever composition.
   Use guard clauses, early normalization, and direct branches when they reveal the story. Reach for higher-order functions, metaprogramming, or dynamic dispatch only when they simplify real variation.

5. Tests should protect behavior, not implementation trivia.
   Test observable outcomes, edge cases, and contracts. For refactors, add characterization tests before moving behavior.

6. Comments explain why.
   Good comments record constraints, invariants, tradeoffs, data provenance, security assumptions, and external quirks. They do not translate obvious code into prose.

## Human Readability Checks

Ask these questions before finishing:

- Can a maintainer locate the feature's entry point quickly?
- Do names describe domain meaning instead of implementation mechanics?
- Are side effects visible at module boundaries?
- Is there one obvious place to change the rule later?
- Does the test name explain the behavior being protected?
- Would deleting the new abstraction make the code easier to understand?

## Balancing Forward Progress

Perfect code is not the target. Ship a change when it improves code health, preserves behavior, and leaves the next maintainer with a clearer system than before.

When a larger cleanup is real but out of scope, leave an actionable note in the final response or create a follow-up plan. Do not smuggle broad cleanup into an unrelated fix.
