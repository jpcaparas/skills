# Canonical Code-Review Rules

Every review invocation applies all twelve peer rules:

1. Trace each changed behavior to an explicit requirement.
2. Check boundary inputs and failure outcomes.
3. Preserve established public contracts unless the change explicitly migrates them.
4. Keep side effects visible and scoped.
5. Prefer names that reveal intent without comments.
6. Remove duplicated policy and unreachable code.
7. Keep types and data shapes precise at boundaries.
8. Check authorization before any protected effect.
9. Ensure logs and errors do not expose secrets.
10. Require tests for changed behavior and meaningful failure paths.
11. Verify configuration and deployment changes with repository-native checks.
12. Record any changed file or rule that could not be reviewed and why it is out of scope.

A review is complete when every changed file has been checked against all applicable rules or is explicitly recorded as out of scope with a reason.
