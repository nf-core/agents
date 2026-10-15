"""Shared helpers for the nf-core-template-sync scripts. Python 3.9+, standard library only."""

from __future__ import annotations

import http.client
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
MODULES_REPO = "https://github.com/nf-core/modules.git"
BOT_LOGIN = "nf-core-bot"
BOT_EMAIL = "core@nf-co.re"
BOT_SUBJECT = re.compile(r"^Template update for nf-core/tools version (\S+)$")
PR_TITLE = re.compile(r"Template update for nf-core/tools v(\S+)")


class StopError(Exception):
    """Stop the script with a message. Exit code 2 = hard stop, 3 = needs the user to decide."""

    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code


def run(
    cmd: list, cwd: Path | None = None, check: bool = True, timeout: int | None = None
) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout
    )
    if check and proc.returncode != 0:
        raise StopError(
            f"Command failed ({proc.returncode}): {' '.join(map(str, cmd))}\n{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc


def git(*args: str, cwd: Path | None = None, check: bool = True) -> str:
    return run(["git", *args], cwd=cwd, check=check).stdout.strip()


def repo_root() -> Path:
    try:
        return Path(git("rev-parse", "--show-toplevel"))
    except StopError:
        raise StopError("Run this script from inside the pipeline repository.") from None


def state_dir(root: Path) -> Path:
    path = Path(git("rev-parse", "--absolute-git-dir", cwd=root)) / "nf-core-template-sync"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def load_state(root: Path) -> dict:
    state = load_json(state_dir(root) / "state.json")
    if not state:
        raise StopError("No state found. Run prepare.py first.")
    return state


def version_tuple(version: str) -> tuple:
    parts = [int(p) for p in re.findall(r"\d+", version)[:3]]
    return tuple(parts + [0] * (3 - len(parts)))


def fetch_url(url: str, timeout: int = 30) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (OSError, ValueError, http.client.HTTPException):
        return None


def gh_json(*args: str, check: bool = True) -> Any:
    proc = run(["gh", *args], check=check)
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return json.loads(proc.stdout)


def file_at(ref: str, path: str, cwd: Path) -> str | None:
    proc = run(["git", "show", f"{ref}:{path}"], cwd=cwd, check=False)
    return proc.stdout if proc.returncode == 0 else None


def path_exists_at(ref: str, path: str, cwd: Path) -> bool:
    return bool(git("ls-tree", ref, "--", path, cwd=cwd, check=False))


def template_components(ref: str, cwd: Path) -> list:
    """nf-core modules and subworkflows listed in modules.json at `ref`."""
    text = file_at(ref, "modules.json", cwd)
    if not text:
        return []
    repo = json.loads(text).get("repos", {}).get(MODULES_REPO, {})
    out = []
    for kind in ("modules", "subworkflows"):
        for name, info in sorted(repo.get(kind, {}).get("nf-core", {}).items()):
            out.append({"kind": kind, "name": name, "path": f"{kind}/nf-core/{name}", "sha": info.get("git_sha")})
    return out


def nf_core_cmd(state: dict) -> list:
    return state["tools"]["nf_core_cmd"]


def main_wrapper(func) -> None:
    try:
        func()
    except StopError as err:
        print(f"\nSTOP: {err}", file=sys.stderr)
        sys.exit(err.code)
