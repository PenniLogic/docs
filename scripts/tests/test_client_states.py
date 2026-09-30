"""Tests for the shared client state taxonomy (T-UX-01, PenniLogic/docs#1).

Each acceptance criterion of the ticket maps to a named test below, and every check is proven to
bite with a planted defect. Version 1.1.0 (PenniLogic/docs#139) adds the reviewer follow-ups of
PR #138, the seven Android capture-health reason identifiers of PenniLogic/android#57 and the
ADR-021 / ADR-023 wording, each with its own planted negative. These tests prove the published
data, schema and document; they are not a client build and claim no client coverage.
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
# The document hard-wraps prose; phrase assertions run against the whitespace-collapsed text.
PLAIN_DOCUMENT = re.sub(r"\s+", " ", DOCUMENT)
STATES = {state["id"]: state for state in DATA["states"]}
CONDITIONS = {item["id"]: item for item in DATA["contract_conditions"]}
RENDERINGS = {item["id"]: item for item in DATA.get("content_renderings", [])}

# The identifier surface published as 1.0.0 (6eb4da65). Removing or renaming any of it is a major
# change under section 13.2, so 1.1.0 must still carry every entry byte for byte.
PUBLISHED_1_0_0 = {
    "states": {"empty", "loading", "error", "offline", "stale", "permission_denied", "quota_exceeded", "degraded"},
    "recovery_actions": {
        "empty": "primary_action", "loading": "cancel", "error": "retry", "offline": "retry",
        "stale": "refresh", "permission_denied": "review_access", "quota_exceeded": "view_usage",
        "degraded": "retry",
    },
    "labels": {
        "empty": "{primary_action}", "loading": "Cancel", "error": "Try again", "offline": "Try again",
        "stale": "Refresh", "permission_denied": "Review access", "quota_exceeded": "See usage and plans",
        "degraded": "Try again",
    },
    "label_by_cause": {
        "device": "Allow {permission}", "plan": "See plans", "sharing": "See what's shared with you",
        "role": "Request access",
    },
    "causes": {"device", "plan", "sharing", "role"},
    "conditions": {
        "entitlement_denied", "grant_not_active", "offline_lease_elapsed", "device_permission_not_granted",
        "role_capability_denied", "quota_exhausted", "rate_limited", "dependency_unavailable",
        "request_failed", "validation_rejected", "capture_paused_by_platform", "capture_blocked_by_setting",
        "resource_pressure",
    },
    "placeholders": {
        "item", "attempt", "capability", "permission", "last_updated", "limit", "resets_at",
        "still_available", "primary_action", "what_appears_here", "field_guidance",
    },
    "headlines": {
        "empty": "Nothing here yet", "loading": "Still loading", "error": "Couldn't {attempt}",
        "offline": "You're offline", "stale": "Last updated {last_updated}",
        "permission_denied": "You don't have access to this right now",
        "quota_exceeded": "You've reached this period's limit of {limit}",
        "degraded": "{capability} isn't available right now",
    },
    "variants": {
        "error": {"validation"}, "permission_denied": {"device", "plan", "sharing", "role"},
        "quota_exceeded": {"with_reset", "rate_limited"},
    },
}

# PenniLogic/android#57, docs/platform/capture-health-identifiers.json at android main ff15e94e
# (blob affe6d7f): the reason identifiers exactly as the client implements them.
ANDROID_57_REASONS = {
    "capture_paused_by_platform": (
        "force_stopped", "private_space_paused", "standby_bucket_restricted", "background_restricted",
    ),
    "capture_blocked_by_setting": (
        "listener_access_not_granted", "restricted_setting_locked", "capture_permission_not_granted",
    ),
}


def taxonomy():
    return copy.deepcopy(DATA)


def state(data, state_id):
    return next(item for item in data["states"] if item["id"] == state_id)


def condition(data, condition_id):
    return next(item for item in data["contract_conditions"] if item["id"] == condition_id)


def reason(data, reason_id):
    for item in data["contract_conditions"]:
        for candidate in item.get("reasons", []):
            if candidate["id"] == reason_id:
                return item, candidate
    raise KeyError(reason_id)


def validate(data, document=DOCUMENT, schema=SCHEMA):
    module.validate_schema(data, schema)
    return module.check_taxonomy(data, document)


class PublishedFilesTests(unittest.TestCase):
    def test_published_data_validates_against_schema_and_rules(self):
        summary = module.validate_taxonomy(ROOT)
        self.assertEqual(summary["states"], 8)
        self.assertEqual(summary["worked_examples"], 3)
        self.assertEqual(summary["reasons"], 7)
        self.assertEqual(summary["content_renderings"], 5)
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
        for example in DATA["worked_examples"]:
            self.assertTrue(example["signal_recorded"]["attributes"]["surface_id"].startswith("example_"))


class IndependentReviewFixTests(unittest.TestCase):
    """Findings from the independent reviews of PR #138 (head 7e042cc) stay fixed."""

    def test_d1_degraded_composes_only_over_dependency_failures(self):
        composing = {state_id for state_id, item in STATES.items() if item["composes_to_degraded"]}
        self.assertEqual(composing, {"error", "offline"})
        condition = STATES["degraded"]["triggering_condition"]
        producers = condition.split("A supplementary region in permission_denied")[0]
        self.assertNotIn("permission_denied", producers)
        self.assertNotIn("quota_exceeded", producers)
        self.assertIn("never produces degraded", condition)
        for state_id in ("permission_denied", "quota_exceeded"):
            forbidden = " ".join(STATES[state_id]["forbidden_content"])
            self.assertIn("degraded", forbidden, state_id)
        for example in DATA["worked_examples"]:
            if example["state"] in ("permission_denied", "quota_exceeded"):
                self.assertTrue(any("not degraded" in line for line in example["shown"]), example["id"])

    def test_d2_cancel_never_produces_empty(self):
        behaviour = STATES["loading"]["recovery_action"]["behaviour"]
        self.assertIn("never produces empty", behaviour)
        self.assertNotIn("or to empty", behaviour)

    def test_d3_a1_validation_variant_recovers_through_the_rejected_field(self):
        error = STATES["error"]
        behaviour = error["recovery_action"]["behaviour"]
        self.assertIn("submits the edited input", behaviour)
        self.assertIn("never the rejected input unchanged", behaviour)
        required = " ".join(error["required_content"])
        self.assertIn("focus moves to the rejected field", required)
        self.assertIn("programmatically associated with the field", required)
        self.assertIn("focus moves to the rejected field", error["copy"]["variants"]["validation"]["when"])
        self.assertTrue(any("rejected field instead of the headline" in rule for rule in DATA["accessibility_rules"]))

    def test_a2_stale_marker_is_one_per_region(self):
        self.assertIn("one text marker per region", DATA["data_display_values"]["shown_marked"])
        self.assertIn("announced once per region", DATA["data_display_values"]["shown_marked"])
        required = " ".join(STATES["stale"]["required_content"])
        self.assertIn("One canonical marker per stale region", required)
        self.assertTrue(any("repeated after every figure" in line for line in STATES["stale"]["forbidden_content"]))
        distinction = next(item for item in DATA["distinctions"] if item["id"] == "offline_vs_stale")
        self.assertIn("one text marker", distinction["observable_difference"])
        self.assertNotIn("each with the text marker", distinction["observable_difference"])

    def test_a3_persistent_denial_is_not_reannounced(self):
        self.assertTrue(any("not re-announced" in rule for rule in DATA["accessibility_rules"]))
        self.assertTrue(any("not re-announced" in line for line in STATES["permission_denied"]["forbidden_content"]))

    def test_p1_revoked_grant_rendering_states_the_inherent_signal_floor(self):
        example = next(item for item in DATA["worked_examples"] if item["id"] == "shared_balance_stale")
        blob = json.dumps(example)
        self.assertNotIn("nothing indicates", blob)
        self.assertIn("region leave the view", blob)
        self.assertIn("only on explicit navigation", blob)
        self.assertIn("inherent-signal floor", blob)
        self.assertTrue(any("persistent denial card" in line for line in example["must_not_show"]))
        required = " ".join(STATES["permission_denied"]["required_content"])
        self.assertIn("never as a persistent card standing where the figure was", required)
        self.assertIn("inherent signal of unilateral revocation", required)

    def test_d5_still_available_placeholder_requires_a_plural_phrase(self):
        placeholder = next(item for item in DATA["placeholders"] if item["id"] == "still_available")
        self.assertIn("plural noun phrase", placeholder["description"])

    def test_f4_default_review_access_destination_is_specified(self):
        behaviour = STATES["permission_denied"]["recovery_action"]["behaviour"]
        self.assertIn("default label opens the account's access overview", behaviour)
        self.assertIn("without naming any denied item", behaviour)


class Docs139FollowUpTests(unittest.TestCase):
    """Version 1.1.0 (PenniLogic/docs#139): reviewer notes N1-N6 and N-1..N-5 of PR #138,
    PenniLogic/android#57, ADR-021 and ADR-023 stay applied."""

    def test_version_is_1_1_0_with_schema_version_1(self):
        self.assertEqual(DATA["taxonomy_version"], "1.1.0")
        self.assertEqual(DATA["schema_version"], 1)
        self.assertEqual(SCHEMA["properties"]["schema_version"], {"const": 1})
        self.assertIn("version 1.1.0", DOCUMENT)

    def test_every_1_0_0_identifier_and_canonical_string_survives(self):
        # No removal or rename: the change is additive, so 1.1.0 is a minor bump (section 13.2).
        self.assertLessEqual(PUBLISHED_1_0_0["states"], set(STATES))
        for state_id, action_id in PUBLISHED_1_0_0["recovery_actions"].items():
            self.assertEqual(STATES[state_id]["recovery_action"]["id"], action_id)
            self.assertEqual(STATES[state_id]["recovery_action"]["label"], PUBLISHED_1_0_0["labels"][state_id])
            self.assertEqual(STATES[state_id]["copy"]["headline"], PUBLISHED_1_0_0["headlines"][state_id])
        self.assertEqual(
            STATES["permission_denied"]["recovery_action"]["label_by_cause"], PUBLISHED_1_0_0["label_by_cause"]
        )
        self.assertEqual({cause["id"] for cause in STATES["permission_denied"]["causes"]}, PUBLISHED_1_0_0["causes"])
        self.assertLessEqual(PUBLISHED_1_0_0["conditions"], set(CONDITIONS))
        self.assertLessEqual(PUBLISHED_1_0_0["placeholders"], {item["id"] for item in DATA["placeholders"]})
        for state_id, keys in PUBLISHED_1_0_0["variants"].items():
            self.assertLessEqual(keys, set(STATES[state_id]["copy"]["variants"]))
        for state_id, item in STATES.items():
            self.assertEqual(item["signal"], "client_state." + state_id)

    def test_n5_n_1_submit_control_keeps_its_registered_label(self):
        error = STATES["error"]
        self.assertEqual(error["recovery_action"]["label_by_variant"], {"validation": "{submit_label}"})
        self.assertEqual(error["recovery_action"]["label"], "Try again")
        self.assertIn("keeps its registered label", error["recovery_action"]["behaviour"])
        self.assertIn("under its registered label", error["copy"]["variants"]["validation"]["when"])
        placeholder = next(item for item in DATA["placeholders"] if item["id"] == "submit_label")
        self.assertEqual(placeholder["source"], "surface_registration")
        registration = SCHEMA["definitions"]["surface_registration"]
        self.assertIn("submit_label", registration["properties"])
        self.assertNotIn("submit_label", registration["required"])
        self.assertIn("keeps its registered label", PLAIN_DOCUMENT)

    def test_n_5_registration_shape_carries_still_available(self):
        registration = SCHEMA["definitions"]["surface_registration"]
        self.assertIn("still_available", registration["properties"])
        self.assertNotIn("still_available", registration["required"])
        self.assertEqual(registration["required"], ["surface_id", "client", "applicable_states", "item", "attempt"])
        self.assertIn("`still_available`", DOCUMENT)

    def test_n_2_stale_marker_is_associated_with_the_group_of_figures(self):
        # A1 of the #166 accessibility review: the association is a region-level description or an
        # addition to the region's own name, never a replacement, worded identically everywhere.
        phrase = "group of figures it qualifies"
        precision = "or appended to the region's own accessible name, never replacing it"
        self.assertIn(phrase, DATA["data_display_values"]["shown_marked"])
        self.assertIn(precision, DATA["data_display_values"]["shown_marked"])
        self.assertIn("one text marker per region", DATA["data_display_values"]["shown_marked"])
        stale_line = next(line for line in STATES["stale"]["required_content"] if phrase in line)
        self.assertIn(precision, stale_line)
        rule = next(rule for rule in DATA["accessibility_rules"] if phrase in rule)
        self.assertIn(precision, rule)
        self.assertNotIn("every figure it qualifies", json.dumps(DATA))
        self.assertNotIn("every figure it qualifies", PLAIN_DOCUMENT)
        self.assertNotIn("accessible name or description", json.dumps(DATA))
        self.assertNotIn("accessible name or description", PLAIN_DOCUMENT)
        self.assertGreaterEqual(PLAIN_DOCUMENT.count(phrase), 4)
        self.assertEqual(PLAIN_DOCUMENT.count(precision), 3)

    def test_n_3_no_notification_after_access_ends_and_lease_drop_is_local(self):
        required = " ".join(STATES["permission_denied"]["required_content"])
        self.assertIn("no notification is issued for an item the viewer can no longer access", required.lower())
        self.assertIn("issued while the grant was active", required)
        example = next(item for item in DATA["worked_examples"] if item["id"] == "shared_balance_stale")
        blob = " ".join(example["transitions"] + example["privacy_notes"])
        self.assertIn("may still be active server-side", blob)
        self.assertEqual(blob.count("next confirmed refresh while the grant is still active"), 2)
        self.assertIn("not a revocation signal", blob)
        self.assertIn("no notification is issued for an item the viewer can no longer access", PLAIN_DOCUMENT.lower())
        self.assertEqual(PLAIN_DOCUMENT.count("next confirmed refresh while the grant is still active"), 2)

    def test_n_4_rate_limited_condition_does_not_dictate_the_contract_shape(self):
        description = CONDITIONS["rate_limited"]["description"]
        self.assertIn("should state the limit, its window and when it lifts", description)
        self.assertNotIn("must state", description)
        self.assertIn("omitted when absent", description)
        self.assertIsNone(module.CODE_LIKE.search(description))
        self.assertIn("the shape should state the limit", PLAIN_DOCUMENT)

    def test_n6_version_history_records_the_first_published_version(self):
        history = DATA["version_history"]
        self.assertEqual(history[0]["version"], "1.0.0")
        self.assertEqual(history[0]["bump"], "initial")
        self.assertIn("6eb4da65", history[0]["change"])
        self.assertIn("not a versioning event", history[0]["change"])
        self.assertEqual(history[-1]["version"], "1.1.0")
        self.assertEqual(history[-1]["bump"], "minor")
        for reference in ("PenniLogic/docs#139", "PenniLogic/android#57", "PenniLogic/docs#41", "PenniLogic/docs#47"):
            self.assertTrue(any(reference in item for item in history[-1]["references"]), reference)
        self.assertIn("### 13.2 Versioning rule", DOCUMENT)
        self.assertIn("### 13.3 Version history", DOCUMENT)
        self.assertIn("*required* schema property", PLAIN_DOCUMENT)
        self.assertIn("was not a versioning event", PLAIN_DOCUMENT)

    def test_n2_accepted_limit_is_recorded_in_section_14(self):
        self.assertIn("**Accepted limit (N2 of the #138 review).**", DOCUMENT)
        self.assertIn("substring", DOCUMENT.split("**Accepted limit (N2 of the #138 review).**")[1][:400])

    def test_android_57_reason_identifiers_are_published_byte_for_byte(self):
        self.assertEqual(module.REQUIRED_REASONS, ANDROID_57_REASONS)
        for condition_id, reason_ids in ANDROID_57_REASONS.items():
            published = tuple(item["id"] for item in CONDITIONS[condition_id]["reasons"])
            self.assertEqual(published, reason_ids)
            for item in CONDITIONS[condition_id]["reasons"]:
                self.assertEqual(item["client"], "android")
                self.assertIn("PenniLogic/android#57", item["published_by"])
                self.assertIn("ff15e94e", item["published_by"])
                self.assertIsNone(module.CODE_LIKE.search(json.dumps(item)), item["id"])
            self.assertIs(CONDITIONS[condition_id]["contract_level"], False)
        self.assertEqual(CONDITIONS["capture_paused_by_platform"]["binds_to"], "degraded")
        self.assertEqual(CONDITIONS["capture_blocked_by_setting"]["binds_to"], "permission_denied")
        self.assertEqual(CONDITIONS["capture_blocked_by_setting"]["cause"], "device")
        _, force_stopped = reason(DATA, "force_stopped")
        self.assertIn("cannot be told apart from a swipe", force_stopped["limitation"])
        _, private_space = reason(DATA, "private_space_paused")
        self.assertIn("never joined to an account identifier", private_space["privacy"])
        # C5 of the #166 core review: the android source says "not exported by this baseline".
        self.assertIn("not exported by this baseline", private_space["privacy"])
        self.assertIn("not exported by this baseline", PLAIN_DOCUMENT)
        _, locked = reason(DATA, "restricted_setting_locked")
        self.assertIn("App info page", locked["recovery_destination"])
        self.assertIn("this version adds none", locked["recovery_destination"])
        for reason_id in sum(ANDROID_57_REASONS.values(), ()):
            self.assertIn(f"| `{reason_id}` |", DOCUMENT)

    def test_android_57_placeholder_values_are_confirmed(self):
        placeholders = {item["id"]: item["description"] for item in DATA["placeholders"]}
        self.assertIn("'Automatic capture'", placeholders["capability"])
        self.assertIn("confirmed for PenniLogic/android#57", placeholders["permission"])
        self.assertIn("user-facing name", placeholders["permission"])
        attribute = next(item for item in DATA["signals"]["attributes"] if item["id"] == "permission")
        self.assertIn("not the user-facing name", attribute["description"])
        self.assertIn("A reason is not a signal attribute", DATA["reason_rule"])
        self.assertEqual(
            [item["id"] for item in DATA["signals"]["attributes"]],
            ["client", "surface_id", "scope", "cause", "permission", "recovery_action_taken", "taxonomy_version"],
        )

    def test_adr_023_own_key_wording(self):
        condition_text = STATES["quota_exceeded"]["triggering_condition"]
        self.assertIn("its tokens are never charged against plan quota and never produce this state", condition_text)
        self.assertIn("request allowance still applies and can", condition_text)
        self.assertNotIn("does not produce this state", condition_text)
        example = next(item for item in DATA["worked_examples"] if item["id"] == "ai_surface_quota_exceeded")
        self.assertTrue(any("request allowance still applies" in line for line in example["transitions"]))
        self.assertFalse(any("so this state does not appear" in line for line in example["transitions"]))
        self.assertTrue(any("never resets" in line for line in STATES["quota_exceeded"]["required_content"]))
        self.assertIn("request allowance still applies and can", PLAIN_DOCUMENT)

    def test_adr_021_renderings_are_ordinary_states_naming_no_person(self):
        self.assertEqual(
            set(RENDERINGS),
            {"erased_member_placeholder", "redacted_description", "redacted_note", "pseudonymised_viewer", "partial_total"},
        )
        denied_copy = set(module.canonical_strings(STATES["permission_denied"]))
        for item in RENDERINGS.values():
            self.assertEqual(item["rendered_in"], "content")
            self.assertNotIn(item["id"], STATES)
            label = item["copy"]["label"]
            self.assertFalse(module.PLACEHOLDER.search(label), label)
            self.assertNotIn(label, denied_copy)
            self.assertIsNone(module.forbidden_term(label, DATA["forbidden_terms"]), label)
            self.assertLessEqual(len(label), 60)
            self.assertIn("ADR-021", item["source"])
            self.assertIn(f'"{label}"', DOCUMENT)
        self.assertIn("never permission_denied", DATA["content_rendering_rule"])
        self.assertIn("adds no state identifier", DATA["content_rendering_rule"])
        self.assertIn("### 9.2 Content renderings", DOCUMENT)


class PlantedDefectTests(unittest.TestCase):
    """Each check must fail when the corresponding defect is planted."""

    def test_removed_state_is_rejected(self):
        data = taxonomy()
        data["states"] = [item for item in data["states"] if item["id"] != "degraded"]
        data["precedence"].remove("degraded")
        with self.assertRaisesRegex(ValueError, "fewer than 8 items"):
            validate(data)

    def test_duplicate_state_identifier_is_rejected(self):
        # uniqueItems cannot cover object arrays, so _unique_ids is the only guard (N4).
        data = taxonomy()
        duplicate = copy.deepcopy(state(data, "offline"))
        duplicate["definition"] = "A second definition of the same identifier."
        data["states"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "Duplicate state identifier"):
            validate(data)

    def test_duplicate_contract_condition_identifier_is_rejected(self):
        data = taxonomy()
        duplicate = copy.deepcopy(condition(data, "request_failed"))
        duplicate["binds_to"] = "offline"
        data["contract_conditions"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "Duplicate contract condition identifier"):
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

    def test_sharing_cause_label_with_a_placeholder_is_rejected(self):
        # P1 of the #166 privacy review: the sharing label is rendered beside the sharing copy.
        data = taxonomy()
        state(data, "permission_denied")["recovery_action"]["label_by_cause"]["sharing"] = "See {item} shared with you"
        with self.assertRaisesRegex(ValueError, "sharing-cause label_by_cause label must not contain placeholders"):
            validate(data)

    def test_sharing_variant_label_with_a_placeholder_is_rejected(self):
        data = taxonomy()
        state(data, "permission_denied")["recovery_action"]["label_by_variant"] = {"sharing": "Ask about {item}"}
        with self.assertRaisesRegex(ValueError, "sharing-cause label_by_variant label must not contain placeholders"):
            validate(data)

    def test_sharing_variant_label_without_a_placeholder_is_accepted(self):
        data = taxonomy()
        state(data, "permission_denied")["recovery_action"]["label_by_variant"] = {"sharing": "See what's shared with you"}
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

    def test_required_worked_example_replaced_by_another_is_rejected(self):
        data = taxonomy()
        extra = copy.deepcopy(data["worked_examples"][2])
        extra["id"] = "currency_rate_stale"
        extra["signal_recorded"]["attributes"]["surface_id"] = "example_currency_rates"
        data["worked_examples"][2] = extra
        with self.assertRaisesRegex(ValueError, "Missing required worked example: shared_balance_stale"):
            validate(data)

    def test_additional_worked_example_is_accepted(self):
        data = taxonomy()
        extra = copy.deepcopy(data["worked_examples"][2])
        extra["id"] = "currency_rate_stale"
        extra["title"] = "Stale currency rate"
        extra["signal_recorded"]["attributes"]["surface_id"] = "example_currency_rates"
        data["worked_examples"].append(extra)
        document = DOCUMENT + "\n### 11.4 Stale currency rate\n"
        self.assertEqual(validate(data, document)["worked_examples"], 4)

    def test_worked_example_with_wrong_state_is_rejected(self):
        data = taxonomy()
        data["worked_examples"][2]["state"] = "offline"
        with self.assertRaisesRegex(ValueError, "must use state stale"):
            validate(data)

    def test_worked_example_paraphrasing_canonical_copy_is_rejected(self):
        data = taxonomy()
        example = data["worked_examples"][0]
        example["copy_rendered"]["headline"] = "SMS access is needed for capture"
        with self.assertRaisesRegex(ValueError, "not an instantiation of the canonical copy"):
            validate(data)

    def test_worked_example_with_foreign_action_label_is_rejected(self):
        data = taxonomy()
        data["worked_examples"][1]["copy_rendered"]["action"] = "Upgrade now"
        with self.assertRaisesRegex(ValueError, "not the recovery action of quota_exceeded"):
            validate(data)

    def test_worked_example_may_render_any_variant(self):
        data = taxonomy()
        rendered = data["worked_examples"][1]["copy_rendered"]
        rendered["headline"] = "You've reached the limit of 3 AI questions for now"
        rendered["body"] = "Saved answers and everything outside AI still work. Resets in a minute."
        validate(data)

    def test_worked_example_with_real_looking_surface_id_is_rejected(self):
        data = taxonomy()
        data["worked_examples"][0]["signal_recorded"]["attributes"]["surface_id"] = "transactions_home"
        with self.assertRaisesRegex(ValueError, "surface_id must be prefixed example_"):
            validate(data)

    def test_worked_example_with_wrong_signal_is_rejected(self):
        data = taxonomy()
        data["worked_examples"][2]["signal_recorded"]["signal"] = "client_state.offline"
        with self.assertRaisesRegex(ValueError, "signal must be client_state.stale"):
            validate(data)

    def test_worked_example_with_forbidden_term_is_rejected(self):
        data = taxonomy()
        data["worked_examples"][2]["copy_rendered"]["body"] = "Showing what was last saved. Sorry."
        with self.assertRaisesRegex(ValueError, "forbidden term 'sorry'"):
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

    def test_precedence_with_a_non_state_is_rejected(self):
        data = taxonomy()
        data["precedence"][-1] = "pending_sync"
        with self.assertRaisesRegex(ValueError, "Precedence must list every state exactly once"):
            validate(data)

    def test_denial_flagged_as_composing_to_degraded_is_rejected(self):
        data = taxonomy()
        state(data, "permission_denied")["composes_to_degraded"] = True
        with self.assertRaisesRegex(ValueError, "region in permission_denied must not compose to degraded"):
            validate(data)

    def test_quota_flagged_as_composing_to_degraded_is_rejected(self):
        data = taxonomy()
        state(data, "quota_exceeded")["composes_to_degraded"] = True
        with self.assertRaisesRegex(ValueError, "region in quota_exceeded must not compose to degraded"):
            validate(data)

    def test_dependency_failure_not_composing_to_degraded_is_rejected(self):
        data = taxonomy()
        state(data, "offline")["composes_to_degraded"] = False
        with self.assertRaisesRegex(ValueError, "region in offline must compose to degraded"):
            validate(data)

    def test_state_without_composition_flag_is_rejected_by_schema(self):
        data = taxonomy()
        del state(data, "empty")["composes_to_degraded"]
        with self.assertRaisesRegex(ValueError, "missing required property 'composes_to_degraded'"):
            validate(data)

    def test_hyphenated_name_mismatch_is_rejected(self):
        data = taxonomy()
        state(data, "permission_denied")["name"] = "access-denied"
        with self.assertRaisesRegex(ValueError, "name must be the hyphenated identifier"):
            validate(data)

    def test_label_by_cause_naming_unknown_cause_is_rejected(self):
        data = taxonomy()
        state(data, "permission_denied")["recovery_action"]["label_by_cause"]["integrity"] = "Verify device"
        with self.assertRaisesRegex(ValueError, "label_by_cause names unknown cause 'integrity'"):
            validate(data)

    def test_permission_denied_missing_required_cause_is_rejected(self):
        data = taxonomy()
        denied = state(data, "permission_denied")
        denied["causes"] = [cause for cause in denied["causes"] if cause["id"] != "sharing"]
        del denied["copy"]["variants"]["sharing"]
        del denied["recovery_action"]["label_by_cause"]["sharing"]
        with self.assertRaisesRegex(ValueError, "must define cause 'sharing'"):
            validate(data)

    def test_degraded_widened_to_region_scope_is_rejected(self):
        data = taxonomy()
        state(data, "degraded")["scopes"] = ["surface", "region"]
        with self.assertRaisesRegex(ValueError, "degraded is a surface-scope notice"):
            validate(data)

    def test_condition_with_cause_not_on_target_is_rejected(self):
        data = taxonomy()
        condition = next(item for item in data["contract_conditions"] if item["id"] == "quota_exhausted")
        condition["cause"] = "plan"
        with self.assertRaisesRegex(ValueError, "cause 'plan' is not a cause of quota_exceeded"):
            validate(data)

    def test_illustrative_registration_with_unknown_state_is_rejected(self):
        data = taxonomy()
        data["adoption"]["illustrative_surface_registration"]["applicable_states"].append("pending_sync")
        with self.assertRaisesRegex(ValueError, "names unknown state 'pending_sync'"):
            validate(data)

    def test_document_omitting_an_identifier_is_rejected(self):
        document = DOCUMENT.replace("`quota_exceeded`", "`quota-exceeded`")
        with self.assertRaisesRegex(ValueError, "no section headed ### 3.n `quota_exceeded`"):
            validate(taxonomy(), document)

    def test_document_omitting_a_mention_outside_the_state_sections_is_rejected(self):
        document = DOCUMENT.replace("`entitlement_denied`", "`plan_refusal`")
        with self.assertRaisesRegex(ValueError, "Document does not mention contract condition `entitlement_denied`"):
            validate(taxonomy(), document)

    def test_document_omitting_a_worked_example_is_rejected(self):
        document = DOCUMENT.replace("Stale shared balance", "Stale household total")
        with self.assertRaisesRegex(ValueError, "worked example 'Stale shared balance'"):
            validate(taxonomy(), document)

    def test_document_paraphrasing_canonical_copy_everywhere_is_rejected(self):
        document = DOCUMENT.replace("You're offline", "No connection")
        with self.assertRaisesRegex(ValueError, "Section 3.n `offline` does not carry the canonical copy \"You're offline\""):
            validate(taxonomy(), document)

    def test_document_paraphrasing_copy_in_the_state_section_only_is_rejected(self):
        # "You're offline" also appears in section 5 and the worked examples; altering the single
        # occurrence in section 3.4 must still fail, so a paraphrase cannot hide behind another mention.
        marker = '- **Copy.** Headline "You\'re offline". Body "Try again when you\'re back online."'
        self.assertEqual(DOCUMENT.count(marker), 1)
        self.assertGreater(DOCUMENT.count("You're offline"), 1)
        document = DOCUMENT.replace(marker, marker.replace("You're offline", "No connection"))
        with self.assertRaisesRegex(ValueError, "Section 3.n `offline` does not carry the canonical copy \"You're offline\""):
            validate(taxonomy(), document)

    def test_document_paraphrasing_action_label_in_the_state_section_only_is_rejected(self):
        marker = '- **Recovery action `refresh`.** Label "Refresh";'
        self.assertEqual(DOCUMENT.count(marker), 1)
        self.assertGreater(DOCUMENT.count("Refresh"), 1)
        document = DOCUMENT.replace(marker, marker.replace('"Refresh"', '"Reload"'))
        with self.assertRaisesRegex(ValueError, "Section 3.n `stale` does not carry the canonical copy 'Refresh'"):
            validate(taxonomy(), document)

    def test_data_copy_absent_from_document_is_rejected(self):
        data = taxonomy()
        state(data, "offline")["copy"]["body"] = "Try again when the connection is back."
        with self.assertRaisesRegex(ValueError, "Section 3.n `offline` does not carry the canonical copy"):
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

    # --- 1.1.0 (PenniLogic/docs#139): N1, N3 and the new identifier checks ---

    def test_duplicate_state_section_hiding_a_paraphrase_is_rejected(self):
        # N1: a second `### 3.n \`offline\`` section carrying the canonical copy must not let the
        # first section paraphrase it; the duplicate heading itself is the error.
        marker = '- **Copy.** Headline "You\'re offline". Body "Try again when you\'re back online."'
        self.assertEqual(DOCUMENT.count(marker), 1)
        paraphrased = DOCUMENT.replace(marker, marker.replace("You're offline", "No connection"))
        duplicate = "\n### 3.9 `offline`\n\n" + marker + "\n- **Recovery action `retry`.** Label \"Try again\".\n"
        document = paraphrased.replace("\n## 4. Precedence and composition", duplicate + "\n## 4. Precedence and composition")
        self.assertIn("### 3.9 `offline`", document)
        with self.assertRaisesRegex(ValueError, "duplicate section for state offline"):
            validate(taxonomy(), document)

    def test_duplicate_state_section_alone_is_rejected(self):
        document = DOCUMENT.replace("### 3.8 `degraded`", "### 3.8 `degraded`\n\n### 3.9 `degraded`")
        with self.assertRaisesRegex(ValueError, "duplicate section for state degraded"):
            validate(taxonomy(), document)

    def test_cause_bound_example_rendering_another_causes_label_is_rejected(self):
        # N3: a device example must render the device label, not any label_by_cause value.
        data = taxonomy()
        data["worked_examples"][0]["copy_rendered"]["action"] = "See plans"
        with self.assertRaisesRegex(ValueError, "not the recovery action of permission_denied for cause 'device'"):
            validate(data)

    def test_cause_bound_example_rendering_another_causes_copy_is_rejected(self):
        data = taxonomy()
        rendered = data["worked_examples"][0]["copy_rendered"]
        rendered["headline"] = "Not included in your plan"
        rendered["body"] = "Everything in your current plan keeps working."
        with self.assertRaisesRegex(ValueError, "canonical copy of permission_denied for cause 'device'"):
            validate(data)

    def test_cause_bound_example_rendering_its_own_cause_is_accepted(self):
        data = taxonomy()
        rendered = data["worked_examples"][0]["copy_rendered"]
        rendered["headline"] = "Automatic capture needs notification access"
        rendered["action"] = "Allow notification access"
        validate(data)

    def _add_fifth_cause(self, data, with_variant, with_label):
        # C1 of the #166 core review: a cause without a variant or label must not fall open to
        # the other causes' copy and labels.
        denied = state(data, "permission_denied")
        denied["causes"].append({
            "id": "integrity",
            "description": "Planted: an adverse integrity verdict denied the operation.",
            "contract_level": True,
            "client_determined": False,
        })
        if with_variant:
            denied["copy"]["variants"]["integrity"] = {
                "when": "Planted.",
                "headline": "Not available on this device right now",
                "body": "Everything else keeps working.",
            }
        if with_label:
            denied["recovery_action"]["label_by_cause"]["integrity"] = "See device status"
        attribute = next(item for item in data["signals"]["attributes"] if item["id"] == "cause")
        attribute["values"].append("integrity")
        example = data["worked_examples"][0]
        example["cause"] = "integrity"
        example["signal_recorded"]["attributes"]["cause"] = "integrity"
        example["copy_rendered"] = {
            "headline": "Not included in your plan",
            "body": "Everything in your current plan keeps working.",
            "action": "See plans",
        }
        return example

    def test_example_naming_a_cause_without_a_variant_fails_closed(self):
        data = taxonomy()
        self._add_fifth_cause(data, with_variant=False, with_label=True)
        with self.assertRaisesRegex(ValueError, "permission_denied has no copy variant for cause 'integrity'"):
            validate(data)

    def test_example_naming_a_cause_without_a_label_fails_closed(self):
        data = taxonomy()
        self._add_fifth_cause(data, with_variant=True, with_label=False)
        with self.assertRaisesRegex(ValueError, "permission_denied has no recovery label for cause 'integrity'"):
            validate(data)

    def test_example_naming_a_fully_defined_cause_is_still_bound_to_it(self):
        data = taxonomy()
        example = self._add_fifth_cause(data, with_variant=True, with_label=True)
        with self.assertRaisesRegex(ValueError, "canonical copy of permission_denied for cause 'integrity'"):
            validate(data)
        example["copy_rendered"]["headline"] = "Not available on this device right now"
        example["copy_rendered"]["body"] = "Everything else keeps working."
        with self.assertRaisesRegex(ValueError, "not the recovery action of permission_denied for cause 'integrity'"):
            validate(data)
        example["copy_rendered"]["action"] = "See device status"
        document = DOCUMENT.replace("### 3.7 `quota_exceeded`", "Not available on this device right now See device status\n\n### 3.7 `quota_exceeded`")
        validate(data, document)

    def test_label_by_variant_naming_unknown_variant_is_rejected(self):
        data = taxonomy()
        state(data, "error")["recovery_action"]["label_by_variant"]["timeout"] = "Wait"
        with self.assertRaisesRegex(ValueError, "label_by_variant names unknown variant 'timeout'"):
            validate(data)

    def test_label_by_variant_with_undeclared_placeholder_is_rejected(self):
        data = taxonomy()
        state(data, "error")["recovery_action"]["label_by_variant"]["validation"] = "{button_text}"
        with self.assertRaisesRegex(ValueError, "undeclared placeholder {button_text}"):
            validate(data)

    def test_label_by_variant_offering_two_actions_is_rejected(self):
        data = taxonomy()
        state(data, "error")["recovery_action"]["label_by_variant"]["validation"] = "Save or discard"
        with self.assertRaisesRegex(ValueError, "exactly one action"):
            validate(data)

    def test_document_omitting_the_variant_label_is_rejected(self):
        self.assertEqual(DOCUMENT.count("`{submit_label}`"), 4)
        section = DOCUMENT[DOCUMENT.index("### 3.3 `error`"):DOCUMENT.index("### 3.4 `offline`")]
        document = DOCUMENT.replace(section, section.replace("`{submit_label}`", "its own label"))
        with self.assertRaisesRegex(ValueError, "Section 3.n `error` does not carry the canonical copy '{submit_label}'"):
            validate(taxonomy(), document)

    def test_registration_may_carry_still_available_and_submit_label(self):
        data = taxonomy()
        registration = data["adoption"]["illustrative_surface_registration"]
        registration["still_available"] = "Saved answers and everything outside AI"
        registration["submit_label"] = "Add"
        validate(data)
        registration["banner_text"] = "Free trial"
        with self.assertRaisesRegex(ValueError, "unexpected property 'banner_text'"):
            validate(data)

    def test_missing_published_reason_is_rejected(self):
        data = taxonomy()
        item, _ = reason(data, "force_stopped")
        item["reasons"] = [entry for entry in item["reasons"] if entry["id"] != "force_stopped"]
        with self.assertRaisesRegex(ValueError, "Missing published reason identifier force_stopped under capture_paused_by_platform"):
            validate(data)

    def test_renamed_published_reason_is_rejected(self):
        data = taxonomy()
        _, entry = reason(data, "background_restricted")
        entry["id"] = "background_limited"
        with self.assertRaisesRegex(ValueError, "Missing published reason identifier background_restricted"):
            validate(data)

    def test_reason_moved_to_the_other_condition_in_data_is_rejected(self):
        data = taxonomy()
        blocked, entry = reason(data, "listener_access_not_granted")
        blocked["reasons"].remove(entry)
        condition(data, "capture_paused_by_platform")["reasons"].append(entry)
        with self.assertRaisesRegex(
            ValueError,
            "Reason listener_access_not_granted is published under capture_paused_by_platform; "
            "the published identifier belongs under capture_blocked_by_setting",
        ):
            validate(data)

    def test_reason_under_the_wrong_condition_in_document_is_rejected(self):
        row = "| `listener_access_not_granted` | `capture_blocked_by_setting` |"
        self.assertEqual(DOCUMENT.count(row), 1)
        document = DOCUMENT.replace(row, "| `listener_access_not_granted` | `capture_paused_by_platform` |")
        with self.assertRaisesRegex(
            ValueError,
            "Document places reason `listener_access_not_granted` under `capture_paused_by_platform` "
            "but the data file publishes it under `capture_blocked_by_setting`",
        ):
            validate(taxonomy(), document)

    def test_reason_absent_from_document_is_rejected(self):
        lines = DOCUMENT.splitlines(keepends=True)
        document = "".join(line for line in lines if not line.startswith("| `standby_bucket_restricted` |"))
        self.assertNotEqual(document, DOCUMENT)
        with self.assertRaisesRegex(ValueError, "Document does not list reason `standby_bucket_restricted`"):
            validate(taxonomy(), document)

    def test_reason_in_document_but_not_in_data_is_rejected(self):
        row = "| `force_stopped` | `capture_paused_by_platform` |"
        extra = "| `screen_locked` | `capture_paused_by_platform` | android | Planted. | Planted. |\n"
        document = DOCUMENT.replace(row, extra + row)
        with self.assertRaisesRegex(ValueError, "Document lists reason `screen_locked` that the data file does not publish"):
            validate(taxonomy(), document)

    def test_reason_listed_twice_in_document_is_rejected(self):
        row = "| `force_stopped` | `capture_paused_by_platform` |"
        document = DOCUMENT.replace(row, row + " x | x | x |\n" + row)
        with self.assertRaisesRegex(ValueError, "Document lists reason `force_stopped` twice"):
            validate(taxonomy(), document)

    def test_document_without_a_reason_table_is_rejected(self):
        document = DOCUMENT.replace("### 9.1 Reason identifiers", "### 9.1 Reasons")
        with self.assertRaisesRegex(ValueError, "Document has no section headed ### n.m Reason identifiers"):
            validate(taxonomy(), document)

    def test_additional_reason_is_accepted_when_documented(self):
        data = taxonomy()
        condition(data, "capture_paused_by_platform")["reasons"].append({
            "id": "doze_deferred",
            "client": "android",
            "description": "Planted extension: the platform deferred background work.",
            "clears_when": "Capture health is restored.",
            "published_by": "Planted test.",
        })
        row = "| `force_stopped` | `capture_paused_by_platform` |"
        document = DOCUMENT.replace(row, "| `doze_deferred` | `capture_paused_by_platform` | android | Planted. | Planted. |\n" + row)
        self.assertEqual(validate(data, document)["reasons"], 8)

    def test_duplicate_reason_identifier_is_rejected(self):
        data = taxonomy()
        _, entry = reason(data, "force_stopped")
        condition(data, "capture_blocked_by_setting")["reasons"].append(copy.deepcopy(entry))
        with self.assertRaisesRegex(ValueError, "Duplicate reason identifier 'force_stopped'"):
            validate(data)

    def test_reason_under_contract_level_condition_is_rejected(self):
        data = taxonomy()
        _, entry = reason(data, "force_stopped")
        condition(data, "quota_exhausted")["reasons"] = [dict(entry, id="daily_window_used")]
        with self.assertRaisesRegex(ValueError, "quota_exhausted: reasons are published only for client-determined conditions"):
            validate(data)

    def test_reason_with_code_like_token_is_rejected(self):
        data = taxonomy()
        _, entry = reason(data, "standby_bucket_restricted")
        entry["description"] = "The bucket is STANDBY_BUCKET_RESTRICTED."
        with self.assertRaisesRegex(ValueError, "Reason standby_bucket_restricted: names a code-like token 'STANDBY_BUCKET_RESTRICTED'"):
            validate(data)

    def test_reason_colliding_with_a_state_identifier_is_rejected(self):
        data = taxonomy()
        condition(data, "capture_paused_by_platform")["reasons"].append({
            "id": "offline",
            "client": "android",
            "description": "Planted.",
            "clears_when": "Planted.",
            "published_by": "Planted.",
        })
        with self.assertRaisesRegex(ValueError, "Reason identifier 'offline' collides"):
            validate(data)

    def test_reason_without_required_fields_is_rejected_by_schema(self):
        data = taxonomy()
        _, entry = reason(data, "force_stopped")
        del entry["clears_when"]
        with self.assertRaisesRegex(ValueError, "missing required property 'clears_when'"):
            validate(data)

    def test_content_rendering_copy_with_placeholder_is_rejected(self):
        data = taxonomy()
        data["content_renderings"][0]["copy"]["label"] = "Former member {item}"
        with self.assertRaisesRegex(ValueError, "erased_member_placeholder copy must not contain placeholders"):
            validate(data)

    def test_content_rendering_with_forbidden_term_is_rejected(self):
        data = taxonomy()
        data["content_renderings"][1]["copy"]["label"] = "Description removed because the author left"
        with self.assertRaisesRegex(ValueError, "redacted_description: forbidden term 'because'"):
            validate(data)

    def test_content_rendering_copy_paraphrased_in_document_is_rejected(self):
        document = DOCUMENT.replace('"Former member"', '"Previous member"')
        with self.assertRaisesRegex(ValueError, "Content renderings does not carry the canonical copy 'Former member' verbatim"):
            validate(taxonomy(), document)

    def test_content_rendering_copy_changed_in_data_only_is_rejected(self):
        data = taxonomy()
        data["content_renderings"][4]["copy"]["label"] = "Incomplete total"
        with self.assertRaisesRegex(ValueError, "does not carry the canonical copy 'Incomplete total' verbatim"):
            validate(data)

    def test_content_rendering_absent_from_document_is_rejected(self):
        lines = DOCUMENT.splitlines(keepends=True)
        document = "".join(line for line in lines if not line.startswith("| `pseudonymised_viewer` |"))
        with self.assertRaisesRegex(ValueError, "Document does not list content rendering `pseudonymised_viewer`"):
            validate(taxonomy(), document)

    def test_content_rendering_in_document_but_not_in_data_is_rejected(self):
        row = "| `partial_total` |"
        document = DOCUMENT.replace(row, "| `hidden_balance` | Planted. | \"Planted\" |\n" + row)
        with self.assertRaisesRegex(ValueError, "Document lists content rendering `hidden_balance` that the data file does not publish"):
            validate(taxonomy(), document)

    def test_content_rendering_colliding_with_a_state_is_rejected(self):
        data = taxonomy()
        data["content_renderings"][0]["id"] = "empty"
        with self.assertRaisesRegex(ValueError, "Content rendering empty collides with a state, condition, reason or cause identifier"):
            validate(data)

    def test_content_rendering_colliding_with_a_condition_reason_or_cause_is_rejected(self):
        # C2/Q2 of the #166 reviews: the same reserved set as for reasons.
        for taken in ("rate_limited", "force_stopped", "device"):
            data = taxonomy()
            data["content_renderings"][0]["id"] = taken
            with self.assertRaisesRegex(ValueError, f"Content rendering {taken} collides with"):
                validate(data)

    def test_reason_colliding_with_a_condition_or_cause_identifier_is_rejected(self):
        for taken in ("rate_limited", "device"):
            data = taxonomy()
            condition(data, "capture_paused_by_platform")["reasons"].append({
                "id": taken,
                "client": "android",
                "description": "Planted.",
                "clears_when": "Planted.",
                "published_by": "Planted.",
            })
            with self.assertRaisesRegex(ValueError, f"Reason identifier '{taken}' collides"):
                validate(data)

    def test_content_rendering_copy_over_sixty_characters_is_rejected(self):
        # Q1 of the #166 QA review: the plain_language limit is enforced for rendering copy.
        data = taxonomy()
        long_label = "Former member whose details are no longer available on this shared record"
        self.assertGreater(len(long_label), 60)
        data["content_renderings"][0]["copy"]["label"] = long_label
        with self.assertRaisesRegex(ValueError, "erased_member_placeholder: copy is longer than 60 characters"):
            validate(data)

    def test_content_rendering_copy_of_exactly_sixty_characters_is_accepted(self):
        data = taxonomy()
        label = "Former member of this group whose account is no longer here."
        self.assertEqual(len(label), 60)
        data["content_renderings"][0]["copy"]["label"] = label
        document = DOCUMENT.replace('"Former member"', f'"{label}"')
        validate(data, document)

    def test_duplicate_content_rendering_is_rejected(self):
        data = taxonomy()
        data["content_renderings"].append(copy.deepcopy(data["content_renderings"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate content rendering identifier"):
            validate(data)

    def test_content_rendering_claiming_a_state_is_rejected_by_schema(self):
        data = taxonomy()
        data["content_renderings"][0]["rendered_in"] = "permission_denied"
        with self.assertRaisesRegex(ValueError, "expected constant 'content'"):
            validate(data)

    def test_version_history_ending_elsewhere_is_rejected(self):
        data = taxonomy()
        data["taxonomy_version"] = "1.2.0"
        document = DOCUMENT.replace("version 1.1.0", "version 1.2.0")
        with self.assertRaisesRegex(ValueError, "version_history must end with the current taxonomy_version"):
            validate(data, document)

    def test_version_history_with_wrong_bump_kind_is_rejected(self):
        data = taxonomy()
        data["version_history"][-1]["bump"] = "patch"
        with self.assertRaisesRegex(ValueError, "1.1.0 is not a patch bump from 1.0.0"):
            validate(data)

    def test_version_history_not_starting_at_first_published_version_is_rejected(self):
        data = taxonomy()
        data["version_history"] = data["version_history"][1:]
        with self.assertRaisesRegex(ValueError, "must start with the first published version 1.0.0"):
            validate(data)

    def test_empty_version_history_is_rejected_by_schema_and_tolerated_by_the_rules(self):
        # C4 of the #166 core review: the schema rejects an empty history; the rules alone skip it
        # instead of raising an IndexError.
        data = taxonomy()
        data["version_history"] = []
        with self.assertRaisesRegex(ValueError, "fewer than 1 items"):
            validate(data)
        module.check_taxonomy(data, DOCUMENT)

    def test_version_history_entry_absent_from_document_is_rejected(self):
        document = DOCUMENT.replace("1.0.0", "1.0.x")
        with self.assertRaisesRegex(ValueError, "Document does not mention version history entry 1.0.0"):
            validate(taxonomy(), document)

    def test_document_omitting_a_placeholder_is_rejected(self):
        # {item} appears in no canonical string, so the placeholder mention check is its only guard.
        self.assertEqual(DOCUMENT.count("`{item}`"), 1)
        document = DOCUMENT.replace("`{item}`", "`{items}`")
        with self.assertRaisesRegex(ValueError, "Document does not mention placeholder `{item}`"):
            validate(taxonomy(), document)
        document = DOCUMENT.replace("`{last_updated}`", "`{last-updated}`")
        with self.assertRaisesRegex(ValueError, "does not carry the canonical copy 'Last updated {last_updated}'"):
            validate(taxonomy(), document)

    def test_optional_1_1_0_blocks_may_be_absent(self):
        # Every 1.1.0 addition other than the pinned reason identifiers is optional: a data file
        # without version_history, renderings, label_by_variant or submit_label still validates
        # against the new schema and rules with a matching document.
        data = taxonomy()
        for key in ("version_history", "reason_rule", "content_renderings", "content_rendering_rule"):
            del data[key]
        del state(data, "error")["recovery_action"]["label_by_variant"]
        data["placeholders"] = [item for item in data["placeholders"] if item["id"] != "submit_label"]
        summary = validate(data)
        self.assertEqual((summary["reasons"], summary["content_renderings"]), (7, 0))

    def test_data_file_shaped_like_1_0_0_fails_only_on_the_pinned_reasons(self):
        # The published reason identifiers are required like the eight states: a data file that
        # drops them (the 1.0.0 shape) is rejected by name, so a removal needs a major bump.
        data = taxonomy()
        for key in ("version_history", "reason_rule", "content_renderings", "content_rendering_rule"):
            del data[key]
        for item in data["contract_conditions"]:
            item.pop("reasons", None)
        del state(data, "error")["recovery_action"]["label_by_variant"]
        data["placeholders"] = [item for item in data["placeholders"] if item["id"] != "submit_label"]
        with self.assertRaisesRegex(ValueError, "Missing published reason identifier force_stopped under capture_paused_by_platform"):
            validate(data)


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
