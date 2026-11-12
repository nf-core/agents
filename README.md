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

This repository contains the official AI agent context files for developing nf-core pipelines. The repository aims to enable swift updates as the field evolves and the community discovers specific agent behaviour.

## Repository rules

Adding or editing files in this repository requires approval from an nf-core core member (or maintainer with special permissions) and can only be done via pull requests.

## Files in this repository

- [`resources/pipeline/AGENTS.md`](resources/pipeline/AGENTS.md): main agent context file containing instructions for the nf-core pipeline template.
- [`resources/skills/migrating-nf-core-utils/`](resources/skills/migrating-nf-core-utils/SKILL.md): migrate vendored pipeline utilities to the nf-core-utils Nextflow plugin, update plugin pins and diagnose plugin function errors.

## Using skills

Copy the whole skill directory from `resources/skills/` into your agent's skill directory, for example `.agents/skills/` or `.claude/skills/` in a pipeline checkout. Keep its references and licence file together. Skills supplement the pipeline's own agent instructions.

The migration skill is adapted from [maxulysse/nf-core-utils-migration](https://github.com/maxulysse/nf-core-utils-migration) by Maxime U Garcia. Its original MIT notice is preserved in the [skill's LICENSE](resources/skills/migrating-nf-core-utils/LICENSE), and its source revision is recorded in the skill.
