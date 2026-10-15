# Conflict playbook

General rules for resolving template sync conflicts. Rules for one tools release are in `releases/<version>.md`; when a release file and this playbook disagree, follow the release file.

## Orientation

- You work on the bot's sync branch and merge `dev` into it.
- `ours` / `HEAD` is the template side. `theirs` is the pipeline side (`dev`).
- `git checkout --theirs <file>` takes the pipeline version. `git checkout --ours <file>` takes the template version.

## Principles

1. Copy text exactly from one side. Combine the two sides when both changes are necessary. Write new code only when no copy works, and then follow `nextflow-docs.md`.
2. Keep everything that is specific to the pipeline: parameters, profiles, `includeConfig` lines, the DOI, contributors, custom code, documentation and changelog history.
3. Take the template change for boilerplate: CI workflows, linting configuration, template modules, badges, version numbers.
4. Do not add back a `TODO nf-core` comment that the pipeline removed. Keep one only if the pipeline has it on `dev`. The template always has these comments, and pipeline developers remove them.
5. Never edit generated files by hand: `ro-crate-metadata.json`, `conf/containers_*.config`, `modules.json`, the template modules and subworkflows, and nf-test snapshots. The scripts handle them.
6. Record each decision in `decisions.json` (see `report-style.md`).

## Files

### `.nf-core.yml`

- Take `nf_core_version` from the template.
- Keep the `lint:` settings and all other pipeline keys. Keep `template.skip_features`.
- Remove lint entries for files that no longer exist, and duplicate keys.

### `nextflow.config`

- Keep `manifest.doi`, `manifest.contributors`, `manifest.diagram` and all pipeline `params`.
- Keep the higher `manifest.nextflowVersion` and the higher plugin versions.
- Keep all pipeline `includeConfig` lines and profiles. Take new template profiles and settings.
- A common mistake is to take the template side for the whole file. This loses the DOI and `includeConfig` lines (seen in nf-core/fastqrepair#32).

### `CHANGELOG.md`

- Keep the pipeline header and all history lines.
- Add one line for the sync under the current development version, for example: `- [#123](https://github.com/nf-core/<pipeline>/pull/123) Template update for nf-core/tools v4.1.0`.

### `README.md`

- Take the template version badge.
- Make the Nextflow version badge match `manifest.nextflowVersion` in `nextflow.config`. Some pipelines pin an older minimum version on purpose.
- Keep the Zenodo DOI and all pipeline text.

### `main.nf` and `workflows/<pipeline>.nf`

- By default keep the pipeline version. The template version is boilerplate that the pipeline has usually changed on purpose.
- Examine each hunk. Take template changes that the pipeline needs, for example a new argument for an nf-core subworkflow.
- Remove template declarations that the pipeline does not use (seen in nf-core/rnaseq#1827).
- Make sure that no pipeline code is lost (seen in nf-core/hlatyping#231).

### `subworkflows/local/utils_nfcore_<pipeline>_pipeline/main.nf`

- Keep the pipeline logic.
- Take the template changes to the calls of nf-core subworkflows. The calls must match the updated subworkflow, and `nextflow lint` reports a wrong number of arguments.

### `conf/base.config`

- Take the template version. Add back the pipeline's own labels and resource settings.

### `conf/igenomes.config` and `conf/igenomes_ignored.config`

- The template owns these files. Take the template version.
- If the pipeline added genomes or keys, add them back with the syntax of the new template file. This is new code: check it against the Nextflow docs, and set `needs_review`.

### `conf/modules.config`

- The pipeline owns this file. Keep the pipeline version.
- Apply the template change only where it configures a template module, for example `MULTIQC`.
- If the pipeline deleted this file (some pipelines put module config next to each module), keep the deletion. Apply the same change where the pipeline now configures that module.

### `conf/test.config`, `conf/test_full.config`, `tests/nextflow.config`

- Take the template form for shared settings.
- Before you change `pipelines_testdata_base_path`, check how `conf/test*.config` uses it. If the pipeline adds its own path to it (for example `crisprseq/...`), keep the pipeline value.
- Keep the pipeline parameters and input paths.

### `tests/.nftignore`

- Take the template entries and keep the pipeline entries. Do not leave an empty line at the end.

### `.github/workflows/*` and `.github/actions/*`

- Take the template version, including action versions and pins.
- Keep the pipeline additions, for example extra test profiles, tags or steps.

### `.gitignore` and `.prettierignore`

- Put the template entries first and the pipeline entries at the end. Lint checks that the template entries are present.

### `assets/multiqc_config.yml`

- Take the template lines before `disable_version_detection: true`. Keep the pipeline lines after it.

### `docs/*.md`, `CITATIONS.md`, `nextflow_schema.json`, `assets/schema_input.json`

- Keep the pipeline content. Take the template boilerplate changes.
- Never remove a pipeline parameter from `nextflow_schema.json`.

### Files that the template deleted or renamed

- Delete them. If the pipeline still needs something in them (for example custom CI tests), move that content to the new file, and record a decision with category `kept` or `pipeline`.

### Logo images

- `assets/nf-core-<pipeline>_logo_light.png` and `docs/images/nf-core-<pipeline>_logo_{light,dark}.png`: always keep the file that is already in the pipeline. `prepare.py` does this. To do it by hand: `git checkout <dev sha> -- <path>`.
- This is a known issue: `nf-core pipelines lint` (`files_unchanged`) draws the logos again and compares them. The result depends on the local fonts and image libraries, so the test can fail for a correct file, often on macOS.
- Do not run `nf-core pipelines lint --fix files_unchanged` for logos, and do not commit logos that lint or `nf-core pipelines create-logo` made. If `git diff <dev sha> -- <path>` shows no difference, record the lint failure as this known issue.

### Pipeline copies of template files

- Apply the template change to pipeline files that copy or replace a template file. Examples: a second `awsfulltest_*.yml` workflow, or the pipeline's own workflows when it deleted `workflows/<pipeline>.nf`. Calls to updated template modules (`FASTQC`, `MULTIQC`) must match the new module inputs and outputs.

### Files that the pipeline deleted

- If the template changed a file that `dev` deleted, keep the deletion unless the template change is necessary. Record the decision.

## Lint failures that the merge did not cause

- If `files_unchanged` fails for a file that is identical to the bot's template commit (`git diff <template commit> -- <file>` shows nothing), the local tools environment causes it. Record it; do not edit the file. Logo images are the usual case (see "Logo images").
- Errors that are also on `dev` are not caused by the merge. Fix them only if the fix is small and safe; otherwise record them as a follow-up.

## When you are not sure

- Look at how the reference PRs resolved the same file (in `worklist.md`).
- Choose the option that keeps pipeline behaviour unchanged, and set `needs_review` to `true`.
- Ask the user if a choice can change the results of the pipeline.
