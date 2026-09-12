# Source Notes

This skill adapts stable maintainability ideas into agent behavior. It does not copy any source as a rulebook.

## Influences

- nunomaduro/essentials: Treat strictness, immutability, environment-scoped safety, compatibility checks, and repository automation as executable defaults rather than review folklore. The dissection was pinned to commit `bad47a6653a035ef8033856f0c4af3b65a704293` from 2026-05-14.
- shadcn/improve: Treat planning as a product. Do recon first, verify evidence, and write self-contained plans for executors that lack session context.
- Martin Fowler's refactoring guidance: Prefer small behavior-preserving transformations and use tests to reduce risk while improving design.
- Google Engineering Practices: Optimize code review for improving code health over time, not for perfection or personal taste.
- Cognitive complexity work from SonarSource: Understandability is distinct from testability; deeply nested or mentally expensive code deserves refactoring even when branch coverage looks adequate.
- Clean Code ideas associated with Robert C. Martin: Names, functions, comments, and boundaries matter, but apply them pragmatically rather than as slogans.
- Operational engineering practice from CI/CD, shell, infrastructure, and migration work: dense glue code needs context comments because syntax alone rarely exposes external contracts, failure modes, or artifact/data-shape assumptions.

## Adaptation Choices

This skill intentionally avoids absolute rules like "never comment" or "every function must be tiny." Those rules are easy for agents to over-apply and often make code worse. It treats comments as maintainability tools when names, types, and structure cannot carry system context by themselves.

The Essentials adaptation is selective. It generalizes the repository's layered strictness, narrow configurable lifecycle, safe destructive-operation defaults, compatibility seams, lowest-supported dependency checks, and check-mode automation. It does not canonize framework-specific choices such as public class-name configuration keys, side-effectful collection pipelines, an action class for every operation, unconditional transactions, or repetitive docblocks.

Instead, it uses maintainability gates:

- Can a human understand the intent?
- Is behavior preserved?
- Are responsibilities stable?
- Is verification proportional to risk?
- Does the code fit the repository?

## Pinned Essentials Evidence

| Evidence | Adapted lesson | Caveat retained here |
|---|---|---|
| `Configurable.php` and `EssentialsServiceProvider.php` | A typed registry can separate policy selection from application when several optional startup policies share a lifecycle | Prefer a direct loop when a fluent pipeline hides dependency resolution, order, or effects |
| `ShouldBeStrict.php`, `ImmutableDates.php`, `phpstan.neon.dist`, and `pint.json` | Layer language, analyzer, formatter, and framework strictness; make value-like state immutable | Treat runtime strictness as a behavior migration in established systems |
| `ProhibitDestructiveCommands.php` plus the publish commands | Default dangerous behavior off and give overwrites confirmation, an explicit automation path, and recovery | A force flag never bypasses authorization, validation, invariants, or promised backup verification |
| `AutomaticallyEagerLoadRelationships.php`, `composer.json`, and `tests.yml` | Use the stack's compatibility seam and test lowest/current supported combinations; this source demonstrates runtime feature detection | Required capabilities must fail with context rather than silently no-op |
| Composer scripts and both GitHub Actions workflows | Compose formatter check mode, static analysis, refactor dry-runs, tests, pinned automation, and least permissions | Automated refactors still need diff review and behavior verification |

All lessons above are paraphrased from the MIT-licensed source and checked against the pinned snapshot; no upstream implementation is copied into this skill.

## Source URLs

- `https://github.com/nunomaduro/essentials/tree/bad47a6653a035ef8033856f0c4af3b65a704293`
- `https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/src/Contracts/Configurable.php`
- `https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/src/EssentialsServiceProvider.php`
- `https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/composer.json`
- `https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/.github/workflows/tests.yml`
- `https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/LICENSE.md`
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

## See Also

- `references/principles.md`
- `references/commenting.md`
- `references/guardrails-and-quality-gates.md`
