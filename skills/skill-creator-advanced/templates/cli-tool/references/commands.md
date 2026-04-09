# {{TOOL_NAME}} Commands Reference

## Table of Contents

- [Overview](#overview)
- [Global Flags](#global-flags)
- [{{COMMAND_GROUP_1}}](#{{COMMAND_GROUP_1_ANCHOR}})
- [{{COMMAND_GROUP_2}}](#{{COMMAND_GROUP_2_ANCHOR}})
- [{{COMMAND_GROUP_3}}](#{{COMMAND_GROUP_3_ANCHOR}})
- [Exit Codes](#exit-codes)

---

## Overview

Use this file for the exact `{{TOOL_NAME}}` subcommands, flags, and output modes.

**Binary:** `{{TOOL_BIN}}`  
**Version:** `{{TOOL_VERSION}}`

## Global Flags

| Flag | Meaning | Notes |
|------|---------|-------|
| `{{GLOBAL_FLAG_1}}` | {{GLOBAL_FLAG_1_DESCRIPTION}} | {{GLOBAL_FLAG_1_NOTES}} |
| `{{GLOBAL_FLAG_2}}` | {{GLOBAL_FLAG_2_DESCRIPTION}} | {{GLOBAL_FLAG_2_NOTES}} |
| `{{GLOBAL_FLAG_3}}` | {{GLOBAL_FLAG_3_DESCRIPTION}} | {{GLOBAL_FLAG_3_NOTES}} |

## {{COMMAND_GROUP_1}}

### `{{TOOL_BIN}} {{COMMAND_1}}`

```bash
{{TOOL_BIN}} {{COMMAND_1}} {{COMMAND_1_USAGE}}
```

**Required flags:** {{COMMAND_1_REQUIRED_FLAGS}}  
**Common output:** {{COMMAND_1_OUTPUT}}

## {{COMMAND_GROUP_2}}

{{COMMAND_GROUP_2_CONTENT}}

## {{COMMAND_GROUP_3}}

{{COMMAND_GROUP_3_CONTENT}}

## Exit Codes

| Exit Code | Meaning | Resolution |
|-----------|---------|------------|
| `0` | Success | No action needed |
| `{{EXIT_CODE_1}}` | {{EXIT_CODE_1_MEANING}} | {{EXIT_CODE_1_FIX}} |
| `{{EXIT_CODE_2}}` | {{EXIT_CODE_2_MEANING}} | {{EXIT_CODE_2_FIX}} |

## See Also

- `references/configuration.md` -- installation and auth setup
- `references/patterns.md` -- multi-step workflows and pipelines
- `references/gotchas.md` -- shell quirks and edge cases
