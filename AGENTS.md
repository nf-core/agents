# AGENTS.md

> Table of contents for agents working in this repository. Keep this file short — point at deeper docs, do not duplicate them.

This repository is a portable [Agent Skills](https://agentskills.io/specification) package for [nf-core](https://nf-co.re). It is consumed by Claude Code, Codex CLI, OpenCode, Cursor, and any other skills-compatible harness.

## Map

- [`README.md`](README.md) — install and usage.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — repository layout and how harnesses load these skills.
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — how to add or modify a skill.
- [`skills/`](skills/) — one directory per skill, each with a `SKILL.md`.

## Operating principles

1. **Skills are the unit of work.** Each capability lives in `skills/<name>/SKILL.md` with a tight YAML frontmatter (`name`, `description`) so harnesses can route to it.
2. **Progressive disclosure.** Keep `SKILL.md` under ~500 lines. Push detail into `references/` and load it only when needed.
3. **Portable first.** The `skills/` tree must work unmodified across Claude Code, Codex CLI, OpenCode, and Cursor.
4. **Repository is the source of truth.** If guidance for an agent isn't in this repo, it doesn't exist. Promote tribal knowledge into a skill or a `docs/` page.
