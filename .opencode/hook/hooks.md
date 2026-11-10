---
hooks:
  - event: "session.idle"
    conditions:
      - "isMainSession"
    actions:
      - bash:
          command: "bash \"$OPENCODE_PROJECT_DIR/scripts/agent-stop-checks.sh\" opencode"
          timeout: 900000
---

# OpenCode hooks

`opencode.json` loads `opencode-froggy`, which reads the hook above. When the main session goes idle it runs the repository stop gate, the same script every other harness runs.

Froggy can only block on `tool.before.*` events, so a failing gate is reported here, not enforced.
