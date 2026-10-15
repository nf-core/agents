---
name: nf-core-template-sync
description: Merge an nf-core template sync pull request into an nf-core pipeline. This is the automated "Important! Template update for nf-core/tools vX.Y.Z" PR from nf-core-bot on a nf-core-template-merge-* branch. The skill resolves the merge conflicts, regenerates generated files, validates the result with nextflow lint, nf-core pipelines lint and nf-test, and writes a review report and PR comment. Use it whenever the user mentions a template sync, a template update PR, the TEMPLATE branch, a nf-core-template-merge branch, merge conflicts after an nf-core/tools release, or bringing a pipeline up to a new nf-core template version, even if they do not ask for a skill. Do not use it to run a manual sync, to repair a broken TEMPLATE branch, or to set up a sync for a pipeline that was not made with the template.
license: MIT
compatibility: Needs git, an authenticated GitHub CLI (gh), Nextflow, Python 3.9+, uv (for uvx) and network access. nf-test and Docker are optional.
metadata:
  author: nf-core
  version: "0.1.0"
---

# nf-core template sync

When nf-core/tools makes a release, nf-core-bot opens a PR on each pipeline from a `nf-core-template-merge-<version>` branch into `dev`. This skill finishes that PR. Scripts do the fixed steps, you make the judgement calls, and then scripts check the result:

1. **Prepare** (script): checks, merge, rule-based resolutions, sources, worklist.
2. **Resolve** (you): the remaining conflicts, with a recorded decision for each.
3. **Regenerate and check** (script): template modules, container configs, RO-Crate, lint, tests. If a check fails, go back to step 2 for that item.
4. **Report** (script): HTML report and PR comment.
5. **Ask the user**: push, comment and follow-up actions.

The scripts are in `scripts/` next to this file. Run them from the root of the pipeline repository with `python3 <skill dir>/scripts/<name>.py`. They keep their state in `.git/nf-core-template-sync/`, which git never commits.

## Rules

These rules protect the git history that every future sync depends on.

- Never run `nf-core pipelines sync` by hand. Never repair a broken TEMPLATE branch, and never set up a sync retrospectively. These tasks are disruptive and rarely necessary. If the scripts stop because of one of these problems, explain the problem to the user and stop.
- Never write to the TEMPLATE branch.
- Never squash or rebase. The sync must go into `dev` with a merge commit, or the next sync shows the same conflicts again. Never revert a sync merge.
- Ask the user before you push, comment on GitHub or open a PR. Never force-push.
- Never edit nf-test snapshots by hand.
- If the pipeline has an `AGENTS.md`, follow it too: commit rules, push rules and the AI disclosure line.

## 1. Prepare

```bash
python3 <skill dir>/scripts/prepare.py            # newest open sync PR
python3 <skill dir>/scripts/prepare.py --pr 623   # a specific PR
```

The script finds the newest open sync PR and checks the tools. Then it checks out the bot's branch and merges `dev` into it without a commit. It deals with these files by rule:

- `ro-crate-metadata.json` and `conf/containers_*.config`: deleted, then regenerated in phase 3.
- `modules.json` and the template modules and subworkflows (fastqc, multiqc, `utils_*`): taken from `dev`. Their old `.conda-lock` files are deleted. Phase 3 updates them to the template version, but never to an older version than `dev`.
- The nf-core logo images: taken from `dev`. Lint draws logos again with local fonts, so a correct logo can fail lint (known issue, see the playbook).

If `.nf-core.yml` on `dev` names a newer template than the git history contains (after a squash merge or a manual template update), the script merges against the TEMPLATE commit of that newer version. This removes many false conflicts. The script prints a warning: tell the user, and record a decision with `needs_review: true`.

Exit codes:

- `0`: ready. Read the two files that it names: `worklist.md` (each remaining conflict with the guidance for it) and `sources.md` (changelog, blog posts, release notes, reference PRs, docs, for each release in the range).
- `2`: hard stop. Tell the user why, in plain words, and stop. Do not try to work around it.
- `3`: the user must decide. For example, someone already started work on the sync branch. Ask the user, then run again with the option that the message names.

## 2. Resolve

Work through `worklist.md` one file at a time. The template side is `ours` (`HEAD`), and `dev` is `theirs`.

Use these sources in this order. If two sources disagree, follow the earlier one and record the disagreement:

1. Skill release notes for that version (in the worklist, from `references/releases/`).
2. `references/conflict-playbook.md`: the general rules for each file.
3. The blog post guidance for that version (in the worklist and `sources.md`).
4. How the reference PRs resolved the same file (in the worklist). Other maintainers already made these choices.
5. The nf-core docs.

Keep pipeline content and take template boilerplate. Copy text exactly from one side when you can. If you write Nextflow code that is not an exact copy, read `references/nextflow-docs.md` first and check the docs for the pipeline's Nextflow version. Wrong syntax from memory is the most dangerous mistake in this task, because it can look correct.

`nextflow lint` can report a wrong number of arguments for a call to a template subworkflow (for example `UTILS_NFSCHEMA_PLUGIN`). Phase 3 updates that subworkflow, so take the template version of the call and do not change the subworkflow yourself.

Template changes also apply where the pipeline has its own copy or replacement of a template file. Examples: a second `awsfulltest_*.yml` workflow, or the pipeline's own workflows when it deleted `workflows/<pipeline>.nf` (calls to updated template modules such as `FASTQC` and `MULTIQC`).

To read another version of a file, use `git show <ref>:<path>`. Do not check out other trees while the merge is in progress, because that can overwrite the merge index.

Also deal with the files in the section "The template deleted or renamed these files". Delete them, or keep them with a recorded reason.

Write `.git/nf-core-template-sync/decisions.json` as you go. `references/report-style.md` has the format and the writing style. Each conflicted file needs at least one decision. Set `needs_review` to `true` for any choice that a person should examine.

When there are no conflicts left, add a line for the sync to `CHANGELOG.md`, stage everything, and commit the merge:

```bash
git add -A && git commit --no-edit --cleanup=strip
```

Keep the default merge message. `--cleanup=strip` removes the `# Conflicts:` lines that git adds. Add the AI disclosure line if the pipeline `AGENTS.md` requires one.

## 3. Regenerate and check

```bash
python3 <skill dir>/scripts/finalise.py regenerate
python3 <skill dir>/scripts/finalise.py check
```

`regenerate` makes one commit for each step: template modules and subworkflows, container configs, `prek` fixes, RO-Crate.

`check` prints PASS, FAIL, WARN or INFO for each check and writes `checks.json`:

- The merge is committed, with no conflict markers.
- The branch contains the template commit and the latest `dev`.
- Nothing pipeline-specific was lost compared with `dev`: params, profiles, `includeConfig` lines, DOI, Nextflow version, changelog lines.
- `TODO nf-core` comments were not added back.
- Lines that come from neither side are listed. In Nextflow files, these lines need a decision that lists `nextflow_docs`.
- `nextflow lint` has no errors, and the config parses with the test profiles.
- Files that the template deleted are gone.
- The template modules and their lock files are at the template version.
- `CHANGELOG.md` has a line for the sync.
- Each conflicted file has a decision.
- `nf-core pipelines lint` has no failures.

Fix each failure, commit the fix, and run `check` again. You can skip the slow lint while you iterate (`--skip nf_core_lint`), but the last run must include it. Fix all lint failures, and fix warnings when you can. If you cannot fix a failure (for example a known tool bug in the release notes), record it as a decision with `needs_review: true`.

- Params that the template removed on purpose show as expected in `nothing_lost`. Put them in `behaviour_changes`.
- If a command fails with a lock error in the nf-core modules cache (`index.lock`), another nf-core command is running. Wait, then run again.

### nf-test

Ask the user each time if nf-test must run. It is slow and needs Docker (or another container engine).

- On x86_64 (the CPU type of CI): `finalise.py nftest`. If the only failures are snapshot changes that the template changes explain (for example a new MultiQC version), run `finalise.py nftest --update-snapshots`.
- On another CPU type (for example an Apple Silicon Mac): checksums can differ from CI. First offer `finalise.py nftest --on-dev`. If `dev` passes on this machine, the machine matches CI for this pipeline, and you can update snapshots after the merge. If not, run the tests only to find real failures, and do not update snapshots.

Run `finalise.py check` again after nf-test, so that the result is in `checks.json`.

## 4. Report

```bash
python3 <skill dir>/scripts/report.py --out <scratch directory>
```

Use your harness's scratch or temporary directory. Never write the report into the pipeline repository. The script writes the HTML report and `pr-comment.md`. Open the report for the user if you can.

## 5. Ask the user

Show the user a short summary: the decisions for review, the failed checks, and the paths of the report and the comment. Then ask, one step at a time:

1. **Push.** Default: push to the bot's branch, so that the existing sync PR gets the resolution: `git push <remote> HEAD:<sync branch>`. Check that the user can push to the nf-core repository with `gh api repos/nf-core/<pipeline> --jq .permissions.push`. If they cannot, push the branch to their fork and open a PR to `dev` with the pipeline PR template. The bot PR closes when that PR merges.
2. **Comment.** `gh pr comment <number> -R nf-core/<pipeline> --body-file <out>/pr-comment.md`. `gh --attach` accepts only images and video, so tell the user to drag the HTML report into the comment in the web browser (GitHub accepts `.html` files there).
3. **Follow-up actions.** Show the list from the report and ask which ones to do. Each follow-up needs its own branch and PR. Examples:
   - Update all nf-core modules and subworkflows.
   - Make files more similar to the template.
   - Regenerate snapshots on x86_64.
   - If you made a decision that no source covered, offer to draft an entry for `references/releases/<version>.md` in nf-core/agents. The next sync then gets that knowledge.
