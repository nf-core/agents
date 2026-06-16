"""Cursor provider adapter for hook phase reports."""
from __future__ import annotations

from agent_hooks.phases import PhaseReport
from agent_hooks.providers.generic import ProviderResponse, render


def render_phase(report: PhaseReport) -> ProviderResponse:
    """Render a Cursor hook response.

    Cursor hook documentation defines event names and command/matcher wiring, but
    not a structured decision JSON contract. Use exit-code semantics for now.
    """
    return render(report)
