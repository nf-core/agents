# nf-core: agents

This is the main AI context file for nf-core pipelines. All AI agents and coding assistants must read and strictly follow the rules contained in this document.

## Nextflow language
Unless otherwise stated, all code in the repository is written in the Nextflow programming language. The documentation can be found at https://docs.seqera.io/nextflow/.

## Natural language
All comments and documentation must be written in English with British spelling. Documentation files should additionally follow the style guide at https://nf-co.re/docs/developing/documentation/style-guide.

## Nextflow pitfalls
TBC

## nf-core template structure
The directory you are working on was created with the nf-core pipeline template. It follows a strict directory structure, demonstrated below:

```
.
├── AGENTS.md // this file
├── assets                 // miscellaneous files that don't belong in other directories; do not add files here unless directly prompted
│   ├── multiqc_config.yml // configuration for the MultiQC report
│   ├── samplesheet.csv    // example valid samplesheet
│   └── schema_input.json  // JSON schema describing the samplesheet format
├── bin           // scripts for local modules
|   ├── script.py // all scripts must start with a shebang
|   └── other_script.R
├── CHANGELOG.md // changelog, should be updated after every substantial change
├── CITATIONS.md // list of tool citations, should be updated when new tools are added
├── conf                        // directory containing Nextflow configurations for the pipeline
│   ├── base.config             // config file with default nf-core settings, do not edit
│   ├── igenomes.config         // config file with AWS paths for common reference genomes, do not edit
│   ├── igenomes_ignored.config // do not edit
│   ├── modules.config          // config file with settings for all modules
│   ├── test.config             // config file with settings and parameters for a quick self-test
│   └── test_full.config        // config file with settings and parameters for a complete self-test
├── docs                // documentation in Markdown format, do not add files unless prompted
│   ├── CONTRIBUTING.md // contributing rules, follow and do not edit
│   ├── images          // images used in documentation files, do not add files
│   │   └── ...
│   ├── output.md       // document describing pipeline outputs, edit if the outputs change
│   ├── README.md       // dummy file for GitHub, do not edit 
│   └── usage.md        // document describing the correct usage of the pipeline
├── LICENSE // do not edit
├── main.nf // core Nextflow script, may need editing if input structure changes
├── modules // Nextflow DSL2 modules
│   ├── local            // local modules (see section below)
|   |   └── mymodule     // each module must be in a separate directory 
|   |       ├── main.nf  // file with Nextflow code
|   |       └── meta.yml // YAML files with module description
│   └── nf-core          // nf-core modules (see section below)
│       ├── fastqc
│       |   ├── main.nf  // Nextflow script, may be edited if necessary
|       |   └── ...      // do not edit other files in nf-core modules
|       └── samtools
|           └── sort     // nf-core modules may have 2 levels of directories
|               ├── main.nf
|               └── ...
├── modules.json           // list of nf-core modules, do not edit
├── nextflow.config        // main pipeline configuration, edit when parameters change
├── nextflow_schema.json   // JSON schema with pipeline parameters
├── nf-test.config         // nf-test configuration (see below)
├── README.md              // main documentation file
├── ro-crate-metadata.json // automatically generated, do not edit
├── subworkflows                       // Nextflow subworkflows (see below)
│   ├── local                          // local subworkflows
│   │   └── utils_nfcore_demo_pipeline
│   │       └── main.nf
│   └── nf-core                        // nf-core subworkflows
│       ├── utils_nfcore_pipeline
│       │   ├── main.nf
│       │   └── ...
│       └── ...
├── tests                    // nf-test end-to-end tests for the pipeline
│   ├── default.nf.test      // main test script, must exist
│   ├── default.nf.test.snap // test output snapshot, do not edit
│   ├── nextflow.config      // configuration used in tests only
|   ├── other.nf.test        // other tests might exist if the pipeline has multiple modes
│   └── other.nf.test.snap   // every test must have a snapshot
├── tower.yml   // configuration for running in Seqera Platform
└── workflows   // do not add files 
    └── demo.nf // Nextflow file containing main pipeline logic
```

Several files have been skipped from the treemap. These files are rarely edited and you should not edit them unless prompted. The pipeline you are working on might have minor changes, e.g. a configuration file split into multiple parts.

## Key nf-core terms
- **Module**: a single process that achieves a single, well defined task (e.g. aligning reads to a genome)
- **Subworkflow**: a sequence of chained modules that achieve a specific objective (e.g. FASTQ cleanup and quality check)
- **Workflow**: a complete sequence of modules and subworkflows that performs a specific analysis (e.g. bulk RNA-seq analysis)
- **Pipeline**: a full, executable Nextflow project with input and output handling

A pipeline contains one workflow, and may contain any number of subworkflows and modules.

## Modules
nf-core has a remote module repository at https://github.com/nf-core/modules. You should use them whenever possible. You can find available modules and install modules with nf-core tools (see below). If a new module would only use a single tool, suggest adding it to nf-core modules to the user.

You should generally not edit nf-core modules in the pipeline repository. You may edit their `main.nf` if necessary. If you do it, you must run `nf-core modules patch {name}` afterwards.

The pipeline also has a local modules directory. If a task cannot be reasonably achieved with existing nf-core modules and has no use outside of the pipeline, you can create a local module for it. Use nf-core tools (see below) to create the module boilerplate and then edit the files.

## Subworkflows
The same repository also contains nf-core subworkflows. Use them whenever they are relevant to the task. If none is applicable, you can create local subworkflows liberally.

## Pipeline structure
An nf-core pipeline contains 3 main parts called by the root `workflow` block in `main.nf`:
- initialisation workflow (defined in `subworkflows/local/utils_nfcore_{name}_pipeline/main.nf`): handles input processing and validation
- main workflow (defined in `workflows/{name}.nf`): contains the main analysis, including generation of all output files
- completion workflow (defined in `subworkflows/local/utils_nfcore_{name}_pipeline/main.nf`): handles sending completion notifications

## Configuration files
Nextflow automatically reads settings from a file called `nextflow.config`. In nf-core, some settings are moved to other files in the `conf/` directory and included with `includeConfig`. The following files may exist by default:
- base.config: contains default resource allocation for modules; it is defined by nf-core and should not be edited
- igenomes.config: contains paths to common reference genomes in a custom AWS S3 bucket; do not edit
- igenomes_ignored.config: contains replacement settings when iGenomes is not used; do not edit
- modules.config: contains settings for all modules; should contain a single `process` block with multiple `withName` selectors; edit as required
- test.config: contains parameters and settings for a minimal self-test; this test should take a few minutes and only test the basic functionality with minimal input
- test_full.config: contains parameters and settings for a complete self-test; this test should check as much functionality as possible with realistic input, and has no runtime limit

## Meta map
Nextflow is designed for parallel processing of multiple samples. To facilitate this, nf-core uses a meta map: a Nextflow map passed along with each file that contains sample-specific information. The map is automatically created during input processing and nearly all nf-core modules pass it through.

The meta map should at least contain an `id` field with a unique identifier. nf-core modules and subworkflows may only access `id` and `single_end` fields. Local modules, subworkflows, and the workflow may create and access any meta fields that are useful for the pipeline.

## nf-core tools
nf-core provides a CLI toolkit for working with the nf-core template. The core command is `nf-core`. You should always prefer using the tools to creating files manually when possible.

The following subcommands are most relevant to your work:
- `nf-core modules create {name}`: create a new local module
- `nf-core modules info {name}`: obtain detailed information about an nf-core module
- `nf-core modules install {name}`: install a module from a remote repository
- `nf-core modules list remote [query]`: list all available nf-core modules; if a query is provided only matching modules are returned
- `nf-core modules patch {name}`: generate a patch file after editing an nf-core module
- `nf-core modules update {name}`: update a previously installed remote module
- `nf-core pipelines lint`: run lint tests on a pipeline directory
- `nf-core subworkflows create {name}`: create a local subworkflow
- `nf-core subworkflows info {name}`: obtain detailed information about an nf-core subworkflow
- `nf-core subworkflows install {name}`: install a subworkflow from a remote repository
- `nf-core subworkflows list remote [query]`: list all available nf-core subworkflows; if a query is provided only matching modules are returned
- `nf-core subworkflows update {name}`: update a previously installed nf-core subworkflow

The {name} for subtool modules must be written with a slash, like `samtools/sort`.

You can find the complete documentation for nf-core tools at https://nf-co.re/docs/nf-core-tools/.

## nf-test and testing
nf-core uses a testing framework called nf-test to create and run module, subworkflow, and pipeline tests. Each pipeline must have at least 1 test case, with a normal and stub variant. Tests have a standardized syntax, with setup (optional), input ("when"), and assertion ("then") sections. Tests at a path can be executed with `nf-test test {path}`.

Most tests create at least 1 snapshot file that contains a combination of file counts, file paths, and file hashes. The snapshots are used to verify output stability. Never edit snapshots manually. If you expect the output to change (e.g. after a tool update), you can update the snapshot with `nf-test test --update-snapshot`.

Full nf-test documentation is available at https://www.nf-test.com/docs/getting-started/ and other pages inside https://www.nf-test.com/docs/.

## Branch policy
This repository has at least 3 git branches: `main` (or `master`), `dev`, and `TEMPLATE`. The TEMPLATE branch is managed by nf-core tools and it is forbidden to switch to it or run any command that would write to it. Directly writing to `main` is also forbidden, and all changes to that branch must be made through a pull request.

If you are working directly in the nf-core repository (git origin is `nf-core/{pipeline}`), you must create a new branch for each feature (with a meaningful name) and open a pull request to `dev`. If you are working on a fork (`{username}/{pipeline}`), you can push directly to origin/dev and open a PR to upstream/dev.

If you only want to fix a bug in a released version of a pipeline, you should instead create a branch called `patch` from `main`, work in it, and open a PR to nf-core main once done.

## Commit rules and routine
Each commit should be as atomic as possible, that is, only contain one logical change. There is no limit on the number of files in a commit. There is no mandated commit message format, but the commit title should be concise and written in imperative mood. If the commit consists only of installing or updating an nf-core module or subworkflow, limit the commit title to `Install/update nf-core module/subworkflow {name}`.

Before each commit, perform all of the following:
1. Run `nextflow lint .` to lint all Nextflow scripts in the repository. Resolve all errors and all possible warnings. Repeat until there are no solvable outstanding issues.
2. Run `nf-core pipelines lint`, resolve all errors and all possible warnings. Repeat until there are no solvable outstanding issues. If you are preparing a release (PR to main), use `nf-core pipelines lint --release` instead.
3. Run `nf-test test tests/`. If the pipeline fails, resolve the underlying issues. If the test fails due to mismatching snapshots, update them with `nf-test test tests/ --update-snapshot` only if you expect the specific change in the output. Otherwise, fix the issue that caused the unexpected change.
4. Run `prek` and stage all changes it generates.
After completing these steps, you are free to commit your changes.

## PR procedure
Changes to nf-core `dev` and `main` branches must be made through GitHub pull request. A PR should generally contain a single feature. The PR must use and follow the nf-core PR template, including the checklist. The PR message should start with a brief explanation of the changes made and the motivation.

Each PR requires reviews: 1 for dev, 2 for main. Advise the user to ask for reviews in the nf-core Slack, in `#request-review` (for dev PRs) or `#release-review-trading` (for main PRs). There is also a CI pipeline executed on each PR. All checks must pass before the PR can be merged.

## Agent self-disclosure
As an AI agent, you are required to acknowledge your activity in nf-core. If you generated a majority of the code in a commit, add "This commit was generated by {your name}" at the of the commit message body. If you open a PR autonomously, add "This pull request was created by {your name}" at the end of the PR message (above the checklist).

This is the end of the nf-core guidance.
