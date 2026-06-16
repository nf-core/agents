from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "prek-hooks"
sys.path.insert(0, str(ROOT / "scripts" / "prek-hooks"))
sys.path.insert(0, str(ROOT / "scripts"))


class NfCoreHarnessScriptTests(unittest.TestCase):
    def make_pipeline(self, tmp: Path) -> dict[str, Path]:
        root = tmp / "pipeline"
        module = root / "modules" / "local" / "foo" / "main.nf"
        subworkflow = root / "subworkflows" / "local" / "bar" / "main.nf"
        for path in (module, subworkflow):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("// test\n")
        (root / "nextflow.config").write_text("params.foo = 'bar'\n")
        (root / "nextflow_schema.json").write_text("{}\n")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "nextflow.config", "nextflow_schema.json"], cwd=root, check=True)
        subprocess.run(
            ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-q", "-m", "init"],
            cwd=root,
            check=True,
        )
        return {"root": root, "module": module, "subworkflow": subworkflow}

    def run_hook(self, script: str, *files: Path, fake_log: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if fake_log is not None:
            env["NF_CORE_HARNESS_FAKE_LOG"] = str(fake_log)
        return subprocess.run(
            [str(SCRIPTS / script), *(str(file) for file in files)],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_generic_provider_uses_exit_code_for_blocking_failure(self) -> None:
        from agent_hooks.phases import CheckResult, PhaseReport
        from agent_hooks.providers.generic import render

        response = render(
            PhaseReport(
                phase="stop",
                blocking=True,
                results=(CheckResult("nf-core pipelines lint", 1),),
            )
        )
        self.assertEqual(response.exit_code, 1)
        self.assertEqual(response.stdout, "")
        self.assertIn("FAIL: nf-core pipelines lint", response.stderr)


    def test_cursor_provider_uses_exit_code_for_blocking_failure(self) -> None:
        from agent_hooks.phases import CheckResult, PhaseReport
        from agent_hooks.providers.cursor import render_phase

        response = render_phase(
            PhaseReport(
                phase="stop",
                blocking=True,
                results=(CheckResult("nf-core pipelines lint", 1),),
            )
        )
        self.assertEqual(response.exit_code, 1)
        self.assertEqual(response.stdout, "")
        self.assertIn("FAIL: nf-core pipelines lint", response.stderr)

    def test_codex_provider_blocks_with_json_reason_but_zero_exit(self) -> None:
        from agent_hooks.phases import CheckResult, PhaseReport
        from agent_hooks.providers.codex import render_stop

        response = render_stop(
            PhaseReport(
                phase="stop",
                blocking=True,
                results=(CheckResult("nf-core pipelines lint", 1),),
            ),
            {"hook_event_name": "Stop", "stop_hook_active": False},
        )
        payload = json.loads(response.stdout)
        self.assertEqual(response.exit_code, 0)
        self.assertEqual(payload["decision"], "block")
        self.assertIn("FAIL: nf-core pipelines lint", payload["reason"])

    def test_claude_provider_blocks_with_json_reason_but_zero_exit(self) -> None:
        from agent_hooks.phases import CheckResult, PhaseReport
        from agent_hooks.providers.claude import render_stop

        response = render_stop(
            PhaseReport(
                phase="stop",
                blocking=True,
                results=(CheckResult("nf-core pipelines lint", 1),),
            ),
            {"hook_event_name": "Stop", "stop_hook_active": False},
        )
        payload = json.loads(response.stdout)
        self.assertEqual(response.exit_code, 0)
        self.assertEqual(payload["decision"], "block")
        self.assertIn("FAIL: nf-core pipelines lint", payload["reason"])

    def test_claude_provider_avoids_recursive_stop_blocks(self) -> None:
        from agent_hooks.phases import CheckResult, PhaseReport
        from agent_hooks.providers.claude import render_stop

        response = render_stop(
            PhaseReport(
                phase="stop",
                blocking=True,
                results=(CheckResult("nf-core pipelines lint", 1),),
            ),
            {"hook_event_name": "Stop", "stop_hook_active": True},
        )
        payload = json.loads(response.stdout)
        self.assertEqual(response.exit_code, 0)
        self.assertEqual(payload["decision"], "approve")
        self.assertIn("already active", payload["reason"])

    def test_phase_report_exit_code_and_feedback_for_blocking_failure(self) -> None:
        from agent_hooks.phases import CheckResult, PhaseReport

        report = PhaseReport(
            phase="stop",
            blocking=True,
            results=(CheckResult("nf-core component lint", 0), CheckResult("nf-core pipelines lint", 1)),
        )
        self.assertEqual(report.exit_code, 1)
        self.assertIn("FAIL: nf-core pipelines lint", report.format())
        self.assertIn("continue fixing before stopping", report.format())

    def test_pipelines_lint_script_dispatches_once_per_root(self) -> None:
        with TemporaryDirectory() as raw:
            fixture = self.make_pipeline(Path(raw))
            log = Path(raw) / "nf-core.log"
            result = self.run_hook("nf-core-pipelines-lint.py", fixture["module"], fixture["subworkflow"], fake_log=log)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(log.read_text().splitlines(), [f"pipelines lint --dir {fixture['root'].resolve()}"])

    def test_component_lint_script_routes_local_modules_and_subworkflows(self) -> None:
        with TemporaryDirectory() as raw:
            fixture = self.make_pipeline(Path(raw))
            log = Path(raw) / "nf-core.log"
            result = self.run_hook("nf-core-component-lint.py", fixture["module"], fixture["subworkflow"], fake_log=log)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(
                log.read_text().splitlines(),
                [
                    f"modules lint --local foo --dir {fixture['root'].resolve()}",
                    f"subworkflows lint --local bar --dir {fixture['root'].resolve()}",
                ],
            )

    def test_schema_check_script_runs_schema_lint_and_build(self) -> None:
        with TemporaryDirectory() as raw:
            fixture = self.make_pipeline(Path(raw))
            log = Path(raw) / "nf-core.log"
            result = self.run_hook("nf-core-schema-check.py", fixture["root"] / "nextflow_schema.json", fake_log=log)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(
                log.read_text().splitlines(),
                [
                    f"pipelines schema lint --dir {fixture['root'].resolve()}",
                    f"schema build --dir {fixture['root'].resolve()}",
                ],
            )

    def test_no_pipeline_root_is_noop_success(self) -> None:
        with TemporaryDirectory() as raw:
            lone_file = Path(raw) / "README.md"
            lone_file.write_text("# test\n")
            result = self.run_hook("nf-core-pipelines-lint.py", lone_file)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)



    def test_after_file_edit_phase_runs_targeted_fast_checks(self) -> None:
        with TemporaryDirectory() as raw:
            fixture = self.make_pipeline(Path(raw))
            log = Path(raw) / "nf-core.log"
            env = os.environ.copy()
            env["NF_CORE_HARNESS_FAKE_LOG"] = str(log)
            result = subprocess.run(
                [
                    str(ROOT / "scripts" / "agent_hooks" / "run_phase.py"),
                    "after-file-edit",
                    str(fixture["module"]),
                    str(fixture["root"] / "nextflow_schema.json"),
                    "--provider",
                    "cursor",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("checks passed", result.stdout)
            self.assertEqual(
                log.read_text().splitlines(),
                [
                    f"modules lint --local foo --dir {fixture['root'].resolve()}",
                    f"pipelines schema lint --dir {fixture['root'].resolve()}",
                    f"schema build --dir {fixture['root'].resolve()}",
                ],
            )

    def test_run_phase_cursor_provider_uses_exit_code_contract(self) -> None:
        with TemporaryDirectory() as raw:
            fixture = self.make_pipeline(Path(raw))
            log = Path(raw) / "nf-core.log"
            env = os.environ.copy()
            env["NF_CORE_HARNESS_FAKE_LOG"] = str(log)
            result = subprocess.run(
                [
                    str(ROOT / "scripts" / "agent_hooks" / "run_phase.py"),
                    "stop",
                    str(fixture["module"]),
                    "--provider",
                    "cursor",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("checks passed", result.stdout)

    def test_run_phase_claude_provider_reads_stdin_and_returns_json(self) -> None:
        with TemporaryDirectory() as raw:
            fixture = self.make_pipeline(Path(raw))
            log = Path(raw) / "nf-core.log"
            env = os.environ.copy()
            env["NF_CORE_HARNESS_FAKE_LOG"] = str(log)
            result = subprocess.run(
                [
                    str(ROOT / "scripts" / "agent_hooks" / "run_phase.py"),
                    "stop",
                    str(fixture["module"]),
                    "--provider",
                    "claude",
                ],
                cwd=ROOT,
                env=env,
                input=json.dumps({"hook_event_name": "Stop", "stop_hook_active": False}),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"], "approve")
            self.assertIn("checks passed", payload["reason"])


if __name__ == "__main__":
    unittest.main()
