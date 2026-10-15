#!/usr/bin/env python3
"""Phase 3 of nf-core-template-sync.

finalise.py regenerate   Update template modules/subworkflows, regenerate container configs and RO-Crate,
                         apply prek fixes. One commit for each step.
finalise.py check        Run all checks. Writes checks.json. Exit code 1 if a check fails.
finalise.py nftest       Run nf-test (only when the user agrees). Options: --on-dev, --update-snapshots.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
from pathlib import Path

from common import (
    StopError,
    file_at,
    gh_json,
    git,
    load_json,
    load_state,
    main_wrapper,
    nf_core_cmd,
    repo_root,
    run,
    save_json,
    state_dir,
    template_components,
    version_tuple,
)

VENDORED = re.compile(r"^(modules|subworkflows)/nf-core/")
CATEGORIES = {"rule", "template", "pipeline", "combined", "agent-written", "deleted", "kept"}
GENERATED = re.compile(r"^conf/containers_|ro-crate-metadata\.json$|^modules\.json$|\.snap$|\.conda-lock/")
TRIVIAL_LINE = re.compile(r"^[\s()\[\]{},;]*$")


def merge_in_progress(root: Path) -> bool:
    return (Path(git("rev-parse", "--absolute-git-dir", cwd=root)) / "MERGE_HEAD").exists()


def require_merged(root: Path, state: dict) -> None:
    if merge_in_progress(root):
        raise StopError("The merge is not committed yet. Finish phase 2 and run `git commit` first.")
    if git("branch", "--show-current", cwd=root) != state["pr"]["headRefName"]:
        raise StopError(f"Switch to the sync branch `{state['pr']['headRefName']}` first.")
    for sha, name in ((state["head_sha"], "the template commit"), (state["dev_sha"], "`dev`")):
        if run(["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=root, check=False).returncode != 0:
            raise StopError(f"HEAD does not contain {name}. Do not squash or rebase the merge.")


def commit_if_changed(root: Path, message: str, paths: list) -> bool:
    run(["git", "add", "-A", "--", *paths], cwd=root, check=False)
    if run(["git", "diff", "--cached", "--quiet"], cwd=root, check=False).returncode == 0:
        return False
    git("commit", "-q", "-m", message, cwd=root)
    print(f"  committed: {message}")
    return True


def restore_container_configs(root: Path) -> None:
    """`nf-core modules update` rewrites the container configs with only the updated modules (tools 4.1.0)."""
    for f in (root / "conf").glob("containers_*.config"):
        rel = str(f.relative_to(root))
        if git("ls-files", "--", rel, cwd=root):
            git("restore", "--staged", "--worktree", "--", rel, cwd=root)
        else:
            f.unlink()


def regenerate(root: Path, state: dict, args) -> None:
    require_merged(root, state)
    if git("status", "--porcelain", "--untracked-files=no", cwd=root):
        raise StopError("Commit or discard your changes before `regenerate`.")
    nf_core = nf_core_cmd(state)
    steps = args.only or ["components", "containers", "prek", "rocrate"]

    if "components" in steps:
        updates = [c for c in state["template_components"] if c.get("action") == "update"]
        for comp in updates:
            print(f"Updating {comp['kind'][:-1]} {comp['name']} to {comp['sha'][:8]}")
            run(
                [*nf_core, comp["kind"], "update", comp["name"], "--sha", comp["sha"], "--no-preview", "--skip-deps"],
                cwd=root,
                timeout=900,
            )
            if not comp.get("tests_on_dev", True):
                run(["git", "rm", "-r", "-q", "--ignore-unmatch", "--", f"{comp['path']}/tests"], cwd=root)
                shutil.rmtree(root / comp["path"] / "tests", ignore_errors=True)
        restore_container_configs(root)
        if updates:
            names = ", ".join(c["name"] for c in updates)
            commit_if_changed(
                root, f"Update nf-core module/subworkflow {names}", ["modules.json", "modules", "subworkflows"]
            )

    if "containers" in steps and state["container_configs_enabled"]:
        print("Regenerating container configs")
        has_cmd = (
            run([*nf_core, "pipelines", "containers", "create-configs", "--help"], cwd=root, check=False).returncode
            == 0
        )
        if has_cmd:
            run([*nf_core, "pipelines", "containers", "create-configs"], cwd=root, timeout=900)
        else:
            # Needs a clean tree; compares with the committed files.
            run(
                [*nf_core, "pipelines", "lint", "-f", "container_configs", "-k", "container_configs"],
                cwd=root,
                check=False,
                timeout=900,
            )
        commit_if_changed(root, "Regenerate container configs", ["conf"])

    if "prek" in steps:
        hook = shutil.which("prek") or shutil.which("pre-commit")
        changed = [
            p
            for p in git("diff", "--name-only", state["dev_sha"], "HEAD", cwd=root).splitlines()
            if (root / p).is_file()
        ]
        if hook and changed:
            print(f"Running {Path(hook).name} on {len(changed)} files changed by the sync")
            for _ in range(2):
                proc = run([hook, "run", "--files", *changed], cwd=root, check=False, timeout=900)
            if proc.returncode != 0:
                print("  prek still reports problems. `check` will show them; fix them by hand.")
            commit_if_changed(root, "Apply prek fixes", changed)
        elif not hook:
            print("prek is not installed. Skipping the prek step.")

    if "rocrate" in steps:
        print("Regenerating ro-crate-metadata.json")
        run([*nf_core, "pipelines", "rocrate", ".", "--json_path", "."], cwd=root, timeout=900)
        commit_if_changed(root, "Regenerate RO-Crate metadata", ["ro-crate-metadata.json"])
    print("\nNext: python3 finalise.py check")


class Checks:
    def __init__(self):
        self.results = []

    def add(self, cid: str, title: str, status: str, details=None) -> None:
        self.results.append({"id": cid, "title": title, "status": status, "details": details or []})


def dev_tree(root: Path, sdir: Path, dev_sha: str) -> Path:
    path = sdir / "dev-tree"
    if not path.exists():
        git("worktree", "add", "-q", "--detach", str(path), dev_sha, cwd=root)
    return path


def flat_config(path: Path, profile: str = "") -> tuple:
    cmd = ["nextflow", "config", "-flat", "."] + (["-profile", profile] if profile else [])
    proc = run(cmd, cwd=path, check=False, timeout=300)
    values = {}
    for line in proc.stdout.splitlines():
        m = re.match(r"^(\S+)\s*=\s*(.*)$", line)
        if m:
            values[m.group(1)] = m.group(2)
    return proc.returncode, values, proc.stderr


def profiles(path: Path) -> set:
    out = run(["nextflow", "config", "-show-profiles", "."], cwd=path, check=False, timeout=300).stdout
    names, inside = set(), False
    for line in out.splitlines():
        if line.startswith("profiles {"):
            inside = True
        elif inside and re.match(r"^   [^\s].* \{$", line):
            names.add(line.strip()[:-2].strip().strip("'\""))
        elif inside and line.startswith("}"):
            inside = False
    return names


def include_configs(path: Path) -> set:
    found = set()
    for f in [path / "nextflow.config", *sorted((path / "conf").glob("*.config"))]:
        if f.exists() and not f.name.startswith("containers_"):
            for m in re.finditer(r"includeConfig\s+(.+)", f.read_text(errors="replace")):
                found.add(re.sub(r"\s+", " ", m.group(1).strip()))
    return found


def check_nothing_lost(root: Path, sdir: Path, state: dict, checks: Checks) -> None:
    dev = dev_tree(root, sdir, state["dev_sha"])
    code_dev, cfg_dev, _ = flat_config(dev)
    code_head, cfg_head, err = flat_config(root)
    if code_head != 0:
        checks.add(
            "nothing_lost",
            "Nothing pipeline-specific lost compared with dev",
            "fail",
            ["`nextflow config` fails on the merge result:", err.strip()[-1500:]],
        )
        return
    problems, notes = [], []
    old_tpl = top_level_params(file_at(state["from_commit"], "nextflow.config", root) or "")
    new_tpl = top_level_params(file_at(state["head_sha"], "nextflow.config", root) or "")
    lost = sorted(k for k in cfg_dev if k.startswith("params.") and k not in cfg_head)
    intended = [k for k in lost if k.split(".")[1] in old_tpl - new_tpl]
    lost = [k for k in lost if k not in intended]
    if lost:
        problems.append("Params lost: " + ", ".join(f"`{k}`" for k in lost))
    if intended:
        notes.append("Params that the template removed (expected): " + ", ".join(f"`{k}`" for k in intended))
    if cfg_dev.get("manifest.doi") and cfg_dev.get("manifest.doi") != cfg_head.get("manifest.doi"):
        problems.append(f"`manifest.doi` changed: {cfg_dev.get('manifest.doi')} -> {cfg_head.get('manifest.doi')}")
    old_nf, new_nf = cfg_dev.get("manifest.nextflowVersion", ""), cfg_head.get("manifest.nextflowVersion", "")
    if old_nf and new_nf and version_tuple(new_nf) < version_tuple(old_nf):
        problems.append(f"`manifest.nextflowVersion` went down: {old_nf} -> {new_nf}")
    lost_profiles = sorted(profiles(dev) - profiles(root))
    if lost_profiles:
        problems.append("Profiles lost: " + ", ".join(lost_profiles))
    lost_includes = sorted(include_configs(dev) - include_configs(root))
    if lost_includes:
        problems.append("`includeConfig` lines lost: " + "; ".join(f"`{i}`" for i in lost_includes))
    dev_log = file_at(state["dev_sha"], "CHANGELOG.md", root) or ""
    head_log = (root / "CHANGELOG.md").read_text(errors="replace") if (root / "CHANGELOG.md").exists() else ""
    head_lines = {line.strip() for line in head_log.splitlines()}
    lost_log = [
        line
        for line in dev_log.splitlines()
        if line.strip() and not line.startswith("## ") and line.strip() not in head_lines
    ]
    if lost_log:
        problems.append(
            f"{len(lost_log)} CHANGELOG.md lines from dev are missing, for example: `{lost_log[0].strip()[:120]}`"
        )
    checks.add(
        "nothing_lost",
        "Nothing pipeline-specific lost compared with dev",
        "fail" if problems else "pass",
        problems + notes,
    )

    readded = []
    for f in git("diff", "--name-only", state["dev_sha"], "HEAD", cwd=root).splitlines():
        old = file_at(state["dev_sha"], f, root)
        if old is None or not (root / f).is_file() or VENDORED.match(f):
            continue
        before, after = old.count("TODO nf-core"), (root / f).read_text(errors="replace").count("TODO nf-core")
        if after > before:
            readded.append(f"`{f}`: {before} -> {after}")
    checks.add("todo_comments", "No `TODO nf-core` comments added back", "warn" if readded else "pass", readded)


def top_level_params(config: str) -> set:
    block = re.search(r"^params\s*\{(.*?)^\}", config, re.M | re.S)
    return set(re.findall(r"^\s{4}([A-Za-z_]\w*)\s*=", block.group(1), re.M)) if block else set()


def norm(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip()).rstrip(",")


def check_authored_lines(root: Path, state: dict, decisions: dict, checks: Checks) -> None:
    by_file = {}
    for d in decisions.get("decisions", []):
        by_file.setdefault(d.get("file"), []).append(d)
    authored, missing_docs = {}, []
    changed = git("diff", "--name-only", state["dev_sha"], "HEAD", cwd=root).splitlines()
    for f in changed:
        path = root / f
        if VENDORED.match(f) or GENERATED.search(f) or not path.is_file() or b"\0" in path.read_bytes()[:8000]:
            continue
        known = set()
        for ref in (state["dev_sha"], state["head_sha"]):
            known |= {norm(line) for line in (file_at(ref, f, root) or "").splitlines()}
        lines = [
            (i + 1, line)
            for i, line in enumerate((root / f).read_text(errors="replace").splitlines())
            if not TRIVIAL_LINE.match(line) and norm(line) not in known
        ]
        if not lines:
            continue
        authored[f] = [f"{n}: {line.strip()[:160]}" for n, line in lines]
        if f.endswith((".nf", ".config")) and not any(d.get("nextflow_docs") for d in by_file.get(f, [])):
            missing_docs.append(f)
    details = [
        f"`{f}`: " + " | ".join(v[:5]) + (f" ... (+{len(v) - 5})" if len(v) > 5 else "") for f, v in authored.items()
    ]
    if missing_docs:
        details.insert(
            0,
            "These Nextflow files have lines from neither side, but no decision lists `nextflow_docs`: "
            + ", ".join(f"`{f}`" for f in missing_docs),
        )
    checks.add(
        "authored_lines",
        "New Nextflow code is checked against the docs",
        "fail" if missing_docs else ("info" if authored else "pass"),
        details,
    )
    save_json(state_dir(root) / "authored_lines.json", authored)


def fmt(e: dict) -> str:
    return f"`{e['filename']}:{e.get('startLine')}`: {e.get('message')}"


def check_nextflow_lint(root: Path, state: dict, checks: Checks) -> None:
    proc = run(["nextflow", "lint", ".", "-output", "json"], cwd=root, check=False, timeout=600)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        checks.add("nextflow_lint", "`nextflow lint` has no errors", "fail", [(proc.stderr or proc.stdout)[-1500:]])
        return
    conflicted = {c["file"] for c in state["conflicts"]}
    own = [e for e in data.get("errors", []) if not VENDORED.match(e["filename"])]
    vendored = [e for e in data.get("errors", []) if VENDORED.match(e["filename"])]
    details = [fmt(e) for e in own]
    details += [f"(nf-core component, do not edit) {fmt(e)}" for e in vendored]
    details += [f"warning: {fmt(w)}" for w in data.get("warnings", []) if w["filename"] in conflicted]
    status = "fail" if own else ("warn" if vendored else "pass")
    checks.add("nextflow_lint", "`nextflow lint` has no errors", status, details)


def check_nextflow_config(root: Path, checks: Checks) -> None:
    details, failed = [], False
    for profile in ("test", "test_full"):
        code, _, err = flat_config(root, profile)
        if code != 0:
            failed = True
            details.append(f"`nextflow config -profile {profile}` failed: {err.strip()[-800:]}")
    checks.add("nextflow_config", "The config parses with the test profiles", "fail" if failed else "pass", details)


def check_nf_core_lint(root: Path, state: dict, checks: Checks) -> None:
    out = Path(tempfile.mkdtemp()) / "lint.json"
    proc = run([*nf_core_cmd(state), "pipelines", "lint", "--json", str(out)], cwd=root, check=False, timeout=1800)
    data = load_json(out, {})
    if not data:
        output = (proc.stderr + proc.stdout).strip()
        details = ["Lint did not produce results:", output[-1200:]]
        if "index.lock" in output:
            details.append("Another nf-core command is using the modules cache. Wait for it to finish, then run again.")
        checks.add("nf_core_lint", "`nf-core pipelines lint` has no failures", "fail", details)
        return
    failed = [f"{t}: {m}" for t, m in data.get("tests_failed", [])]
    warned = [f"warning: {t}: {m}" for t, m in data.get("tests_warned", [])]
    checks.add(
        "nf_core_lint",
        "`nf-core pipelines lint` has no failures",
        "fail" if failed else ("warn" if warned else "pass"),
        failed + warned,
    )


def check_template_files(root: Path, state: dict, decisions: dict, checks: Checks) -> None:
    kept = {d.get("file") for d in decisions.get("decisions", []) if d.get("category") in ("kept", "pipeline")}
    changes = state["template_changes"]
    gone = changes["deleted"] + [r["from"] for r in changes["renamed"]]
    present = [p for p in gone if (root / p).exists() and p not in kept]
    checks.add(
        "template_files",
        "Files the template deleted or renamed are gone",
        "fail" if present else "pass",
        [f"`{p}` is still present (delete it, or record a `kept` decision)" for p in present],
    )


def check_components(root: Path, state: dict, checks: Checks) -> None:
    current = {c["path"]: c["sha"] for c in template_components("HEAD", root)}
    problems = []
    for comp in state["template_components"]:
        if comp.get("action") != "update":
            continue
        if current.get(comp["path"]) != comp["sha"]:
            problems.append(f"`{comp['name']}` is not at the template version {comp['sha'][:8]}")
        if comp["kind"] == "modules":
            remote = gh_json(
                "api", f"repos/nf-core/modules/contents/{comp['path']}/.conda-lock?ref={comp['sha']}", check=False
            )
            expected = sorted(f["name"] for f in remote) if isinstance(remote, list) else []
            lock_dir = root / comp["path"] / ".conda-lock"
            local = sorted(p.name for p in lock_dir.iterdir()) if lock_dir.is_dir() else []
            if local != expected:
                problems.append(f"`{comp['path']}/.conda-lock` has {local}, expected {expected}")
    checks.add(
        "components",
        "Template modules/subworkflows are at the template version",
        "fail" if problems else "pass",
        problems,
    )


def check_changelog(root: Path, state: dict, checks: Checks) -> None:
    text = (root / "CHANGELOG.md").read_text(errors="replace") if (root / "CHANGELOG.md").exists() else ""
    version = re.escape(state["to_version"])
    ok = re.search(rf"(?i)template.*{version}|{version}.*template", text)
    checks.add(
        "changelog",
        f"CHANGELOG.md has a line for template {state['to_version']}",
        "pass" if ok else "fail",
        []
        if ok
        else [
            f"Add a line such as `- [#{state['pr']['number']}]({state['pr']['url']}) "
            f"Template update for nf-core/tools v{state['to_version']}`"
        ],
    )


def check_decisions(state: dict, decisions: dict, checks: Checks) -> None:
    problems = []
    if not decisions:
        problems.append("decisions.json is missing. See references/report-style.md.")
    entries = decisions.get("decisions", []) if decisions else []
    for i, d in enumerate(entries):
        for key in ("file", "category", "choice", "reason"):
            if not d.get(key):
                problems.append(f"Decision {i + 1} has no `{key}`")
        if d.get("category") and d["category"] not in CATEGORIES:
            problems.append(f"Decision {i + 1}: category `{d['category']}` is not one of {sorted(CATEGORIES)}")
    covered = {d.get("file") for d in entries}
    problems += [
        f"No decision for conflicted file `{c['file']}`" for c in state["conflicts"] if c["file"] not in covered
    ]
    if decisions and not decisions.get("summary"):
        problems.append("decisions.json has no `summary`")
    checks.add("decisions", "Every conflict has a recorded decision", "fail" if problems else "pass", problems)


def check(root: Path, state: dict, args) -> int:
    sdir = state_dir(root)
    decisions = load_json(sdir / "decisions.json", {})
    checks = Checks()
    skip = set(args.skip or [])

    problems = []
    if merge_in_progress(root):
        problems.append("The merge is not committed")
    unmerged = git("diff", "--name-only", "--diff-filter=U", cwd=root)
    if unmerged:
        problems.append("Unmerged paths: " + ", ".join(unmerged.splitlines()))
    markers = run(["git", "grep", "-n", "-I", "-E", "^(<<<<<<<|>>>>>>>)( |$)"], cwd=root, check=False).stdout.strip()
    if markers:
        problems += ["Conflict marker: " + m for m in markers.splitlines()[:20]]
    if git("status", "--porcelain", "--untracked-files=no", cwd=root):
        problems.append("There are uncommitted changes (lint only reads committed container configs)")
    checks.add("git_state", "Merge committed, no conflict markers", "fail" if problems else "pass", problems)

    remote = state["remote"]
    run(["git", "fetch", "-q", remote, f"+refs/heads/dev:refs/remotes/{remote}/dev"], cwd=root, check=False)
    problems = []
    for ref, name in (
        (state["head_sha"], "the bot's template commit"),
        (f"{remote}/dev", f"the latest `{remote}/dev`"),
    ):
        if run(["git", "merge-base", "--is-ancestor", ref, "HEAD"], cwd=root, check=False).returncode != 0:
            problems.append(
                f"HEAD does not contain {name}"
                + (f". Merge it: `git merge {remote}/dev`" if "dev" in name else ". Do not squash or rebase.")
            )
    if git("branch", "--show-current", cwd=root) != state["pr"]["headRefName"]:
        problems.append(f"Not on the sync branch `{state['pr']['headRefName']}`")
    checks.add(
        "ancestry", "Branch contains the template commit and the latest dev", "fail" if problems else "pass", problems
    )

    for cid, func in (
        ("nothing_lost", lambda: check_nothing_lost(root, sdir, state, checks)),
        ("authored_lines", lambda: check_authored_lines(root, state, decisions, checks)),
        ("nextflow_lint", lambda: check_nextflow_lint(root, state, checks)),
        ("nextflow_config", lambda: check_nextflow_config(root, checks)),
        ("template_files", lambda: check_template_files(root, state, decisions, checks)),
        ("components", lambda: check_components(root, state, checks)),
        ("changelog", lambda: check_changelog(root, state, checks)),
        ("decisions", lambda: check_decisions(state, decisions, checks)),
        ("nf_core_lint", lambda: check_nf_core_lint(root, state, checks)),
    ):
        if cid in skip:
            checks.add(cid, cid, "skip", ["Skipped with --skip"])
        else:
            print(f"Checking {cid}...")
            func()

    if (sdir / "dev-tree").exists():
        run(["git", "worktree", "remove", "--force", str(sdir / "dev-tree")], cwd=root, check=False)
    nftest = load_json(sdir / "nftest.json")
    if nftest:
        checks.add("nf_test", "nf-test", nftest["status"], nftest["details"])
    save_json(sdir / "checks.json", checks.results)

    icons = {"pass": "PASS", "fail": "FAIL", "warn": "WARN", "info": "INFO", "skip": "SKIP"}
    print()
    for r in checks.results:
        print(f"[{icons[r['status']]}] {r['title']}")
        for d in r["details"][:15]:
            print(f"       {d}")
    failed = [r for r in checks.results if r["status"] == "fail"]
    print(f"\n{len(failed)} failed. Results: {sdir / 'checks.json'}")
    return 1 if failed else 0


def nftest(root: Path, state: dict, args) -> None:
    if not shutil.which("nf-test"):
        raise StopError("nf-test is not installed.")
    sdir = state_dir(root)
    arch = state["tools"]["arch"]
    baseline = load_json(sdir / "nftest_dev.json", {})
    if args.update_snapshots and arch not in ("x86_64", "AMD64") and baseline.get("status") != "pass":
        raise StopError(
            f"This machine is {arch}. CI runs on x86_64, so do not update snapshots here unless "
            "`nftest --on-dev` passed first on this machine."
        )
    path = dev_tree(root, sdir, state["dev_sha"]) if args.on_dev else root
    cmd = ["nf-test", "test", "tests/", "--profile", f"+{args.profile}"] + (
        ["--update-snapshot"] if args.update_snapshots else []
    )
    print("Running: " + " ".join(cmd))
    proc = run(cmd, cwd=path, check=False, timeout=7200)
    tail = [line for line in (proc.stdout + proc.stderr).splitlines() if line.strip()][-25:]
    result = {
        "status": "pass" if proc.returncode == 0 else "fail",
        "arch": arch,
        "on_dev": args.on_dev,
        "updated_snapshots": args.update_snapshots,
        "details": tail,
    }
    save_json(sdir / ("nftest_dev.json" if args.on_dev else "nftest.json"), result)
    if args.on_dev:
        run(["git", "worktree", "remove", "--force", str(path)], cwd=root, check=False)
    elif args.update_snapshots:
        commit_if_changed(root, "Update nf-test snapshots", ["tests"])
    print("\n".join(tail))
    print(f"\nnf-test {result['status']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("regenerate")
    p.add_argument("--only", nargs="+", choices=["components", "containers", "prek", "rocrate"])
    p = sub.add_parser("check")
    p.add_argument("--skip", nargs="+", help="Check ids to skip, for example nf_core_lint during quick iterations")
    p = sub.add_parser("nftest")
    p.add_argument("--on-dev", action="store_true", help="Run on `dev` to see if this machine matches CI checksums")
    p.add_argument("--update-snapshots", action="store_true")
    p.add_argument("--profile", default="docker")
    args = parser.parse_args()
    root = repo_root()
    state = load_state(root)
    if args.cmd == "regenerate":
        regenerate(root, state, args)
    elif args.cmd == "check":
        raise SystemExit(check(root, state, args))
    else:
        nftest(root, state, args)


if __name__ == "__main__":
    main_wrapper(main)
