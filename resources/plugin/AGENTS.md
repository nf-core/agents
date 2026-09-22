# nf-core: agents

All AI agents and coding assistants **MUST** follow the rules in this document.

This document incorporates shared guidelines from [../AGENTS.md](../AGENTS.md), which cover natural language, git policies, commit routines, and more. Please refer to that file for general standards.

## Natural language

See [../AGENTS.md#natural-language](../AGENTS.md#natural-language) for the shared natural language guidelines.

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

- See [../AGENTS.md#git-and-branch-policy](../AGENTS.md#git-and-branch-policy) for general git guidelines.
- For plugins specifically: Always open a pull request to `main`.

## Commit rules and routine

See [../AGENTS.md#commit-rules-and-routine](../AGENTS.md#commit-rules-and-routine) for general guidelines.

## Push routine

See [../AGENTS.md#push-routine](../AGENTS.md#push-routine) for general guidelines. For plugins specifically:

- Before pushing, you **MUST** run the project build and tests (see "Build and test" above), resolve all errors and all possible warnings. Repeat until there are no solvable outstanding issues.

## PR procedure

See [../AGENTS.md#pr-procedure](../AGENTS.md#pr-procedure) for general guidelines.

## Agent self-disclosure

See [../AGENTS.md#agent-self-disclosure](../AGENTS.md#agent-self-disclosure).

## References

See [../AGENTS.md#references](../AGENTS.md#references) for shared references.
