---
name: nf-core-lint
description: Run and interpret `nf-core pipelines lint` to validate a Nextflow pipeline against nf-core community guidelines. Use when the user wants to check pipeline compliance, fix lint failures, run specific lint tests, or configure `.nf-core.yml` lint overrides.
license: MIT
metadata:
  author: nf-core
  version: "0.1.0"
  nf_core_tools_version: "4.0.2"
---

# nf-core pipelines lint

Validates a pipeline against nf-core guidelines — same tests that run in CI. For nf-core/tools 4.x, expect checks for strict syntax, topic-version metadata, generated container config files, and `prek`-based code quality.

## When to use

- User asks to lint, validate, or check an nf-core pipeline.
- CI lint checks are failing and the user needs to diagnose or fix them.
- User wants to disable or configure specific lint tests.

## When not to use

- Generic Nextflow scripts outside an nf-core pipeline.
- Module-level linting (`nf-core modules lint` is a separate command).

## Basic usage

```bash
nf-core pipelines lint              # lint current directory
nf-core pipelines lint --dir /path  # lint a specific pipeline
```

## Targeted runs

Use `-k` to iterate on a single failing test:

```bash
nf-core pipelines lint -k files_exist
nf-core pipelines lint -k container_configs
nf-core pipelines lint -k files_exist -k files_unchanged
```

## Key flags

| Flag | Purpose |
|------|---------|
| `--dir <path>` | Target directory (default: `.`) |
| `-k / --key <test>` | Run only named test(s), repeatable |
| `--show-passed` | Show passing tests in output |
| `--fix` | Auto-fix issues where supported; review the diff carefully |
| `--json <file>` | Write results as JSON |
| `--markdown <file>` | Write results as Markdown |

## Interpreting results

| Status | Meaning |
|--------|---------|
| **FAILED** | Must fix — blocks nf-core listing |
| **WARNED** | Best-practice issue, not blocking |
| **PASSED** | Shown only with `--show-passed` |
| **IGNORED** | Disabled in `.nf-core.yml` |

## Configuration via `.nf-core.yml`

Disable entire tests or exclude specific files:

```yaml
lint:
  actions_awsfulltest: False
  pipeline_todos: False
  files_exist:
    - docs/images/custom_logo.png
```

## Fix workflow

1. Run `nf-core pipelines lint` — note failing tests.
2. Focus: `nf-core pipelines lint -k <test_name>`.
3. For auto-fix: ensure clean git state first, then `nf-core pipelines lint --fix`.
4. Review diff before committing.
5. Re-run full lint to confirm green.

## References

- [Lint test documentation](https://nf-co.re/tools/docs/latest/pipeline_lint_tests/)
- [nf-core tools CLI docs](https://nf-co.re/docs/nf-core-tools/cli/pipelines/lint)
