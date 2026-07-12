# Source Notes

This skill adapts language-agnostic testing guidance and examples from multiple ecosystems into agent instructions. Pest is one illustrative influence, not a requirement, and no source is copied as a rulebook.

## Original Direction

The motivating examples emphasize Pest-style behavior names, compact Arrange / Act / Assert structure, concrete domain values, and assertions that document both result and state. The skill treats tests as living documentation, onboarding material, and explicit edge-case documentation, including rationale for legacy behavior.

## Public Sources Consulted

- nunomaduro/essentials, pinned at commit `bad47a6653a035ef8033856f0c4af3b65a704293` (2026-05-14):
  - https://github.com/nunomaduro/essentials/tree/bad47a6653a035ef8033856f0c4af3b65a704293
  - https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/src/Configurables/PreventStrayRequests.php
  - https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/src/Configurables/FakeSleep.php
  - https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/tests/Commands/EssentialsPintCommandTest.php
  - https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/tests/Commands/EssentialsRectorCommandTest.php
  - https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/.github/workflows/tests.yml
  - https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/LICENSE.md

- Pest documentation on writing tests and datasets:
  - https://pestphp.com/docs/writing-tests
  - https://pestphp.com/docs/datasets
- PHPUnit documentation on fixtures, test doubles, and risky tests:
  - https://docs.phpunit.de/en/12.5/fixtures.html
  - https://docs.phpunit.de/en/12.5/test-doubles.html
  - https://docs.phpunit.de/en/12.5/risky-tests.html
- Google Testing Blog on DAMP tests:
  - https://testing.googleblog.com/2019/12/testing-on-toilet-tests-too-dry-make.html
- Martin Fowler's testing guide and practical test pyramid article:
  - https://martinfowler.com/testing/
  - https://martinfowler.com/articles/practical-test-pyramid.html

## Adaptation Notes

- Pest influenced the short behavior-description examples, not a PHP-only requirement.
- PHPUnit influenced fixture-noise and test-double guidance.
- Google Testing Blog influenced the DAMP-over-DRY rule for test readability.
- Fowler influenced the balanced portfolio framing: unit, integration, contract, and end-to-end tests should work together instead of chasing one universal shape.
- Essentials influenced default-deny network tests, fake waiting, explicit restoration of framework globals, configuration decision matrices, capability-based compatibility coverage, lowest-supported dependency testing, and outcome-focused command tests.

The Essentials dissection was deliberately critical rather than imitative. Two upstream assertions became counterexamples here: one compares a file-existence boolean with old file contents, and another checks a similarly named backup path instead of the path production writes. Both can remain green while the intended behavior is broken. The skill adapts that failure mode into typed assertion-subject and exact-artifact guidance; it does not copy the tests.

All Essentials lessons are paraphrased from the pinned MIT-licensed source. Framework-specific defaults remain evidence, not universal rules.

## See Also

- `references/principles.md`
- `references/structure-and-fixtures.md`
- `references/side-effects-and-compatibility.md`
