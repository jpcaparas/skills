# {{API_NAME}} Configuration and Access

Use this reference only for setup shared by the supported {{API_NAME}}
operations.

## Supported Access Paths

{{SUPPORTED_ACCESS_PATHS}}

Document only clients, transports, runtimes, and versions that have current
evidence. If a low-level request example is useful, label it as illustrative
and state which contract style it applies to.

## Authentication or Identity

{{AUTHENTICATION_CONTRACT}}

State explicitly whether authentication is required. When it is required,
document the credential type, acquisition location, scope, rotation or expiry
behavior, and injection mechanism supported by the target environment. Do not
assume an authorization header or bearer token.

Credentials source: {{CREDENTIALS_SOURCE}}

## Configuration Inputs

{{CONFIGURATION_INPUTS}}

Cover only applicable inputs such as environment configuration, credential
stores, configuration files, runtime arguments, or platform-native secret
managers. Prefer secret references over literal credential values. Include
platform-specific commands only when verified for that platform; never present
a Unix shell export as the universal setup path.

## Safe Access Check

Run the least-privileged, non-mutating check supported by the contract:

```{{ACCESS_CHECK_LANGUAGE}}
{{SAFE_ACCESS_CHECK}}
```

Success evidence: {{EXPECTED_ACCESS_CHECK_EVIDENCE}}

If it fails, distinguish configuration, identity, permission, transport, and
contract-version failures before changing credentials or retrying.

## See Also

- `references/api.md` -- exact operations after access is established
- `references/patterns.md` -- supported multi-step workflows
- `references/gotchas.md` -- evidenced setup and identity pitfalls

## Release Gate

Remove unsupported installation paths and replace every template token. Do not
ship sample secrets, machine-specific paths, or unverified setup commands.
