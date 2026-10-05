"""Offline #65 preparation and synthetic policy checks; no store, contact or approval."""

import datetime
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location(
    "research_schema_subset", ROOT / "scripts" / "check_threat_model.py"
)
schema_subset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schema_subset)


class Refused(ValueError):
    """A fixed rule message that never includes rejected participant content."""


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Refused("Duplicate JSON key refused.")
            result[key] = value
        return result

    def invalid_constant(value):
        raise Refused("Non-JSON numeric constant refused.")

    try:
        return json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=unique,
            parse_constant=invalid_constant,
        )
    except (OSError, UnicodeError, ValueError):
        raise Refused("Research metadata is not readable, unique UTF-8 JSON.") from None


SCHEMA = load_json(HERE / "schema.json")
PLAN_RULES = SCHEMA["definitions"]["research_plan"]["properties"]
RETENTION_HOURS = PLAN_RULES["retention_hours"]["properties"]["coded_evidence"]["const"]
WITHDRAWAL_DAYS = PLAN_RULES["withdrawal_days_after_field_window"]["const"]
FIELD_DAYS = PLAN_RULES["field_window_days"]["const"]


def validate(kind, value):
    if kind not in SCHEMA["definitions"]:
        raise Refused("Unknown research record kind.")
    try:
        schema_subset.validate_schema(value, schema_subset.definition(SCHEMA, kind))
    except ValueError:
        # The shared validator's diagnostic can contain the rejected value.
        raise Refused("Research metadata violates its closed schema.") from None


def timestamp(value):
    validate("timestamp", value)
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        raise Refused("Invalid UTC calendar timestamp.") from None


def require_clock(now):
    if not isinstance(now, datetime.datetime) or now.tzinfo is None:
        raise Refused("An aware UTC clock is required.")
    if now.utcoffset() != datetime.timedelta(0):
        raise Refused("An aware UTC clock is required.")


def require_evidence_access(participant, evidence, grant, now):
    """Check metadata only; caller identity/grants/storage are not authenticated here."""
    require_clock(now)
    for kind, value in (
        ("participant_code", participant), ("evidence", evidence), ("access_grant", grant)
    ):
        validate(kind, value)
    if len({record["study_id"] for record in (participant, evidence, grant)}) != 1:
        raise Refused("Cross-study access refused.")
    if len({record["data_origin"] for record in (participant, evidence, grant)}) != 1:
        raise Refused("Mixed fixture and live metadata refused.")
    if participant["participant_code"] != evidence["participant_code"]:
        raise Refused("Participant binding mismatch.")
    if participant["eligibility"] != "eligible":
        raise Refused("Eligibility is not affirmed.")
    if (participant["consent_state"] != "granted"
            or participant["consented_at"] is None
            or participant["consent_expires_at"] is None
            or participant["withdrawal_until"] is None
            or participant["withdrawn_at"] is not None):
        raise Refused("Affirmative, current, unwithdrawn consent is required.")
    if evidence["state"] != "active":
        raise Refused("Withdrawn or deleted evidence is unreadable.")
    if grant["role"] not in {"moderator", "analyst"} or grant["revoked"]:
        raise Refused("Evidence access role or grant refused.")

    consented = timestamp(participant["consented_at"])
    consent_expiry = timestamp(participant["consent_expires_at"])
    withdrawal_until = timestamp(participant["withdrawal_until"])
    collected = timestamp(evidence["collected_at"])
    evidence_expiry = timestamp(evidence["expires_at"])
    issued = timestamp(grant["issued_at"])
    grant_expiry = timestamp(grant["expires_at"])
    maximum = collected + datetime.timedelta(hours=RETENTION_HOURS)
    if not consented <= collected <= now or issued > now:
        raise Refused("Consent, collection or grant chronology refused.")
    if not collected < evidence_expiry <= maximum or not collected < consent_expiry <= maximum:
        raise Refused("Retention interval exceeds the proposed bound.")
    if not (collected + datetime.timedelta(days=WITHDRAWAL_DAYS)
            <= withdrawal_until <= collected + datetime.timedelta(days=WITHDRAWAL_DAYS + FIELD_DAYS)):
        raise Refused("Withdrawal window is outside the frozen proposal.")
    if withdrawal_until >= min(evidence_expiry, consent_expiry):
        raise Refused("Retention must cover withdrawal processing before synthesis.")
    if not issued < grant_expiry <= min(evidence_expiry, consent_expiry):
        raise Refused("Grant must expire within evidence and consent bounds.")
    if now >= min(evidence_expiry, consent_expiry, grant_expiry):
        raise Refused("Expired evidence, consent or grant is unreadable.")


def require_safe_recruitment(case):
    """Exercise synthetic tabletop decisions, not a live recruitment authorization."""
    validate("recruitment_check", case)
    required = ("reviewed_route", "private_opt_in", "private_channel", "private_context", "stop_available")
    forbidden = (
        "personal_network", "household_referral", "shared_contact",
        "paired_session", "household_disclosure_requested",
    )
    if not all(case[key] for key in required) or any(case[key] for key in forbidden):
        raise Refused("Independent private recruitment safeguards are not met.")
    if case["study_kind"] == "household_coercion" and not case["specialist_reviewed"]:
        raise Refused("Qualified household/coercion specialist review is required.")


def comparison_decision(de, ed):
    """Proposed integer decision rules on synthetic or restricted aggregate counts."""
    validate("preference_counts", de)
    validate("preference_counts", ed)
    n_de, n_ed = sum(de.values()), sum(ed.values())
    n = n_de + n_ed
    if n > 16 or max(n_de, n_ed) > 8:
        raise Refused("Counts exceed the frozen session allocation.")
    if n < 12 or min(n_de, n_ed) < 5:
        return "inconclusive"
    opposite_leaders = (de["debt"] - de["expense"]) * (ed["debt"] - ed["expense"]) < 0
    rate_gap = abs(de["debt"] * n_ed - ed["debt"] * n_de)
    if opposite_leaders or 4 * rate_gap >= n_de * n_ed:
        return "order_sensitive"
    debt, expense = de["debt"] + ed["debt"], de["expense"] + ed["expense"]
    if debt <= expense or 2 * debt <= n:
        return "not_supported"
    if 8 * debt >= 5 * n and 2 * de["debt"] > n_de and 2 * ed["debt"] > n_ed:
        return "candidate_support"
    return "inconclusive"


def validate_report(report, *, allow_synthetic=False):
    """Check aggregate shape/small cells only, never certify provenance or anonymity."""
    validate("aggregate_report", report)
    measurements = (
        "participant_count", "preference", "pricing", "sms", "withdrawal_count",
        "evidence_age_days", "undispositioned_finding_count",
    )
    if report["execution_state"] == "UNRUN":
        if (report["data_origin"] != "pending"
                or any(report[key] is not None for key in measurements)
                or report["withheld_tables"] or report["finding_dispositions"]
                or report["order_effect_status"] != "pending"
                or report["coverage_status"] != "pending"
                or report["decision"] != "pending"
                or "unrun" not in report["limitations"]):
            raise Refused("An unrun study must have only pending, null observations.")
        return
    allowed_origins = {"genuine_sessions"}
    if allow_synthetic:
        allowed_origins.add("synthetic_fixture")
    if report["data_origin"] not in allowed_origins:
        raise Refused("Reported evidence needs declared provenance; fixtures are not findings.")
    n = report["participant_count"]
    if n is None or n < 5:
        raise Refused("A report count is missing or below the privacy floor.")
    if "unrun" in report["limitations"]:
        raise Refused("Reported and unrun states conflict.")
    if report["order_effect_status"] == "pending" or report["coverage_status"] == "pending":
        raise Refused("Reported evidence must state order and coverage limitations.")
    for table, kind in (("preference", "preference_counts"), ("pricing", "price_counts"), ("sms", "sms_counts")):
        counts = report[table]
        if counts is None:
            if table not in report["withheld_tables"]:
                raise Refused("Missing aggregate table needs explicit withholding.")
            continue
        if table in report["withheld_tables"]:
            raise Refused("A withheld table must not expose counts.")
        validate(kind, counts)
        if sum(counts.values()) != n:
            raise Refused("Aggregate denominator mismatch.")
        if any(0 < count < 5 for count in counts.values()):
            raise Refused("Suppress the entire related table, not just the small cell.")
    withdrawals = report["withdrawal_count"]
    if withdrawals is not None and 0 < withdrawals < 5:
        raise Refused("Small operational counts must be withheld.")
    if withdrawals is not None and n + withdrawals > 16:
        raise Refused("Participant and withdrawal totals exceed the session allocation.")
    findings = report["finding_dispositions"]
    if len({finding["id"] for finding in findings}) != len(findings):
        raise Refused("Duplicate finding disposition.")
    for finding in findings:
        if (finding["decision"] == "ticketed") != (finding["issue_reference"] is not None):
            raise Refused("A ticketed disposition requires its actual issue reference.")
        if finding["decision"] != "pending" and finding["reason_code"] == "review_pending":
            raise Refused("A resolved disposition needs a reason.")
    pending = sum(finding["decision"] == "pending" for finding in findings)
    if report["undispositioned_finding_count"] != pending:
        raise Refused("Undispositioned finding count disagrees with the register.")
    if report["decision"] == "no_change" and pending:
        raise Refused("No-change cannot silently ignore pending findings.")


def check_preparation(plan, report):
    validate("research_plan", plan)
    if plan["planned_orders"] != ["DE", "ED", "ED", "DE"] * 4:
        raise Refused("Counterbalanced order differs from the frozen proposal.")
    required_hours = (
        plan["field_window_days"] + plan["withdrawal_days_after_field_window"] + plan["synthesis_days"]
    ) * 24
    if plan["retention_hours"]["coded_evidence"] != required_hours:
        raise Refused("Retention, withdrawal and synthesis windows disagree.")
    expected = set(SCHEMA["definitions"]["limitation_code"]["enum"])
    if {item["code"] for item in plan["limitations"]} != expected:
        raise Refused("A planned limitation is absent or duplicated.")
    validate_report(report)
    if report["execution_state"] != "UNRUN" or set(report["limitations"]) != expected:
        raise Refused("The committed preparation report must stay unrun with its limitations.")


def main():
    try:
        if len(sys.argv) != 1:
            raise Refused("This source-only checker accepts no participant files or arguments.")
        plan = load_json(HERE / "concept-study.plan.json")
        report = load_json(HERE / "concept-study.report.json")
        check_preparation(plan, report)
    except Refused as error:
        print(f"Research preparation refused: {error}", file=sys.stderr)
        return 1
    print("Research preparation source valid; contact BLOCKED, study UNRUN, participant_count null.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
