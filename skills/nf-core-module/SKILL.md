---
name: nf-core-module
description: Create, modify, lint, and test nf-core modules and subworkflows using nf-core/tools 4.x conventions. Use when editing files under modules/nf-core, modules/local, subworkflows/nf-core, subworkflows/local, modules.json, conf/modules.config, meta.yml, or nf-test files for components.
license: MIT
metadata:
  author: nf-core
  version: "0.1.0"
  nf_core_tools_version: "4.0.2"
---

# nf-core modules and subworkflows

Use this skill when creating, installing, patching, linting, or testing nf-core components. nf-core/tools 4.x expects strict Nextflow syntax, topic-based version reporting, `prek`-managed code quality, and current module metadata conventions.

## When to use

- Creating a module or subworkflow with `nf-core modules create` or `nf-core subworkflows create`.
- Installing, updating, removing, or patching shared components in a pipeline.
- Editing `main.nf`, `meta.yml`, `environment.yml`, `tests/main.nf.test`, snapshots, or `conf/modules.config`.
- Fixing `nf-core modules lint`, `nf-core subworkflows lint`, or component-related `nf-core pipelines lint` failures.
- Migrating modules from `versions.yml`-only capture to topic channels.

## Current nf-core/tools 4.x rules

- Use canonical commands: `nf-core modules <subcommand>`, `nf-core subworkflows <subcommand>`, and `nf-core pipelines <subcommand>`. Deprecated prefix-free commands such as `nf-core create` are gone.
- Keep code strict-syntax clean. Check with `NXF_SYNTAX_PARSER=v2 nextflow lint <component-path>` when syntax issues are suspected.
- Use `prek`, not `pre-commit`, for hook setup and local linting.
- Do not edit installed `modules/nf-core/*` directly unless creating a patch with `nf-core modules patch`.
- Prefer adding custom project logic in `modules/local/` or `subworkflows/local/`.

## Module authoring checklist

- One module should wrap one command or one clear subcommand. Avoid multi-tool modules unless piping saves runtime/storage or the tool semantics require it.
- Mandatory files go in `input:` channels. Mandatory non-file arguments should be `val(...)` inputs.
- Optional non-file CLI flags must be supplied through `task.ext.args`; use `args2`, `args3`, etc. for additional tools in a pipe.
- Use `task.ext.prefix` for output prefixes and default to `${meta.id}` when there is a meta map.
- Use `task.ext.when` from config instead of changing the process `when:` statement.
- Use compressed inputs/outputs where supported, e.g. `*.fastq.gz` rather than uncompressed FASTQ.
- Include a `stub:` block that creates representative files for every output channel.

## Meta maps

- File inputs should usually be tuples such as `tuple val(meta), path(reads)`.
- Meta variable names are positional: `meta`, `meta2`, `meta3`, etc.
- nf-core modules may only assume `meta.id` and `meta.single_end` as standard keys.
- Do not hard-code custom meta fields in shared modules. Pass sample-specific values via `ext.args`, `ext.prefix`, `tag`, or other process config in `conf/modules.config`.
- Subworkflows may create new meta keys, but must document them in `meta.yml`.

## Version reporting with topics

Each tool in a module must report its version. For nf-core/tools 4.x, prefer topic outputs:

```groovy
tuple val("${task.process}"), val('fastqc'), eval('fastqc --version | sed "s/FastQC v//"'), emit: versions_fastqc, topic: versions
```

Rules:

- Version strings should start with a number, not `v`.
- Use one version output per tool with unique emit names such as `versions_samtools`.
- If a tool cannot report a version, use `val('1.2.3')` and keep it synced with the container/package version.
- Template-based modules may still emit `versions.yml`, but should add `topic: versions` to that output.
- `meta.yml` must document version outputs and include a non-empty `topics:` block when topics are declared in `main.nf`.

## Testing workflow

```bash
nf-core modules lint <tool>/<subtool>
nf-core modules test <tool>/<subtool>
nf-core modules test <tool>/<subtool> --update
```

For subworkflows, use the matching `nf-core subworkflows ...` commands.

Testing expectations:

- Every module/subworkflow needs `tests/main.nf.test` and a snapshot.
- Prefer stable snapshots: sort variable lists, snapshot selected fields, and avoid volatile paths or timestamps.
- Test stubs as well as normal execution when possible.
- If tests depend on `ext.args`, configure them in the test `nextflow.config`.

## Useful commands

```bash
nf-core modules list remote
nf-core modules create <tool>/<subtool>
nf-core modules install <tool>/<subtool>
nf-core modules patch <tool>/<subtool>
nf-core modules update <tool>/<subtool>
nf-core modules lint <tool>/<subtool> --fix
nf-core modules test <tool>/<subtool> --update
nf-core subworkflows lint <name>
```

Aliases exist in nf-core/tools 4.x (`lint` → `l`, `install` → `add`/`i`, `remove` → `rm`, `update` → `up`), but use full commands in documentation and scripts for clarity.

## References

- nf-core docs: developing components
- nf-core docs: module specifications
- nf-core docs: meta maps and ext arguments
- nf-core docs: migrating to topic channels
