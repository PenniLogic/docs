"""Source-only checks for original Docs52's declined bureau decision, not runtime or legal acceptance."""

import copy
import hashlib
import importlib.util
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("bureau_check_docs", ROOT / "scripts" / "check_docs.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
adr = checks.load_check("validate_adr_layout")
schema_check = checks.load_check("check_client_states")

RECORD = ROOT / "adr" / "ADR-024.md"
DATA = ROOT / "adr" / "credit-bureau-consequences.json"
SCHEMA = ROOT / "adr" / "credit-bureau-consequences.schema.json"
TICKET = "T-ADR-BUREAU-11"
REOPENING_IDS = {
    "REOPEN-NEED", "REOPEN-PROVIDER-LEGAL", "REOPEN-CONSENT-ROLE", "REOPEN-ECONOMICS",
    "REOPEN-SECURITY-ERASURE", "REOPEN-SHARING", "REOPEN-ADVICE",
}
NO_SCORE_PROMISE = "Debt-first progress does not promise a bureau score improvement."


def validate_data(data, schema):
    schema_check.validate_schema(data, schema)
    identifiers = [item["id"] for item in data["reopening"]["required_evidence"]]
    if len(set(identifiers)) != len(identifiers) or set(identifiers) != REOPENING_IDS:
        raise ValueError("Reopening evidence identifiers must cover each required gate exactly once")


def validate_record(document, data_bytes, schema_bytes):
    data = adr.strict_json_loads(data_bytes.decode("utf-8"), DATA.name)
    schema = adr.strict_json_loads(schema_bytes.decode("utf-8"), SCHEMA.name)
    validate_data(data, schema)
    source = adr.parse_source(RECORD.name, document.encode("utf-8"))
    if source.number != data["record"] or source.ticket != data["ticket"] or source.date != data["decision_date"]:
        raise ValueError("Decision record, ticket and date must match the consequences")
    for label, raw in (("Consequences", data_bytes), ("Schema", schema_bytes)):
        binding = re.search(rf"\*\*{label} SHA-256:\*\* `([0-9a-f]{{64}})`", document)
        if binding is None or binding[1] != hashlib.sha256(raw).hexdigest():
            raise ValueError(f"{label} differs from its dated ADR binding")
    version = f'{data["artifact_id"]}@{data["consequences_version"]}'
    if f"`{version}`" not in document:
        raise ValueError("The ADR must name its exact consequences version")
    for identifier in [*REOPENING_IDS, data["future_implementation"]["activation_gate_id"]]:
        if f"`{identifier}`" not in document:
            raise ValueError(f"Missing named reopening or activation gate: {identifier}")
    if NO_SCORE_PROMISE not in re.sub(r"\s+", " ", document):
        raise ValueError("The debt-first progress non-promise must remain explicit")


class PublishedBureauDecisionTests(unittest.TestCase):
    def test_declined_artifact_schema_and_dated_record_agree(self):
        validate_record(RECORD.read_text(encoding="utf-8"), DATA.read_bytes(), SCHEMA.read_bytes())

    def test_original_ticket_allocation_index_and_registry_agree(self):
        layout = adr.validate_sources(ROOT)
        self.assertEqual(layout.allocations["ADR-024"].ticket, TICKET)
        self.assertEqual(layout.sources["ADR-024"].ticket, TICKET)
        self.assertEqual(layout.sources["ADR-024"].status, "ACCEPTED")
        adr.check_layout(ROOT)
        registry = adr.load_json_document(ROOT / "adr" / "accepted-records.json")
        entry = next(item for item in registry["items"] if item["number"] == "ADR-024")
        raw = RECORD.read_bytes()
        self.assertEqual(entry["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(entry["bytes"], len(raw))
        self.assertEqual(entry["date"], layout.sources["ADR-024"].date)

    def test_machine_readable_consequences_allow_no_bureau_surface(self):
        data = adr.load_json_document(DATA)
        self.assertEqual(data["scope"], "DECLINED")
        self.assertEqual(set(data["allowed"]), {
            "collection_channels", "endpoints", "schema_fields", "wire_fields", "storage_objects",
            "sharing_categories", "score_narratives", "score_improvement_advice",
        })
        self.assertTrue(all(value == [] for value in data["allowed"].values()))
        self.assertEqual(data["sharing"], {
            "category_status": "NOT_AVAILABLE", "default": "DENY",
            "family_access": "NONE", "consent_override_allowed": False,
        })
        self.assertEqual(data["delivery"]["blocking_tickets"], [])
        self.assertEqual(data["delivery"]["implementation_tickets"], [])
        self.assertIs(data["delivery"]["runtime_enforcement_claimed"], False)

    def test_authority_is_coordinator_default_not_bespoke_owner_attestation(self):
        data = adr.load_json_document(DATA)
        self.assertEqual(data["authority"], {
            "selection": "COORDINATOR_SELECTED_DEFAULT", "basis": "DELEGATED_AUTONOMOUS_DELIVERY",
            "specific_owner_bureau_attestation": False,
        })
        self.assertEqual(data["effective_on"], "PROTECTED_MERGE")

    def test_reopening_does_not_enable_implementation_or_relax_permanent_non_goals(self):
        data = adr.load_json_document(DATA)
        self.assertEqual({item["id"] for item in data["reopening"]["required_evidence"]}, REOPENING_IDS)
        self.assertIs(data["reopening"]["automatic"], False)
        self.assertIs(data["reopening"]["new_explicit_superseding_decision_required"], True)
        self.assertEqual(data["future_implementation"]["default"], "OFF")
        self.assertIs(data["future_implementation"]["created_only_after_new_merged_decision"], True)
        for key in ("score_improvement_claims", "bureau_score_inference_from_debt_progress",
                    "lending", "loan_brokering", "credit_referral"):
            self.assertEqual(data["advice"][key], "PROHIBITED")

    def test_new_artifacts_use_ascii_lf_and_exact_final_newline(self):
        for path in (DATA, SCHEMA, Path(__file__)):
            with self.subTest(path=path.name):
                raw = path.read_bytes()
                raw.decode("ascii")
                self.assertNotIn(b"\r", raw)
                self.assertTrue(raw.endswith(b"\n"))
                self.assertFalse(raw.endswith(b"\n\n"))


class ContradictoryBureauStateTests(unittest.TestCase):
    def setUp(self):
        self.data = adr.load_json_document(DATA)
        self.schema = adr.load_json_document(SCHEMA)

    def rejected(self, changes):
        data = copy.deepcopy(self.data)
        changes(data)
        with self.assertRaises(ValueError):
            validate_data(data, self.schema)

    def test_enabled_or_stale_scope_and_versions_are_rejected(self):
        for key, value in (("scope", "ALLOWED"), ("schema_version", 2),
                           ("schema_version", True), ("consequences_version", "0.9.0"),
                           ("consequences_version", "1.0.1"), ("record", "ADR-023"),
                           ("ticket", "T-ADR-ENT-09")):
            with self.subTest(key=key, value=value):
                self.rejected(lambda data: data.__setitem__(key, value))

    def test_every_nonempty_bureau_allowlist_is_rejected(self):
        for key in self.data["allowed"]:
            with self.subTest(key=key):
                self.rejected(lambda data: data["allowed"][key].append("synthetic-forbidden-identifier"))

    def test_collection_import_fetch_storage_cache_and_inference_are_rejected(self):
        for key in ("collect", "import", "fetch", "store", "cache", "derive"):
            with self.subTest(key=key):
                self.rejected(lambda data: data["data"].__setitem__(key, "ALLOWED"))

    def test_zero_day_retention_or_bureau_crypto_shredding_cannot_authorize_a_pull(self):
        self.rejected(lambda data: data["data"].__setitem__("retention_period_days", 0))
        self.rejected(lambda data: data["data"].__setitem__("retention_status", "ACTIVE"))
        self.rejected(lambda data: data["data"].__setitem__("crypto_shredding", "REQUIRED"))

    def test_provider_role_consent_cadence_cost_and_metrics_are_not_invented(self):
        for key in self.data["provider"]:
            with self.subTest(key=key):
                self.rejected(lambda data: data["provider"].__setitem__(key, "synthetic-provider-setting"))

    def test_family_consent_or_membership_cannot_override_unavailable_category(self):
        for key, value in (("category_status", "AVAILABLE"), ("default", "ALLOW"),
                           ("family_access", "MEMBERS"), ("consent_override_allowed", True),
                           ("consent_override_allowed", 0)):
            with self.subTest(key=key):
                self.rejected(lambda data: data["sharing"].__setitem__(key, value))

    def test_score_narrative_advice_and_credit_business_exceptions_are_rejected(self):
        for key in self.data["advice"]:
            with self.subTest(key=key):
                self.rejected(lambda data: data["advice"].__setitem__(key, "ALLOWED"))

    def test_fabricated_authority_runtime_acceptance_and_follow_up_tickets_are_rejected(self):
        self.rejected(lambda data: data["authority"].__setitem__("specific_owner_bureau_attestation", True))
        self.rejected(lambda data: data["delivery"].__setitem__("runtime_enforcement_claimed", True))
        self.rejected(lambda data: data["delivery"]["blocking_tickets"].append("synthetic-ticket"))
        self.rejected(lambda data: data["delivery"]["implementation_tickets"].append("synthetic-ticket"))
        self.rejected(lambda data: data["delivery"].__setitem__("future_sprint_assignment_changed", True))

    def test_missing_or_duplicate_reopening_evidence_is_rejected(self):
        self.rejected(lambda data: data["reopening"]["required_evidence"].pop())
        self.rejected(lambda data: data["reopening"]["required_evidence"][0].__setitem__(
            "id", data["reopening"]["required_evidence"][1]["id"]
        ))
        for key in ("all_evidence_required", "new_explicit_superseding_decision_required",
                    "consequences_version_bump_required"):
            with self.subTest(key=key):
                self.rejected(lambda data: data["reopening"].__setitem__(key, False))
        self.rejected(lambda data: data["reopening"].__setitem__("automatic", True))

    def test_default_on_or_unreviewed_future_activation_is_rejected(self):
        self.rejected(lambda data: data["future_implementation"].__setitem__("default", "ON"))
        self.rejected(lambda data: data["future_implementation"].__setitem__(
            "created_only_after_new_merged_decision", False
        ))
        self.rejected(lambda data: data["future_implementation"].__setitem__(
            "reopening_alone_enables_nothing", False
        ))
        self.rejected(lambda data: data["future_implementation"]["required_activation_checks"].pop())

    def test_unknown_optional_or_nested_bureau_fields_are_rejected(self):
        self.rejected(lambda data: data.__setitem__("optional_score", None))
        self.rejected(lambda data: data["allowed"].__setitem__("manual_score_entry", []))

    def test_duplicate_json_keys_are_rejected_by_existing_adr_parser(self):
        text = DATA.read_text(encoding="utf-8").replace(
            '"scope": "DECLINED"', '"scope": "DECLINED", "scope": "ALLOWED"', 1
        )
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            adr.strict_json_loads(text, DATA.name)

    def test_unversioned_consequence_or_schema_edits_break_dated_record_bindings(self):
        document = RECORD.read_text(encoding="utf-8")
        for data_raw, schema_raw, label in (
            (DATA.read_bytes() + b" ", SCHEMA.read_bytes(), "Consequences"),
            (DATA.read_bytes(), SCHEMA.read_bytes() + b" ", "Schema"),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, f"{label} differs"):
                    validate_record(document, data_raw, schema_raw)

    def test_stale_date_or_missing_non_promise_is_rejected(self):
        document = RECORD.read_text(encoding="utf-8")
        stale = document.replace("2026-10-04", "2026-10-03")
        with self.assertRaisesRegex(ValueError, "date must match"):
            validate_record(stale, DATA.read_bytes(), SCHEMA.read_bytes())
        with self.assertRaisesRegex(ValueError, "non-promise"):
            validate_record(document.replace(NO_SCORE_PROMISE, ""), DATA.read_bytes(), SCHEMA.read_bytes())


if __name__ == "__main__":
    unittest.main()
