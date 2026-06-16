# Claude Code hook provider shape

Claude Code uses JSON stdin for hook events and supports structured JSON stdout
for decisions on blocking-capable events.

## Stop input shape

Claude Code `Stop` input is JSON on stdin. Relevant fields include:

```json
{
  "hook_event_name": "Stop",
  "session_id": "...",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/path/to/project",
  "stop_hook_active": false,
  "last_assistant_message": "...",
  "background_tasks": [],
  "session_crons": []
}
```

Important fields for this repo:

- `cwd`
- `hook_event_name`
- `stop_hook_active`
- `last_assistant_message`

## Stop output shape

For `Stop`, block with clean JSON on stdout:

```json
{
  "decision": "block",
  "reason": "Continue fixing before stopping."
}
```

Allow stopping with:

```json
{
  "decision": "approve",
  "reason": "nf-core stop hook: checks passed"
}
```

## Rules and gotchas

- Use stdout for the structured response.
- Keep stdout clean JSON; send harness logs to stderr.
- The adapter should return exit code `0` when expressing a structured block.
- If `stop_hook_active` is true, avoid recursive blocking.
- `SessionEnd` is not a substitute for `Stop` because it does not provide the
  same blocking control.
