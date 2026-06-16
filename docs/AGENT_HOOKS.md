# Agent hook provider notes

This repo keeps nf-core validation policy provider-neutral in `scripts/agent_hooks/`.
Provider-specific hook formats belong in adapter modules under
`scripts/agent_hooks/providers/`.

## Internal contract

The internal interface is a phase report, not a provider wire format:

```python
report = run_phase("stop", files)
```

Provider adapters translate that report into each agent runtime's required stdout,
stderr, and exit-code behavior.

## Provider shape references

- [Codex](agent-hooks/codex.md)
- [Claude Code](agent-hooks/claude.md)
- [Cursor](agent-hooks/cursor.md)
- [Generic exit-code providers](agent-hooks/generic.md)
