"""Finite no-contact Docs65 source preparation; never a real-study or approval record."""

import argparse
import ast
from collections import Counter
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TEST_PATH = "scripts/tests/test_research_operations.py"
SOURCE_PATHS = (
    "research/operations/README.md", "research/operations/check.py",
    "research/operations/concept-study.plan.json", "research/operations/concept-study.report.json",
    "research/operations/debt-first-protocol.md", "research/operations/household-tabletop.md",
    "research/operations/procedures.md", "research/operations/report-template.md",
    "research/operations/schema.json", "research/operations/run_synthetic.py", TEST_PATH,
    ".github/skills/docs65-synthetic-operations/SKILL.md",
    "governance/design-gates.json", "governance/design-gates.schema.json",
    "governance/design-operations.md", "scripts/check_design_gates.py",
    "scripts/check_client_states.py", "scripts/check_threat_model.py",
)
CHECKS = (
    ("preparation", ("research/operations/check.py",)),
    ("research_regressions", ("-m", "unittest", "discover", "-s", "scripts/tests",
                              "-p", "test_research_operations.py", "-v")),
)
TIMEOUT_SECONDS = 180


class Refused(ValueError):
    """Static diagnostic; never echo untrusted arguments or source contents."""


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refused("Only --output <new local directory> is accepted; no research inputs or approval switches.")


def fingerprint(raw):
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def linked(path):
    return path.is_symlink() or path.is_junction()


def output_directory(value):
    path = Path(value)
    if (not path.is_absolute() or path.drive.startswith("\\\\") or path.as_posix().startswith("//")
            or any(part.lower() == ".git" for part in path.parts)):
        raise Refused("Output must be a new absolute local directory outside Git metadata.")
    if any(linked(parent) for parent in (path, *path.parents)):
        raise Refused("Linked output paths are not supported.")
    path = path.resolve()
    if path.is_relative_to(ROOT) or path.exists() or not path.parent.is_dir():
        raise Refused("Output must be new, outside the repository, with an existing local parent.")
    for parent in path.parents:
        if ((parent / ".git").exists()
                or ((parent / "HEAD").is_file() and (parent / "objects").is_dir() and (parent / "refs").is_dir())):
            raise Refused("Output must be outside Git checkouts and bare metadata.")
    return path


def snapshot():
    result = {}
    for name in SOURCE_PATHS:
        path = ROOT / name
        if any(linked(parent) for parent in (path, *path.parents) if parent.is_relative_to(ROOT)):
            raise Refused("A fixed source path is linked; no assessment was performed.")
        if not path.is_file():
            raise Refused("A required operations source is missing.")
        result[name] = path.read_bytes()
    return result


def expected_tests(raw):
    tests = {
        f"test_research_operations.{node.name}.{method.name}"
        for node in ast.parse(raw).body if isinstance(node, ast.ClassDef)
        for method in node.body if isinstance(method, ast.FunctionDef) and method.name.startswith("test_")
    }
    if not tests:
        raise Refused("The existing research suite has no test cases.")
    return tests


def test_evidence(stdout, stderr, expected):
    # Test diagnostics are not outcomes: require an uninterrupted native stderr report.
    text = stderr.decode("utf-8", errors="replace").replace("\r\n", "\n")
    summary = re.search(
        r"\n-{70}\nRan (\d+) tests in ([0-9]+(?:\.[0-9]+)?)s\n\n"
        r"(OK(?: \([^\n]+\))?|FAILED(?: \([^\n]+\))?)\n\Z", text,
    )
    events = []
    unambiguous = summary is not None
    if summary:
        for line in text[:summary.start()].splitlines():
            event = re.fullmatch(
                r"(test_\w+) \((test_research_operations\.\w+\.(test_\w+))\) \.\.\. "
                r"(ok|FAIL|ERROR|skipped .+|expected failure|unexpected success)", line,
            )
            if event is None or event.group(1) != event.group(3):
                unambiguous, events = False, []
                break
            outcome = event.group(4)
            events.append((event.group(2), "skipped" if outcome.startswith("skipped ") else outcome))
    counts = Counter(name for name, _ in events)
    complete = (
        unambiguous and summary.group(3) == "OK" and int(summary.group(1)) == len(expected)
        and set(counts) == expected and set(counts.values()) == {1}
        and all(outcome == "ok" for _, outcome in events)
    )
    return {
        "complete": complete, "expected": len(expected), "unambiguous_outcomes": unambiguous,
        "executed": int(summary.group(1)) if summary else None,
        "runner_seconds": float(summary.group(2)) if summary else None,
        "passed": sum(outcome == "ok" for _, outcome in events) if unambiguous else None,
        "skipped": sum(outcome == "skipped" for _, outcome in events) if unambiguous else None,
        "cases": [{"id": name, "outcome": outcome} for name, outcome in events if name in expected],
        "missing_ids": sorted(expected - set(counts)),
        "unexpected_or_duplicate_ids": bool(set(counts) - expected or any(n != 1 for n in counts.values())),
    }


def execute(name, arguments, expected):
    command = [sys.executable, "-I", "-B", *arguments]
    env = {
        key: value for key, value in os.environ.items()
        if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "PATHEXT", "COMSPEC",
                           "HOME", "USERPROFILE", "TEMP", "TMP"}
    }
    env.update(GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0")
    started = time.perf_counter()
    evidence = {"id": name, "command": ["python", "-I", "-B", *arguments], "uses_current_interpreter": True}
    try:
        result = subprocess.run(
            command, cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
            env=env, timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        evidence.update(status="failed", failure="command_timeout", exit_code=None,
                        stdout=fingerprint(error.stdout or b""), stderr=fingerprint(error.stderr or b""))
    except OSError:
        evidence.update(status="failed", failure="command_unavailable", exit_code=None)
    else:
        evidence.update(exit_code=result.returncode, stdout=fingerprint(result.stdout), stderr=fingerprint(result.stderr))
        if name == "research_regressions":
            evidence["tests"] = test_evidence(result.stdout, result.stderr, expected)
        if result.returncode != 0:
            evidence.update(status="failed", failure="command_failed")
        elif name == "research_regressions" and not evidence["tests"]["complete"]:
            evidence.update(status="failed", failure="incomplete_native_test_evidence")
        else:
            evidence.update(status="passed", failure=None)
    evidence["wall_seconds"] = round(time.perf_counter() - started, 6)
    return evidence


def assess(output):
    assessment = {
        "kind": "automated_synthetic_operations_assessment", "version": "1.0.0",
        "scope": "source_preparation_and_synthetic_software_checks_only",
        "source_snapshot": "local_working_tree_bytes",
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "status": "failed", "failure": None,
        "routine_human_coordination_required": False, "participants_required_for_this_run": False,
        "qualified_approval_required_for_this_run": False,
        "contact_allowed": False, "qualified_approvals": [], "role_assignments": [],
        "original_docs65_acceptance": "not_decided_by_this_run",
        "later_study": {"execution_state": "UNRUN", "participant_count": None,
                        "decision": "pending", "findings": [], "conditions_cleared_by_this_run": []},
        "source_files": [], "checks": [], "prepared_artifacts": [],
        "limitations": [
            "An automated software assessment is not participant research or independent review.",
            "No qualified Privacy, Legal, Accessibility or UX Research approval is provided.",
            "No real encrypted-store, backup, access, expiry, deletion or withdrawal operation is proved.",
            "Recruitment coverage and household safety in practice are not observed by these tests.",
            "Running a specific study is outside Docs65; genuine participants are not a condition for this run.",
            "Docs53 contact and real-study conditions remain unchanged; synthetic tests cannot satisfy them.",
            "The reviewed Python, Git and local source are trusted; this runner is not a host sandbox.",
            "Child output is fingerprinted, not copied; only recognized test IDs and outcomes are retained.",
        ],
    }
    exit_code = 1
    try:
        sources = snapshot()
        expected = expected_tests(sources[TEST_PATH])
        assessment["source_files"] = [
            {"path": name, **fingerprint(raw)} for name, raw in sources.items()
        ]
        for name, arguments in CHECKS:
            evidence = execute(name, arguments, expected)
            assessment["checks"].append(evidence)
            if evidence["status"] != "passed":
                assessment["failure"] = evidence["failure"]
                exit_code = evidence["exit_code"] if evidence["exit_code"] and evidence["exit_code"] > 0 else 1
                break
        else:
            if snapshot() != sources:
                raise Refused("Source changed during assessment; no prepared artifacts are valid.")
            plan = json.loads(sources["research/operations/concept-study.plan.json"])
            report = json.loads(sources["research/operations/concept-study.report.json"])
            if (plan["contact_allowed"] is not False or report["execution_state"] != "UNRUN"
                    or report["participant_count"] is not None or report["finding_dispositions"]
                    or report["decision"] != "pending"):
                raise Refused("The source does not preserve the no-contact, UNRUN and null-participant boundary.")
            assessment["later_study"]["source_plan_conditions"] = plan["unmet_prerequisites"]
            assessment["later_study"]["source_method_limitations"] = report["limitations"]
            for destination, source in (
                ("plan.source.json", "research/operations/concept-study.plan.json"),
                ("report.UNRUN.json", "research/operations/concept-study.report.json"),
            ):
                with (output / destination).open("xb") as stream:
                    stream.write(sources[source])
                assessment["prepared_artifacts"].append({
                    "path": destination, "source": source, "classification": "unchanged_source_copy",
                    **fingerprint(sources[source]),
                })
            assessment["status"], exit_code = "passed", 0
    except Refused as error:
        assessment["failure"] = str(error)
    except (OSError, ValueError, KeyError, SyntaxError):
        assessment["failure"] = "Required source or output is unreadable or invalid; assessment failed."
    temporary = output / ".assessment.json.tmp"
    stream = temporary.open("x", encoding="utf-8", newline="\n")
    published = False
    try:
        with stream:
            json.dump(assessment, stream, ensure_ascii=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # A hard link publishes the closed file without replacing an existing destination.
        os.link(temporary, output / "assessment.json")
        published = True
    finally:
        try:
            temporary.unlink()
        except OSError:
            if not published:
                raise
            print("Synthetic operations warning: assessment persisted; temporary-file cleanup failed.", file=sys.stderr)
    return assessment, exit_code


def main(argv=None):
    parser = Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", required=True, help="New local directory outside Git; no existing files are overwritten.")
    try:
        options = parser.parse_args(argv)
        output = output_directory(options.output)
        output.mkdir()
    except Refused as error:
        print(f"Synthetic operations refused: {error}", file=sys.stderr)
        return 2
    except OSError:
        print("Synthetic operations refused: cannot create a new local output directory.", file=sys.stderr)
        return 2
    try:
        assessment, exit_code = assess(output)
    except OSError:
        print("Synthetic operations failed: assessment could not be persisted.", file=sys.stderr)
        return 1
    print(f"Synthetic operations {assessment['status']}; see assessment.json. Study UNRUN; no contact or approval.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
