# {{TOOL_NAME}} Installation and Configuration

## Supported Environments

{{SUPPORTED_ENVIRONMENT_MATRIX}}

Document only operating systems, architectures, runtimes, package managers,
and versions backed by current evidence. Give a verified path for each claimed
environment instead of treating one shell or package manager as universal.

## Installation

{{SUPPORTED_INSTALLATION_PATHS}}

State provenance, version pinning or compatibility policy, integrity checks,
and upgrade behavior when relevant.

## Authentication or Identity

{{IDENTITY_SETUP}}

State explicitly when the tool needs no identity. Otherwise document the
credential source, minimum scope, expiry or rotation behavior, and supported
injection mechanism. Prefer platform-native secret storage or secret references
over literal credentials.

## Configuration Inputs

{{CONFIGURATION_INPUTS}}

Cover only applicable sources such as flags, environment configuration,
credential stores, or configuration files. State precedence when multiple
sources can set the same value. Include platform-specific commands only when
verified for that platform.

## Safe Verification

Run the least-privileged, non-mutating verification supported by the tool:

```{{COMMAND_FENCE_LANGUAGE}}
{{SAFE_VERIFY_COMMAND}}
```

Success evidence: {{EXPECTED_VERIFY_EVIDENCE}}

If it fails, distinguish installation, version, identity, permission,
configuration, connectivity, and target-selection failures before retrying.

## See Also

- `references/commands.md` -- exact commands and outcomes
- `references/patterns.md` -- supported multi-step workflows
- `references/gotchas.md` -- evidenced setup and platform pitfalls

## Release Gate

Replace every template token and remove unsupported environment or installation
paths. Do not ship sample secrets, machine-specific paths, or unverified setup
commands.
