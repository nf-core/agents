# Architecture

This repository is a flat collection of [Agent Skills](https://agentskills.io/specification). There is no application code — the "product" is the `skills/` tree.

## Layout

```tree
.
├── AGENTS.md                    # entry point for agents (table of contents)
├── README.md                    # entry point for humans
├── docs/                        # repository-internal documentation
│   ├── ARCHITECTURE.md          # this file
│   └── CONTRIBUTING.md          # how to author a skill
└── skills/                      # the portable Agent Skills payload
    └── <skill-name>/
        ├── SKILL.md             # required: frontmatter + instructions
        ├── references/          # optional: progressive-disclosure docs
        ├── scripts/             # optional: executable helpers
        └── assets/              # optional: templates, schemas, fixtures
```

## Harness integration

Each harness consumes the same `skills/` tree:

| Harness     | How it loads skills                             |
|-------------|-------------------------------------------------|
| Claude Code | `/plugin marketplace add` (see README)          |
| Codex CLI   | Reads `~/.codex/skills/<name>/SKILL.md`          |
| OpenCode    | Auto-discovers `~/.opencode/skills/**/SKILL.md`  |
| Cursor      | Project-local `.cursor/skills/`                 |

Keep the `skills/` tree free of harness-specific files — it is the portable contract.
