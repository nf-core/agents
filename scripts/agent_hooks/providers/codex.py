"""Codex provider adapter for hook phase reports."""
from __future__ import annotations

from typing import Any

from agent_hooks.phases import PhaseReport
from agent_hooks.providers.claude import parse_event
from agent_hooks.providers.generic import ProviderResponse
import json


def render_stop(report: PhaseReport, event: dict[str, Any] | None = None) -> ProviderResponse:
    """Render a Codex Stop response as clean JSON stdout.

    Codex also supports exit-code-2 blocking, but JSON keeps behavior aligned
    with Claude while preserving a separate adapter seam for future Codex-only
    events.
    """
    event = event or {}
    if event.get("stop_hook_active"):
        payload = {
            "decision": None,
            "reason": "nf-core stop hook is already active; avoiding a recursive stop block.",
        }
    elif report.exit_code:
        payload = {"decision": "block", "reason": report.format()}
    else:
        payload = {"decision": None, "reason": report.format()}
    return ProviderResponse(stdout=json.dumps(payload, separators=(",", ":")), exit_code=0)
