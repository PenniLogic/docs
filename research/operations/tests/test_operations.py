"""SYNTHETIC SOFTWARE FIXTURES ONLY. No people, sessions, consents or approvals."""

import contextlib
import copy
import datetime
import importlib.util
import io
from pathlib import Path
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parents[1]
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
        altered["dependency"]["accepted"] = True
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
