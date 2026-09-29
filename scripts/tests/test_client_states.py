"""Tests for the shared client state taxonomy (T-UX-01, PenniLogic/docs#1).

Each acceptance criterion of the ticket maps to a named test below, and every check is proven to
bite with a planted defect. These tests prove the published data, schema and document; they are
not a client build and claim no client coverage.
"""

import copy
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "scripts" / "check_client_states.py"
spec = importlib.util.spec_from_file_location("check_client_states", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

DATA = module.load_json(ROOT / module.DATA)
SCHEMA = module.load_json(ROOT / module.SCHEMA)
DOCUMENT = (ROOT / module.DOCUMENT).read_text(encoding="utf-8")
STATES = {state["id"]: state for state in DATA["states"]}


def taxonomy():
    return copy.deepcopy(DATA)


def state(data, state_id):
    return next(item for item in data["states"] if item["id"] == state_id)


def validate(data, document=DOCUMENT, schema=SCHEMA):
    module.validate_schema(data, schema)
    return module.check_taxonomy(data, document)


class PublishedFilesTests(unittest.TestCase):
    def test_published_data_validates_against_schema_and_rules(self):
        summary = module.validate_taxonomy(ROOT)
        self.assertEqual(summary["states"], 8)
        self.assertEqual(summary["worked_examples"], 3)
        self.assertEqual(summary["taxonomy_version"], DATA["taxonomy_version"])

    def test_main_reports_success(self):
        self.assertEqual(module.main(), 0)

    def test_main_reports_failure_for_missing_files(self):
        original = module.ROOT
        module.ROOT = Path(tempfile.gettempdir()) / "pennilogic-missing-taxonomy"
        try:
            self.assertEqual(module.main(), 1)
        finally:
            module.ROOT = original

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "dup.json"
            target.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
                module.load_json(target)

    def test_data_file_uses_lf_line_endings_and_utf8(self):
        raw = (ROOT / module.DATA).read_bytes()
        self.assertNotIn(b"\r\n", raw)
        raw.decode("utf-8")


class AcceptanceCriteriaTests(unittest.TestCase):
    """One test per acceptance criterion in PenniLogic/docs#1."""

    def test_every_state_has_definition_condition_content_and_one_recovery_action(self):
        self.assertEqual(set(STATES), set(module.REQUIRED_STATES))
        for item in DATA["states"]:
            self.assertTrue(item["definition"].strip(), item["id"])
            self.assertTrue(item["triggering_condition"].strip(), item["id"])
            self.assertTrue(item["required_content"], item["id"])
            self.assertTrue(item["forbidden_content"], item["id"])
            # The recovery action is a single object, never a list, so a second one is unexpressible.
            self.assertIsInstance(item["recovery_action"], dict, item["id"])
            self.assertTrue(item["recovery_action"]["label"].strip(), item["id"])

    def test_offline_stale_and_error_degraded_are_observably_different(self):
        pairs = {frozenset(item["states"]): item for item in DATA["distinctions"]}
        for first, second in module.REQUIRED_DISTINCTIONS:
            distinction = pairs[frozenset((first, second))]
            self.assertNotEqual(distinction["data_shown"][first], distinction["data_shown"][second])
            self.assertNotEqual(STATES[first]["data_display"], STATES[second]["data_display"])
            self.assertIn(first, distinction["observable_difference"])
            self.assertIn(second, distinction["observable_difference"])
        self.assertEqual(STATES["offline"]["data_display"], "none")
        self.assertEqual(STATES["stale"]["data_display"], "shown_marked")
        self.assertEqual(STATES["error"]["data_display"], "none")
        self.assertEqual(STATES["degraded"]["data_display"], "shown")
        self.assertNotEqual(STATES["offline"]["copy"]["headline"], STATES["stale"]["copy"]["headline"])
        self.assertNotEqual(STATES["error"]["copy"]["headline"], STATES["degraded"]["copy"]["headline"])

    def test_identifiers_are_machine_readable_and_distinct_from_display_strings(self):
        identifier = re.compile(r"^[a-z][a-z0-9_]*$")
        for item in DATA["states"]:
            self.assertRegex(item["id"], identifier)
            self.assertNotEqual(item["id"], item["copy"]["headline"])
            self.assertEqual(item["signal"], "client_state." + item["id"])
        self.assertEqual(sorted(DATA["precedence"]), sorted(STATES))
        self.assertEqual(module.REQUIRED_STATES, (
            "empty", "loading", "error", "offline", "stale",
            "permission_denied", "quota_exceeded", "degraded",
        ))

    def test_copy_rules_forbid_blame_invented_cause_and_require_same_wording(self):
        rules = {rule["id"]: rule["rule"] for rule in DATA["copy_rules"]}
        self.assertIn("never attributes fault to the user", rules["no_blame"])
        self.assertIn("states only what the client knows", rules["no_invented_cause"])
        self.assertIn("same canonical copy on Android, web and admin", rules["same_wording"])
        for term in ("you failed", "you denied", "wrong", "because"):
            self.assertIn(term, DATA["forbidden_terms"])
        for item in DATA["states"]:
            for text in module.canonical_strings(item):
                self.assertIsNone(module.forbidden_term(text, DATA["forbidden_terms"]), text)

    def test_permission_denied_keeps_surface_usable_and_hides_data(self):
        denied = STATES["permission_denied"]
        self.assertEqual(denied["data_display"], "hidden")
        self.assertIs(denied["guarantees"]["rest_of_surface_usable"], True)
        self.assertIs(denied["guarantees"]["discloses_hidden_data"], False)
        self.assertIn("Everything else keeps working.", denied["copy"]["body"])
        sharing = denied["copy"]["variants"]["sharing"]
        self.assertFalse(module.PLACEHOLDER.search(sharing["headline"] + sharing["body"]))
        self.assertEqual(sharing["headline"], denied["copy"]["headline"])
        self.assertEqual(
            {cause["id"] for cause in denied["causes"]}, {"device", "plan", "sharing", "role"}
        )
        self.assertTrue(
            any("reveal" in line and "exists" in line for line in denied["forbidden_content"])
        )

    def test_quota_exceeded_states_what_remains_available(self):
        quota = STATES["quota_exceeded"]
        self.assertIs(quota["guarantees"]["states_what_remains_available"], True)
        self.assertEqual(quota["data_display"], "shown")
        self.assertIn("{still_available}", quota["copy"]["body"])
        self.assertTrue(any("still available" in line for line in quota["required_content"]))

    def test_three_worked_examples_cover_the_named_high_risk_surfaces(self):
        examples = {example["id"]: example for example in DATA["worked_examples"]}
        self.assertEqual(set(examples), set(module.REQUIRED_EXAMPLES))
        self.assertEqual(examples["capture_surface_permission_denied"]["state"], "permission_denied")
        self.assertEqual(examples["capture_surface_permission_denied"]["cause"], "device")
        self.assertEqual(examples["ai_surface_quota_exceeded"]["state"], "quota_exceeded")
        self.assertEqual(examples["shared_balance_stale"]["state"], "stale")
        for example in examples.values():
            self.assertTrue(example["privacy_notes"])
            self.assertTrue(example["money_notes"])
            self.assertIn(example["title"], DOCUMENT)


class ContractAndSafetyTests(unittest.TestCase):
    def test_contract_level_conditions_name_entitlement_deny_and_revoked_grant(self):
        conditions = {item["id"]: item for item in DATA["contract_conditions"]}
        self.assertEqual(conditions["entitlement_denied"]["binds_to"], "permission_denied")
        self.assertEqual(conditions["entitlement_denied"]["cause"], "plan")
        self.assertIs(conditions["entitlement_denied"]["contract_level"], True)
        self.assertEqual(conditions["grant_not_active"]["binds_to"], "permission_denied")
        self.assertEqual(conditions["grant_not_active"]["cause"], "sharing")
        self.assertIn("revoked", conditions["grant_not_active"]["description"])
        for condition in conditions.values():
            self.assertIn("T-", condition["binding_owner"])

    def test_no_api_error_codes_are_invented(self):
        serialized = json.dumps(DATA["contract_conditions"])
        self.assertIsNone(module.CODE_LIKE.search(serialized), serialized)
        self.assertIsNone(re.search(r'"(code|status_code|http_status|error_code)"', json.dumps(DATA)))
        # The schema cannot express a code field on a condition.
        self.assertNotIn("code", SCHEMA["definitions"]["contract_condition"]["properties"])
        self.assertIs(SCHEMA["definitions"]["contract_condition"]["additionalProperties"], False)

    def test_state_copy_carries_no_money_and_no_internal_detail(self):
        money = re.compile(r"(₹|\bINR\b|\bRs\.?\b|\$|\b[0-9]+\.[0-9]{2}\b)")
        for item in DATA["states"]:
            for text in module.canonical_strings(item):
                self.assertIsNone(money.search(text), text)
        for example in DATA["worked_examples"]:
            for text in example["copy_rendered"].values():
                self.assertIsNone(money.search(text), text)
                self.assertIsNone(module.forbidden_term(text, DATA["forbidden_terms"]), text)

    def test_signals_carry_no_financial_or_personal_content(self):
        attributes = {item["id"] for item in DATA["signals"]["attributes"]}
        for forbidden in ("amount", "balance", "grant_id", "member_id", "message", "device_id"):
            self.assertNotIn(forbidden, attributes)
        for example in DATA["worked_examples"]:
            for key, value in example["signal_recorded"]["attributes"].items():
                self.assertIn(key, attributes)
                self.assertNotRegex(value, r"[0-9]{4,}")

    def test_adoption_implies_no_existing_client_coverage(self):
        self.assertTrue(DATA["adoption"]["existing_client_coverage"].startswith("None."))
        assertions = {item["id"]: item for item in DATA["adoption"]["coverage_assertions"]}
        self.assertIn("every applicable state identifier", assertions["client_state_coverage"]["proves"])
        self.assertIn("taxonomy first", assertions["taxonomy_first"]["proves"])
        registration = DATA["adoption"]["illustrative_surface_registration"]
        self.assertTrue(registration["surface_id"].startswith("example_"))
        self.assertLessEqual(set(registration["applicable_states"]), set(STATES))


class PlantedDefectTests(unittest.TestCase):
    """Each check must fail when the corresponding defect is planted."""

    def test_removed_state_is_rejected(self):
        data = taxonomy()
        data["states"] = [item for item in data["states"] if item["id"] != "degraded"]
        data["precedence"].remove("degraded")
        with self.assertRaisesRegex(ValueError, "fewer than 8 items"):
            validate(data)

    def test_renamed_identifier_is_rejected(self):
        data = taxonomy()
        state(data, "offline")["id"] = "no_network"
        with self.assertRaisesRegex(ValueError, "Missing required state identifier: offline"):
            validate(data)

    def test_identifier_with_mismatched_signal_is_rejected(self):
        data = taxonomy()
        state(data, "offline")["signal"] = "client_state.no_network"
        with self.assertRaisesRegex(ValueError, "signal must be client_state.offline"):
            validate(data)

    def test_second_recovery_action_is_rejected_by_schema(self):
        data = taxonomy()
        action = state(data, "error")["recovery_action"]
        state(data, "error")["recovery_action"] = [action, dict(action, id="report")]
        with self.assertRaisesRegex(ValueError, "expected type object"):
            validate(data)

    def test_recovery_label_offering_two_actions_is_rejected(self):
        data = taxonomy()
        state(data, "error")["recovery_action"]["label"] = "Try again or report"
        with self.assertRaisesRegex(ValueError, "exactly one action"):
            validate(data)

    def test_blaming_copy_is_rejected(self):
        data = taxonomy()
        state(data, "error")["copy"]["body"] = "You entered the wrong amount."
        with self.assertRaisesRegex(ValueError, "forbidden term 'wrong'"):
            validate(data)

    def test_invented_cause_is_rejected(self):
        data = taxonomy()
        state(data, "degraded")["copy"]["body"] = "Unavailable because the server is down."
        with self.assertRaisesRegex(ValueError, "forbidden term"):
            validate(data)

    def test_undeclared_placeholder_is_rejected(self):
        data = taxonomy()
        state(data, "empty")["copy"]["body"] = "Nothing for {account_name} yet."
        with self.assertRaisesRegex(ValueError, "undeclared placeholder"):
            validate(data)

    def test_missing_copy_rule_is_rejected(self):
        data = taxonomy()
        data["copy_rules"] = [rule for rule in data["copy_rules"] if rule["id"] != "no_blame"]
        with self.assertRaisesRegex(ValueError, "Missing copy rule: no_blame"):
            validate(data)

    def test_identical_data_display_for_distinguished_pair_is_rejected(self):
        data = taxonomy()
        state(data, "stale")["data_display"] = "none"
        distinction = next(item for item in data["distinctions"] if item["id"] == "offline_vs_stale")
        distinction["data_shown"]["stale"] = "none"
        with self.assertRaisesRegex(ValueError, "not observably different"):
            validate(data)

    def test_distinction_disagreeing_with_state_is_rejected(self):
        data = taxonomy()
        distinction = next(item for item in data["distinctions"] if item["id"] == "error_vs_degraded")
        distinction["data_shown"]["degraded"] = "shown_marked"
        with self.assertRaisesRegex(ValueError, "disagrees with state degraded"):
            validate(data)

    def test_missing_distinction_is_rejected(self):
        data = taxonomy()
        data["distinctions"] = [item for item in data["distinctions"] if item["id"] != "offline_vs_stale"]
        with self.assertRaisesRegex(ValueError, "fewer than 2 items"):
            validate(data)

    def test_invented_error_code_is_rejected(self):
        data = taxonomy()
        condition = next(item for item in data["contract_conditions"] if item["id"] == "request_failed")
        condition["description"] = "Returned as REQUEST_FAILED with status 503."
        with self.assertRaisesRegex(ValueError, "code-like token"):
            validate(data)

    def test_code_field_on_condition_is_rejected_by_schema(self):
        data = taxonomy()
        condition = next(item for item in data["contract_conditions"] if item["id"] == "request_failed")
        condition["code"] = "E_FAILED"
        with self.assertRaisesRegex(ValueError, "unexpected property 'code'"):
            validate(data)

    def test_condition_bound_to_unknown_state_is_rejected(self):
        data = taxonomy()
        condition = next(item for item in data["contract_conditions"] if item["id"] == "request_failed")
        condition["binds_to"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "binds to unknown state"):
            validate(data)

    def test_required_condition_rebound_to_another_state_is_rejected(self):
        data = taxonomy()
        condition = next(item for item in data["contract_conditions"] if item["id"] == "entitlement_denied")
        condition["binds_to"] = "error"
        with self.assertRaisesRegex(ValueError, "entitlement_denied must bind to permission_denied"):
            validate(data)

    def test_permission_denied_showing_data_is_rejected(self):
        data = taxonomy()
        state(data, "permission_denied")["data_display"] = "shown"
        with self.assertRaisesRegex(ValueError, "must hide data"):
            validate(data)

    def test_permission_denied_disclosure_guarantee_is_enforced(self):
        data = taxonomy()
        state(data, "permission_denied")["guarantees"]["discloses_hidden_data"] = True
        with self.assertRaisesRegex(ValueError, "must not disclose hidden data"):
            validate(data)

    def test_permission_denied_blocking_surface_is_rejected(self):
        data = taxonomy()
        state(data, "permission_denied")["guarantees"]["rest_of_surface_usable"] = False
        with self.assertRaisesRegex(ValueError, "rest of the surface usable"):
            validate(data)

    def test_sharing_copy_with_a_placeholder_is_rejected(self):
        data = taxonomy()
        variant = state(data, "permission_denied")["copy"]["variants"]["sharing"]
        variant["headline"] = "{item} isn't shared with you"
        with self.assertRaisesRegex(ValueError, "sharing-cause copy must not contain placeholders"):
            validate(data)

    def test_quota_exceeded_without_remaining_availability_is_rejected(self):
        data = taxonomy()
        state(data, "quota_exceeded")["guarantees"]["states_what_remains_available"] = False
        with self.assertRaisesRegex(ValueError, "what remains available"):
            validate(data)

    def test_missing_worked_example_is_rejected(self):
        data = taxonomy()
        data["worked_examples"] = data["worked_examples"][:2]
        with self.assertRaisesRegex(ValueError, "fewer than 3 items"):
            validate(data)

    def test_worked_example_with_wrong_state_is_rejected(self):
        data = taxonomy()
        data["worked_examples"][2]["state"] = "offline"
        with self.assertRaisesRegex(ValueError, "must use state stale"):
            validate(data)

    def test_worked_example_signal_attribute_with_undeclared_key_is_rejected(self):
        data = taxonomy()
        data["worked_examples"][0]["signal_recorded"]["attributes"]["amount_minor"] = "1200"
        with self.assertRaisesRegex(ValueError, "undeclared signal attribute"):
            validate(data)

    def test_precedence_missing_a_state_is_rejected(self):
        data = taxonomy()
        data["precedence"][0] = data["precedence"][1]
        with self.assertRaisesRegex(ValueError, "not unique"):
            validate(data)

    def test_document_omitting_an_identifier_is_rejected(self):
        document = DOCUMENT.replace("`quota_exceeded`", "`quota-exceeded`")
        with self.assertRaisesRegex(ValueError, "Document does not mention state `quota_exceeded`"):
            validate(taxonomy(), document)

    def test_document_omitting_a_worked_example_is_rejected(self):
        document = DOCUMENT.replace("Stale shared balance", "Stale household total")
        with self.assertRaisesRegex(ValueError, "worked example 'Stale shared balance'"):
            validate(taxonomy(), document)

    def test_document_paraphrasing_canonical_copy_is_rejected(self):
        document = DOCUMENT.replace("You're offline", "No connection")
        with self.assertRaisesRegex(ValueError, "canonical copy \"You're offline\" of state `offline`"):
            validate(taxonomy(), document)

    def test_data_copy_absent_from_document_is_rejected(self):
        data = taxonomy()
        state(data, "offline")["copy"]["body"] = "Try again when the connection is back."
        with self.assertRaisesRegex(ValueError, "Document does not carry the canonical copy"):
            validate(data)

    def test_unknown_top_level_property_is_rejected_by_schema(self):
        data = taxonomy()
        data["client_overrides"] = {"web": {"error": "Whoops"}}
        with self.assertRaisesRegex(ValueError, "unexpected property 'client_overrides'"):
            validate(data)

    def test_unsupported_schema_keyword_fails_closed(self):
        schema = copy.deepcopy(SCHEMA)
        schema["properties"]["states"]["contains"] = {"const": "x"}
        with self.assertRaisesRegex(module.SchemaError, "unsupported schema keyword"):
            validate(taxonomy(), schema=schema)

    def test_unknown_definition_reference_fails_closed(self):
        schema = copy.deepcopy(SCHEMA)
        schema["properties"]["precedence_rule"] = {"$ref": "#/definitions/does_not_exist"}
        with self.assertRaisesRegex(module.SchemaError, "Unknown definition"):
            validate(taxonomy(), schema=schema)


class SchemaValidatorTests(unittest.TestCase):
    """The stdlib schema subset behaves like draft-07 for the keywords it implements."""

    def test_type_checks_exclude_booleans_from_integers(self):
        with self.assertRaisesRegex(ValueError, "expected type integer"):
            module.validate_schema(True, {"type": "integer"})
        module.validate_schema(3, {"type": "integer"})

    def test_pattern_and_min_length(self):
        module.validate_schema("permission_denied", SCHEMA["definitions"]["identifier"])
        with self.assertRaisesRegex(ValueError, "does not match"):
            module.validate_schema("Permission-Denied", SCHEMA["definitions"]["identifier"])
        with self.assertRaisesRegex(ValueError, "shorter than 1"):
            module.validate_schema("", SCHEMA["definitions"]["text"])

    def test_required_enum_const_and_unique_items(self):
        with self.assertRaisesRegex(ValueError, "missing required property 'id'"):
            module.validate_schema({"rule": "x"}, SCHEMA["definitions"]["copy_rule"], SCHEMA)
        with self.assertRaisesRegex(ValueError, "is not one of"):
            module.validate_schema("ios", SCHEMA["definitions"]["client"])
        with self.assertRaisesRegex(ValueError, "expected constant"):
            module.validate_schema(2, {"const": 1})
        with self.assertRaisesRegex(ValueError, "not unique"):
            module.validate_schema(["a", "a"], {"type": "array", "uniqueItems": True})

    def test_max_items_and_additional_properties_schema(self):
        with self.assertRaisesRegex(ValueError, "more than 1 items"):
            module.validate_schema([1, 2], {"type": "array", "maxItems": 1})
        module.validate_schema({"x": "ok"}, {"type": "object", "additionalProperties": {"type": "string"}})
        with self.assertRaisesRegex(ValueError, "expected type string"):
            module.validate_schema({"x": 1}, {"type": "object", "additionalProperties": {"type": "string"}})


if __name__ == "__main__":
    unittest.main()
