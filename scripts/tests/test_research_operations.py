"""SYNTHETIC SOFTWARE FIXTURES ONLY. No people, sessions, consents or approvals."""

import contextlib
import copy
import datetime
import importlib.util
import io
from pathlib import Path
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parents[2] / "research" / "operations"
spec = importlib.util.spec_from_file_location("research_operations", HERE / "check.py")
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)
UTC = datetime.timezone.utc
START = datetime.datetime(2000, 1, 1, tzinfo=UTC)
EXPIRY = START + datetime.timedelta(days=35)
WITHDRAWAL = START + datetime.timedelta(days=28)
NOW = START + datetime.timedelta(days=1)


def stamp(value):
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def fixtures():
    participant = {
        "kind": "participant_code", "data_origin": "synthetic_fixture", "study_id": "T-RES-01",
        "participant_code": "P-" + "a" * 32, "eligibility": "eligible",
        "consent_version": "1.0.0", "consent_state": "granted",
        "consented_at": stamp(START), "consent_expires_at": stamp(EXPIRY),
        "withdrawal_until": stamp(WITHDRAWAL), "withdrawn_at": None,
    }
    evidence = {
        "kind": "coded_reaction", "data_origin": "synthetic_fixture", "study_id": "T-RES-01",
        "participant_code": participant["participant_code"], "collected_at": stamp(START),
        "expires_at": stamp(EXPIRY), "state": "active", "order": "DE",
        "preference": "neither", "post_disclosure_preference": "neither",
        "price_choice": "skipped", "sms_reaction": "deny", "reason_codes": ["not_coded"],
    }
    grant = {
        "data_origin": "synthetic_fixture", "study_id": "T-RES-01", "role": "analyst",
        "resource": "coded_evidence", "issued_at": stamp(START), "expires_at": stamp(EXPIRY),
        "revoked": False,
    }
    return participant, evidence, grant


def recruitment():
    return {
        "data_origin": "synthetic_fixture", "study_kind": "concept",
        "reviewed_route": True, "private_opt_in": True, "private_channel": True,
        "private_context": True, "stop_available": True, "personal_network": False,
        "household_referral": False, "shared_contact": False, "paired_session": False,
        "household_disclosure_requested": False, "specialist_reviewed": False,
    }


def counts(**values):
    result = {key: 0 for key in ("debt", "expense", "equal", "neither", "unsure", "skipped")}
    result.update(values)
    return result


def reported_fixture():
    report = ops.load_json(HERE / "concept-study.report.json")
    report.update(
        execution_state="REPORTED", data_origin="synthetic_fixture", participant_count=16,
        preference=counts(debt=8, expense=8),
        pricing={"paid": 8, "free": 8, "neither": 0, "unsure": 0, "skipped": 0},
        sms={"allow": 8, "deny": 8, "unsure": 0, "skipped": 0},
        order_effect_status="no_detected_order_sensitivity", coverage_status="incomplete",
        withdrawal_count=0, evidence_age_days=14, undispositioned_finding_count=0,
        limitations=["small_purposive_sample", "hypothetical_intent"], decision="retest",
    )
    return report


class SourceRightsFixture:
    """In-memory software records, not real assignments, review evidence or decisions."""

    def __init__(self, artifact_class="research_plan"):
        self.blobs = {}
        author, actor, verifier = (
            f"{number:08x}-0000-4000-8000-000000000000" for number in range(1, 4)
        )
        self.assignments = [
            {
                "context_id": context, "runtime": "synthetic-test-not-a-role-appointment",
                "login": "basiltt", "roles": [role],
                "artifact_ids": ["T-RES-01-plan", "T-RES-01-synthesis"],
                "issued_at": stamp(NOW - datetime.timedelta(hours=1)),
                "expires_at": stamp(NOW + datetime.timedelta(hours=6)),
                "evidence": self.source("assignment_" + role),
            }
            for context, role in ((actor, "research"), (verifier, "privacy"))
        ]
        proposal = self.source("proposal")
        self.entry = {
            "id": "SYNTHETIC_DECISION", "artifact_id": (
                "T-RES-01-plan" if artifact_class == "research_plan" else "T-RES-01-synthesis"
            ),
            "artifact_class": artifact_class, "kind": "research_disposition", "disposition": "accept",
            "author_contexts": [author], "actor_context_id": actor, "actor_role": "research",
            "verifier_context_id": verifier, "verifier_role": "privacy",
            "base_sha256": proposal["sha256"], "target_version": "1.1.0",
            "proposals": [{
                "squad": "research", "branch": "T-RES-01__research__synthetic-source", "source": proposal,
            }],
            "result": None, "reason": self.source("reason"), "related_decisions": [],
            "occurred_at": stamp(NOW - datetime.timedelta(minutes=30)),
            "expires_at": stamp(NOW + datetime.timedelta(hours=4)),
        }

    def source(self, name):
        key = "1" * 40, f"fixtures/synthetic_research_{name}.txt"
        data = f"Synthetic software fixture only: {name}\n".encode("ascii")
        self.blobs[key] = data
        return {"commit": key[0], "path": key[1], "sha256": ops.design.digest(data)}

    def read_blob(self, commit, path):
        return self.blobs[(commit, path)]


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.plan = ops.load_json(HERE / "concept-study.plan.json")
        self.report = ops.load_json(HERE / "concept-study.report.json")

    def test_published_preparation_stays_unrun(self):
        ops.check_preparation(self.plan, self.report)
        self.assertFalse(self.plan["contact_allowed"])
        self.assertIsNone(self.report["participant_count"])
        self.assertEqual(self.plan["planned_orders"].count("DE"), 8)
        self.assertEqual(self.plan["planned_orders"].count("ED"), 8)

    def test_start_conditions_cannot_be_self_approved(self):
        for key, value in (
            ("contact_allowed", True), ("source_status", "accepted"), ("execution_state", "RUNNING"),
            ("recordings_allowed", True), ("raw_notes_allowed", True), ("target_sample", 17),
        ):
            with self.subTest(field=key):
                altered = copy.deepcopy(self.plan)
                altered[key] = value
                with self.assertRaises(ops.Refused):
                    ops.check_preparation(altered, self.report)
        for index in range(len(self.plan["unmet_prerequisites"])):
            altered = copy.deepcopy(self.plan)
            del altered["unmet_prerequisites"][index]
            with self.assertRaises(ops.Refused):
                ops.check_preparation(altered, self.report)
        altered = copy.deepcopy(self.plan)
        altered["dependency"]["accepted"] = False
        with self.assertRaises(ops.Refused):
            ops.check_preparation(altered, self.report)

    def test_changed_order_or_hidden_limitation_fails(self):
        altered = copy.deepcopy(self.plan)
        altered["planned_orders"][0], altered["planned_orders"][1] = (
            altered["planned_orders"][1], altered["planned_orders"][0]
        )
        with self.assertRaises(ops.Refused):
            ops.check_preparation(altered, self.report)
        altered = copy.deepcopy(self.plan)
        altered["limitations"][1] = altered["limitations"][0]
        with self.assertRaises(ops.Refused):
            ops.check_preparation(altered, self.report)

    def test_unrun_counts_even_zero_and_decisions_are_refused(self):
        for key, value in (
            ("participant_count", 0), ("participant_count", 16), ("withdrawal_count", 0),
            ("evidence_age_days", 0), ("undispositioned_finding_count", 0),
            ("decision", "no_change"), ("coverage_status", "purposive_targets_met"),
            ("order_effect_status", "no_detected_order_sensitivity"),
            ("data_origin", "genuine_sessions"),
        ):
            with self.subTest(field=key, replacement=value):
                report = copy.deepcopy(self.report)
                report[key] = value
                with self.assertRaises(ops.Refused):
                    ops.check_preparation(self.plan, report)

    def test_checker_has_no_live_file_or_authorization_interface(self):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(ops.sys, "argv", ["check.py"]):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(ops.main(), 0)
        self.assertIn("contact BLOCKED", out.getvalue())
        with mock.patch.object(ops.sys, "argv", ["check.py", "not-a-real-participant-file"]):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(ops.main(), 1)
        self.assertNotIn("not-a-real-participant-file", err.getvalue())

    def test_dissent_has_equal_top_level_visibility(self):
        text = (HERE / "report-template.md").read_text(encoding="utf-8")
        headings = [
            "## Contradictory evidence", "## Supporting evidence",
            "## Mixed, uncertain and missing evidence",
        ]
        self.assertTrue(all(heading in text for heading in headings))
        self.assertLess(text.index(headings[0]), text.index(headings[1]))


class AcceptedDesignProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = ops.load_design_provider(ops.load_json(HERE / "concept-study.plan.json"))

    def setUp(self):
        self.plan = ops.load_json(HERE / "concept-study.plan.json")
        self.report = ops.load_json(HERE / "concept-study.report.json")

    def evaluate(self, fixture, history=None, expected_head=None, now=NOW):
        history = [] if history is None else history
        expected_head = ops.design.ZERO if expected_head is None else expected_head
        with mock.patch.object(ops, "load_design_provider", return_value=copy.deepcopy(self.provider)):
            with mock.patch.object(ops.design, "git_blob", side_effect=fixture.read_blob):
                return ops.research_disposition(
                    self.plan, history, fixture.entry, expected_head, fixture.assignments, now,
                )

    def test_accepted_provider_allocates_research_and_independent_privacy_only(self):
        policy, schema = ops.load_design_provider(self.plan)
        self.assertEqual(policy["contract_version"], self.plan["dependency"]["contract_version"])
        self.assertTrue(self.plan["dependency"]["accepted"])
        self.assertNotIn("docs64_accepted", self.plan["unmet_prerequisites"])
        self.assertEqual(len(self.plan["unmet_prerequisites"]), 11)
        artifacts = {item["id"]: item for item in policy["artifact_classes"]}
        for name in ("research_plan", "research_synthesis"):
            self.assertEqual(artifacts[name]["accountable"], "research")
            self.assertEqual(artifacts[name]["responsible"], ["research"])
            self.assertEqual(artifacts[name]["verifiers"], ["privacy"])
        self.assertEqual(artifacts["research_access"]["accountable"], "research_store_owner")
        self.assertTrue({"legal", "accessibility", "research_store_owner"} <=
                        set(artifacts["research_plan"]["consulted"]))
        self.assertEqual(len(policy["gates"]), 10)
        self.assertIn("snapshot", schema["definitions"])
        for flag in ("participant_contact_enabled", "figma_access_verified", "figma_publishing_enabled",
                     "role_rights_approved"):
            self.assertFalse(policy["workspace"][flag])
        self.assertFalse(policy["access"]["external_sharing_enabled"])
        self.assertFalse(policy["access"]["public_links_enabled"])

    def test_obsolete_or_unaccepted_provider_pins_fail_closed(self):
        for key, value in (
            ("accepted", False), ("accepted_commit", "4485333ac1355695f020230e9df8ecb681a0daa7"),
            ("accepted_tree", "0" * 40), ("contract_version", "2.0.0"),
        ):
            plan = copy.deepcopy(self.plan)
            plan["dependency"][key] = value
            with self.subTest(field=key), self.assertRaises(ops.Refused):
                ops.load_design_provider(plan)
        for key, value in (("version", "1.0.0"), ("protocol_version", "1.1.0"),
                           ("source_base", "3e4afcb9575badf8669a50136da69fcc6f634500")):
            plan = copy.deepcopy(self.plan)
            plan[key] = value
            with self.subTest(field=key), self.assertRaises(ops.Refused):
                ops.load_design_provider(plan)

    def test_each_missing_or_changed_provider_source_is_refused(self):
        read_blob = ops.design.git_blob
        for target in (ops.design.DATA, ops.design.SCHEMA, ops.design.DOCUMENT, "scripts/check_design_gates.py"):
            for missing in (False, True):
                def changed(commit, path):
                    if path == target:
                        if missing:
                            raise ops.design.Refused("evidence.blob_unavailable")
                        return b"Synthetic altered provider; not accepted source.\n"
                    return read_blob(commit, path)

                with self.subTest(path=target, missing=missing):
                    with mock.patch.object(ops.design, "git_blob", side_effect=changed):
                        with self.assertRaises(ops.Refused):
                            ops.load_design_provider(self.plan)

    def test_preparation_and_source_disposition_both_require_the_bound_provider(self):
        fixture = SourceRightsFixture()
        with mock.patch.object(ops, "load_design_provider", side_effect=ops.Refused("Provider unavailable.")):
            with self.assertRaises(ops.Refused):
                ops.check_preparation(self.plan, self.report)
            with self.assertRaises(ops.Refused):
                ops.research_disposition(
                    self.plan, [], fixture.entry, ops.design.ZERO, fixture.assignments, NOW,
                )

    def test_four_dispositions_use_provider_history_without_activating_research(self):
        before = copy.deepcopy((self.plan, self.report, self.provider))
        for artifact in ("research_plan", "research_synthesis"):
            for disposition in ("accept", "revise", "decline", "defer"):
                fixture = SourceRightsFixture(artifact)
                fixture.entry["disposition"] = disposition
                original = copy.deepcopy((fixture.entry, fixture.assignments))
                with self.subTest(artifact=artifact, disposition=disposition):
                    result = self.evaluate(fixture)
                    self.assertEqual(len(result), 1)
                    self.assertEqual(result[0]["disposition"], disposition)
                    self.assertEqual(ops.design.validate_history(result, self.provider[1]), result[0]["sha256"])
                    self.assertIsNone(result[0]["result"])
                    self.assertEqual((fixture.entry, fixture.assignments), original)
        self.assertEqual((self.plan, self.report, self.provider), before)
        self.assertFalse(self.plan["contact_allowed"])
        self.assertEqual(self.plan["execution_state"], "UNRUN")
        self.assertEqual(self.plan["source_status"], "source_only")
        self.assertIsNone(self.report["participant_count"])

    def test_nonresearch_kinds_and_classes_cannot_use_the_research_interface(self):
        for kind in ("source_change", "freeze", "material_exception", "conflict"):
            fixture = SourceRightsFixture()
            fixture.entry["kind"] = kind
            with self.subTest(kind=kind), self.assertRaises(ops.Refused):
                self.evaluate(fixture)
        for artifact in ("research_access", "components"):
            fixture = SourceRightsFixture()
            fixture.entry["artifact_class"] = artifact
            with self.subTest(artifact=artifact), self.assertRaises(ops.Refused):
                self.evaluate(fixture)

    def test_authority_and_non_author_verification_cannot_be_bypassed(self):
        for change in ("actor_role", "verifier_role", "same_context", "actor_is_author", "verifier_is_author"):
            fixture = SourceRightsFixture()
            entry = fixture.entry
            if change == "actor_role":
                entry["actor_role"] = "product_owner"
            elif change == "verifier_role":
                entry["verifier_role"] = "research"
            elif change == "same_context":
                entry["verifier_context_id"] = entry["actor_context_id"]
            elif change == "actor_is_author":
                entry["author_contexts"].append(entry["actor_context_id"])
            else:
                entry["author_contexts"].append(entry["verifier_context_id"])
            with self.subTest(change=change), self.assertRaises(ops.Refused):
                self.evaluate(fixture)

    def test_actual_assignments_must_be_present_scoped_and_current(self):
        for index in (0, 1):
            for change in ("missing", "scope", "role", "expired", "not_yet_assigned", "outlived"):
                fixture = SourceRightsFixture()
                assignment = fixture.assignments[index]
                if change == "missing":
                    del fixture.assignments[index]
                elif change == "scope":
                    assignment["artifact_ids"] = ["unrelated_source"]
                elif change == "role":
                    assignment["roles"] = ["systems"]
                elif change == "expired":
                    assignment["expires_at"] = stamp(NOW)
                elif change == "not_yet_assigned":
                    assignment["issued_at"] = stamp(NOW)
                else:
                    assignment["expires_at"] = stamp(NOW + datetime.timedelta(hours=1))
                with self.subTest(index=index, change=change), self.assertRaises(ops.Refused):
                    self.evaluate(fixture)

    def test_source_decision_expiry_and_trusted_clock_fail_closed(self):
        for key, value in (
            ("expires_at", stamp(NOW)),
            ("expires_at", stamp(NOW + datetime.timedelta(hours=25))),
            ("occurred_at", stamp(NOW + datetime.timedelta(minutes=1))),
            ("occurred_at", stamp(NOW) + "\n"),
        ):
            fixture = SourceRightsFixture()
            fixture.entry[key] = value
            with self.subTest(field=key, value=value), self.assertRaises(ops.Refused):
                self.evaluate(fixture)
        for clock in (None, NOW.replace(tzinfo=None), NOW.astimezone(datetime.timezone(datetime.timedelta(hours=1)))):
            with self.subTest(clock=clock), self.assertRaises(ops.Refused):
                self.evaluate(SourceRightsFixture(), now=clock)

    def test_pinned_reason_proposal_and_assignment_evidence_must_exist_and_match(self):
        for field in ("reason", "proposal", "assignment"):
            for change in ("missing", "digest", "unsafe_path"):
                fixture = SourceRightsFixture()
                source = {
                    "reason": fixture.entry["reason"],
                    "proposal": fixture.entry["proposals"][0]["source"],
                    "assignment": fixture.assignments[0]["evidence"],
                }[field]
                if change == "missing":
                    del fixture.blobs[(source["commit"], source["path"])]
                elif change == "digest":
                    source["sha256"] = "sha256:" + "0" * 64
                else:
                    source["path"] = "../SYNTHETIC_DO_NOT_ECHO.txt"
                with self.subTest(field=field, change=change):
                    with self.assertRaises(ops.Refused) as refused:
                        self.evaluate(fixture)
                    self.assertNotIn("SYNTHETIC_DO_NOT_ECHO", str(refused.exception))

    def test_source_history_is_append_only_and_rejects_stale_or_altered_heads(self):
        fixture = SourceRightsFixture()
        history = self.evaluate(fixture)
        saved = copy.deepcopy(history)
        fixture.entry.update(id="SYNTHETIC_REVISION", disposition="revise")
        result = self.evaluate(fixture, history, history[-1]["sha256"])
        self.assertEqual(history, saved)
        self.assertEqual(result[:-1], saved)
        self.assertEqual(result[-1]["previous_sha256"], history[-1]["sha256"])
        with self.assertRaises(ops.Refused):
            self.evaluate(fixture, history, ops.design.ZERO)
        history[0]["disposition"] = "decline"
        with self.assertRaises(ops.Refused):
            self.evaluate(fixture, history, saved[-1]["sha256"])

    def test_source_acceptance_neither_grants_data_access_nor_supplies_consent(self):
        self.evaluate(SourceRightsFixture())
        for role in ("research", "privacy", "research_store_owner"):
            participant, evidence, grant = fixtures()
            grant["role"] = role
            with self.subTest(role=role), self.assertRaises(ops.Refused):
                ops.require_evidence_access(participant, evidence, grant, NOW)
        for consent in ("pending", "withdrawn"):
            participant, evidence, grant = fixtures()
            participant["consent_state"] = consent
            with self.subTest(consent=consent), self.assertRaises(ops.Refused):
                ops.require_evidence_access(participant, evidence, grant, NOW)


class DataBoundaryTests(unittest.TestCase):
    def test_planted_financial_data_and_credentials_are_rejected_without_echo(self):
        participant, evidence, grant = fixtures()
        records = (
            ("participant_code", participant), ("evidence", evidence), ("access_grant", grant),
            ("aggregate_report", reported_fixture()), ("recruitment_check", recruitment()),
        )
        planted = {
            "balance_minor": 123456789, "income": "INR 123456789",
            "account": "SYNTHETIC-NOT-AN-ACCOUNT", "raw_sms": "SYNTHETIC FINANCIAL MESSAGE",
            "credential": "ghp_" + "x" * 36, "email": "fixture@example.invalid",
            "household_member": "SYNTHETIC-NOT-A-PERSON", "notes": "SYNTHETIC RAW NOTE",
        }
        for kind, record in records:
            for key, value in planted.items():
                with self.subTest(kind=kind, field=key):
                    altered = copy.deepcopy(record)
                    altered[key] = value
                    with self.assertRaises(ops.Refused) as error:
                        ops.validate(kind, altered)
                    self.assertNotIn(str(value), str(error.exception))
                    self.assertEqual(str(error.exception), "Research metadata violates its closed schema.")

    def test_existing_fields_and_nested_aggregates_cannot_hold_free_text(self):
        _, evidence, _ = fixtures()
        for key, value in (
            ("preference", "SYNTHETIC BALANCE INR 123456789"),
            ("reason_codes", ["SYNTHETIC-SECRET-" + "x" * 36]),
            ("price_choice", 123456789),
        ):
            altered = copy.deepcopy(evidence)
            altered[key] = value
            with self.assertRaises(ops.Refused):
                ops.validate("evidence", altered)
        for table in ("preference", "pricing", "sms"):
            report = reported_fixture()
            report[table]["balance_minor"] = 123456789
            with self.assertRaises(ops.Refused):
                ops.validate("aggregate_report", report)
        report = reported_fixture()
        report["preference"]["debt"] = True
        with self.assertRaises(ops.Refused):
            ops.validate_report(report, allow_synthetic=True)

    def test_strict_json_and_errors_never_echo_rejected_content(self):
        bad_values = (
            '{"SYNTHETIC-PRIVATE": 1, "SYNTHETIC-PRIVATE": 2}',
            '{"SYNTHETIC-PRIVATE": NaN}', '{"SYNTHETIC-PRIVATE": Infinity}',
            '\ufeff{"SYNTHETIC-PRIVATE": 1}', '{"SYNTHETIC-PRIVATE":',
        )
        for text in bad_values:
            with mock.patch.object(Path, "read_text", return_value=text):
                with self.assertRaises(ops.Refused) as error:
                    ops.load_json(Path("unused.json"))
            self.assertNotIn("SYNTHETIC-PRIVATE", str(error.exception))


class EvidenceAccessTests(unittest.TestCase):
    def test_expiry_boundary_and_roles(self):
        participant, evidence, grant = fixtures()
        for role in ("moderator", "analyst"):
            grant["role"] = role
            ops.require_evidence_access(participant, evidence, grant, EXPIRY - datetime.timedelta(microseconds=1))
            for now in (EXPIRY, EXPIRY + datetime.timedelta(seconds=1)):
                with self.assertRaises(ops.Refused):
                    ops.require_evidence_access(participant, evidence, grant, now)
        for role in ("recruiter", "designer", "privacy_reviewer", "legal_reviewer", "auditor", "custodian"):
            grant["role"] = role
            with self.assertRaises(ops.Refused):
                ops.require_evidence_access(participant, evidence, grant, NOW)

    def test_consent_and_withdrawal_deny_access(self):
        for key, value in (
            ("eligibility", "pending"), ("eligibility", "ineligible"),
            ("consent_state", "pending"), ("consent_state", "withdrawn"),
            ("consented_at", None), ("consent_expires_at", None), ("withdrawal_until", None),
            ("withdrawn_at", stamp(NOW)), ("consent_version", "unreviewed"),
        ):
            with self.subTest(field=key, replacement=value):
                participant, evidence, grant = fixtures()
                participant[key] = value
                with self.assertRaises(ops.Refused):
                    ops.require_evidence_access(participant, evidence, grant, NOW)
        for state in ("withdrawn", "deleted"):
            participant, evidence, grant = fixtures()
            evidence["state"] = state
            with self.assertRaises(ops.Refused):
                ops.require_evidence_access(participant, evidence, grant, NOW)

    def test_cross_study_binding_wrong_resource_revocation_and_origin_fail(self):
        for index, key, value in (
            (2, "study_id", "T-RES-02"), (1, "study_id", "T-RES-02"),
            (1, "participant_code", "P-" + "b" * 32), (2, "resource", "identity"),
            (2, "role", "unknown"), (2, "revoked", True), (2, "revoked", "false"),
            (1, "data_origin", "restricted_live"),
        ):
            records = fixtures()
            records[index][key] = value
            with self.assertRaises(ops.Refused):
                ops.require_evidence_access(*records, NOW)

    def test_retention_extension_and_malformed_or_future_times_fail(self):
        for index, key, value in (
            (1, "expires_at", stamp(EXPIRY + datetime.timedelta(seconds=1))),
            (0, "consent_expires_at", stamp(EXPIRY + datetime.timedelta(seconds=1))),
            (2, "expires_at", stamp(EXPIRY + datetime.timedelta(seconds=1))),
            (1, "expires_at", stamp(START)), (2, "expires_at", stamp(START)),
            (1, "collected_at", stamp(NOW + datetime.timedelta(seconds=1))),
            (0, "consented_at", stamp(NOW)), (2, "issued_at", stamp(NOW + datetime.timedelta(seconds=1))),
            (1, "expires_at", "2000-02-30T00:00:00Z"), (1, "expires_at", "2000-01-15T00:00:00"),
        ):
            records = fixtures()
            records[index][key] = value
            with self.assertRaises(ops.Refused):
                ops.require_evidence_access(*records, NOW)
        for now in (None, NOW.replace(tzinfo=None), NOW.astimezone(datetime.timezone(datetime.timedelta(hours=1)))):
            with self.assertRaises(ops.Refused):
                ops.require_evidence_access(*fixtures(), now)

    def test_independently_shortened_consent_or_grant_is_enforced(self):
        participant, evidence, grant = fixtures()
        grant["expires_at"] = stamp(NOW)
        with self.assertRaises(ops.Refused):
            ops.require_evidence_access(participant, evidence, grant, NOW)
        participant["consent_expires_at"] = stamp(NOW)
        with self.assertRaises(ops.Refused):
            ops.require_evidence_access(participant, evidence, grant, NOW)

    def test_withdrawal_window_cannot_be_shortened_or_outlive_evidence(self):
        for value in (
            stamp(START + datetime.timedelta(days=14) - datetime.timedelta(seconds=1)),
            stamp(START + datetime.timedelta(days=28, seconds=1)),
        ):
            participant, evidence, grant = fixtures()
            participant["withdrawal_until"] = value
            with self.assertRaises(ops.Refused):
                ops.require_evidence_access(participant, evidence, grant, NOW)
        participant, evidence, grant = fixtures()
        evidence["expires_at"] = stamp(WITHDRAWAL)
        with self.assertRaises(ops.Refused):
            ops.require_evidence_access(participant, evidence, grant, NOW)


class RecruitmentTests(unittest.TestCase):
    def test_recruitment_control_positive_is_only_synthetic(self):
        case = recruitment()
        ops.require_safe_recruitment(case)
        case["data_origin"] = "restricted_live"
        with self.assertRaises(ops.Refused):
            ops.require_safe_recruitment(case)

    def test_household_disclosure_paths_are_refused(self):
        for key in ("personal_network", "household_referral", "shared_contact", "paired_session", "household_disclosure_requested"):
            case = recruitment()
            case[key] = True
            with self.assertRaises(ops.Refused):
                ops.require_safe_recruitment(case)

    def test_recruitment_missing_safeguards_are_refused(self):
        for key in ("reviewed_route", "private_opt_in", "private_channel", "private_context", "stop_available"):
            case = recruitment()
            case[key] = False
            with self.assertRaises(ops.Refused):
                ops.require_safe_recruitment(case)
            del case[key]
            with self.assertRaises(ops.Refused):
                ops.require_safe_recruitment(case)

    def test_specialist_review_cannot_be_omitted(self):
        case = recruitment()
        case["study_kind"] = "household_coercion"
        with self.assertRaises(ops.Refused):
            ops.require_safe_recruitment(case)
        case["specialist_reviewed"] = True
        ops.require_safe_recruitment(case)


class OrderEffectTests(unittest.TestCase):
    def test_empty_small_or_imbalanced_samples_are_inconclusive(self):
        for de, ed in (
            (counts(), counts()), (counts(debt=5), counts(debt=6)),
            (counts(debt=4), counts(debt=8)),
        ):
            self.assertEqual(ops.comparison_decision(de, ed), "inconclusive")

    def test_exact_support_boundary_and_dissent_are_not_relabelled(self):
        self.assertEqual(ops.comparison_decision(counts(debt=5, expense=3), counts(debt=5, expense=3)), "candidate_support")
        self.assertEqual(ops.comparison_decision(counts(debt=4, expense=4), counts(debt=4, expense=4)), "not_supported")
        self.assertEqual(ops.comparison_decision(counts(debt=3, expense=5), counts(debt=3, expense=5)), "not_supported")
        self.assertEqual(ops.comparison_decision(counts(debt=4, expense=3), counts(debt=4, expense=2)), "inconclusive")

    def test_order_flip_and_exact_25_point_gap_are_visible(self):
        for de, ed in (
            (counts(debt=4, expense=3, unsure=1), counts(debt=3, expense=4, unsure=1)),
            (counts(debt=5, expense=3), counts(debt=3, expense=3, equal=2)),
        ):
            self.assertEqual(ops.comparison_decision(de, ed), "order_sensitive")
            self.assertEqual(ops.comparison_decision(ed, de), "order_sensitive")

    def test_skips_stay_in_denominators_and_invalid_counts_fail(self):
        self.assertEqual(ops.comparison_decision(counts(debt=3, expense=1, skipped=4), counts(debt=3, expense=1, skipped=4)), "not_supported")
        for de, ed in (
            (counts(debt=-1), counts()), (counts(debt=True), counts(debt=7)),
            (counts(debt=9), counts(debt=7)), (counts(debt=8), counts(debt=9)),
        ):
            with self.assertRaises(ops.Refused):
                ops.comparison_decision(de, ed)


class AggregateTests(unittest.TestCase):
    def test_synthetic_aggregates_are_never_published_as_findings(self):
        report = reported_fixture()
        with self.assertRaises(ops.Refused):
            ops.validate_report(report)
        ops.validate_report(report, allow_synthetic=True)

    def test_small_cells_complements_and_mismatched_denominators_fail(self):
        for table, values in (
            ("preference", counts(debt=12, expense=4)),
            ("preference", counts(debt=8, expense=7)),
            ("pricing", {"paid": 12, "free": 4, "neither": 0, "unsure": 0, "skipped": 0}),
            ("sms", {"allow": 12, "deny": 4, "unsure": 0, "skipped": 0}),
        ):
            report = reported_fixture()
            report[table] = values
            with self.assertRaises(ops.Refused):
                ops.validate_report(report, allow_synthetic=True)
        report = reported_fixture()
        report["withdrawal_count"] = 1
        with self.assertRaises(ops.Refused):
            ops.validate_report(report, allow_synthetic=True)

    def test_whole_table_suppression_is_explicit(self):
        report = reported_fixture()
        report["preference"] = None
        with self.assertRaises(ops.Refused):
            ops.validate_report(report, allow_synthetic=True)
        report["withheld_tables"] = ["preference"]
        ops.validate_report(report, allow_synthetic=True)
        report["preference"] = counts(debt=8, expense=8)
        with self.assertRaises(ops.Refused):
            ops.validate_report(report, allow_synthetic=True)

    def test_reported_counts_and_method_statuses_cannot_conflict(self):
        for key, value in (
            ("withdrawal_count", 5), ("order_effect_status", "pending"),
            ("coverage_status", "pending"), ("participant_count", 0),
        ):
            report = reported_fixture()
            report[key] = value
            with self.assertRaises(ops.Refused):
                ops.validate_report(report, allow_synthetic=True)

    def test_findings_require_disposition_without_fabricating_tickets(self):
        report = reported_fixture()
        finding = {
            "id": "F-001", "direction": "contradictory", "area": "sms", "decision": "pending",
            "reason_code": "review_pending", "issue_reference": None,
        }
        report["finding_dispositions"] = [finding]
        with self.assertRaises(ops.Refused):
            ops.validate_report(report, allow_synthetic=True)
        report["undispositioned_finding_count"] = 1
        ops.validate_report(report, allow_synthetic=True)
        report["decision"] = "no_change"
        with self.assertRaises(ops.Refused):
            ops.validate_report(report, allow_synthetic=True)
        report["decision"] = "pending"
        finding["decision"] = "ticketed"
        report["undispositioned_finding_count"] = 0
        with self.assertRaises(ops.Refused):
            ops.validate_report(report, allow_synthetic=True)


if __name__ == "__main__":
    unittest.main()
