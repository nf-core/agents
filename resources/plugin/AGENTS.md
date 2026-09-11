# nf-core: agents

All AI agents and coding assistants **MUST** follow the rules in this document.

## Natural language

All comments and documentation **MUST** be written in English with British spelling. Documentation files **SHOULD** additionally follow the style guide at https://nf-co.re/docs/developing/documentation/style-guide.
Never use emdashes in prose text, be succinct and to the point. Avoid telltale LLM phrasing such as "Not X, but Y", and excessive use of bold formatting.

## Key terms

- Plugin: a packaged library that extends Nextflow or nf-test with reusable functionality for Nextflow pipelines.

## Plugin structure

The directory you are working on will match one of these layouts.

### nf-test plugin (Java/Maven)

```text
.
├── pom.xml                          // Maven build file
├── src/
│   ├── main/
│   │   ├── java/                    // Java source code
│   │   │   └── nfcore/nftest/utils/ // Package with utility classes
│   │   └── resources/
│   │       └── META-INF/
│   │           └── nf-test-plugin   // Plugin registration (name, version, extension methods)
│   └── test/
│       └── java/                    // Unit tests
├── tests/                           // nf-test test cases
│   └── <functionName>/
│       └── main.nf.test
├── tests_noplugins/                 // Tests that run without plugin dependencies
├── build.sh                         // Build script (wraps mvn)
└── test.sh                          // Test script (wraps nf-test with --plugins)
```

### Nextflow plugin (Groovy/Gradle)

```text
.
├── build.gradle                     // Gradle build file
├── Makefile                         // Convenience commands wrapping Gradle
├── src/
│   ├── main/
│   │   ├── groovy/                  // Groovy source code
│   │   │   └── nfcore/plugin/       // Package with plugin classes
│   │   └── resources/
│   │       └── META-INF/
│   │           └── extensions.idx   // Extension point registration
│   └── test/
│       └── groovy/                  // Unit tests (Spock)
└── validation/                      // Integration tests
```

If a file does not follow the layout above, you **MUST** verify with the user before editing it.

## Code style

- Static analysis tools run on every build. For Maven plugins: checkstyle, PMD, and SpotBugs. For Gradle plugins: SpotBugs. Fix all violations before pushing.
- Throw exceptions instead of calling `System.exit()`.
- Do not swallow exceptions silently. Log and rethrow, or let the caller handle it.
- No raw types. Use `List<?>` or the concrete type.
- Utility classes **MUST** have private constructors.
- Public API methods **MUST** have Javadoc or Groovydoc describing parameters, return values, and usage.

## Build and test

- You **MUST** verify the project builds and tests pass before committing or pushing.
- For Maven plugins: run `mvn clean verify` or `./build.sh`.
- For Gradle plugins: run `make assemble` or `./gradlew assemble`.
- To run the full test suite: use `./test.sh` (nf-test plugins) or `make test` (Nextflow plugins).
- If a build command fails, ask the user for help. You **MUST NOT** generate build output files manually.

## nf-test and testing

- Each function **MUST** have at least one test case.
- nf-test plugins: tests live in `tests/` as `main.nf.test` files, one per utility function. Tests use `nextflow_process` or `nextflow_pipeline` blocks with setup/when/then sections.
- Nextflow plugins: unit tests live in `src/test/` using the Spock framework. Integration tests live in `validation/`.
- Most tests create at least 1 snapshot file. You **MUST NOT** edit snapshots manually.
- If you expect the output to change, update the snapshot with the appropriate `--update-snapshot` flag. Only regenerate snapshots on the same CPU architecture as CI.
- If a new output file has unstable content, add it to `.nftignore`.

## git and branch policy

The default branch is `main`.

- You **MUST NOT** write any code to `main`; use a pull request instead.
- Always create a new branch with a meaningful name for each feature, then open a pull request to `main`.
- You **MUST NOT** commit feature work directly to `main`, even on a fork.
- If you work on multiple features in parallel, you **SHOULD** use a separate worktree for each task to prevent clobber.

## Commit rules and routine

- Each commit **SHOULD** contain one logical change.
- Commit title **SHOULD** be concise and written in imperative mood.
- Before each commit, you **MUST** stage changes and then run `prek`. Resolve all errors and all possible warnings. Repeat until there are no solvable outstanding issues.

## Push routine

- You should only push to GitHub after your changes are working.
- Before pushing, you **MUST** run the project build and tests (see "Build and test"), resolve all errors and all possible warnings. Repeat until there are no solvable outstanding issues.
- If you know the code will cause issues or you intend to push more changes, you **SHOULD** add `[skip ci]` at the end of the commit title. You **SHOULD** omit this tag for final review-ready commits.

## PR procedure

- A PR **SHOULD** contain a single feature.
- You **SHOULD** add a line in the relevant section in CHANGELOG.md, listing contributors and the expected PR number.
- The PR **MUST** use and follow the nf-core PR template, including the checklist.
- The PR message **SHOULD** start with a brief explanation of the changes made and the motivation.
- Each PR requires reviews and passing CI before merging.
- A human can request PR reviews on Slack.

## Agent self-disclosure

- If you generated a majority of the code in a commit, you **MUST** add "Generated by {your name}" at the end of the commit message body.
- If you open a PR autonomously, you **MUST** add "Generated by {your name}" at the end of the PR message (above the checklist).

## References

- Nextflow documentation: https://docs.seqera.io/nextflow
- nf-core tools documentation: https://nf-co.re/docs/nf-core-tools/
- nf-test documentation: https://www.nf-test.com/docs/getting-started/
