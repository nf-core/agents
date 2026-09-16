<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/nf-core-agents_logo_dark.png">
    <img alt="nf-core/demo" src="assets/nf-core-agents_logo_light.png">
  </picture>
</h1>

[![Get help on Slack](http://img.shields.io/badge/slack-nf--core%20%23agents-4A154B?labelColor=000000&logo=slack)](https://nfcore.slack.com/channels/agents)
[![Follow on Bluesky](https://img.shields.io/badge/bluesky-%40nf__core-1185fe?labelColor=000000&logo=bluesky)](https://bsky.app/profile/nf-co.re)
[![Follow on Mastodon](https://img.shields.io/badge/mastodon-nf__core-6364ff?labelColor=FFFFFF&logo=mastodon)](https://mstdn.science/@nf_core)
[![Watch on YouTube](http://img.shields.io/badge/youtube-nf--core-FF0000?labelColor=000000&logo=youtube)](https://www.youtube.com/c/nf-core)

## About

This repository contains the official AI agent context files and [Agent Skills](https://agentskills.io/specification) for developing nf-core pipelines, modules, subworkflows, and using the nf-core toolchain. It aims to enable swift updates as the field evolves and the community discovers specific agent behaviour.

The skills follow the [Agent Skills specification](https://agentskills.io/specification) so they can be used by any skills-compatible agent, including Claude Code, Codex CLI, OpenCode, and Cursor.

## Repository rules

Adding or editing files in this repository requires approval from an nf-core core member (or maintainer with special permissions) and can only be done via pull requests.

## Skills

| Skill | Description |
|-------|-------------|
| [nf-core-pipeline](skills/nf-core-pipeline) | Create and modify [nf-core pipelines](https://nf-co.re/docs/contributing/pipelines) following community standards |
| [nf-core-lint](skills/nf-core-lint) | Run and interpret `nf-core pipelines lint` to validate pipeline compliance |
| [nf-core-module](skills/nf-core-module) | Create, modify, lint, and test nf-core modules and subworkflows with nf-core/tools 4.x conventions |
| [nf-core-containers](skills/nf-core-containers) | Choose, pin, validate, and troubleshoot nf-core containers and software dependencies |

## Installation

### Claude Code

```text
/plugin marketplace add nf-core/agents
/plugin install nf-core@nf-core-agents
```

### Codex CLI

Copy the `skills/` directory into your Codex skills path (typically `~/.codex/skills`).

### OpenCode

Clone the repository into the OpenCode skills directory:

```sh
git clone https://github.com/nf-core/agents.git ~/.opencode/skills/nf-core-agents
```

OpenCode auto-discovers `SKILL.md` files under `~/.opencode/skills/`.

### Cursor

Place the repository contents under `.cursor/skills/` in your project (or globally where Cursor reads skills from).

### Manual

Drop the `skills/` directory contents into any agent harness that follows the [Agent Skills specification](https://agentskills.io/specification).

## Files in this repository

- [`AGENTS.md`](AGENTS.md): table of contents for agents working in this repository.
- [`skills/`](skills): one directory per skill, each with a `SKILL.md`.
- [`docs/`](docs): repository-internal documentation ([architecture](docs/ARCHITECTURE.md), [contributing](docs/CONTRIBUTING.md)).

See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for how to add or modify a skill and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the repository layout.

## License

MIT — see [LICENSE](LICENSE).
