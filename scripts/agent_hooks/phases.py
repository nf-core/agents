"""Agent hook phase policy for nf-core validation harnesses."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from nf_core_harness import component_lint, pipelines_lint, schema_check

CheckRunner = Callable[[Sequence[Path]], int]


@dataclass(frozen=True)
class CheckSpec:
    name: str
    runner: CheckRunner


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: int

    @property
    def passed(self) -> bool:
        return self.status == 0


@dataclass(frozen=True)
class PhaseSpec:
    name: str
    checks: tuple[CheckSpec, ...]
    blocking: bool = True


@dataclass(frozen=True)
class PhaseReport:
    phase: str
    blocking: bool
    results: tuple[CheckResult, ...]

    @property
    def exit_code(self) -> int:
        if not self.blocking:
            return 0
        return 1 if any(not result.passed for result in self.results) else 0

    @property
    def passed(self) -> bool:
        return self.exit_code == 0

    def format(self) -> str:
        if not self.results:
            return f"nf-core {self.phase} hook: no matching checks to run"
        lines = [f"nf-core {self.phase} hook: check results"]
        for result in self.results:
            mark = "PASS" if result.passed else "FAIL"
            lines.append(f"- {mark}: {result.name}")
        if self.exit_code:
            lines.append(f"nf-core {self.phase} hook: checks failed; continue fixing before stopping")
        else:
            lines.append(f"nf-core {self.phase} hook: checks passed")
        return "\n".join(lines)


PHASES: dict[str, PhaseSpec] = {
    "after-file-edit": PhaseSpec(
        name="after-file-edit",
        checks=(
            CheckSpec("nf-core component lint", component_lint),
            CheckSpec("nf-core schema check", schema_check),
        ),
        blocking=True,
    ),
    "stop": PhaseSpec(
        name="stop",
        checks=(
            CheckSpec("nf-core component lint", component_lint),
            CheckSpec("nf-core schema check", schema_check),
            CheckSpec("nf-core pipelines lint", pipelines_lint),
        ),
        blocking=True,
    ),
}


def run_phase(phase: str, files: Sequence[Path]) -> PhaseReport:
    spec = PHASES[phase]
    results: list[CheckResult] = []
    for check in spec.checks:
        results.append(CheckResult(check.name, check.runner(files)))
    return PhaseReport(spec.name, spec.blocking, tuple(results))
