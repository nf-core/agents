# AGENTS.md

> Table of contents for agents working in this repository. Keep this file short — point at deeper docs, do not duplicate them.

This repository is a portable [Agent Skills](https://agentskills.io/specification) package for [nf-core](https://nf-co.re). It is consumed by Claude Code, Codex CLI, OpenCode, Cursor, and any other skills-compatible harness.

## Map

- [`README.md`](README.md) — install and usage.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — repository layout and how harnesses load these skills.
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — how to add or modify a skill.
- [`skills/`](skills/) — one directory per skill, each with a `SKILL.md`.
- [`.claude-plugin/`](.claude-plugin/) — Claude Code plugin + marketplace manifests.
- [`prek.toml`](prek.toml) — pre-commit hooks (validation, markdown lint).
- [`prek.toml`](prek.toml) hooks use [`skills-ref`](https://github.com/agentskills/agentskills/tree/main/skills-ref) to validate every `SKILL.md`.

## Operating principles

1. **Skills are the unit of work.** Each capability lives in `skills/<name>/SKILL.md` with a tight YAML frontmatter (`name`, `description`) so harnesses can route to it.
2. **Progressive disclosure.** Keep `SKILL.md` under ~500 lines. Push detail into `references/` and load it only when needed.
3. **Portable first.** Anything Claude-Code-specific lives in `.claude-plugin/`. The `skills/` tree itself must work unmodified in Codex CLI, OpenCode, and Cursor.
4. **Mechanical enforcement.** Structure rules are checked by `prek` hooks, not prose. If a rule matters, encode it in a lint hook in [`prek.toml`](prek.toml).
5. **Repository is the source of truth.** If guidance for an agent isn't in this repo, it doesn't exist. Promote tribal knowledge into a skill or a `docs/` page.
