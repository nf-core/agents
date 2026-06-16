"""Generic provider adapter: human output plus blocking exit code."""
from __future__ import annotations

from dataclasses import dataclass

from agent_hooks.phases import PhaseReport


@dataclass(frozen=True)
class ProviderResponse:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0


def render(report: PhaseReport) -> ProviderResponse:
    output = report.format()
    if report.exit_code:
        return ProviderResponse(stderr=output, exit_code=report.exit_code)
    return ProviderResponse(stdout=output, exit_code=0)
