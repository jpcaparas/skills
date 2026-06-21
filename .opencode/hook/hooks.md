---
hooks:
  # BEGIN scaffold-hooks managed opencode-froggy
  - event: "session.created"
    # Record the skills repo session baseline quietly.
    conditions:
      - "isMainSession"
    actions:
      - bash:
          command: "if [ -f \"$OPENCODE_PROJECT_DIR/scripts/agent-session-context.sh\" ]; then AGENT_HOOK_HARNESS=opencode AGENT_HOOK_PROJECT_ROOT=\"$OPENCODE_PROJECT_DIR\" AGENT_HOOK_SESSION_ID=\"$OPENCODE_SESSION_ID\" bash \"$OPENCODE_PROJECT_DIR/scripts/agent-session-context.sh\" >/dev/null; fi"
          timeout: 20000
  - event: "session.idle"
    # Run the repository stop checks after the main OpenCode session goes idle.
    conditions:
      - "isMainSession"
    actions:
      - bash:
          command: "if [ -f \"$OPENCODE_PROJECT_DIR/scripts/agent-stop-checks.sh\" ]; then AGENT_HOOK_HARNESS=opencode AGENT_HOOK_PROJECT_ROOT=\"$OPENCODE_PROJECT_DIR\" AGENT_HOOK_SESSION_ID=\"$OPENCODE_SESSION_ID\" bash \"$OPENCODE_PROJECT_DIR/scripts/agent-stop-checks.sh\" \"$OPENCODE_PROJECT_DIR\"; fi"
          timeout: 600000
  # END scaffold-hooks managed opencode-froggy
---

# OpenCode Froggy Hooks

Managed by scaffold-hooks (scaffold-hooks/opencode-froggy). Edit the scaffold plan and rerun /scaffold-hooks to refresh this block.
