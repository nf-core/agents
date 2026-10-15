#!/usr/bin/env python3
"""Write the HTML report and the PR comment for a template sync.

Reads state.json, decisions.json, checks.json and authored_lines.json from .git/nf-core-template-sync/.
Usage: report.py [--out DIR]   (default: a new temporary directory)
"""

from __future__ import annotations

import argparse
import html
import re
import tempfile
from datetime import date
from pathlib import Path

from common import SKILL_DIR, StopError, git, load_json, load_state, main_wrapper, repo_root, state_dir

CATEGORY_TEXT = {
    "rule": ("Fixed rule", "--c1"),
    "template": ("Template version", "--c2"),
    "pipeline": ("Pipeline version", "--c3"),
    "combined": ("Both, combined", "--c4"),
    "agent-written": ("New code by the agent", "--c5"),
    "deleted": ("Deleted", "--c6"),
    "kept": ("Kept a file the template removed", "--c7"),
}
# Files that `nf-core pipelines lint` (files_unchanged) expects to be identical to the template.
TEMPLATE_OWNED = re.compile(
    r"^(\.gitattributes|\.prettierrc\.yml|CODE_OF_CONDUCT\.md|LICEN[CS]E(\.md)?|\.github/\.dockstore\.yml|"
    r"\.github/ISSUE_TEMPLATE/.*|\.github/PULL_REQUEST_TEMPLATE\.md|\.github/workflows/(branch|pr-comment|linting)\.yml|"
    r"assets/(email_template\.(html|txt)|sendmail_template\.txt)|docs/README\.md)$"
)
PIPELINE_CONTENT = re.compile(
    r"^(CHANGELOG\.md|README\.md|CITATIONS\.md|docs/(output|usage)\.md|assets/(schema_input\.json|samplesheet\.csv|"
    r"multiqc_config\.yml|methods_description_template\.yml)|nextflow_schema\.json|conf/(modules|test|test_full)\.config|"
    r"main\.nf|workflows/.*|tests/.*|assets/nf-core-.*|docs/images/.*|\.nf-core\.yml|modules\.json)$"
)
SKIP_DIVERGENCE = re.compile(
    r"^(modules|subworkflows)/nf-core/|^conf/containers_|ro-crate-metadata\.json$|\.conda-lock/|\.snap$"
)


def esc(text) -> str:
    """Escape text, then turn `code` spans and bare URLs into HTML."""
    out = html.escape(str(text or ""))
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return re.sub(r"(?<![\"'>])(https?://[^\s<)]+)", r'<a href="\1">\1</a>', out)


def link(source) -> str:
    if isinstance(source, dict):
        title, url = source.get("title") or source.get("url"), source.get("url")
    else:
        title, url = source, source
    return f'<a href="{html.escape(url)}">{esc(title)}</a>' if url and str(url).startswith("http") else esc(title)


def bar_chart(counts: dict) -> str:
    rows = [(k, v) for k, v in counts.items() if v]
    if not rows:
        return ""
    width, row_h, label_w = 760, 30, 230
    top = max(v for _, v in rows)
    parts = [
        f'<svg class="figure" viewBox="0 0 {width} {len(rows) * row_h + 10}" role="img" '
        f'aria-label="Number of files for each type of resolution">'
    ]
    for i, (key, value) in enumerate(rows):
        label, color = CATEGORY_TEXT.get(key, (key, "--c6"))
        y = i * row_h + 5
        bar = max(4, (width - label_w - 60) * value / top)
        parts.append(
            f'<text x="{label_w - 10}" y="{y + 18}" text-anchor="end" font-size="14" fill="var(--text)">{esc(label)}</text>'
            f'<rect x="{label_w}" y="{y + 4}" width="{bar:.0f}" height="20" rx="4" fill="var({color})"/>'
            f'<text x="{label_w + bar + 8:.0f}" y="{y + 19}" font-size="14" fill="var(--text)">{value}</text>'
        )
    return "".join(parts) + "</svg>"


def branch_diagram(state: dict) -> str:
    frm, to, branch = state["from_version"], state["to_version"], state["pr"]["headRefName"]
    return f"""<svg class="figure" viewBox="0 0 820 230" role="img" aria-labelledby="bd-title">
<title id="bd-title">TEMPLATE commit {esc(to)} goes to the sync branch. dev is merged into the sync branch.
The pull request then merges the sync branch into dev with a merge commit.</title>
<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
<path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"/></marker></defs>
<g font-size="13" fill="var(--text)">
<text x="10" y="44" font-weight="700" fill="var(--c2)">TEMPLATE</text>
<line x1="110" y1="40" x2="420" y2="40" stroke="var(--c2)" stroke-width="3"/>
<circle cx="160" cy="40" r="8" fill="var(--c2)"/><text x="160" y="22" text-anchor="middle">{esc(frm)}</text>
<circle cx="400" cy="40" r="8" fill="var(--c2)"/><text x="400" y="22" text-anchor="middle">{esc(to)}</text>
<text x="10" y="124" font-weight="700" fill="var(--c1)">sync branch</text>
<path d="M400,48 C400,90 440,120 470,120" fill="none" stroke="var(--c1)" stroke-width="3"/>
<line x1="470" y1="120" x2="700" y2="120" stroke="var(--c1)" stroke-width="3"/>
<circle cx="560" cy="120" r="9" fill="var(--c1)"/><text x="560" y="100" text-anchor="middle">merge dev</text>
<circle cx="640" cy="120" r="7" fill="var(--c1)"/><text x="660" y="100" text-anchor="middle">regenerate</text>
<text x="10" y="204" font-weight="700" fill="var(--c3)">dev</text>
<line x1="110" y1="200" x2="800" y2="200" stroke="var(--c3)" stroke-width="3"/>
<circle cx="160" cy="200" r="8" fill="var(--c3)"/>
<line x1="160" y1="48" x2="160" y2="192" stroke="var(--c2)" stroke-width="2" stroke-dasharray="4 4"/>
<circle cx="500" cy="200" r="7" fill="var(--c3)"/>
<path d="M500,192 C520,160 540,140 553,128" fill="none" stroke="var(--c3)" stroke-width="2" marker-end="url(#ah)"/>
<path d="M700,120 C740,130 760,170 768,193" fill="none" stroke="var(--c1)" stroke-width="2" marker-end="url(#ah)"/>
<circle cx="770" cy="200" r="9" fill="var(--c3)"/><text x="805" y="226" text-anchor="end">PR merge commit</text>
<text x="585" y="146" text-anchor="middle" font-size="12" fill="var(--muted)">{esc(branch)}</text>
</g></svg>"""


def divergence(root: Path, state: dict, notes: dict) -> tuple:
    template_files = set(git("ls-tree", "-r", "--name-only", state["head_sha"], cwd=root).splitlines())
    rows = []
    for line in git("diff", "--numstat", state["head_sha"], "HEAD", cwd=root).splitlines():
        added, deleted, path = line.split("\t", 2)
        if path not in template_files or SKIP_DIVERGENCE.search(path) or not (root / path).exists():
            continue
        size = (int(added) if added.isdigit() else 0) + (int(deleted) if deleted.isdigit() else 0)
        kind = "owned" if TEMPLATE_OWNED.match(path) else ("content" if PIPELINE_CONTENT.match(path) else "other")
        rows.append({"path": path, "lines": size, "kind": kind, "note": notes.get(path, "")})
    rows.sort(key=lambda r: -r["lines"])
    return [r for r in rows if r["kind"] != "content"], [r for r in rows if r["kind"] == "content"]


def follow_ups(state: dict, decisions: dict, checks: list) -> list:
    items = [
        {
            "title": "Update all nf-core modules and subworkflows",
            "detail": "Do this in a separate PR. Delete the old `.conda-lock` files of a module before you update it.",
        }
    ]
    nft = next((c for c in checks if c["id"] == "nf_test"), None)
    if not nft or nft["status"] != "pass":
        items.append(
            {
                "title": "Run nf-test and regenerate the pipeline snapshots",
                "detail": "Regenerate snapshots on x86_64 (for example GitHub Codespaces), because CI runs on x86_64.",
            }
        )
    items += decisions.get("follow_ups", [])
    items.append(
        {"title": "Request reviews", "detail": "Merge the PR with a merge commit. Do not squash or rebase it."}
    )
    return items


def section(title: str, body: str) -> str:
    return f"<section><h2>{esc(title)}</h2>{body}</section>"


def decision_details(d: dict) -> str:
    label = CATEGORY_TEXT.get(d.get("category"), (d.get("category"), ""))[0]
    body = f"<p><b>Choice:</b> {esc(d.get('choice'))}</p><p><b>Reason:</b> {esc(d.get('reason'))}</p>"
    if d.get("sources"):
        body += "<p><b>Sources:</b></p><ul>" + "".join(f"<li>{link(s)}</li>" for s in d["sources"]) + "</ul>"
    if d.get("nextflow_docs"):
        body += "<p><b>Nextflow docs checked:</b></p><ul>" + "".join(f"<li>{link(s)}</li>" for s in d["nextflow_docs"])
        body += "</ul>"
    return f"<details><summary><code>{esc(d.get('file'))}</code>: {esc(label)}</summary>{body}</details>"


def build_html(root: Path, state: dict, decisions: dict, checks: list, authored: dict) -> str:
    entries = decisions.get("decisions", [])
    counts = dict.fromkeys(CATEGORY_TEXT, 0)
    counts["rule"] = len(state["auto_resolved"])
    for d in entries:
        counts[d.get("category", "")] = counts.get(d.get("category", ""), 0) + 1
    review = [d for d in entries if d.get("needs_review")]
    failed = [c for c in checks if c["status"] == "fail"]
    commits = git("log", "--format=%h %s", f"{state['head_sha']}..HEAD", "--first-parent", cwd=root).splitlines()

    parts = []
    facts = [
        (f"{state['from_version']} to {state['to_version']}", "Template versions"),
        (len(state["conflicts"]), "Files with conflicts"),
        (len(state["auto_resolved"]), "Files resolved by rule"),
        (len(review), "Decisions to review"),
        (len(failed), "Failed checks"),
    ]
    body = '<div class="facts">' + "".join(
        f'<div class="fact"><b>{esc(v)}</b><span>{esc(t)}</span></div>' for v, t in facts
    )
    body += "</div>"
    if failed:
        body += '<div class="callout">Some checks failed. Do not merge until a person examines the failed checks.</div>'
    override = state.get("merge_base_override")
    if override:
        body += (
            f'<div class="callout">The git history of <code>dev</code> only contains template '
            f"{esc(override['git_merge_base_version'])}, but <code>.nf-core.yml</code> says {esc(override['version'])}. "
            f"The merge used the TEMPLATE {esc(override['version'])} commit as its base. Examine the result with care.</div>"
        )
    body += f"<p>{esc(decisions.get('summary', ''))}</p>"
    body += (
        f'<p class="muted">Pull request: {link(state["pr"]["url"])}. Branch: <code>{esc(state["pr"]["headRefName"])}</code>.'
        f" Report date: {date.today().isoformat()}.</p>"
    )
    parts.append(section("Summary", body))

    body = (
        "<p>The bot puts the new template on the sync branch. This work merged <code>dev</code> into that branch.</p>"
    )
    body += branch_diagram(state)
    body += "<p>Commits on the sync branch after the template commit:</p><ul>"
    body += "".join(f"<li><code>{esc(c)}</code></li>" for c in commits) + "</ul>"
    parts.append(section("What was done", body))

    body = "<p>Each file with a conflict, and how it was resolved:</p>" + bar_chart(counts)
    parts.append(section("How the files were resolved", body))

    body = "<p>A person must examine these decisions. Open each item to see the reason and the sources.</p>"
    body += "".join(decision_details(d) for d in review) if review else "<p>None.</p>"
    parts.append(section(f"Decisions for human review ({len(review)})", body))

    rows = "".join(
        f"<tr><td><code>{esc(r['file'])}</code></td><td>{esc(r['action'])}</td><td>{esc(r['source'])}</td></tr>"
        for r in state["auto_resolved"]
    )
    body = (
        '<div class="table-wrap"><table><tr><th>File</th><th>Action</th><th>Source</th></tr>' + rows + "</table></div>"
    )
    body += "<h3>All decisions</h3>" + "".join(decision_details(d) for d in entries)
    parts.append(section("All resolutions", body))

    body = ""
    for sec in state.get("changelog", []):
        items = [esc(re.sub(r"^\s*-\s*", "", line)) for line in sec["template"].splitlines() if line.strip()]
        body += f"<details><summary>nf-core/tools {esc(sec['version'])}</summary><ul>"
        body += "".join(f"<li>{i}</li>" for i in items) + "</ul></details>"
    posts = state.get("blog_posts", [])
    if posts:
        body += "<p>Blog posts: " + ", ".join(link({"title": p["version"], "url": p["url"]}) for p in posts) + "</p>"
    parts.append(section("Template changes in this update", body or "<p>No changelog found.</p>"))

    if authored:
        body = "<p>These lines are not in the template and not in <code>dev</code>. The agent wrote them.</p>"
        for f, lines in authored.items():
            body += f"<details><summary><code>{esc(f)}</code> ({len(lines)} lines)</summary><pre>"
            body += html.escape("\n".join(lines)) + "</pre></details>"
        parts.append(section("Lines written by the agent", body))

    rows = ""
    for c in checks:
        details = "<br>".join(esc(d) for d in c["details"][:30])
        rows += f'<tr><td>{esc(c["title"])}</td><td><span class="pill {c["status"]}">{c["status"]}</span></td>'
        rows += f"<td>{details}</td></tr>"
    body = (
        '<div class="table-wrap"><table><tr><th>Check</th><th>Result</th><th>Details</th></tr>'
        + rows
        + "</table></div>"
        if checks
        else "<p>The checks did not run.</p>"
    )
    parts.append(section("Checks", body))

    other, content = divergence(root, state, decisions.get("divergence_notes", {}))
    body = (
        "<p>These template files are different from the template. Each difference can cause a conflict in a "
        "future sync. If the pipeline does not use a template feature, turn it off with "
        "<code>template.skip_features</code> in <code>.nf-core.yml</code>.</p>"
    )
    rows = "".join(
        f"<tr><td><code>{esc(r['path'])}</code></td><td>{r['lines']}</td><td>"
        f"{'Lint expects this file to be identical to the template. ' if r['kind'] == 'owned' else ''}{esc(r['note'])}"
        f"</td></tr>"
        for r in other[:20]
    )
    body += (
        '<div class="table-wrap"><table><tr><th>File</th><th>Lines different</th><th>Notes</th></tr>'
        + (rows or '<tr><td colspan="3">None.</td></tr>')
        + "</table></div>"
    )
    body += f"<details><summary>Files with pipeline content (differences are expected, {len(content)})</summary><ul>"
    body += "".join(f"<li><code>{esc(r['path'])}</code>: {r['lines']} lines</li>" for r in content) + "</ul></details>"
    parts.append(section("Where the pipeline is different from the template", body))

    body = "<ul>" + "".join(
        f"<li><b>{esc(f['title'])}</b>: {esc(f.get('detail', ''))}</li>" for f in follow_ups(state, decisions, checks)
    )
    parts.append(section("Follow-up actions", body + "</ul>"))
    return "".join(parts)


def build_comment(state: dict, decisions: dict, checks: list) -> str:
    to = state["to_version"]
    lines = [f"## Template merge for nf-core/tools v{to}", "", decisions.get("summary", ""), ""]
    pr_summary = decisions.get("pr_summary", {})
    for key, title in (
        ("kept", "Kept from dev"),
        ("adopted", "Adopted from the template"),
        ("cleanups", "Cleanups"),
        ("behaviour_changes", "Behaviour changes"),
    ):
        if pr_summary.get(key):
            lines += [f"### {title}", ""] + [f"- {item}" for item in pr_summary[key]] + [""]
    review = [d for d in decisions.get("decisions", []) if d.get("needs_review")]
    if review:
        lines += [f"<details><summary>Decisions for review ({len(review)})</summary>", ""]
        for d in review:
            lines.append(f"- `{d['file']}`: {d['choice']} Reason: {d['reason']}")
        lines += ["", "</details>", ""]
    if checks:
        icon = {"pass": "✅", "fail": "❌", "warn": "⚠️", "info": "ℹ️", "skip": "⏭️"}
        lines += ["### Checks", "", "| Check | Result |", "| --- | --- |"]
        lines += [f"| {c['title']} | {icon.get(c['status'], '')} {c['status']} |" for c in checks]
        lines.append("")
    lines += [
        "> [!IMPORTANT]",
        "> Merge this PR with a **merge commit**. Do not squash or rebase it: the template commit must stay in the "
        "history of `dev`, or the next template sync will show the same conflicts again.",
        "",
        "The full report is attached as an HTML file.",
    ]
    if decisions.get("disclosure"):
        lines += ["", decisions["disclosure"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", help="Output directory (default: a new temporary directory)")
    args = parser.parse_args()
    root = repo_root()
    state = load_state(root)
    sdir = state_dir(root)
    decisions = load_json(sdir / "decisions.json", {})
    checks = load_json(sdir / "checks.json", [])
    authored = load_json(sdir / "authored_lines.json", {})
    if not decisions:
        raise StopError("decisions.json is missing. Write it first (see references/report-style.md).")
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="nf-core-template-sync-"))
    out.mkdir(parents=True, exist_ok=True)

    title = f"Template sync report: nf-core/{state['pipeline']} {state['to_version']}"
    subtitle = (
        f"Merge of the nf-core/tools {state['to_version']} template into the pipeline (from {state['from_version']})."
    )
    template = (SKILL_DIR / "assets" / "report-template.html").read_text()
    page = (
        template.replace("{{TITLE}}", html.escape(title))
        .replace("{{SUBTITLE}}", esc(subtitle))
        .replace("{{BODY}}", build_html(root, state, decisions, checks, authored))
    )
    report = out / f"template-sync-{state['pipeline']}-{state['to_version']}.html"
    report.write_text(page)
    comment = out / "pr-comment.md"
    comment.write_text(build_comment(state, decisions, checks))
    print(f"Report: {report}\nPR comment: {comment}")


if __name__ == "__main__":
    main_wrapper(main)
