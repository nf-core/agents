#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["nf-core==4.0.2"]
# ///
"""Thin nf-core/tools harness hooks for prek and agent integrations."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path


def collect_files(args: Sequence[str], cwd: Path | None = None) -> list[Path]:
    """Return explicit files, or changed git files when none are supplied."""
    cwd = cwd or Path.cwd()
    if args:
        return [Path(arg) for arg in args if arg]

    files: set[str] = set()
    for cmd in (("git", "diff", "--name-only", "--cached"), ("git", "diff", "--name-only")):
        result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
        if result.returncode == 0:
            files.update(line for line in result.stdout.splitlines() if line)
    return [Path(file) for file in sorted(files)]


def existing_files(files: Iterable[Path]) -> list[Path]:
    return [file for file in files if file.exists()]


def pipeline_root_for(path: Path) -> Path | None:
    """Find the nearest ancestor containing nextflow.config."""
    path = path.resolve()
    current = path if path.is_dir() else path.parent
    while True:
        if (current / "nextflow.config").is_file():
            return current
        if current.parent == current:
            return None
        current = current.parent


def roots_from_files(files: Iterable[Path]) -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()
    for file in existing_files(files):
        root = pipeline_root_for(file)
        if root and root not in seen:
            roots.append(root)
            seen.add(root)
    return roots


def component_jobs(files: Iterable[Path]) -> list[tuple[str, str, Path]]:
    """Return (kind, name, root) jobs for local modules/subworkflows."""
    jobs: list[tuple[str, str, Path]] = []
    seen: set[tuple[str, str, Path]] = set()
    for file in existing_files(files):
        root = pipeline_root_for(file)
        if not root:
            continue
        try:
            parts = file.resolve().relative_to(root).parts
        except ValueError:
            continue
        if len(parts) < 3:
            continue
        parent, scope, name = parts[:3]
        if scope != "local" or parent not in {"modules", "subworkflows"}:
            continue
        kind = "module" if parent == "modules" else "subworkflow"
        key = (kind, name, root)
        if key not in seen:
            jobs.append(key)
            seen.add(key)
    return jobs



def fake_nf_core_call(*parts: object) -> bool:
    """Test seam: log intended nf-core API calls when NF_CORE_HARNESS_FAKE_LOG is set."""
    log_path = os.environ.get("NF_CORE_HARNESS_FAKE_LOG")
    if not log_path:
        return False
    with Path(log_path).open("a") as handle:
        handle.write(" ".join(str(part) for part in parts) + "\n")
    return True


def run_pipeline_lint(root: Path) -> int:
    """Run nf-core pipeline lint via the nf-core Python API."""
    from nf_core.pipelines.lint import run_linting
    from nf_core.utils import is_pipeline_directory

    print(f"nf-core pipelines lint --dir {root}")
    if fake_nf_core_call("pipelines", "lint", "--dir", root):
        return 0
    try:
        is_pipeline_directory(str(root))
        lint_obj, module_lint_obj, subworkflow_lint_obj = run_linting(str(root), hide_progress=True)
    except (AssertionError, LookupError, UserWarning) as exc:
        print(f"ERROR: nf-core pipelines lint failed for {root}: {exc}", file=sys.stderr)
        return 1

    failures = len(lint_obj.failed)
    if module_lint_obj is not None:
        failures += len(module_lint_obj.failed)
    if subworkflow_lint_obj is not None:
        failures += len(subworkflow_lint_obj.failed)
    return 1 if failures else 0


def run_module_lint(name: str, root: Path) -> int:
    """Run nf-core module lint via the nf-core Python API."""
    from nf_core.components.lint import LintExceptionError
    from nf_core.modules.lint import ModuleLint

    print(f"nf-core modules lint --local {name} --dir {root}")
    if fake_nf_core_call("modules", "lint", "--local", name, "--dir", root):
        return 0
    try:
        module_lint = ModuleLint(str(root), hide_progress=True)
        module_lint.lint(module=name, local=True, print_results=True)
    except (LintExceptionError, LookupError, UserWarning) as exc:
        print(f"ERROR: nf-core modules lint failed for {name}: {exc}", file=sys.stderr)
        return 1
    return 1 if module_lint.failed else 0


def run_subworkflow_lint(name: str, root: Path) -> int:
    """Run nf-core subworkflow lint via the nf-core Python API."""
    from nf_core.components.lint import LintExceptionError
    from nf_core.subworkflows import SubworkflowLint

    print(f"nf-core subworkflows lint --local {name} --dir {root}")
    if fake_nf_core_call("subworkflows", "lint", "--local", name, "--dir", root):
        return 0
    try:
        subworkflow_lint = SubworkflowLint(str(root), hide_progress=True)
        subworkflow_lint.lint(subworkflow=name, local=True, print_results=True)
    except (LintExceptionError, LookupError, UserWarning) as exc:
        print(f"ERROR: nf-core subworkflows lint failed for {name}: {exc}", file=sys.stderr)
        return 1
    return 1 if subworkflow_lint.failed else 0


def run_schema_lint_and_build(root: Path) -> int:
    """Run nf-core schema lint/build via the nf-core Python API."""
    from nf_core.pipelines.schema import PipelineSchema

    status = 0
    print(f"nf-core pipelines schema lint --dir {root}")
    if fake_nf_core_call("pipelines", "schema", "lint", "--dir", root):
        fake_nf_core_call("schema", "build", "--dir", root)
        return 0
    schema_obj = PipelineSchema()
    try:
        schema_obj.get_schema_path(str(root / "nextflow_schema.json"))
        schema_obj.load_lint_schema()
        try:
            schema_obj.validate_schema_title_description()
        except AssertionError as exc:
            print(f"WARNING: {exc}", file=sys.stderr)
    except AssertionError as exc:
        print(f"ERROR: nf-core pipelines schema lint failed for {root}: {exc}", file=sys.stderr)
        status = 1

    print(f"nf-core schema build --dir {root}")
    build_obj = PipelineSchema()
    try:
        if build_obj.build_schema(str(root), no_prompts=True, web_only=False, url=None) is False:
            status = 1
    except (AssertionError, UserWarning) as exc:
        print(f"ERROR: nf-core schema build failed for {root}: {exc}", file=sys.stderr)
        status = 1
    return status


def git_schema_changed(root: Path) -> bool:
    result = subprocess.run(
        ("git", "-C", str(root), "diff", "--quiet", "--", "nextflow_schema.json"),
        check=False,
    )
    return result.returncode != 0


def pipelines_lint(files: Sequence[Path]) -> int:
    roots = roots_from_files(files)
    if not roots:
        return 0
    status = 0
    for root in roots:
        status = run_pipeline_lint(root) or status
    return status


def component_lint(files: Sequence[Path]) -> int:
    jobs = component_jobs(files)
    if not jobs:
        return 0
    status = 0
    for kind, name, root in jobs:
        if kind == "module":
            status = run_module_lint(name, root) or status
        else:
            status = run_subworkflow_lint(name, root) or status
    return status


def schema_check(files: Sequence[Path]) -> int:
    roots = [root for root in roots_from_files(files) if (root / "nextflow_schema.json").is_file()]
    if not roots:
        return 0
    status = 0
    for root in roots:
        status = run_schema_lint_and_build(root) or status
        if git_schema_changed(root):
            print(f"ERROR: nf-core schema build changed {root / 'nextflow_schema.json'}", file=sys.stderr)
            print(f"Run nf-core schema build --dir {root} and commit the result.", file=sys.stderr)
            status = 1
    return status


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hook", choices=("pipelines-lint", "component-lint", "schema-check"))
    parser.add_argument("files", nargs="*")
    args = parser.parse_args(argv)
    files = collect_files(args.files)
    if args.hook == "pipelines-lint":
        return pipelines_lint(files)
    if args.hook == "component-lint":
        return component_lint(files)
    return schema_check(files)


if __name__ == "__main__":
    raise SystemExit(main())
