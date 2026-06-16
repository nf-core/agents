#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["nf-core==4.0.2"]
# ///
"""Run an agent hook phase."""
from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "prek-hooks"))
sys.path.insert(0, str(ROOT / "scripts"))

from agent_hooks.phases import PHASES, run_phase  # noqa: E402
from agent_hooks.providers.claude import parse_event, render_stop as render_claude_stop  # noqa: E402
from agent_hooks.providers.codex import render_stop as render_codex_stop  # noqa: E402
from agent_hooks.providers.cursor import render_phase as render_cursor  # noqa: E402
from agent_hooks.providers.generic import render as render_generic  # noqa: E402
from nf_core_harness import collect_files  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=sorted(PHASES))
    parser.add_argument("files", nargs="*")
    parser.add_argument("--provider", choices=("generic", "claude", "codex", "cursor"), default="generic")
    args = parser.parse_args(argv)

    files = collect_files(args.files, cwd=ROOT)
    if args.provider in {"claude", "codex"}:
        with contextlib.redirect_stdout(sys.stderr):
            report = run_phase(args.phase, files)
    else:
        report = run_phase(args.phase, files)
    if args.provider in {"claude", "codex"}:
        event = parse_event(sys.stdin.read())
        if args.phase != "stop":
            parser.error(f"{args.provider} provider currently supports only the stop phase")
        response = render_claude_stop(report, event) if args.provider == "claude" else render_codex_stop(report, event)
    elif args.provider == "cursor":
        response = render_cursor(report)
    else:
        response = render_generic(report)

    if response.stdout:
        print(response.stdout)
    if response.stderr:
        print(response.stderr, file=sys.stderr)
    return response.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
