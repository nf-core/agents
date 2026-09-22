# nf-core: Shared AI agent guidelines

This document contains shared guidelines used by AI agents across nf-core projects. Project-specific AGENTS.md files reference these standards in addition to project-specific rules.

## Natural language

All comments and documentation **MUST** be written in English with British spelling. Documentation files **SHOULD** additionally follow the style guide at https://nf-co.re/docs/developing/documentation/style-guide.

### Prose

Prose includes all .md files, description fields in meta files, and comments in code (also in quoted scripts). Prose DOES NOT include any code (including quoted scripts) or standardised fields in other files. In all prose:

- Use short declarative sentences, active voice, no hedges or meta-commentary ("it's worth noting," "note that," "worth mentioning"). State the fact or rule directly instead of narrating that you're about to explain it.
- Never use em-dashes, use commas or semicolons instead. Avoid non-ASCII characters (e.g. arrows, fancy quotes), except diacritics in names.
- Use bold and italic formatting sparingly. Avoid bold text in bullet lists.
- Avoid contrasts, metaphors, rhetorical questions, and punchy sentences. Avoid enumerations. If multiple items need to be listed, use a bullet list. Never repeat a sentence structure multiple times in a row.
- Never "correct" established terminology. A tool's actual name, a CLI flag, a package name, or a field's standard term is not a prose style choice - leave it exactly as the ecosystem spells it, even inside otherwise-edited prose.
- Don't write "as shown below" or "we'll cover this later" - state the fact where it's needed, or reorder so the explanation comes first. A comment or doc section should make sense read in isolation.
- Scope to the immediate task, not the whole topic. A code comment supports the one line/block it sits above; a README section supports the reader doing the thing that section is under.

## Code Comments

Code exists to show _how_; comments carry _why_ — a non-obvious constraint, deliberate deviation, gotcha, or workaround. Apply this discipline across all projects:

- Default to no comment. Write comments only when code alone cannot convey the reasoning.
- Never narrate the code ("loop over users", "parse the body") or restate names, types, or signatures.
- Never narrate the change ("fixed X", "updated to Y", "as requested"). A comment must read correctly to someone seeing the file fresh; change context belongs in the commit message.
- Delete by default. A comment restating a decision the code already reflects is dead weight. Keep inline only what readers need _at that line_ and cannot get from the code — a non-obvious invariant/constraint or a cross-file sync obligation.
- Comments must stand on their own with any link removed. Encode the substance; never use a pointer as a substitute. Avoid point-in-time artifacts (specs, section numbers, design docs) that rot over time. Fine: a maintained doc/README at a stable path as breadcrumb context.
- Apply Occam's razor to every comment you keep. A genuine _why_ can still be 3x too long. Keep only the one non-obvious fact a reader needs _at that line_, in the fewest words. Cut the mechanism the code shows, downstream consequences, and justification-of-the-justification.
- A one-line summary on a public function/endpoint is fine; inline restatement of a single clear line never is.
- TODOs are fine and do not need issue IDs, but a TODO is a marker, not a substitute for doing the work in scope.

See project-specific AGENTS.md files for language-specific comment guidance (e.g. Javadoc, Groovydoc, Nextflow comments).

## git and branch policy

- You **MUST NOT** write any code to `main`; use a pull request instead.
- Always create a new branch with a meaningful name for each feature, then open a pull request.
- You **MUST NOT** commit feature work directly to `main` or `dev`, even on a fork.
- If you work on multiple features in parallel, you **SHOULD** use a separate worktree for each task to prevent clobber.

## Commit rules and routine

- Each commit **SHOULD** contain one logical change.
  - A commit **MAY** contain changes in multiple lines and files, as long as they have a shared purpose.
- Commit title **SHOULD** be concise and written in imperative mood.
- Before each commit, you **MUST** stage changes and then run `prek`. Resolve all errors and all possible warnings. Repeat until there are no solvable outstanding issues.

## Push routine

- You should only push to GitHub after implementing some meaningful changes and if the code is working.
- You **MUST** obtain permission from the user before pushing.
- You **MUST NOT** force-push.
  - You **MAY** use `--force-with-lease` **ONLY** if you have rewritten commit history.
  - If a push is rejected by the remote, notify the user and wait.
- Before pushing, run the build and tests (if applicable for your project type). Resolve all errors and all possible warnings. Repeat until there are no solvable outstanding issues.
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

## nf-test and testing

Most projects use snapshot testing to verify output. These shared principles apply across all project types:

- Most tests create at least 1 snapshot file. You **MUST NOT** edit snapshots manually.
- If you expect the output to change (e.g. after a tool update), update the snapshot with the appropriate `--update-snapshot` flag. Only regenerate snapshots on the same CPU architecture as CI.
- If a new output file has unstable content, add it to `.nftignore`.

See project-specific AGENTS.md files for test structure, test locations, and execution commands relevant to your project type.

## References

- Nextflow documentation: https://docs.seqera.io/nextflow
- nf-core tools documentation: https://nf-co.re/docs/nf-core-tools/
- nf-test documentation: https://www.nf-test.com/docs/getting-started/
