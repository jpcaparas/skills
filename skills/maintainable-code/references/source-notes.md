# Source Notes

This skill adapts stable maintainability ideas into agent behavior. It does not copy any source as a rulebook.

## Influences

- shadcn/improve: Treat planning as a product. Do recon first, verify evidence, and write self-contained plans for executors that lack session context.
- Martin Fowler's refactoring guidance: Prefer small behavior-preserving transformations and use tests to reduce risk while improving design.
- Google Engineering Practices: Optimize code review for improving code health over time, not for perfection or personal taste.
- Cognitive complexity work from SonarSource: Understandability is distinct from testability; deeply nested or mentally expensive code deserves refactoring even when branch coverage looks adequate.
- Clean Code ideas associated with Robert C. Martin: Names, functions, comments, and boundaries matter, but apply them pragmatically rather than as slogans.
- Operational engineering practice from CI/CD, shell, infrastructure, and migration work: dense glue code needs context comments because syntax alone rarely exposes external contracts, failure modes, or artifact/data-shape assumptions.

## Adaptation Choices

This skill intentionally avoids absolute rules like "never comment" or "every function must be tiny." Those rules are easy for agents to over-apply and often make code worse. It treats comments as maintainability tools when names, types, and structure cannot carry system context by themselves.

Instead, it uses maintainability gates:

- Can a human understand the intent?
- Is behavior preserved?
- Are responsibilities stable?
- Is verification proportional to risk?
- Does the code fit the repository?

## Source URLs

- `https://github.com/shadcn/improve`
- `https://raw.githubusercontent.com/shadcn/improve/main/skills/improve/SKILL.md`
- `https://martinfowler.com/books/refactoring.html`
- `https://martinfowler.com/bliki/CodeSmell.html`
- `https://google.github.io/eng-practices/review/reviewer/standard.html`
- `https://www.sonarsource.com/resources/cognitive-complexity/`
- `https://www.sonarsource.com/blog/cognitive-complexity-because-testability-understandability`
- `https://www.php.net/manual/en/language.basic-syntax.comments.php`
- `https://docs.python.org/3/tutorial/controlflow.html#documentation-strings`
- `https://laravel.com/docs/13.x/eloquent-mutators`
- `https://laravel.com/docs/13.x/routing`
- `https://nextjs.org/docs/app/api-reference/file-conventions/route`
- `https://nextjs.org/docs/app/getting-started/fetching-data`
