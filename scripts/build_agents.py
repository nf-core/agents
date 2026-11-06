#!/usr/bin/env python3
"""Generate resources/{pipeline,plugin}/AGENTS.md from AGENTS.template.md and resources/AGENTS.md."""

import re
import sys
from pathlib import Path

RESOURCES = Path(__file__).resolve().parent.parent / "resources"

chunks = re.split(r"^(?=## )", (RESOURCES / "AGENTS.md").read_text(), flags=re.M)[1:]
sections = {chunk.splitlines()[0][3:]: chunk.strip() for chunk in chunks}

for project in ("pipeline", "plugin"):
    template = (RESOURCES / project / "AGENTS.template.md").read_text()
    missing = sections.keys() - re.findall(r"<!-- shared: (.+?) -->", template)
    if missing:
        sys.exit(f"resources/{project}/AGENTS.template.md lacks shared sections: {sorted(missing)}")
    output = re.sub(r"<!-- shared: (.+?) -->", lambda match: sections[match[1]], template)
    (RESOURCES / project / "AGENTS.md").write_text(output)
