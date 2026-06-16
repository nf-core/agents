"""Claude Code provider adapter for hook phase reports."""
from __future__ import annotations

import json
from typing import Any

from agent_hooks.phases import PhaseReport
from agent_hooks.providers.generic import ProviderResponse


def parse_event(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Claude hook event must be a JSON object")
    return data


def render_stop(report: PhaseReport, event: dict[str, Any] | None = None) -> ProviderResponse:
    """Render a Claude Stop response.

    Claude consumes structured JSON on stdout. Blocking is expressed with a
    decision, so this adapter exits 0 even when the internal phase failed.
    """
    event = event or {}
    if event.get("stop_hook_active"):
        payload = {
            "decision": "approve",
            "reason": "nf-core stop hook is already active; avoiding a recursive stop block.",
        }
    elif report.exit_code:
        payload = {"decision": "block", "reason": report.format()}
    else:
        payload = {"decision": "approve", "reason": report.format()}
    return ProviderResponse(stdout=json.dumps(payload, separators=(",", ":")), exit_code=0)
