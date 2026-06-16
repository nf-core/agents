#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["skills-ref @ git+https://github.com/agentskills/agentskills.git#subdirectory=skills-ref"]
# ///
"""Validate each SKILL.md path individually with skills-ref."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    paths = [Path(arg) for arg in (argv if argv is not None else sys.argv[1:])]
    status = 0
    for path in paths:
        result = subprocess.run(["skills-ref", "validate", str(path)], check=False)
        status = result.returncode or status
    return status


if __name__ == "__main__":
    raise SystemExit(main())
