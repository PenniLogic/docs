"""Tests for the published test strategy and its reconciliation check (PenniLogic/docs#22).

Each acceptance criterion of the ticket maps to a named test, and every reconciliation rule is proven to
bite with a planted defect: an unowned category, a dangling identifier, a wrong identity, a not-planned
owner, a package with no published number and a document that drifted from the data. The tests prove the
published data, schema, inventory snapshot and document; they are not a harness and claim no coverage,
mutation, accessibility, load or device result.
"""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "scripts" / "check_test_strategy.py"
spec = importlib.util.spec_from_file_location("check_test_strategy", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

STRATEGY = module.load_json(ROOT / module.STRATEGY)
SCHEMA = module.load_json(ROOT / module.SCHEMA)
INVENTORY = module.load_json(ROOT / module.INVENTORY)
DOCUMENT = (ROOT / module.DOCUMENT).read_text(encoding="utf-8")
CATEGORIES = {category["id"]: category for category in STRATEGY["categories"]}
PACKAGES = {package["id"]: package for package in STRATEGY["packages"]}
LANES = {lane["id"]: lane for lane in STRATEGY["device_matrix"]}


def strategy():
    return copy.deepcopy(STRATEGY)


def inventory():
    return copy.deepcopy(INVENTORY)


def category(data, category_id):
    return next(item for item in data["categories"] if item["id"] == category_id)


def package(data, package_id):
    return next(item for item in data["packages"] if item["id"] == package_id)


def issue(data, reference):
    return next(item for item in data["issues"] if item["reference"] == reference)


def check(data=None, snapshot=None, document=None):
    data = STRATEGY if data is None else data
    module.load_check("check_client_states").validate_schema(data, SCHEMA)
    return module.check_strategy(data, INVENTORY if snapshot is None else snapshot, DOCUMENT if document is None else document)


class PublishedFilesTests(unittest.TestCase):
    def test_published_strategy_reconciles_with_zero_unowned_categories(self):
        summary = module.validate_strategy(ROOT)
        self.assertEqual(summary["categories"], len(STRATEGY["categories"]))
        self.assertEqual(summary["strategy_version"], STRATEGY["strategy_version"])
        self.assertEqual(summary["issues"], INVENTORY["issue_count"])
        self.assertGreaterEqual(summary["owner_repositories"], 7)

    def test_main_reports_success(self):
        self.assertEqual(module.main([]), 0)

    def test_main_reports_failure_for_missing_files(self):
        original = module.ROOT
        module.ROOT = Path(tempfile.gettempdir()) / "pennilogic-missing-test-strategy"
        try:
            self.assertEqual(module.main([]), 1)
        finally:
            module.ROOT = original

    def test_render_prints_every_block(self):
        process = subprocess.run(
            [sys.executable, str(path), "--render"], capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        for name in module.render_document_blocks(STRATEGY):
            self.assertIn(f"<!-- {name} -->", process.stdout)

    def test_data_files_use_lf_line_endings_and_ascii(self):
        for relative in (module.STRATEGY, module.SCHEMA, module.INVENTORY):
            raw = (ROOT / relative).read_bytes()
            self.assertNotIn(b"\r\n", raw, relative)
            raw.decode("ascii")
            self.assertTrue(raw.endswith(b"\n"), relative)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "dup.json"
            target.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
                module.load_json(target)

    def test_schema_rejects_unknown_top_level_key(self):
        data = strategy()
        data["unexpected"] = 1
        with self.assertRaisesRegex(ValueError, "unexpected property"):
            check(data)


class AcceptanceCriteriaTests(unittest.TestCase):
    """One test per acceptance criterion in PenniLogic/docs#22."""

    def test_layer_table_covers_every_required_layer_and_category(self):
        for required in module.REQUIRED_CATEGORIES:
            self.assertIn(required, CATEGORIES)
        layers = {CATEGORIES[name]["layer"] for name in CATEGORIES}
        for layer in ("Domain/ledger", "Debt maths", "Parsers", "API", "Android", "Web", "Admin", "Security"):
            self.assertIn(layer, layers)
        self.assertIn("Property-based", CATEGORIES["domain_ledger_property"]["approach"])
        self.assertIn("independently written implementation", CATEGORIES["debt_maths_independent_model"]["approach"])
        self.assertIn("Golden-corpus", CATEGORIES["parser_golden_corpus"]["approach"])
        self.assertIn("OpenAPI", CATEGORIES["api_contract"]["approach"])
        self.assertIn("API 31", CATEGORIES["android_unit_instrumented"]["approach"])
        self.assertIn("Playwright", CATEGORIES["web_e2e_journeys"]["approach"])
        self.assertIn("actively attempt violations", CATEGORIES["security_negative_tests"]["approach"])

    def test_every_category_has_an_owner_that_resolves_and_states_its_signal(self):
        index = module.validate_inventory(INVENTORY)
        for item in STRATEGY["categories"]:
            self.assertTrue(item["owners"], item["id"])
            self.assertTrue(item["evidence"].strip(), item["id"])
            for owner in item["owners"]:
                resolved = module.resolve_owner(owner, index, item["id"])
                self.assertEqual(resolved["reference"], owner["reference"])

    def test_owner_references_use_public_identifiers_only(self):
        for item in STRATEGY["categories"] + STRATEGY["deliverables"] + STRATEGY["device_matrix"]:
            for owner in item["owners"]:
                self.assertRegex(owner["reference"], module.REFERENCE)
        self.assertEqual(STRATEGY["reference_format"], module.REFERENCE.pattern)

    def test_test_data_policy_is_synthetic_only(self):
        policy = STRATEGY["test_data_policy"]
        self.assertIs(policy["synthetic_only"], True)
        self.assertIs(policy["production_data_in_lower_environments"], False)
        self.assertIs(policy["raw_message_content_in_fixtures"], False)
        self.assertIn("Production data never reaches any lower environment", DOCUMENT)
        self.assertTrue(policy["fixture_families"])

    def test_device_matrix_defines_physical_mid_range_indian_sim_device_without_claiming_it(self):
        lane = LANES["physical_mid_range_indian_sim"]
        self.assertEqual(lane["kind"], "physical")
        self.assertEqual(lane["tier"], "mid-range")
        self.assertEqual(lane["sim"], {"required": True, "country": "IN"})
        self.assertEqual(lane["availability"], "required_not_yet_available")
        self.assertEqual(lane["procurement"], {"reference": "PenniLogic/android#14", "identity": "T-QA-07"})
        self.assertEqual(LANES["emulator_api_31"]["android_api_level"], 31)
        self.assertEqual(LANES["emulator_current"]["android_api_level"], "current")
        self.assertIn("the device does not exist yet", DOCUMENT)

    def test_coverage_floors_are_per_package_with_mutation_on_money_paths(self):
        for item in STRATEGY["packages"]:
            self.assertIsInstance(item["line_coverage_floor_percent"], int, item["id"])
            self.assertIsInstance(item["branch_coverage_floor_percent"], int, item["id"])
            if item["money_path"]:
                self.assertIn("mutation_score_floor_percent", item, item["id"])
                self.assertGreaterEqual(item["line_coverage_floor_percent"], 95, item["id"])
        domains = {item["domain"] for item in STRATEGY["packages"] if item["money_path"]}
        for domain in module.REQUIRED_MONEY_DOMAINS:
            self.assertIn(domain, domains)
        self.assertIn("a package without a mutation floor may not carry money-path code", DOCUMENT)

    def test_flake_policy_publishes_ceiling_retry_limit_and_consequences(self):
        policy = STRATEGY["flake_policy"]
        self.assertEqual(policy["quarantine_rate_ceiling_percent"], 2)
        self.assertEqual(policy["retry_limit"], 1)
        self.assertEqual(policy["money_path_retry_limit"], 0)
        for key in ("on_quarantine_ceiling_exceeded", "on_retry_limit_exceeded", "on_quarantine_expired"):
            self.assertTrue(policy[key].strip(), key)
        self.assertIn("never silently retry into green", DOCUMENT)

    def test_definitions_of_ready_and_done_are_published_with_threat_model_and_privacy_review(self):
        ready = {item["id"]: item for item in STRATEGY["definition_of_ready"]}
        done = {item["id"]: item for item in STRATEGY["definition_of_done"]}
        self.assertEqual(ready["threat_model_refreshed"]["owners"][0]["identity"], "T-QA-14")
        for phrase in ("ingestion boundary", "raw content never leaving the device", "parser-config signing chain"):
            self.assertIn(phrase, ready["threat_model_refreshed"]["text"])
        self.assertEqual({owner["identity"] for owner in ready["privacy_payload_reviewed"]["owners"]}, {"T-CMP-03", "T-QA-09"})
        for required in module.REQUIRED_DONE_ITEMS:
            self.assertIn(required, done)
        self.assertIn("### Definition of Ready", DOCUMENT)
        self.assertIn("### Definition of Done", DOCUMENT)

    def test_accessibility_conformance_target_is_explicit_standard_version_and_level(self):
        accessibility = STRATEGY["accessibility"]
        self.assertEqual((accessibility["standard"], accessibility["version"], accessibility["level"]), ("WCAG", "2.2", "AA"))
        self.assertIn("**The conformance target is WCAG 2.2 AA.**", DOCUMENT)
        for surface in ("web", "admin", "android"):
            self.assertIn("WCAG 2.2 AA", accessibility["surfaces"][surface])

    def test_red_team_scenarios_and_independent_model_harness_are_owned_deliverables(self):
        deliverables = {item["id"]: item for item in STRATEGY["deliverables"]}
        self.assertEqual(deliverables["independent_model_harness"]["owners"][0]["identity"], "T-QA-01")
        self.assertEqual({owner["identity"] for owner in deliverables["red_team_scenarios"]["owners"]}, {"T-QA-10", "T-ADM-12"})

    def test_numbers_are_machine_readable_and_keyed_by_package(self):
        for item in STRATEGY["packages"]:
            self.assertRegex(item["id"], module.PACKAGE_ID)
        self.assertIn("money_path_harness_minutes", STRATEGY["pipeline_budgets"])
        gates = {budget["gate"] for budget in STRATEGY["performance_budgets"]}
        self.assertTrue(gates <= set(CATEGORIES))

    def test_change_classes_tell_each_change_when_evidence_is_mandatory(self):
        classes = {item["id"]: item for item in STRATEGY["change_classes"]}
        for required in module.REQUIRED_CHANGE_CLASSES:
            self.assertIn(required, classes)
        for item in classes.values():
            self.assertTrue(item["mandatory_categories"], item["id"])
            self.assertTrue(set(item["mandatory_categories"]) <= set(CATEGORIES), item["id"])
        self.assertIn("mutation_testing", classes["money_path"]["mandatory_categories"])
        self.assertIn("privacy_traffic_inspection", classes["parser"]["mandatory_categories"])

    def test_privacy_traffic_inspection_categories_and_evidence_tickets_are_named(self):
        owners = {owner["identity"] for owner in CATEGORIES["privacy_traffic_inspection"]["owners"]}
        self.assertEqual(owners, {"T-QA-09", "T-CMP-03"})
        self.assertIn("## 13. Privacy traffic inspection is not code review", DOCUMENT)

    def test_review_cadence_and_refresh_command_are_published(self):
        cadence = STRATEGY["review_cadence"]
        self.assertEqual(cadence["inventory_refresh_command"], module.REFRESH_COMMAND)
        self.assertTrue(any("epic" in trigger for trigger in cadence["triggers"]))
        self.assertIn(module.REFRESH_COMMAND, DOCUMENT)


class PlantedDefectTests(unittest.TestCase):
    """Every reconciliation rule is proven to bite."""

    def test_unowned_category_fails(self):
        data = strategy()
        category(data, "load_stress_soak")["owners"] = []
        with self.assertRaisesRegex(ValueError, "load_stress_soak has no owning issue|fewer than 1 items"):
            check(data)

    def test_planted_unowned_category_fails(self):
        data = strategy()
        data["categories"].append({
            "id": "planted_unowned", "name": "Planted", "layer": "Nowhere", "approach": "Asserted without an owner",
            "owners": [], "evidence": "none",
        })
        with self.assertRaises(ValueError):
            check(data)

    def test_dangling_identifier_fails(self):
        data = strategy()
        category(data, "chaos_fault_injection")["owners"] = [{"reference": "PenniLogic/infra#999999", "identity": "T-QA-05"}]
        with self.assertRaisesRegex(ValueError, "dangling identifier"):
            check(data)

    def test_legacy_bare_reference_is_rejected(self):
        data = strategy()
        category(data, "chaos_fault_injection")["owners"] = [{"reference": "infra#29", "identity": "T-QA-05"}]
        with self.assertRaisesRegex(ValueError, "PenniLogic/<repository>#<number>|does not match"):
            check(data)

    def test_wrong_identity_behind_a_valid_number_fails(self):
        data = strategy()
        category(data, "chaos_fault_injection")["owners"] = [{"reference": "PenniLogic/infra#29", "identity": "T-QA-01"}]
        with self.assertRaisesRegex(ValueError, "carries identity T-QA-05.*, not 'T-QA-01'"):
            check(data)

    def test_owner_closed_as_not_planned_owns_nothing(self):
        snapshot = inventory()
        record = issue(snapshot, "PenniLogic/infra#29")
        record["state"], record["state_reason"] = "closed", "not_planned"
        with self.assertRaisesRegex(ValueError, "closed as not_planned and owns nothing"):
            check(snapshot=snapshot)

    def test_owner_closed_as_completed_still_owns(self):
        snapshot = inventory()
        record = issue(snapshot, "PenniLogic/infra#29")
        record["state"], record["state_reason"] = "closed", "completed"
        check(snapshot=snapshot)

    def test_required_category_cannot_be_removed(self):
        data = strategy()
        data["categories"] = [item for item in data["categories"] if item["id"] != "disaster_recovery_restore"]
        with self.assertRaisesRegex(ValueError, "Missing required verification category: disaster_recovery_restore"):
            check(data)

    def test_package_without_line_number_fails(self):
        data = strategy()
        del package(data, "web.app")["line_coverage_floor_percent"]
        with self.assertRaisesRegex(ValueError, "line_coverage_floor_percent|line coverage floor has no published number"):
            check(data)

    def test_package_without_branch_number_fails(self):
        data = strategy()
        del package(data, "web.app")["branch_coverage_floor_percent"]
        with self.assertRaisesRegex(ValueError, "branch_coverage_floor_percent|branch coverage floor has no published number"):
            check(data)

    def test_added_package_with_no_published_number_fails(self):
        data = strategy()
        data["packages"].append({
            "id": "api.planted", "repository": "PenniLogic/api", "domain": "planted",
            "description": "A package added to the inventory without any number", "money_path": False,
        })
        with self.assertRaises(ValueError):
            check(data)

    def test_money_path_package_without_mutation_floor_fails(self):
        data = strategy()
        del package(data, "api.split")["mutation_score_floor_percent"]
        with self.assertRaisesRegex(ValueError, "money-path package with no published mutation-score floor"):
            check(data)

    def test_money_path_floor_below_minimum_fails(self):
        data = strategy()
        package(data, "api.split")["mutation_score_floor_percent"] = 50
        with self.assertRaisesRegex(ValueError, "below the money-path minimum"):
            check(data)

    def test_missing_money_domain_fails(self):
        data = strategy()
        package(data, "api.split")["money_path"] = False
        with self.assertRaisesRegex(ValueError, "No money-path package carries the split domain"):
            check(data)

    def test_percent_out_of_range_fails(self):
        data = strategy()
        package(data, "web.app")["line_coverage_floor_percent"] = 101
        with self.assertRaisesRegex(ValueError, "between 0 and 100"):
            check(data)

    def test_flake_policy_without_consequence_fails(self):
        data = strategy()
        data["flake_policy"]["on_retry_limit_exceeded"] = " "
        with self.assertRaisesRegex(ValueError, "must state what happens|shorter than"):
            check(data)

    def test_flake_retry_limit_must_be_integer(self):
        data = strategy()
        data["flake_policy"]["retry_limit"] = 1.5
        with self.assertRaisesRegex(ValueError, "retry_limit"):
            check(data)

    def test_accessibility_target_cannot_be_weakened(self):
        data = strategy()
        data["accessibility"]["level"] = "A"
        with self.assertRaisesRegex(ValueError, "expected constant 'AA'|accessibility.level"):
            check(data)

    def test_physical_device_cannot_be_recorded_as_available(self):
        data = strategy()
        next(lane for lane in data["device_matrix"] if lane["id"] == "physical_mid_range_indian_sim")["availability"] = "available_in_ci"
        with self.assertRaisesRegex(ValueError, "not recorded as available"):
            check(data)

    def test_physical_device_requires_indian_sim(self):
        data = strategy()
        next(lane for lane in data["device_matrix"] if lane["id"] == "physical_mid_range_indian_sim")["sim"]["country"] = "US"
        with self.assertRaisesRegex(ValueError, "must require an Indian SIM"):
            check(data)

    def test_threat_model_item_must_name_ingestion_scope(self):
        data = strategy()
        item = next(item for item in data["definition_of_ready"] if item["id"] == "threat_model_refreshed")
        item["text"] = "A dated STRIDE threat-model refresh for the epic"
        with self.assertRaisesRegex(ValueError, "must name the ingestion boundary scope"):
            check(data)

    def test_document_drift_from_data_fails(self):
        data = strategy()
        package(data, "api.ledger")["line_coverage_floor_percent"] = 96
        with self.assertRaisesRegex(ValueError, "does not carry the packages table rendered from the data verbatim"):
            check(data)

    def test_document_without_conformance_statement_fails(self):
        with self.assertRaisesRegex(ValueError, "accessibility conformance target as an explicit statement"):
            check(document=DOCUMENT.replace(module.CONFORMANCE_STATEMENT, "The conformance target is WCAG."))

    def test_inventory_reference_disagreeing_with_number_fails(self):
        snapshot = inventory()
        issue(snapshot, "PenniLogic/infra#29")["number"] = 30
        with self.assertRaisesRegex(ValueError, "disagrees with its repository or number"):
            check(snapshot=snapshot)

    def test_inventory_wrong_repository_id_fails(self):
        snapshot = inventory()
        snapshot["repositories"]["PenniLogic/docs"]["id"] = 1
        with self.assertRaisesRegex(ValueError, "does not carry id 1394134442"):
            check(snapshot=snapshot)

    def test_inventory_wrong_organization_fails(self):
        snapshot = inventory()
        snapshot["organization_id"] = 323571547
        with self.assertRaisesRegex(ValueError, "must be a snapshot of PenniLogic"):
            check(snapshot=snapshot)

    def test_inventory_duplicate_plan_identity_fails(self):
        snapshot = inventory()
        issue(snapshot, "PenniLogic/infra#29")["plan_id"] = "T-QA-01"
        with self.assertRaisesRegex(ValueError, "Plan identity T-QA-01 is carried by both"):
            check(snapshot=snapshot)

    def test_inventory_count_mismatch_fails(self):
        snapshot = inventory()
        snapshot["issue_count"] += 1
        with self.assertRaisesRegex(ValueError, "issue_count does not match"):
            check(snapshot=snapshot)


class RefreshTests(unittest.TestCase):
    """The refresh never handles a token and refuses a foreign identity; no network is used here."""

    def test_child_environment_removes_token_variables(self):
        environ = {"GH_TOKEN": "x", "GITHUB_TOKEN": "y", "GIT_CONFIG_PARAMETERS": "z", "PATH": "p", "HOME": "h"}
        self.assertEqual(module.child_environment(environ), {"PATH": "p", "HOME": "h"})

    def test_redact_hides_token_shaped_text(self):
        text = "HTTP 401 for ghp_" + "a" * 36 + " and github_pat_" + "b" * 22
        redacted = module.redact(text)
        self.assertNotIn("ghp_", redacted)
        self.assertNotIn("github_pat_", redacted)
        self.assertEqual(redacted.count("[redacted]"), 2)

    def test_refresh_refuses_foreign_identity(self):
        def run(args, payload=None):
            return {"login": "someone-else", "id": 1}
        with self.assertRaisesRegex(RuntimeError, "authenticated as 'someone-else'"):
            module.fetch_inventory(run=run)

    def test_refresh_refuses_wrong_repository_id(self):
        def run(args, payload=None):
            if args[:2] == ["api", "user"]:
                return {"login": module.OPERATOR, "id": module.OPERATOR_ID}
            if args[1].startswith("orgs/"):
                return {"id": module.ORGANIZATION_ID}
            return {"data": {"repository": {"databaseId": 1, "issues": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": []}}}}
        with self.assertRaisesRegex(RuntimeError, "resolved to id 1"):
            module.fetch_inventory(run=run)

    def test_refresh_builds_a_valid_inventory_from_pages(self):
        pages = {}

        def run(args, payload=None):
            if args[:2] == ["api", "user"]:
                return {"login": module.OPERATOR, "id": module.OPERATOR_ID}
            if args[1].startswith("orgs/"):
                return {"id": module.ORGANIZATION_ID}
            name = payload["variables"]["name"]
            full_name = f"PenniLogic/{name}"
            first = payload["variables"]["after"] is None
            pages[full_name] = pages.get(full_name, 0) + 1
            nodes = []
            if name == "docs":
                if first:
                    nodes = [{"number": 1, "title": "  Taxonomy  ", "state": "OPEN", "stateReason": None,
                              "body": "<!-- plan-id: T-UX-01 -->\nOriginal specification: [https://github.com/PenniLogic-old/docs/issues/52](x)"}]
                else:
                    nodes = [{"number": 22, "title": "Strategy", "state": "CLOSED", "stateReason": "COMPLETED",
                              "body": "Original specification: https://github.com/PenniLogic-old/docs/issues/21"}]
            return {"data": {"repository": {
                "databaseId": module.REPOSITORY_IDS[full_name],
                "issues": {"pageInfo": {"hasNextPage": first and name == "docs", "endCursor": "c1"}, "nodes": nodes},
            }}}

        result = module.fetch_inventory(run=run, now=module.datetime.datetime(2026, 9, 30, tzinfo=module.datetime.timezone.utc))
        index = module.validate_inventory(result)
        self.assertEqual(pages["PenniLogic/docs"], 2)
        self.assertEqual(result["issue_count"], 2)
        self.assertEqual(result["snapshot_at"], "2026-09-30T00:00:00Z")
        self.assertEqual(index["PenniLogic/docs#1"]["title"], "Taxonomy")
        self.assertEqual(index["PenniLogic/docs#1"]["plan_id"], "T-UX-01")
        self.assertEqual(index["PenniLogic/docs#1"]["source"], "PenniLogic-old/docs#52")
        self.assertEqual(index["PenniLogic/docs#22"]["state_reason"], "completed")
        self.assertEqual(index["PenniLogic/docs#22"]["source"], "PenniLogic-old/docs#21")
        self.assertIsNone(index["PenniLogic/docs#22"]["plan_id"])

    def test_gh_failure_is_reported_without_token_text(self):
        def runner(command, **kwargs):
            self.assertNotIn("GH_TOKEN", kwargs["env"])
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="HTTP 401 ghp_" + "c" * 36)
        with self.assertRaisesRegex(RuntimeError, r"gh api user failed: HTTP 401 \[redacted\]"):
            module.gh(["api", "user"], runner=runner, environ={"GH_TOKEN": "secret", "PATH": "p"})

    def test_published_snapshot_has_source_identity_for_every_migrated_issue(self):
        migrated = [item for item in INVENTORY["issues"] if item["source"]]
        self.assertGreaterEqual(len(migrated), 400)
        self.assertEqual(INVENTORY["operator"], "basiltt")
        self.assertEqual(json.loads(json.dumps(INVENTORY))["organization_id"], module.ORGANIZATION_ID)


if __name__ == "__main__":
    unittest.main()
