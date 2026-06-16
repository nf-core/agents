#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
raise SystemExit(subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests" / "prek-hooks")]).returncode)
