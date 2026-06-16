# Architecture

This repository is a flat collection of [Agent Skills](https://agentskills.io/specification) packaged for multiple harnesses. There is no application code — the "product" is the `skills/` tree.

## Layout

```text
.
├── AGENTS.md                    # entry point for agents (table of contents)
├── README.md                    # entry point for humans
├── .claude-plugin/              # Claude Code marketplace manifest
│   └── marketplace.json
├── docs/                        # repository-internal documentation
│   ├── ARCHITECTURE.md          # this file
│   ├── CONTRIBUTING.md          # how to author a skill
│   └── AGENT_HOOKS.md           # provider hook wire-format notes
├── skills/                      # the portable Agent Skills payload
│   └── <skill-name>/
│       ├── SKILL.md             # required: frontmatter + instructions
│       ├── references/          # optional: progressive-disclosure docs
│       ├── scripts/             # optional: executable helpers
│       └── assets/              # optional: templates, schemas, fixtures
├── prek.toml                    # pre-commit hooks (uses skills-ref)
└── .markdownlint.json
```

## Harness integration

Each harness consumes the same `skills/` tree, with one shim per harness:

| Harness     | How it loads skills                                         | Shim in this repo            |
|-------------|-------------------------------------------------------------|------------------------------|
| Claude Code | `/plugin marketplace add` → root marketplace points at plugin | `plugins/nf-core-tools/.claude-plugin/`            |
| Codex CLI   | Reads `~/.codex/skills/<name>/SKILL.md`                     | `skills/` (copied in)        |
| OpenCode    | Auto-discovers `~/.opencode/skills/**/SKILL.md`             | clone whole repo             |
| Cursor      | Project-local `.cursor/skills/`                             | clone whole repo             |

Anything harness-specific MUST stay in its shim directory. The `skills/` tree is the portable contract. Provider hook wire-format notes live in [`docs/AGENT_HOOKS.md`](AGENT_HOOKS.md).

## Invariants enforced mechanically

`prek` runs these on every commit:

- `SKILL.md` has valid frontmatter (`name`, `description`, no unknown fields, name matches directory).
- `name` field obeys the spec (`^[a-z0-9]+(-[a-z0-9]+)*$`, ≤ 64 chars).
- `description` ≤ 1024 chars.
- Markdown passes `markdownlint`.
- JSON manifests parse.

If a rule matters enough to discuss, it belongs in a hook in [`prek.toml`](../prek.toml), not in prose.
