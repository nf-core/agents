# Generic hook provider shape

Use this shape for providers without a structured JSON hook contract.

## Input shape

Generic provider adapters take changed files from argv:

```bash
scripts/agent_hooks/run_phase.py stop path/to/file.nf
```

If no files are passed, the harness falls back to changed git files.

## Output shape

Success:

```text
nf-core stop hook: check results
- PASS: nf-core component lint
- PASS: nf-core schema check
- PASS: nf-core pipelines lint
nf-core stop hook: checks passed
```

Failure:

```text
nf-core stop hook: check results
- FAIL: nf-core pipelines lint
nf-core stop hook: checks failed; continue fixing before stopping
```

## Exit-code behavior

- success: human-readable report on stdout, exit `0`
- failure: human-readable report on stderr, nonzero exit
