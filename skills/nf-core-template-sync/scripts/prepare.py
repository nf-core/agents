#!/usr/bin/env python3
"""Phase 1 of nf-core-template-sync.

Checks the pipeline, merges `dev` into the bot's sync branch, resolves the files that have a fixed rule,
collects the sources for each tools release in the range, and writes worklist.md for the agent.

Exit codes: 0 = ready for phase 2, 2 = hard stop, 3 = the user must decide (see the message).
"""

from __future__ import annotations

import argparse
import fnmatch
import itertools
import platform
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from common import (
    BOT_EMAIL,
    BOT_LOGIN,
    BOT_SUBJECT,
    PR_TITLE,
    SKILL_DIR,
    StopError,
    fetch_url,
    file_at,
    gh_json,
    git,
    main_wrapper,
    path_exists_at,
    repo_root,
    run,
    save_json,
    state_dir,
    template_components,
    version_tuple,
)

STATUS_TEXT = {
    "UU": "both changed",
    "AA": "both added",
    "UD": "the template changed it, the pipeline deleted it",
    "DU": "the template deleted it, the pipeline changed it",
    "AU": "added by the template, conflict",
    "UA": "added by the pipeline, conflict",
    "DD": "both deleted",
}
BLOG_MERGE_HEADING = re.compile(r"conflict|merge the pipeline template|update your pipeline template|sync pr", re.I)
NF_DOCS_RAW = "https://raw.githubusercontent.com/nextflow-io/nextflow/{ref}/docs/"
NF_CORE_DOCS = [
    ("Template syncs: overview", "https://nf-co.re/docs/developing/template-syncs/overview"),
    ("Merging automated PRs", "https://nf-co.re/docs/developing/template-syncs/merge-automated-pull-requests"),
]


def find_remote(root: Path) -> tuple:
    for line in git("remote", "-v", cwd=root).splitlines():
        m = re.match(r"^(\S+)\s+\S*github\.com[:/]nf-core/([A-Za-z0-9_.-]+?)(?:\.git)?\s+\(fetch\)", line)
        if m:
            return m.group(1), m.group(2)
    raise StopError(
        "No git remote points to an nf-core repository. Add one, for example:\n"
        "  git remote add upstream https://github.com/nf-core/<pipeline>.git"
    )


def find_sync_pr(repo: str, pr_arg: str) -> dict:
    fields = "number,title,url,headRefName,headRefOid,baseRefName,author,isCrossRepository"
    if pr_arg:
        pr = gh_json("pr", "view", pr_arg, "-R", repo, "--json", fields)
        if not pr:
            raise StopError(f"Could not read PR {pr_arg} in {repo}.")
        prs = [pr]
    else:
        prs = gh_json("pr", "list", "-R", repo, "--state", "open", "--limit", "50", "--json", fields) or []
    sync = []
    for pr in prs:
        m = PR_TITLE.search(pr["title"])
        if m and pr["author"]["login"] == BOT_LOGIN and not pr["isCrossRepository"]:
            suffix = re.search(r"-(\d+)$", pr["headRefName"])
            pr["version"] = m.group(1)
            pr["_key"] = (version_tuple(pr["version"]), int(suffix.group(1)) if suffix else 1)
            sync.append(pr)
    if not sync:
        raise StopError(
            f"No open template sync PR from {BOT_LOGIN} in {repo}. "
            "Do not run `nf-core pipelines sync` by hand; ask the nf-core infrastructure team instead."
        )
    sync.sort(key=lambda p: p["_key"])
    chosen = sync[-1]
    if chosen["baseRefName"] != "dev":
        raise StopError(
            f"The sync PR targets `{chosen['baseRefName']}`, not `dev`. Ask the maintainers before you continue."
        )
    chosen["older_open"] = [p["url"] for p in sync[:-1]]
    return chosen


def check_branch_commits(root: Path, dev: str, head: str) -> tuple:
    bot, human = [], []
    log = git("log", "--format=%H%x1f%an%x1f%ae%x1f%s%x1f%P", f"{dev}..{head}", cwd=root)
    for line in filter(None, log.splitlines()):
        sha, name, email, subject, parents = line.split("\x1f")
        is_bot = (name == BOT_LOGIN or email == BOT_EMAIL) and BOT_SUBJECT.match(subject) and len(parents.split()) == 1
        (bot if is_bot else human).append({"sha": sha, "author": name, "subject": subject})
    return bot, human


def find_from_version(root: Path, dev: str, head: str) -> tuple:
    base = git("merge-base", dev, head, cwd=root)
    for line in git("log", "--format=%H%x1f%s", base, cwd=root).splitlines():
        sha, subject = line.split("\x1f", 1)
        m = BOT_SUBJECT.match(subject)
        if m:
            return m.group(1), sha
    raise StopError(
        "Could not find the previous template commit in the history of `dev`. The TEMPLATE branch may be broken."
    )


def find_template_commit(root: Path, head: str, version: str) -> str | None:
    for line in git("log", "--format=%H%x1f%s", head, cwd=root).splitlines():
        sha, subject = line.split("\x1f", 1)
        m = BOT_SUBJECT.match(subject)
        if m and m.group(1) == version:
            return sha
    return None


def remerge_with_base(root: Path, base: str, head: str, dev: str) -> None:
    """Replace the merge result with a merge against `base`. MERGE_HEAD stays, so the commit is still a real merge."""
    proc = run(["git", "merge-tree", "--write-tree", f"--merge-base={base}", head, dev], cwd=root, check=False)
    if proc.returncode not in (0, 1):
        raise StopError(f"git merge-tree failed:\n{proc.stderr}")
    lines = proc.stdout.splitlines()
    stages = list(itertools.takewhile(bool, lines[1:]))
    git("read-tree", "--reset", "-u", lines[0], cwd=root)
    if stages:
        paths = sorted({s.split("\t", 1)[1] for s in stages})
        # A zero-mode entry removes stage 0 so that the conflict stages can be added.
        info = "".join(f"0 {'0' * 40}\t{p}\n" for p in paths) + "".join(f"{s}\n" for s in stages)
        subprocess.run(["git", "update-index", "--index-info"], input=info, text=True, cwd=root, check=True)


def check_tools(root: Path, dev: str, to_version: str) -> dict:
    if run(["gh", "auth", "status"], check=False).returncode != 0:
        raise StopError("The GitHub CLI is not logged in. Run `gh auth login` first.")
    if shutil.which("uvx"):
        nf_core = ["uvx", "--from", f"nf-core=={to_version}", "nf-core"]
    elif shutil.which("nf-core"):
        nf_core = ["nf-core"]
    else:
        raise StopError("Install uv (recommended) or nf-core/tools.")
    proc = run([*nf_core, "--version"], check=False, timeout=600)
    found = re.search(r"version (\S+)", proc.stdout + proc.stderr)
    if not found or found.group(1) != to_version:
        raise StopError(
            f"nf-core/tools {to_version} is required (lint compares the pipeline with the template of the installed version). "
            f"Found: {found.group(1) if found else 'none'}. Install uv so the scripts can run `uvx --from nf-core=={to_version}`."
        )
    if not shutil.which("nextflow"):
        raise StopError("Nextflow is not installed.")
    nf_version = re.search(r"version (\d+\.\d+\.\d+)", run(["nextflow", "-version"], check=False).stdout)
    config = file_at(dev, "nextflow.config", root) or ""
    required = re.search(r"nextflowVersion\s*=\s*['\"]!?>=\s*([\d.]+)", config)
    if nf_version and required and version_tuple(nf_version.group(1)) < version_tuple(required.group(1)):
        raise StopError(f"Nextflow {required.group(1)} or later is required. Installed: {nf_version.group(1)}.")
    return {
        "nf_core_cmd": nf_core,
        "nf_core_version": to_version,
        "nextflow_version": nf_version.group(1) if nf_version else None,
        "nextflow_min": required.group(1) if required else None,
        "arch": platform.machine(),
    }


def checkout_and_merge(root: Path, remote: str, pr: dict, dev_sha: str, base: str | None) -> None:
    branch = pr["headRefName"]
    remote_head = f"{remote}/{branch}"
    if git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", cwd=root, check=False):
        local = git("rev-parse", branch, cwd=root)
        if local != pr["headRefOid"] and (
            run(["git", "merge-base", "--is-ancestor", local, pr["headRefOid"]], cwd=root, check=False).returncode != 0
        ):
            raise StopError(
                f"Your local branch `{branch}` has commits that are not on {remote}. Rename or delete it first.", 3
            )
        git("switch", "-q", branch, cwd=root)
        git("merge", "-q", "--ff-only", remote_head, cwd=root)
    else:
        git("switch", "-q", "-c", branch, "--track", remote_head, cwd=root)
    proc = run(
        ["git", "merge", "--no-ff", "--no-commit", "-m", f"Merge branch 'dev' into {branch}", dev_sha],
        cwd=root,
        check=False,
    )
    if "Already up to date" in proc.stdout:
        raise StopError("The sync branch already contains `dev`. There is nothing to merge.")
    if proc.returncode not in (0, 1):
        raise StopError(f"git merge failed:\n{proc.stderr}")
    if base:
        remerge_with_base(root, base, pr["headRefOid"], dev_sha)


def rm(root: Path, *paths: str) -> None:
    run(["git", "rm", "-r", "-q", "-f", "--ignore-unmatch", "--", *paths], cwd=root)
    for p in paths:
        target = root / p
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def compare_shas(dev_sha: str, tpl_sha: str) -> str:
    if dev_sha == tpl_sha:
        return "identical"
    proc = run(["gh", "api", f"repos/nf-core/modules/compare/{dev_sha}...{tpl_sha}", "--jq", ".status"], check=False)
    return proc.stdout.strip() or "unknown"


def apply_rules(root: Path, dev: str, head: str) -> tuple:
    """Resolve files with a fixed rule. Returns (auto_resolved, components, container_configs_enabled)."""
    resolved = []
    dev_json = file_at(dev, "modules.json", root)
    dev_components = {c["path"]: c for c in template_components(dev, root)} if dev_json else {}
    components = []
    for comp in template_components(head, root):
        path = comp["path"]
        if not path_exists_at(dev, path, root):
            rm(root, path)
            comp.update(action="removed on dev", dev_sha=None)
            resolved.append({"file": path + "/", "action": "Kept the deletion from `dev`", "source": "Pipeline choice"})
            components.append(comp)
            continue
        dev_sha = dev_components.get(path, {}).get("sha")
        status = compare_shas(dev_sha, comp["sha"]) if dev_sha else "unknown"
        comp.update(
            dev_sha=dev_sha,
            compare=status,
            action="update" if status == "ahead" else "keep",
            tests_on_dev=path_exists_at(dev, f"{path}/tests", root),
        )
        git("restore", f"--source={dev}", "--staged", "--worktree", "--", path, cwd=root)
        note = "Took `dev`"
        if comp["action"] == "update":
            rm(root, f"{path}/.conda-lock")
            note += "; deleted `.conda-lock`; update to the template version in phase 3"
        else:
            note += f"; `dev` version is {'the same' if status == 'identical' else 'newer or equal'} ({status})"
        resolved.append({"file": path + "/", "action": note, "source": "nf-core/agents#12"})
        components.append(comp)
    if dev_json:
        git("restore", f"--source={dev}", "--staged", "--worktree", "--", "modules.json", cwd=root)
        resolved.append(
            {
                "file": "modules.json",
                "action": "Took `dev`; phase 3 updates the template components",
                "source": "nf-core/agents#12",
            }
        )

    # Lint draws the logos again with local fonts, so a regenerated logo can differ from a correct one.
    logos = [
        p
        for p in git("ls-tree", "-r", "--name-only", dev, "--", "assets", "docs/images", cwd=root).splitlines()
        if re.search(r"nf-core-[^/]*_logo[^/]*\.png$", p)
    ]
    if logos:
        git("restore", f"--source={dev}", "--staged", "--worktree", "--", *logos, cwd=root)
        resolved.append(
            {
                "file": "nf-core logo images",
                "action": "Took the files from `dev`",
                "source": "Known nf-core/tools issue",
            }
        )

    rm(root, "ro-crate-metadata.json")
    resolved.append(
        {"file": "ro-crate-metadata.json", "action": "Deleted; regenerated in phase 3", "source": "nf-core/agents#12"}
    )

    yml = file_at(dev, ".nf-core.yml", root) or ""
    enabled = not re.search(r"^\s+container_configs:\s*(false|False)\s*$", yml, re.M)
    configs = [p for p in git("ls-files", "--", "conf/containers_*.config", cwd=root).splitlines() if p]
    if configs:
        rm(root, *sorted(set(configs)))
        action = (
            "Deleted; regenerated in phase 3"
            if enabled
            else "Deleted; `.nf-core.yml` disables the container_configs lint"
        )
        resolved.append({"file": "conf/containers_*.config", "action": action, "source": "nf-core/agents#12"})
    return resolved, components, enabled


def unmerged(root: Path) -> list:
    out = []
    for line in git("status", "--porcelain=v1", cwd=root).splitlines():
        code, path = line[:2], line[3:]
        if code in STATUS_TEXT:
            text = (root / path).read_text(errors="replace") if (root / path).is_file() else ""
            blocks = len(re.findall(r"(?m)^<<<<<<< ", text))
            out.append({"file": path, "status": code, "meaning": STATUS_TEXT[code], "blocks": blocks})
    return out


def template_change_map(root: Path, old: str, new: str) -> dict:
    deleted, renamed = [], []
    for line in git("diff", "--name-status", "-M", old, new, cwd=root).splitlines():
        parts = line.split("\t")
        if parts[0] == "D":
            deleted.append(parts[1])
        elif parts[0].startswith("R"):
            renamed.append({"from": parts[1], "to": parts[2]})
    stale = [p for p in deleted if (root / p).exists()]
    stale += [r["from"] for r in renamed if (root / r["from"]).exists()]
    # Files from template versions before `old`: a manual template update can leave them behind.
    older = set()
    for line in git("log", "--format=%H%x1f%s", old, cwd=root).splitlines():
        sha, subject = line.split("\x1f", 1)
        if BOT_SUBJECT.match(subject):
            older |= set(git("ls-tree", "-r", "--name-only", sha, cwd=root).splitlines())
    current = set(git("ls-tree", "-r", "--name-only", new, cwd=root).splitlines())
    leftovers = sorted(
        p
        for p in older - current
        if (root / p).exists() and p not in stale and not re.match(r"^(modules|subworkflows)/", p)
    )
    return {"deleted": deleted, "renamed": renamed, "still_present": stale, "older_template_files": leftovers}


def changelog_sections(from_v: str, to_v: str) -> tuple:
    text = fetch_url(f"https://raw.githubusercontent.com/nf-core/tools/{to_v}/CHANGELOG.md") or fetch_url(
        "https://raw.githubusercontent.com/nf-core/tools/main/CHANGELOG.md"
    )
    if not text:
        return [], {}
    heads = list(re.finditer(r"^## \[?v?(\d+\.\d+(?:\.\d+)?)[^\n]*$", text, re.M))
    sections, dates = [], {}
    for i, h in enumerate(heads):
        v = h.group(1)
        if not version_tuple(from_v) < version_tuple(v) <= version_tuple(to_v):
            continue
        date = re.search(r"\[(\d{4}-\d{2}-\d{2})\]", h.group(0))
        dates[v] = date.group(1) if date else None
        body = text[h.end() : heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        tpl = re.search(r"^### Template\s*$(.*?)(?=^##)", body + "\n##", re.M | re.S)
        sections.append({"version": v, "template": tpl.group(1).strip() if tpl else ""})
    sections.sort(key=lambda s: version_tuple(s["version"]))
    return sections, dates


def markdown_sections(text: str) -> list:
    """Split Markdown into (level, heading, body) sections, ignoring headings inside code fences."""
    out, fence, current = [], False, None
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
        m = None if fence else re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            current = [len(m.group(1)), m.group(2).strip(), []]
            out.append(current)
        elif current:
            current[2].append(line)
    return [(lvl, head, "\n".join(body).strip()) for lvl, head, body in out]


def blog_posts(versions: list, sdir: Path) -> list:
    rss = fetch_url("https://nf-co.re/blog/rss.xml")
    if not rss:
        return []
    ns = "{http://purl.org/rss/1.0/modules/content/}encoded"
    minors = {version_tuple(v)[:2] for v in versions}
    posts = []
    for item in ET.fromstring(rss).findall("./channel/item"):
        m = re.search(r"nf-core/tools\s*-\s*v?(\d+\.\d+(?:\.\d+)?)", item.findtext("title") or "")
        if not m or version_tuple(m.group(1))[:2] not in minors:
            continue
        content = item.findtext(ns) or ""
        version = m.group(1)
        (sdir / "sources" / f"blog-{version}.md").write_text(content)
        sections, keep_level = [], None
        for lvl, head, body in markdown_sections(content):
            if keep_level is not None and lvl <= keep_level:
                keep_level = None
            if keep_level is None and BLOG_MERGE_HEADING.search(head):
                keep_level = lvl
            if keep_level is not None:
                sections.append((lvl, head, body))
        videos = [
            v if v.startswith("http") else f"https://www.youtube.com/watch?v={v}"
            for v in re.findall(r"YouTube[^>]*\bid=[\"']([^\"']+)", content)
        ]
        posts.append({"version": version, "url": item.findtext("link"), "sections": sections, "videos": videos})
    return sorted(posts, key=lambda p: version_tuple(p["version"]))


def release_notes(versions: list) -> list:
    notes = []
    for v in versions:
        path = SKILL_DIR / "references" / "releases" / f"{v}.md"
        if path.exists():
            general, by_path = [], []
            for lvl, head, body in markdown_sections(path.read_text()):
                if lvl == 1:
                    continue
                if lvl == 2 and head.startswith("`") and head.endswith("`"):
                    by_path.append({"pattern": head.strip("`"), "body": body})
                else:
                    general.append(f"{'#' * lvl} {head}\n\n{body}")
            notes.append(
                {"version": v, "file": str(path.relative_to(SKILL_DIR)), "general": general, "by_path": by_path}
            )
    return notes


def blog_heading_matches(head: str, path: str) -> bool:
    """Blog headings name files with the example pipeline name, for example `utils_nfcore_demo_pipeline`."""

    def generic(s: str) -> str:
        return re.sub(r"utils_nfcore_\w+?_pipeline", "utils_nfcore_PIPELINE_pipeline", s)

    name = Path(path).name
    return generic(path) in generic(head) or (name not in ("main.nf", "nextflow.config") and name in head)


def path_matches(path: str, pattern: str) -> bool:
    return path == pattern or fnmatch.fnmatch(path, pattern) or (pattern.endswith("/") and path.startswith(pattern))


GRAPHQL = """query($q: String!) { search(query: $q, type: ISSUE, first: 40) { nodes { ... on PullRequest {
  number title url mergedAt baseRefName author { login } repository { name } commits { totalCount } } } } }"""


def reference_prs(pipeline: str, from_v: str, to_v: str, release_date: str) -> list:
    queries = [f'org:nf-core is:pr is:merged in:title "Template update for nf-core/tools v{to_v}"']
    if release_date:
        queries.append(f"org:nf-core is:pr is:merged in:title template -author:{BOT_LOGIN} merged:>={release_date}")
    found = {}
    for q in queries:
        data = gh_json("api", "graphql", "-f", f"query={GRAPHQL}", "-f", f"q={q}", check=False) or {}
        for node in (data.get("data") or {}).get("search", {}).get("nodes", []):
            # One-commit PRs were marked merged by GitHub when a newer sync merged; they hold no resolutions.
            if not node or node["repository"]["name"] == pipeline or node["commits"]["totalCount"] <= 1:
                continue
            if node["baseRefName"] != "dev":
                continue
            if to_v not in node["title"] and "Template update for nf-core/tools" not in node["title"]:
                continue
            found[node["url"]] = node
    refs = []
    for node in sorted(found.values(), key=lambda n: n["mergedAt"])[:15]:
        repo, num = node["repository"]["name"], node["number"]
        files = gh_json("api", f"repos/nf-core/{repo}/pulls/{num}/files?per_page=100", check=False) or []
        patch = next((f.get("patch", "") for f in files if f["filename"] == ".nf-core.yml"), "")
        old = re.search(r"^-\s*nf_core_version:\s*['\"]?([\d.]+)", patch, re.M)
        refs.append(
            {
                "repo": repo,
                "number": num,
                "url": node["url"],
                "title": node["title"],
                "merged_at": node["mergedAt"],
                "author": node["author"]["login"] if node["author"] else None,
                "commits": node["commits"]["totalCount"],
                "from_version": old.group(1) if old else None,
            }
        )
    refs.sort(key=lambda r: (r["from_version"] != from_v, r["merged_at"]))
    return refs


def remerge_diffs(ref: dict, pipeline: str, paths: list, sdir: Path) -> dict:
    """How a reference PR resolved the same files, from `git show --remerge-diff` on its merge commit."""
    commits = (
        gh_json("api", f"repos/nf-core/{ref['repo']}/pulls/{ref['number']}/commits?per_page=100", check=False) or []
    )
    merge = next((c["sha"] for c in commits if len(c.get("parents", [])) == 2), None)
    if not merge:
        return {}
    clone = sdir / "refs" / ref["repo"]
    mapping = {p.replace(pipeline, ref["repo"]): p for p in paths}
    try:
        if not clone.exists():
            proc = run(
                [
                    "git",
                    "clone",
                    "-q",
                    "--filter=blob:none",
                    "--no-checkout",
                    f"https://github.com/nf-core/{ref['repo']}.git",
                    clone,
                ],
                check=False,
                timeout=300,
            )
            if proc.returncode != 0:
                return {}
        # Without a pathspec, a partial clone can fail to fetch some blobs ("not our ref").
        proc = run(
            ["git", "show", "--remerge-diff", "--format=", merge, "--", *mapping], cwd=clone, check=False, timeout=300
        )
    except subprocess.TimeoutExpired:
        return {}
    out = {}
    for chunk in re.split(r"(?m)^(?=diff --git )", proc.stdout):
        m = re.match(r"diff --git a/(\S+) ", chunk)
        if m and m.group(1) in mapping:
            out[mapping[m.group(1)]] = chunk.strip()
    ref["merge_commit"] = merge
    return out


def nextflow_docs(version: str) -> dict:
    ref = f"v{version}" if version else "master"
    names = gh_json("api", f"repos/nextflow-io/nextflow/contents/docs?ref={ref}", check=False)
    if not names:
        ref = "master"
        names = gh_json("api", "repos/nextflow-io/nextflow/contents/docs?ref=master", check=False) or []
    return {"ref": ref, "raw_base": NF_DOCS_RAW.format(ref=ref), "entries": sorted(n["name"] for n in names)}


def write_sources(
    sdir: Path, state: dict, changelog: list, posts: list, notes: list, refs: list, nf_docs: dict
) -> None:
    lines = [f"# Sources: nf-core/tools {state['from_version']} → {state['to_version']}", ""]
    lines += ["## nf-core docs", ""] + [f"- [{t}]({u})" for t, u in NF_CORE_DOCS] + [""]
    for note in notes:
        lines += [f"## Skill release notes for {note['version']} (`{note['file']}`)", "", *note["general"], ""]
        if note["by_path"]:
            lines += [
                "Per-path notes (copied into the worklist): " + ", ".join(f"`{s['pattern']}`" for s in note["by_path"]),
                "",
            ]
    for sec in changelog:
        lines += [
            f"## Changelog: template changes in {sec['version']}",
            "",
            f"https://github.com/nf-core/tools/releases/tag/{sec['version']}",
            "",
            sec["template"] or "(none)",
            "",
        ]
    for post in posts:
        lines += [
            f"## Blog post for {post['version']}: merge-conflict guidance",
            "",
            post["url"],
            f"Full post: `sources/blog-{post['version']}.md`",
            "",
        ]
        lines += [f"Video: {v}" for v in post["videos"]] + [""]
        for lvl, head, body in post["sections"]:
            lines += [f"{'#' * min(lvl + 2, 6)} {head}", "", body, ""]
    lines += ["## Reference PRs (other pipelines, same target version)", ""]
    if refs:
        lines += ["| PR | From | Commits | Merged | By |", "| --- | --- | --- | --- | --- |"]
        for r in refs:
            lines.append(
                f"| [{r['repo']}#{r['number']}]({r['url']}) | {r['from_version'] or '?'} | {r['commits']} | "
                f"{r['merged_at'][:10]} | {r['author']} |"
            )
    else:
        lines.append("None found yet. This pipeline may be one of the first to sync.")
    lines += [
        "",
        "## Nextflow docs",
        "",
        f"Docs source for Nextflow `{nf_docs['ref']}` (the pipeline minimum): {nf_docs['raw_base']}<page>",
        "Pages: " + ", ".join(f"`{e}`" for e in nf_docs["entries"]),
        "",
    ]
    (sdir / "sources.md").write_text("\n".join(lines) + "\n")


def write_worklist(sdir: Path, state: dict, notes: list, posts: list, ref_diffs: dict) -> None:
    pr = state["pr"]
    lines = [
        f"# Worklist: nf-core/{state['pipeline']} template sync {state['from_version']} → {state['to_version']}",
        "",
        f"- PR: {pr['url']} (branch `{pr['headRefName']}`)",
        "- `ours` / `HEAD` = the template side (the sync branch). `theirs` = the pipeline side (`dev`).",
        f"- Sources for every release in the range: `{sdir / 'sources.md'}`",
        "",
        "## Resolved by rule (no action needed)",
        "",
    ]
    lines += [f"- `{r['file']}`: {r['action']} ({r['source']})" for r in state["auto_resolved"]]
    changes = state["template_changes"]
    if changes["still_present"]:
        lines += ["", "## The template deleted or renamed these files, but they are still present", ""]
        lines += [
            f"- `{p}`: delete it, or record a decision that the pipeline needs it" for p in changes["still_present"]
        ]
    if changes["older_template_files"]:
        lines += ["", "## Files from older template versions that the current template does not have", ""]
        lines += [
            "These can be leftovers from a manual template update. Delete them, or record why the pipeline needs them.",
            "",
        ]
        lines += [f"- `{p}`" for p in changes["older_template_files"]]
    lines += ["", f"## Conflicts to resolve ({len(state['conflicts'])})", ""]
    for c in state["conflicts"]:
        path = c["file"]
        lines += [f"### `{path}`: {c['meaning']}" + (f" ({c['blocks']} conflict blocks)" if c["blocks"] else ""), ""]
        for note in notes:
            for sec in note["by_path"]:
                if path_matches(path, sec["pattern"]):
                    lines += [f"**Skill release notes {note['version']}** (highest priority):", "", sec["body"], ""]
        for post in posts:
            sections = post["sections"]
            for i, (level, head, body) in enumerate(sections):
                if not blog_heading_matches(head, path):
                    continue
                subs = itertools.takewhile(lambda s, lvl=level: s[0] > lvl, sections[i + 1 :])
                text = "\n\n".join([body] + [f"{'#' * min(lv + 2, 6)} {h}\n\n{b}" for lv, h, b in subs]).strip()
                lines += [f"**Blog {post['version']}: {head}**", "", text, ""]
        for ref_url, diffs in ref_diffs.items():
            if path in diffs:
                diff_lines = diffs[path].splitlines()
                more = f"\n... ({len(diff_lines) - 80} more lines)" if len(diff_lines) > 80 else ""
                lines += [
                    f"**How {ref_url} resolved it** (`--remerge-diff`: `-` lines were dropped, `+` lines added):",
                    "",
                    "```diff",
                    "\n".join(diff_lines[:80]) + more,
                    "```",
                    "",
                ]
    (sdir / "worklist.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pr", default="", help="Sync PR number or URL (default: the newest open sync PR)")
    parser.add_argument(
        "--continue-existing",
        action="store_true",
        help="Continue when the sync branch already has commits that are not from the bot",
    )
    parser.add_argument(
        "--ref-diffs", type=int, default=2, help="Reference PRs to read with --remerge-diff (default: 2)"
    )
    args = parser.parse_args()

    root = repo_root()
    sdir = state_dir(root)
    if (Path(git("rev-parse", "--absolute-git-dir", cwd=root)) / "MERGE_HEAD").exists():
        raise StopError(
            "A merge is already in progress. Continue with phase 2, or run `git merge --abort` to start again."
        )
    if git("status", "--porcelain", "--untracked-files=no", cwd=root):
        raise StopError("The working tree has uncommitted changes. Commit or stash them first.")

    remote, pipeline = find_remote(root)
    repo = f"nf-core/{pipeline}"
    print(f"Pipeline: {repo} (remote `{remote}`)")
    pr = find_sync_pr(repo, args.pr)
    to_v = pr["version"]
    print(f"Sync PR: {pr['url']} ({pr['headRefName']})")
    branch = pr["headRefName"]
    git(
        "fetch",
        "-q",
        remote,
        f"+refs/heads/dev:refs/remotes/{remote}/dev",
        f"+refs/heads/TEMPLATE:refs/remotes/{remote}/TEMPLATE",
        f"+refs/heads/{branch}:refs/remotes/{remote}/{branch}",
        cwd=root,
    )
    dev_sha = git("rev-parse", f"{remote}/dev", cwd=root)
    head_sha = git("rev-parse", f"{remote}/{branch}", cwd=root)
    if head_sha != pr["headRefOid"]:
        raise StopError("The fetched sync branch does not match the PR head. Fetch again.")

    merges = git("rev-list", "--merges", f"{remote}/TEMPLATE", cwd=root)
    if merges:
        raise StopError(
            "The TEMPLATE branch contains merge commits, so it is probably broken (for example `dev` was merged into it). "
            "Do not try to repair it. Tell the pipeline maintainers and the nf-core infrastructure team."
        )
    bot_commits, human_commits = check_branch_commits(root, dev_sha, head_sha)
    if human_commits and not args.continue_existing:
        listing = "\n".join(f"  {c['sha'][:10]} {c['author']}: {c['subject']}" for c in human_commits)
        raise StopError(
            f"Someone already started work on `{branch}`:\n{listing}\n"
            "Ask the user if the skill must continue from that work (then run again with --continue-existing).",
            3,
        )
    from_v, from_sha = find_from_version(root, dev_sha, head_sha)
    if version_tuple(from_v) >= version_tuple(to_v):
        raise StopError(f"`dev` already contains template {from_v}. There is nothing to sync.")
    main_nf = file_at(dev_sha, "main.nf", root) or ""
    if not re.search(r"^\s*workflow\b", main_nf, re.M):
        raise StopError("`main.nf` on `dev` has no workflow block. This looks like a DSL1 pipeline. Do not work on it.")

    warnings = []
    base_override = None
    yml = re.search(r"^nf_core_version:\s*['\"]?([\d.]+)", file_at(dev_sha, ".nf-core.yml", root) or "", re.M)
    if yml and version_tuple(yml.group(1)) > version_tuple(from_v):
        better = find_template_commit(root, head_sha, yml.group(1))
        git_ok = version_tuple(git("--version", cwd=root)) >= (2, 40, 0)
        if better and git_ok:
            base_override = {"git_merge_base_version": from_v, "version": yml.group(1), "sha": better}
            from_v, from_sha = yml.group(1), better
            warnings.append(
                f"`.nf-core.yml` on `dev` says template {from_v}, but the git history only contains template "
                f"{base_override['git_merge_base_version']} (after a squash merge, a manual template update or a "
                f"rewritten TEMPLATE branch). The merge uses the TEMPLATE {from_v} commit as its base. "
                "A person must review this."
            )
        else:
            warnings.append(
                f"`.nf-core.yml` on `dev` says {yml.group(1)}, but the git history shows template {from_v}. "
                "Expect more conflicts than usual." + ("" if git_ok else " Git 2.40 or later can reduce them.")
            )
    if pr["older_open"]:
        warnings.append("Older sync PRs are also open. They close when this one merges: " + ", ".join(pr["older_open"]))

    print("Checking tools (the first run of uvx downloads nf-core/tools)...")
    tools = check_tools(root, dev_sha, to_v)
    checkout_and_merge(root, remote, pr, dev_sha, base_override["sha"] if base_override else None)
    auto_resolved, components, cc_enabled = apply_rules(root, dev_sha, head_sha)
    if base_override:
        auto_resolved.insert(
            0,
            {
                "file": "(all files)",
                "action": f"Merged with the TEMPLATE {from_v} commit as the base, not the git merge base "
                f"(template {base_override['git_merge_base_version']}). Review this.",
                "source": "`nf_core_version` in `.nf-core.yml` on `dev`",
            },
        )
    changes = template_change_map(root, from_sha, head_sha)
    conflicts = unmerged(root)

    print("Collecting sources...")
    (sdir / "sources").mkdir(exist_ok=True)
    changelog, dates = changelog_sections(from_v, to_v)
    versions = [s["version"] for s in changelog] or [to_v]
    posts = blog_posts(versions, sdir)
    notes = release_notes(versions)
    refs = reference_prs(pipeline, from_v, to_v, dates.get(to_v) or "")
    ref_diffs = {}
    paths = [c["file"] for c in conflicts]
    for ref in refs[:6] if paths and args.ref_diffs else []:
        diffs = remerge_diffs(ref, pipeline, paths, sdir)
        if diffs:
            ref_diffs[ref["url"]] = diffs
        if len(ref_diffs) >= args.ref_diffs:
            break
    nf_docs = nextflow_docs(tools["nextflow_min"])

    state = {
        "pipeline": pipeline,
        "repo": repo,
        "remote": remote,
        "root": str(root),
        "pr": {k: pr[k] for k in ("number", "title", "url", "headRefName", "headRefOid")},
        "from_version": from_v,
        "from_commit": from_sha,
        "to_version": to_v,
        "head_sha": head_sha,
        "dev_sha": dev_sha,
        "versions": versions,
        "bot_commits": bot_commits,
        "human_commits": human_commits,
        "tools": tools,
        "template_components": components,
        "container_configs_enabled": cc_enabled,
        "auto_resolved": auto_resolved,
        "template_changes": changes,
        "conflicts": conflicts,
        "reference_prs": refs,
        "nextflow_docs": nf_docs,
        "warnings": warnings,
        "merge_base_override": base_override,
        "changelog": changelog,
        "blog_posts": [{"version": p["version"], "url": p["url"], "videos": p["videos"]} for p in posts],
    }
    save_json(sdir / "state.json", state)
    write_sources(sdir, state, changelog, posts, notes, refs, nf_docs)
    write_worklist(sdir, state, notes, posts, ref_diffs)

    print(
        f"\nTemplate {from_v} → {to_v}. Resolved by rule: {len(auto_resolved)}. "
        f"Conflicts left: {len(conflicts)}. Template files to remove: {len(changes['still_present'])}."
    )
    for w in warnings:
        print(f"WARNING: {w}")
    print(f"\nNext: read {sdir / 'worklist.md'} and {sdir / 'sources.md'}, then resolve the conflicts (phase 2).")


if __name__ == "__main__":
    main_wrapper(main)
