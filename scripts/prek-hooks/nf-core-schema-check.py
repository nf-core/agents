#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["nf-core==4.0.2"]
# ///
from nf_core_harness import main
raise SystemExit(main(["schema-check", *(__import__('sys').argv[1:])]))
