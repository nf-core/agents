# hooks

Provider hook manifests live here.

- `codex.json` uses Codex hook event names and nested command entries.
- `cursor.json` uses Cursor hook event names and command entries.

Both manifests adapt provider events to the shared internal phase runner instead
of embedding nf-core validation policy directly in provider-specific JSON.
