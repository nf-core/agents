# Codex hook provider shape

Source of truth: OpenAI Codex sources in `openai/codex`:

- `docs/config.md`
- `codex-rs/hooks/src/lib.rs`
- `codex-rs/hooks/src/events/stop.rs`
- `codex-rs/hooks/src/engine/output_parser.rs`
- `codex-rs/hooks/schema/generated/stop.command.input.schema.json`
- `codex-rs/hooks/schema/generated/stop.command.output.schema.json`
- `codex-rs/config/src/hook_config.rs`

## Events

Codex hook events include:

- `PreToolUse`
- `PermissionRequest`
- `PostToolUse`
- `PreCompact`
- `PostCompact`
- `SessionStart`
- `UserPromptSubmit`
- `SubagentStart`
- `SubagentStop`
- `Stop`

## nf-core hook manifest

The Codex plugin manifest points at `plugins/nf-core-tools/hooks/codex.json`.
That file uses Codex event names and nested command hook entries.

## Hook config shape

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": null,
        "hooks": [
          {
            "type": "command",
            "command": "...",
            "timeout": 600,
            "statusMessage": "..."
          }
        ]
      }
    ]
  }
}
```

## Stop input shape

Codex `Stop` input is JSON on stdin:

```json
{
  "hook_event_name": "Stop",
  "cwd": "/path/to/project",
  "session_id": "...",
  "turn_id": "...",
  "transcript_path": null,
  "model": "...",
  "permission_mode": "default",
  "stop_hook_active": false,
  "last_assistant_message": null
}
```

Important fields for this repo:

- `cwd`
- `hook_event_name`
- `stop_hook_active`
- `last_assistant_message`

## Stop output shape

Codex `Stop` output can block with clean JSON on stdout:

```json
{
  "decision": "block",
  "reason": "Continue fixing before stopping."
}
```

A successful no-block response can be empty stdout or structured JSON without a
block decision. This repo prefers structured JSON for provider adapters.

## Rules and gotchas

- `decision: "block"` requires a non-empty `reason`.
- stdout must be valid hook JSON when using JSON output; route harness logs to stderr.
- Exit code `2` plus stderr is also treated as a continuation/block prompt.
- Other nonzero exits are hook failures, not normal block decisions.
- If `stop_hook_active` is true, avoid blocking again to prevent recursive stop loops.
- Keep a distinct Codex adapter even if it initially resembles Claude. Future
  `PreToolUse`, `PermissionRequest`, and `PostToolUse` semantics differ.
