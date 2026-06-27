# Source Notes

This skill adapts language-agnostic testing guidance and PHP-inspired examples into agent instructions. It is not a direct copy of any source.

## User-Provided Direction

The motivating examples emphasize Pest-style behavior names, compact Arrange / Act / Assert structure, concrete domain values, and assertions that document both result and state. The user also required tests to act as living documentation, onboarding material, and explicit edge-case documentation, including rationale for legacy behavior.

The shared ChatGPT URL provided by the user was not readable through the browser fetch during creation, so the skill relies on the pasted examples plus the public sources below.

## Public Sources Consulted

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

## See Also

- `references/principles.md`
- `references/structure-and-fixtures.md`
