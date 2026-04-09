# {{API_NAME}} Configuration & Setup

## Table of Contents

- [Authentication](#authentication)
- [SDK Installation](#sdk-installation)
- [Environment Variables](#environment-variables)
- [Configuration Files](#configuration-files)
- [Testing Your Setup](#testing-your-setup)

---

## Authentication

### {{AUTH_PATTERN}} Setup

{{AUTH_SETUP_STEPS}}

### Where to Get Credentials

1. Go to {{CREDENTIALS_URL}}
2. {{CREDENTIAL_STEP_1}}
3. {{CREDENTIAL_STEP_2}}
4. {{CREDENTIAL_STEP_3}}

### Header Format

Every request requires:

```
{{AUTH_HEADER_NAME}}: {{AUTH_HEADER_FORMAT}}
```

{{AUTH_NOTES}}

---

## SDK Installation

### Python

```bash
pip install {{PYTHON_PACKAGE}}=={{SDK_VERSION}}
```

```python
import {{PYTHON_IMPORT}}

client = {{PYTHON_CLIENT_INIT}}
```

### Node.js / TypeScript

```bash
npm install {{NODE_PACKAGE}}@{{SDK_VERSION}}
```

```typescript
import {{NODE_IMPORT}} from '{{NODE_PACKAGE}}';

const client = {{NODE_CLIENT_INIT}};
```

### Raw HTTP (no SDK)

```bash
curl -X GET "{{BASE_URL}}/{{HEALTH_ENDPOINT}}" \
  -H "{{AUTH_HEADER_NAME}}: {{AUTH_HEADER_FORMAT}}"
```

---

## Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `{{ENV_VAR_NAME}}` | Yes | {{ENV_VAR_DESCRIPTION}} | `sk_live_...` |
| `{{ENV_VAR_2}}` | No | {{ENV_VAR_2_DESCRIPTION}} | {{ENV_VAR_2_EXAMPLE}} |

### Setting Environment Variables

```bash
# Add to ~/.bashrc or ~/.zshrc
export {{ENV_VAR_NAME}}="your-key-here"

# Or use a .env file (add to .gitignore)
echo '{{ENV_VAR_NAME}}=your-key-here' >> .env
```

---

## Configuration Files

{{CONFIG_FILE_SECTION_OR_PLACEHOLDER}}

---

## Testing Your Setup

Run this to verify your credentials work:

```bash
{{TEST_COMMAND}}
```

Expected output: {{EXPECTED_TEST_OUTPUT}}

If you get an error, check:
1. {{TROUBLESHOOTING_STEP_1}}
2. {{TROUBLESHOOTING_STEP_2}}
3. {{TROUBLESHOOTING_STEP_3}}

---

## See Also

- `references/api.md` -- endpoint details after setup is complete
- `references/patterns.md` -- common workflows
- `references/gotchas.md` -- auth-related pitfalls
