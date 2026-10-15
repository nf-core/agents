# Nextflow code: check the docs, then validate

Nextflow syntax changes between versions (strict syntax, typed parameters, new operators, deprecations). Code that looks correct from memory can be wrong for the version that the pipeline uses. Do not guess.

## When to look up the docs

- Code that you copy exactly from the template side or the pipeline side: no lookup is necessary. `nextflow lint` validates it.
- Any other Nextflow code, including code that you combine from both sides into a new form: look it up first.
- This applies to `.nf` files, `.config` files and Groovy closures in config.

## Where to look

1. `sources.md` gives the docs source for the pipeline's minimum Nextflow version (`manifest.nextflowVersion`), and the list of pages. The URL has this form:

   ```
   https://raw.githubusercontent.com/nextflow-io/nextflow/v<version>/docs/<page>
   ```

   Older releases use `.md` pages. Newer releases use `.mdx`. Use the page names from the list in `sources.md`.

2. Useful pages:
   - `strict-syntax` and `reference/syntax`: what the language allows.
   - `config` and `reference/config`: config syntax, scopes and options.
   - `reference/process`, `reference/operator`, `workflow`: directives, operators, workflow syntax.
   - `migrations/<version>` and `deprecations`: what changed and what is removed.

3. The nf-core strict syntax guide: https://nf-co.re/docs/tutorials/migrate_to_strict_syntax/config_strict_syntax

## What to record

For each decision that contains new Nextflow code, put the docs pages that you used in `nextflow_docs` (a list of URLs). `finalise.py check` fails if a `.nf` or `.config` file has lines from neither side and no decision for that file lists `nextflow_docs`.

## Validation

`finalise.py check` runs these commands. You can also run them while you work:

| Command                                         | What it finds                                                             |
| ----------------------------------------------- | ------------------------------------------------------------------------- |
| `nextflow lint <file or dir>`                   | Syntax errors, strict-syntax problems, wrong number of arguments in calls |
| `nextflow config -flat -profile test .`         | Config that does not parse                                                |
| `nf-core pipelines lint`                        | Template rules, schema problems, merge markers                            |
| `nf-test test tests/` (only if the user agrees) | Pipeline runs that fail or give different results                         |

Fix every error that the merge caused. Do not change pipeline behaviour only to make a check pass. If a check fails for a reason that is not in the merge (for example a known tool bug), record it in the report.

## Common traps

- Block syntax and map syntax in config are different: `params { genomes { 'GRCh38' { fasta = '...' } } }` and `params.genomes = [ 'GRCh38': [ fasta: '...' ] ]`. Use the syntax of the file that you keep, and do not mix them.
- Strict syntax uses `channel`, not `Channel`. Implicit closure parameters (`it`) are deprecated.
- `includeConfig` statements and profiles must stay in the same order as in the template, so that later settings override earlier ones.
- When you change a `publishDir` setting, keep the same output paths and file names (for example `${meta.id}` in a path).
