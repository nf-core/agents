# Cursor hook provider shape

Cursor hooks are commands declared in a hook manifest such as `hooks/cursor.json` under event names. The
shape is provider-specific manifest wiring, not the internal nf-core validation
contract.

## Hook config shape

```json
{
  "hooks": {
    "afterFileEdit": [
      {
        "command": "./scripts/format-code.sh"
      }
    ],
    "beforeShellExecution": [
      {
        "command": "./scripts/validate-shell.sh",
        "matcher": "rm|curl|wget"
      }
    ],
    "sessionEnd": [
      {
        "command": "./scripts/audit.sh"
      }
    ]
  }
}
```

## Events

Agent hooks:

- `sessionStart`
- `sessionEnd`
- `preToolUse`
- `postToolUse`
- `postToolUseFailure`
- `subagentStart`
- `subagentStop`
- `beforeShellExecution`
- `afterShellExecution`
- `beforeMCPExecution`
- `afterMCPExecution`
- `beforeReadFile`
- `afterFileEdit`
- `beforeSubmitPrompt`
- `preCompact`
- `stop`
- `afterAgentResponse`
- `afterAgentThought`

Tab hooks:

- `beforeTabFileRead`
- `afterTabFileEdit`

App lifecycle hooks:

- `workspaceOpen`

## Output shape

The Cursor hook shape documented here defines command execution and optional
matchers. It does not define a structured decision JSON contract like Claude or
Codex `Stop` hooks.

Use the Cursor adapter as an exit-code provider:

- success: human-readable report on stdout, exit `0`
- failure: human-readable report on stderr, nonzero exit

## nf-core hook manifest

The Cursor plugin manifest points at `plugins/nf-core-tools/hooks/cursor.json`.
That file uses Cursor event names and command entries.

## nf-core phase mapping

Map Cursor lifecycle events to shared internal phases rather than embedding
nf-core policy in the provider manifest:

```bash
scripts/agent_hooks/run_phase.py after-file-edit --provider cursor
scripts/agent_hooks/run_phase.py stop --provider cursor
```

Current mapping:

- `afterFileEdit` → `after-file-edit` for faster component/schema feedback
- `sessionEnd` → `stop` for final blocking validation
- `stop` → `stop` for agent runtimes that emit Cursor stop events

Add future edit or tool events as thin adapters over additional internal phases.
