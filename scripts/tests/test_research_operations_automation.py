"""SYNTHETIC SOFTWARE TESTS ONLY; no participants, contact, consent or approvals."""

import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "research" / "operations" / "run_synthetic.py"
spec = importlib.util.spec_from_file_location("synthetic_operations_runner", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

PAIRED_NATIVE_FIXTURE = r'''
import sys
import unittest

prefix, outcome = sys.argv[1:]

class SyntheticCase(unittest.TestCase):
    def test_control(self):
        self.assertTrue(True)

    def test_case(self):
        if prefix != "clean":
            sys.stderr.write("synthetic diagnostic\nok\n" if prefix == "diagnostic_then_ok" else "ok\n")
            sys.stderr.flush()
        if outcome == "skip":
            self.skipTest("SYNTHETIC capability skip")
        if outcome == "expected_failure":
            self.fail("SYNTHETIC expected failure")

SyntheticCase.__module__ = "test_research_operations"
if outcome == "expected_failure":
    SyntheticCase.test_case = unittest.expectedFailure(SyntheticCase.test_case)
suite = unittest.defaultTestLoader.loadTestsFromTestCase(SyntheticCase)
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
'''
PAIRED_IDS = {
    "test_research_operations.SyntheticCase.test_case",
    "test_research_operations.SyntheticCase.test_control",
}


class SyntheticOperationsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="pennilogic-synthetic-operations-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.output = self.directory / "assessment"
        self.sources = runner.snapshot()
        self.expected = runner.expected_tests(self.sources[runner.TEST_PATH])

    def native_output(self):
        lines = [f"{name.rsplit('.', 1)[-1]} ({name}) ... ok" for name in sorted(self.expected)]
        return ("\n".join(lines) + "\n\n" + "-" * 70 + f"\nRan {len(lines)} tests in 0.001s\n\nOK\n").encode("ascii")

    def successful_commands(self):
        return [
            subprocess.CompletedProcess([], 0, b"Research preparation source valid.\n", b""),
            subprocess.CompletedProcess([], 0, b"", self.native_output()),
        ]

    def invoke(self, arguments=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = runner.main(arguments if arguments is not None else ["--output", str(self.output)])
        return code, stdout.getvalue(), stderr.getvalue()

    def assessment(self):
        return json.loads((self.output / "assessment.json").read_text(encoding="utf-8"))

    def assert_no_research_claim(self, data):
        self.assertEqual(data["kind"], "automated_synthetic_operations_assessment")
        self.assertEqual(data["scope"], "source_preparation_and_synthetic_software_checks_only")
        self.assertFalse(data["contact_allowed"])
        self.assertEqual(data["qualified_approvals"], [])
        self.assertEqual(data["role_assignments"], [])
        self.assertEqual(data["original_docs65_acceptance"], "not_decided_by_this_run")
        self.assertEqual(data["later_study"]["execution_state"], "UNRUN")
        self.assertIsNone(data["later_study"]["participant_count"])
        self.assertEqual(data["later_study"]["findings"], [])
        self.assertEqual(data["later_study"]["decision"], "pending")
        self.assertEqual(data["later_study"]["conditions_cleared_by_this_run"], [])

    def test_real_synthetic_end_to_end_uses_existing_checker_and_native_research_suite(self):
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(SCRIPT), "--output", str(self.output)],
            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, timeout=240,
        )
        data = self.assessment()
        self.assertEqual(result.returncode, 0, (data["failure"], data["checks"]))
        self.assertEqual(data["status"], "passed")
        self.assert_no_research_claim(data)
        self.assertEqual([item["exit_code"] for item in data["checks"]], [0, 0])
        tests = data["checks"][1]["tests"]
        self.assertTrue(tests["complete"])
        self.assertEqual(tests["executed"], len(self.expected))
        self.assertEqual(tests["passed"], len(self.expected))
        self.assertEqual(tests["skipped"], 0)
        self.assertEqual({item["id"] for item in tests["cases"]}, self.expected)
        self.assertEqual(runner.snapshot(), self.sources)
        for destination, source in (
            ("plan.source.json", "research/operations/concept-study.plan.json"),
            ("report.UNRUN.json", "research/operations/concept-study.report.json"),
        ):
            self.assertEqual((self.output / destination).read_bytes(), self.sources[source])

    def test_automated_lane_does_not_wait_for_people_or_clear_study_conditions(self):
        with mock.patch.object(runner.subprocess, "run", side_effect=self.successful_commands()):
            code, _, _ = self.invoke()
        self.assertEqual(code, 0)
        data = self.assessment()
        self.assert_no_research_claim(data)
        self.assertFalse(data["routine_human_coordination_required"])
        self.assertFalse(data["participants_required_for_this_run"])
        self.assertFalse(data["qualified_approval_required_for_this_run"])
        conditions = json.loads(self.sources["research/operations/concept-study.plan.json"])["unmet_prerequisites"]
        self.assertEqual(data["later_study"]["source_plan_conditions"], conditions)
        self.assertEqual(len(conditions), 11)
        self.assertEqual(len(data["prepared_artifacts"]), 2)

    def test_fixed_commands_have_no_shell_input_or_inherited_credentials(self):
        with mock.patch.dict(os.environ, {
            "GH_TOKEN": "SYNTHETIC-NOT-A-TOKEN", "GITHUB_TOKEN": "SYNTHETIC-NOT-A-TOKEN",
            "GIT_CONFIG_PARAMETERS": "SYNTHETIC-NOT-A-CONFIG", "UNRELATED_PRIVATE_VALUE": "SYNTHETIC",
        }):
            with mock.patch.object(runner.subprocess, "run", side_effect=self.successful_commands()) as run:
                code, _, _ = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(run.call_count, 2)
        for call, (_, arguments) in zip(run.call_args_list, runner.CHECKS):
            self.assertEqual(call.args[0], [sys.executable, "-I", "-B", *arguments])
            self.assertEqual(call.kwargs["cwd"], ROOT)
            self.assertEqual(call.kwargs["stdin"], subprocess.DEVNULL)
            self.assertFalse(call.kwargs.get("shell", False))
            self.assertEqual(call.kwargs["env"]["GIT_NO_LAZY_FETCH"], "1")
            self.assertEqual(call.kwargs["env"]["GIT_NO_REPLACE_OBJECTS"], "1")
            for key in ("GH_TOKEN", "GITHUB_TOKEN", "GIT_CONFIG_PARAMETERS", "UNRELATED_PRIVATE_VALUE"):
                self.assertNotIn(key, call.kwargs["env"])

    def test_unsupported_participant_live_and_approval_inputs_are_refused_without_echo(self):
        marker = "SYNTHETIC-PRIVATE-INPUT-NOT-REAL"
        bad_arguments = [
            ["--input", marker], ["--mode", "live"], ["--approve-legal", marker],
            ["--participant-count", "16"], ["--consent", marker],
            ["--contact", marker], ["--role", "qualified-legal"], [marker],
        ]
        with mock.patch.object(runner, "snapshot") as read, mock.patch.object(runner.subprocess, "run") as run:
            for extra in bad_arguments:
                with self.subTest(extra=extra[0]):
                    code, stdout, stderr = self.invoke(["--output", str(self.output), *extra])
                    self.assertEqual(code, 2)
                    self.assertIn("refused", stderr)
                    self.assertNotIn(marker, stdout + stderr)
                    self.assertFalse(self.output.exists())
            for arguments in ([], ["--out", str(self.output)]):
                self.assertEqual(self.invoke(arguments)[0], 2)
        read.assert_not_called()
        run.assert_not_called()

    def test_output_cannot_overwrite_reports_source_metadata_or_another_checkout(self):
        existing = self.directory / "existing"
        existing.mkdir()
        sentinel = existing / "assessment.json"
        sentinel.write_text("SYNTHETIC-PRIOR-REPORT", encoding="utf-8")
        checkout = self.directory / "checkout"
        checkout.mkdir()
        (checkout / ".git").mkdir()
        bare = self.directory / "bare-metadata"
        bare.mkdir()
        (bare / "HEAD").write_text("SYNTHETIC-BARE-METADATA", encoding="utf-8")
        (bare / "objects").mkdir()
        (bare / "refs").mkdir()
        paths = (
            str(existing), str(ROOT / "research" / "operations" / "new-assessment"),
            str(self.directory / ".git" / "new-assessment"), str(checkout / "new-assessment"),
            str(bare / "new-assessment"),
            "relative-assessment", "https://example.invalid/assessment", r"\\example.invalid\share\assessment",
            str(self.directory / "missing-parent" / "new-assessment"),
        )
        with mock.patch.object(runner.subprocess, "run") as run:
            for path in paths:
                with self.subTest(kind=path):
                    code, _, stderr = self.invoke(["--output", path])
                    self.assertEqual(code, 2)
                    self.assertIn("refused", stderr)
        run.assert_not_called()
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "SYNTHETIC-PRIOR-REPORT")

    def test_linked_output_is_refused_without_platform_privilege_skips(self):
        original = runner.linked
        with mock.patch.object(runner, "linked", side_effect=lambda path: path == self.directory or original(path)):
            with mock.patch.object(runner.subprocess, "run") as run:
                code, _, stderr = self.invoke()
        self.assertEqual(code, 2)
        self.assertIn("Linked output paths", stderr)
        self.assertFalse(self.output.exists())
        run.assert_not_called()

    def test_missing_or_linked_fixed_source_fails_before_commands(self):
        for condition in ("missing", "linked"):
            self.output = self.directory / condition
            with self.subTest(condition=condition):
                patch = (
                    mock.patch.object(runner, "SOURCE_PATHS", ("research/operations/SYNTHETIC-MISSING.json",))
                    if condition == "missing" else
                    mock.patch.object(runner, "linked", side_effect=lambda path: path == SCRIPT)
                )
                with patch, mock.patch.object(runner.subprocess, "run") as run:
                    code, _, _ = self.invoke()
                self.assertEqual(code, 1)
                self.assertEqual(self.assessment()["status"], "failed")
                self.assertEqual(self.assessment()["prepared_artifacts"], [])
                run.assert_not_called()

    def test_actual_existing_source_command_failure_stops_and_propagates(self):
        checks = (("preparation", ("research/operations/check.py", "--unsupported-synthetic-input")), *runner.CHECKS[1:])
        with mock.patch.object(runner, "CHECKS", checks):
            code, _, _ = self.invoke()
        self.assertEqual(code, 1)
        data = self.assessment()
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["failure"], "command_failed")
        self.assertEqual(len(data["checks"]), 1)
        self.assertEqual(data["checks"][0]["exit_code"], 1)
        self.assertGreater(data["checks"][0]["stderr"]["size_bytes"], 0)
        self.assertEqual(data["prepared_artifacts"], [])
        self.assert_no_research_claim(data)

    def test_actual_existing_unittest_command_failure_is_not_relabelled_as_success(self):
        name, arguments = runner.CHECKS[1]
        checks = (runner.CHECKS[0], (name, (*arguments, "--unsupported-synthetic-option")))
        with mock.patch.object(runner, "CHECKS", checks):
            code, _, _ = self.invoke()
        self.assertEqual(code, 2)
        data = self.assessment()
        self.assertEqual(data["checks"][0]["exit_code"], 0)
        self.assertEqual(data["checks"][1]["exit_code"], 2)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["prepared_artifacts"], [])
        self.assert_no_research_claim(data)

    def test_no_tests_skips_missing_duplicates_or_unrecognized_cases_cannot_pass(self):
        valid = self.native_output()
        first_line = valid.splitlines(keepends=True)[0]
        variants = {
            "zero": b"Ran 0 tests in 0.001s\n\nOK\n",
            "skipped": valid.replace(b"... ok", b"... skipped 'SYNTHETIC-PRIVATE-REASON'", 1),
            "missing": valid[len(first_line):],
            "duplicate": first_line + valid,
            "unrecognized": valid.replace(first_line, b"test_unknown (test_research_operations.Unknown.test_unknown) ... ok\n"),
        }
        for condition, log in variants.items():
            self.output = self.directory / condition
            responses = self.successful_commands()
            responses[1] = subprocess.CompletedProcess([], 0, b"", log)
            with self.subTest(condition=condition), mock.patch.object(runner.subprocess, "run", side_effect=responses):
                code, _, _ = self.invoke()
            data = self.assessment()
            self.assertEqual(code, 1)
            self.assertEqual(data["status"], "failed")
            self.assertEqual(data["failure"], "incomplete_native_test_evidence")
            self.assertFalse(data["checks"][1]["tests"]["complete"])
            self.assertEqual(data["prepared_artifacts"], [])
            self.assertNotIn("SYNTHETIC-PRIVATE-REASON", json.dumps(data))

    def test_native_lf_and_windows_crlf_summaries_produce_the_same_test_evidence(self):
        raw = self.native_output()
        lf = runner.test_evidence(b"", raw, self.expected)
        crlf = runner.test_evidence(b"", raw.replace(b"\n", b"\r\n"), self.expected)
        self.assertTrue(lf["complete"])
        self.assertEqual(crlf, lf)
        self.assertNotEqual(runner.fingerprint(raw), runner.fingerprint(raw.replace(b"\n", b"\r\n")))

    def native_pair(self, prefix, outcome):
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", PAIRED_NATIVE_FIXTURE, prefix, outcome],
            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"Ran 2 tests", result.stderr)
        return result

    def assert_native_paired_rejected(self, outcome):
        for prefix in ("clean", "diagnostic_then_ok", "ok_prefix_only"):
            self.output = self.directory / prefix
            with self.subTest(prefix=prefix):
                result = self.native_pair(prefix, outcome)
                self.assertIn(b"OK (skipped=1)" if outcome == "skip" else b"OK (expected failures=1)", result.stderr)
                parsed = runner.test_evidence(result.stdout, result.stderr, PAIRED_IDS)
                self.assertFalse(parsed["complete"])
                self.assertEqual(parsed["passed"], 1 if prefix == "clean" else None)
                if prefix != "clean":
                    self.assertEqual(parsed["cases"], [])
                lf = result.stderr.replace(b"\r\n", b"\n")
                self.assertEqual(parsed, runner.test_evidence(result.stdout, lf, PAIRED_IDS))
                self.assertEqual(parsed, runner.test_evidence(result.stdout, lf.replace(b"\n", b"\r\n"), PAIRED_IDS))
                responses = self.successful_commands()
                responses[1] = result
                with mock.patch.object(runner, "expected_tests", return_value=PAIRED_IDS):
                    with mock.patch.object(runner.subprocess, "run", side_effect=responses):
                        code, stdout, stderr = self.invoke()
                data = self.assessment()
                self.assertEqual(code, 1)
                self.assertEqual(data["status"], "failed")
                self.assertEqual(data["failure"], "incomplete_native_test_evidence")
                self.assertEqual(data["checks"][1]["exit_code"], 0)
                self.assertEqual(data["checks"][1]["status"], "failed")
                self.assertEqual(data["prepared_artifacts"], [])
                self.assertFalse((self.output / "plan.source.json").exists())
                self.assertFalse((self.output / "report.UNRUN.json").exists())
                self.assertNotIn("SYNTHETIC capability skip", json.dumps(data) + stdout + stderr)
                self.assert_no_research_claim(data)

    def test_native_paired_skip_diagnostics_cannot_be_pass_evidence(self):
        self.assert_native_paired_rejected("skip")

    def test_native_paired_expected_failure_diagnostics_cannot_be_pass_evidence(self):
        self.assert_native_paired_rejected("expected_failure")

    def test_native_paired_passing_results_are_preserved(self):
        result = self.native_pair("clean", "pass")
        parsed = runner.test_evidence(result.stdout, result.stderr, PAIRED_IDS)
        self.assertTrue(parsed["complete"])
        self.assertEqual(parsed["passed"], 2)
        self.assertEqual(parsed["skipped"], 0)
        responses = self.successful_commands()
        responses[1] = result
        with mock.patch.object(runner, "expected_tests", return_value=PAIRED_IDS):
            with mock.patch.object(runner.subprocess, "run", side_effect=responses):
                code, _, _ = self.invoke()
        self.assertEqual(code, 0)
        self.assert_no_research_claim(self.assessment())

    def test_terminal_report_cannot_be_supplied_by_stdout_or_ambiguous_diagnostics(self):
        valid = self.native_output()
        first_line = valid.splitlines(keepends=True)[0]
        variants = (
            (valid, b""),
            (valid, valid.replace(b"\nOK\n", b"\nOK (skipped=1)\n")),
            (b"", valid.replace(b"\nOK\n", b"\nOK (expected failures=1)\n")),
            (b"", first_line + b"skipped 'SYNTHETIC hidden status'\n" + valid[len(first_line):]),
            (b"", valid + b"SYNTHETIC trailing diagnostic\n"),
            (b"", valid + valid),
            (b"", valid.replace(b"\nOK\n", b"\n")),
        )
        for index, (stdout, stderr) in enumerate(variants):
            with self.subTest(index=index):
                self.assertFalse(runner.test_evidence(stdout, stderr, self.expected)["complete"])
        self.assertTrue(runner.test_evidence(b"SYNTHETIC stdout is not a result\n", valid, self.expected)["complete"])

    def test_raw_command_text_and_false_approval_claims_are_not_retained(self):
        marker = b"SYNTHETIC-not-real@example.invalid; legal approved; 16 real participants; consent granted"
        responses = self.successful_commands()
        responses[0] = subprocess.CompletedProcess([], 0, marker, marker)
        with mock.patch.object(runner.subprocess, "run", side_effect=responses):
            code, stdout, stderr = self.invoke()
        self.assertEqual(code, 0)
        data = self.assessment()
        self.assert_no_research_claim(data)
        self.assertNotIn(marker.decode(), json.dumps(data) + stdout + stderr)
        self.assertEqual(data["checks"][0]["stdout"], runner.fingerprint(marker))
        self.assertEqual(data["checks"][0]["stderr"], runner.fingerprint(marker))

    def test_timeout_and_launch_failures_are_explicit_without_error_content(self):
        marker = b"SYNTHETIC-PRIVATE-ERROR-NOT-REAL"
        failures = (
            subprocess.TimeoutExpired([], runner.TIMEOUT_SECONDS, output=marker, stderr=marker),
            FileNotFoundError(marker.decode()),
        )
        for index, failure in enumerate(failures):
            self.output = self.directory / f"failure-{index}"
            with self.subTest(index=index), mock.patch.object(runner.subprocess, "run", side_effect=failure):
                code, stdout, stderr = self.invoke()
            data = self.assessment()
            self.assertEqual(code, 1)
            self.assertEqual(data["status"], "failed")
            self.assertIn(data["failure"], {"command_timeout", "command_unavailable"})
            self.assertIsNone(data["checks"][0]["exit_code"])
            self.assertEqual(data["prepared_artifacts"], [])
            self.assertNotIn(marker.decode(), json.dumps(data) + stdout + stderr)

    def test_source_drift_after_successful_commands_refuses_prepared_artifacts(self):
        altered = copy.deepcopy(self.sources)
        altered["research/operations/report-template.md"] += b"\nSYNTHETIC changed source.\n"
        with mock.patch.object(runner, "snapshot", side_effect=[self.sources, altered]):
            with mock.patch.object(runner.subprocess, "run", side_effect=self.successful_commands()):
                code, _, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(self.assessment()["prepared_artifacts"], [])
        self.assertIn("Source changed", self.assessment()["failure"])

    def test_no_contact_unrun_and_null_boundary_is_rechecked_before_copying(self):
        for kind, field, value in (
            ("plan", "contact_allowed", True),
            ("report", "execution_state", "REPORTED"), ("report", "participant_count", 16),
            ("report", "decision", "no_change"), ("report", "finding_dispositions", [{"synthetic": "not a finding"}]),
        ):
            self.output = self.directory / field
            altered = copy.deepcopy(self.sources)
            name = f"research/operations/concept-study.{kind}.json"
            document = json.loads(altered[name])
            document[field] = value
            altered[name] = json.dumps(document).encode("utf-8")
            with self.subTest(field=field), mock.patch.object(runner, "snapshot", return_value=altered):
                with mock.patch.object(runner.subprocess, "run", side_effect=self.successful_commands()):
                    code, _, _ = self.invoke()
            self.assertEqual(code, 1)
            self.assertEqual(self.assessment()["prepared_artifacts"], [])
            self.assert_no_research_claim(self.assessment())

    def test_output_persistence_failure_is_not_reported_as_success(self):
        original = Path.open

        def deny_report(path, *args, **kwargs):
            if path == self.output / ".assessment.json.tmp":
                raise PermissionError("SYNTHETIC-PRIVATE-ERROR")
            return original(path, *args, **kwargs)

        with mock.patch.object(runner.subprocess, "run", side_effect=self.successful_commands()):
            with mock.patch.object(Path, "open", autospec=True, side_effect=deny_report):
                code, stdout, stderr = self.invoke()
        self.assertEqual(code, 1)
        self.assertNotIn("passed", stdout)
        self.assertIn("could not be persisted", stderr)
        self.assertNotIn("SYNTHETIC-PRIVATE-ERROR", stderr)

    def test_late_assessment_write_flush_or_close_failure_never_publishes_success(self):
        original = Path.open
        for fault in ("write", "flush", "close"):
            self.output = self.directory / fault
            injected = []

            class FaultingWriter:
                def __init__(self, handle):
                    self.handle = handle

                def __enter__(self):
                    self.handle.__enter__()
                    return self

                def write(self, text):
                    result = self.handle.write(text)
                    if fault == "write" and text == "\n":
                        injected.append(fault)
                        raise OSError("SYNTHETIC-PRIVATE-ERROR")
                    return result

                def flush(self):
                    self.handle.flush()
                    if fault == "flush":
                        injected.append(fault)
                        raise OSError("SYNTHETIC-PRIVATE-ERROR")

                def fileno(self):
                    return self.handle.fileno()

                def __exit__(self, kind, error, traceback):
                    result = self.handle.__exit__(kind, error, traceback)
                    if fault == "close":
                        injected.append(fault)
                        raise OSError("SYNTHETIC-PRIVATE-ERROR")
                    return result

            def fail_late(path, *args, **kwargs):
                handle = original(path, *args, **kwargs)
                return FaultingWriter(handle) if path == self.output / ".assessment.json.tmp" else handle

            with self.subTest(fault=fault), mock.patch.object(Path, "open", autospec=True, side_effect=fail_late):
                with mock.patch.object(runner.subprocess, "run", side_effect=self.successful_commands()):
                    code, stdout, stderr = self.invoke()
            self.assertEqual(injected, [fault])
            self.assertEqual(code, 1)
            self.assertFalse((self.output / "assessment.json").exists())
            self.assertFalse((self.output / ".assessment.json.tmp").exists())
            self.assertNotIn("passed", stdout)
            self.assertIn("could not be persisted", stderr)
            self.assertNotIn("SYNTHETIC-PRIVATE-ERROR", stderr)

    def test_final_publication_preserves_existing_destination_and_staging_files(self):
        for name in ("assessment.json", ".assessment.json.tmp"):
            self.output = self.directory / name.replace(".", "-")
            self.output.mkdir()
            sentinel = self.output / name
            sentinel.write_bytes(b"SYNTHETIC prior file must not be changed")
            with self.subTest(name=name), mock.patch.object(runner.subprocess, "run", side_effect=self.successful_commands()):
                with self.assertRaises(FileExistsError):
                    runner.assess(self.output)
            self.assertEqual(sentinel.read_bytes(), b"SYNTHETIC prior file must not be changed")
            if name == "assessment.json":
                self.assertFalse((self.output / ".assessment.json.tmp").exists())
            else:
                self.assertFalse((self.output / "assessment.json").exists())

    def test_sync_or_no_clobber_publication_failure_never_leaves_a_success_receipt(self):
        for operation in ("fsync", "link"):
            self.output = self.directory / operation
            with self.subTest(operation=operation), mock.patch.object(runner.os, operation, side_effect=OSError("SYNTHETIC-PRIVATE-ERROR")):
                with mock.patch.object(runner.subprocess, "run", side_effect=self.successful_commands()):
                    code, stdout, stderr = self.invoke()
            self.assertEqual(code, 1)
            self.assertFalse((self.output / "assessment.json").exists())
            self.assertFalse((self.output / ".assessment.json.tmp").exists())
            self.assertNotIn("passed", stdout)
            self.assertIn("could not be persisted", stderr)
            self.assertNotIn("SYNTHETIC-PRIVATE-ERROR", stderr)

    def test_post_publication_cleanup_warning_does_not_contradict_persisted_result(self):
        original = Path.unlink

        def fail_cleanup(path, *args, **kwargs):
            if path == self.output / ".assessment.json.tmp":
                raise OSError("SYNTHETIC-PRIVATE-ERROR")
            return original(path, *args, **kwargs)

        with mock.patch.object(Path, "unlink", autospec=True, side_effect=fail_cleanup):
            with mock.patch.object(runner.subprocess, "run", side_effect=self.successful_commands()):
                code, _, stderr = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(self.assessment()["status"], "passed")
        self.assertIn("temporary-file cleanup failed", stderr)
        self.assertNotIn("SYNTHETIC-PRIVATE-ERROR", stderr)
        self.assertEqual((self.output / "assessment.json").read_bytes(), (self.output / ".assessment.json.tmp").read_bytes())

    def test_project_skill_has_one_native_entry_point_without_permission_overrides(self):
        skill = ROOT / ".github" / "skills" / "docs65-synthetic-operations" / "SKILL.md"
        text = skill.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: docs65-synthetic-operations\ndescription: "))
        self.assertIn("python research\\operations\\run_synthetic.py --output", text)
        self.assertIn("copilot skill list --json", text)
        self.assertIn("successful runner exit (0)", text)
        self.assertIn("not a new policy", (ROOT / "research" / "operations" / "README.md").read_text(encoding="utf-8"))
        self.assertNotIn("allowed-tools:", text)
        self.assertNotIn("mcp-servers:", text)
        self.assertFalse((ROOT / ".github" / "agents" / "docs65-synthetic-operations.agent.md").exists())


if __name__ == "__main__":
    unittest.main()
