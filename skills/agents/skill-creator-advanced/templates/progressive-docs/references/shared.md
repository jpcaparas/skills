# {{DOMAIN_NAME}} Shared Conventions

Keep this file only when multiple domain branches genuinely depend on the same
rules. If one branch owns the material, move it there and delete this file and
its route.

## Scope

{{SHARED_SCOPE_AND_CONSUMERS}}

## Terminology

| Term | Meaning | Used by |
|------|---------|---------|
{{TERMINOLOGY_ROWS}}

## Shared Setup or Preconditions

{{SHARED_SETUP_OR_PRECONDITIONS}}

## Cross-Cutting Rules

{{CROSS_CUTTING_RULES}}

## Evidenced Gotchas

{{SHARED_EVIDENCED_GOTCHAS}}

## See Also

{{CONDITION_AND_PURPOSE_CROSS_LINKS}}

Every cross-link must say when to follow it and what decision or procedure it
supports. Do not duplicate the root routing guide here.

## Release Gate

Replace every template token and delete sections without shared, evidenced
content. If this file is not needed by at least two branches, delete it before
release.
