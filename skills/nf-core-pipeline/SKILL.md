---
name: nf-core-pipeline
description: Create, lint, and modify nf-core pipelines following community standards. Use when the user is working on a Nextflow pipeline that lives under nf-core, mentions `nf-core create`, `nf-core lint`, or edits files like `main.nf`, `nextflow.config`, `nextflow_schema.json`, or anything under `conf/`, `workflows/`, or `subworkflows/local/` inside an nf-core pipeline.
license: MIT
metadata:
  author: nf-core
  version: "0.1.0"
  nf_core_tools_version: "4.0.2"
---

# nf-core pipeline

Use this skill when working inside (or scaffolding) an [nf-core pipeline](https://nf-co.re/docs/contributing/pipelines). nf-core pipelines are opinionated Nextflow DSL2 workflows with strict structural and style requirements enforced by `nf-core pipelines lint`. nf-core/tools 4.x uses strict Nextflow syntax, `prek` for hooks, and topic channels for software version reporting.

## When to use

- Creating a new pipeline (`nf-core pipelines create`; deprecated prefix-free commands such as `nf-core create` are removed in nf-core/tools 4.x).
- Adding a workflow, subworkflow, or process to an existing pipeline.
- Editing `nextflow.config`, `nextflow_schema.json`, `conf/*.config`, or `assets/schema_input.json`.
- Resolving `nf-core lint` failures.
- Bumping pipeline version, updating `CHANGELOG.md`, or preparing a release.

Do **not** use this skill for generic Nextflow scripts that are not part of an nf-core pipeline — use a plain Nextflow skill instead.

## Core conventions

- **DSL2 / strict syntax.** Keep code compatible with Nextflow strict syntax; use `NXF_SYNTAX_PARSER=v2 nextflow lint` when diagnosing parser warnings.
- **Modules** live under `modules/nf-core/<tool>/<subtool>/main.nf` and are managed via `nf-core modules install`. Do not edit them in place — patch via `nf-core modules patch`.
- **Local code** goes under `modules/local/`, `subworkflows/local/`, or `workflows/`.
- **Parameters** must be declared in `nextflow.config` *and* `nextflow_schema.json` — they must agree.
- **Tests** use [`nf-test`](https://www.nf-test.com/). Every workflow, subworkflow, and local module needs a `*.nf.test` file with a snapshot. nf-core/tools 4.x also lints container config generation and topic-based version reporting.

## Workflow

1. Run `nf-core pipelines lint` early and often — it is the source of truth.
2. For new modules, prefer `nf-core modules create` over hand-rolling.
3. After any parameter change, run `nf-core schema build` to keep `nextflow_schema.json` in sync.
4. After module/container changes, expect `nf-core pipelines lint` to check generated container config files in `conf/`.
5. Update `CHANGELOG.md` under the `## [Unreleased]` heading for every user-visible change.

## Useful commands

```bash
nf-core pipelines create            # scaffold a new pipeline
nf-core pipelines lint              # run all lint checks
nf-core pipelines lint --fix        # auto-fix where supported
nf-core modules list remote         # browse available shared modules
nf-core modules install <tool>      # add a shared module
nf-core schema build                # sync nextflow_schema.json
nf-test test --profile docker       # run pipeline tests
```

## References

- [nf-core contributing guidelines](https://nf-co.re/docs/contributing/guidelines)
- [Nextflow DSL2 docs](https://www.nextflow.io/docs/latest/dsl2.html)
- [nf-test docs](https://www.nf-test.com/)
