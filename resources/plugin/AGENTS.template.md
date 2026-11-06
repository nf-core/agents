# nf-core: agents

All AI agents and coding assistants **MUST** follow the rules in this document.

<!-- shared: Natural language -->

<!-- shared: Code Comments -->

## Key terms

- Plugin: a packaged library that extends Nextflow or nf-test with reusable functionality for Nextflow pipelines.

## Plugin structure

- `mise.toml`: pinned tools and project tasks, with checksums in `mise.lock`.
- `src/main/`: plugin source code.
- `src/test/`: unit tests.
- `tests/` (nf-test plugins) or `validation/` (Nextflow plugins): integration tests.

## Code style

- You **SHOULD** throw exceptions instead of calling `System.exit()`.
- Do not swallow exceptions silently. Log and rethrow, or let the caller handle it.
- No raw types. Use `List<?>` or the concrete type.
- Utility classes **MUST** have private constructors.
- Public API methods **MUST** have Javadoc or Groovydoc describing parameters, return values, and usage.

## Build and test

- You **MUST** verify the project builds and tests pass before committing or pushing.
- Install the pinned tools with `mise install --locked`.
- Run unit tests with `mise run test`.
- Run integration tests with `mise run validate`, which also builds the plugin.
- Run builds and tests through `mise run`, not directly with Gradle, Maven or nf-test, so the pinned tools and project settings apply.
- After changing `[tools]` in `mise.toml`, run `mise lock` and commit the lock files.
- If a build command fails, ask the user for help. You **MUST NOT** generate build output files manually.

<!-- shared: git and branch policy -->

### For plugins specifically

The default branch is `main`.

- Always open a pull request to `main`.

<!-- shared: Commit rules and routine -->

<!-- shared: Push routine -->

<!-- shared: PR procedure -->

<!-- shared: Agent self-disclosure -->

<!-- shared: nf-test and testing -->

### For plugins specifically

- Each function **MUST** have at least one test case.
- Normalise unstable values in `.nf.test` files, not in `.snap` files.

<!-- shared: References -->
