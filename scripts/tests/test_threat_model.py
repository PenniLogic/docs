"""Tests for the per-epic STRIDE threat-model refresh (T-QA-14, PenniLogic/docs#48).

Each acceptance criterion and each test the ticket names maps to a test below, and every rule is
proven to bite with a planted defect. These tests prove the published model, records, schema, checker
and documents; they implement no mitigation and claim nothing about T-GOV-04, which does not exist yet.
"""

import contextlib
import copy
import datetime
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "scripts" / "check_threat_model.py"
spec = importlib.util.spec_from_file_location("check_threat_model", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

SCHEMA = module.load_json(ROOT / module.SCHEMA)
MODEL = module.load_json(ROOT / module.MODEL)
RECORDS = {p.stem: module.load_json(p) for p in sorted((ROOT / module.RECORDS).glob("*.json"))}
AGENT_POLICY = module.load_json(ROOT / ".github" / "agent-policy.json")
BASE_EPIC = "E33"  # a published record whose only refresh is current with every finding handed off
TODAY = datetime.date(2026, 10, 1)
REFRESHED = ("E01", "E07", "E25", "E26", "E33", "E34")


def record(epic=BASE_EPIC):
    return copy.deepcopy(RECORDS[epic])


def latest(rec):
    return rec["refreshes"][-1]


def review(refresh, category_id):
    return next(item for item in refresh["categories"] if item["id"] == category_id)


def finding(refresh, finding_id):
    return next(item for item in refresh["findings"] if item["id"] == finding_id)


def validate_record(rec):
    module.validate_schema(rec, module.definition(SCHEMA, "record"))


def problems(rec, epic=BASE_EPIC, model=MODEL, today=TODAY):
    validate_record(rec)
    epic_issues = {r["issue"] for r in RECORDS.values() if r["issue"]}
    return module.check_record(rec, epic, model, today, epic_issues)


def evaluate(rec, epic=BASE_EPIC, model=MODEL, today=TODAY):
    return module.evaluate_epic(rec, epic, model, today, problems(rec, epic, model, today))


class TempRootMixin:
    """Build a repository-shaped folder with real documents and chosen records."""

    def temp_root(self, records, model=MODEL, template_suffix=""):
        folder = Path(tempfile.mkdtemp(prefix="pennilogic-threat-model-"))
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        threat_model = folder / "governance" / "threat-model"
        (threat_model / "records").mkdir(parents=True)
        (threat_model / "categories.json").write_text(json.dumps(model), encoding="utf-8")
        shutil.copy(ROOT / module.SCHEMA, threat_model / "schema.json")
        shutil.copy(ROOT / module.README, threat_model / "README.md")
        template = (ROOT / module.TEMPLATE).read_text(encoding="utf-8") + template_suffix
        (threat_model / "STRIDE-refresh-template.md").write_text(template, encoding="utf-8")
        for epic, rec in records.items():
            (threat_model / "records" / f"{epic}.json").write_text(json.dumps(rec), encoding="utf-8")
        (folder / "planning" / "source").mkdir(parents=True)
        backlog = {
            "schema_version": 1, "item_count": len(records),
            "items": [{"title": f"[EPIC] {epic} - {rec.get('title', epic)}"} for epic, rec in records.items()],
        }
        (folder / "planning" / "backlog.json").write_text(json.dumps(backlog), encoding="utf-8")
        (folder / "planning" / "source" / "epics.json").write_text(json.dumps({"items": []}), encoding="utf-8")
        return folder

    def run_main(self, root, argv):
        original = module.ROOT
        module.ROOT = root
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = module.main(argv)
        finally:
            module.ROOT = original
        return code, out.getvalue(), err.getvalue()


class PublishedDataTests(TempRootMixin, unittest.TestCase):
    def test_published_model_records_and_documents_validate(self):
        summary = module.run(ROOT, TODAY)
        self.assertEqual(summary["counts"]["invalid"], 0)
        self.assertEqual(len(summary["epics"]), 38)
        self.assertEqual(sum(summary["counts"].values()), 38)
        self.assertEqual(summary["categories"], 13)
        self.assertEqual(summary["cadence_weeks"], 12)

    def test_every_epic_entering_implementation_has_a_dated_refresh_naming_owner_and_categories(self):
        """AC: every epic entering implementation has a dated record naming its owner and categories."""
        required = module.required_categories(MODEL, MODEL["model_version"])
        for epic in REFRESHED:
            refresh = latest(RECORDS[epic])
            datetime.date.fromisoformat(refresh["date"])
            self.assertEqual(refresh["trigger"], "definition_of_ready", epic)
            self.assertIn(refresh["performed_by"]["accountable"], MODEL["accountable_owners"], epic)
            self.assertRegex(refresh["performed_by"]["session"], r"^copilot-session:", epic)
            self.assertEqual({item["id"] for item in refresh["categories"]}, required, epic)
            self.assertTrue(refresh["tickets_in_scope"], epic)

    def test_unrefreshed_epics_carry_an_explicit_not_refreshed_record(self):
        for epic, rec in RECORDS.items():
            if epic not in REFRESHED:
                self.assertEqual(rec["refreshes"], [], epic)
                self.assertEqual(rec["owner"]["accountable"], "basiltt", epic)
        self.assertIsNone(RECORDS["E31"]["issue"])
        self.assertIn("No public epic issue", RECORDS["E31"]["note"])

    def test_model_contains_the_seven_previously_missing_categories_each_with_an_owner(self):
        """AC: the model contains all seven previously missing categories, each with an owner."""
        by_id = {category["id"]: category for category in MODEL["categories"]}
        self.assertEqual(len(by_id), 13)
        for category_id in module.ADDED_CATEGORIES:
            category = by_id[category_id]
            self.assertEqual(category["family"], "extension", category_id)
            self.assertEqual(category["baseline_threats"], [], category_id)
            self.assertIn(category["owner"]["accountable"], MODEL["accountable_owners"], category_id)
            self.assertIn(category["owner"]["review_role"], MODEL["review_roles"], category_id)
        for category_id in module.STRIDE_CATEGORIES:
            self.assertEqual(by_id[category_id]["family"], "stride")
            self.assertTrue(by_id[category_id]["baseline_threats"], category_id)

    def test_review_roles_are_the_repository_policy_roles(self):
        self.assertTrue(set(MODEL["review_roles"]).issubset(AGENT_POLICY["review_roles"]))
        for category in MODEL["categories"]:
            self.assertIn(category["owner"]["review_role"], AGENT_POLICY["review_roles"])

    def test_every_finding_in_published_records_is_owned_closed_or_explicitly_open(self):
        """AC: every finding is closed or handed to a named ticket; open ones are reported as blocking."""
        summary = module.run(ROOT, TODAY)
        reported = {(item["epic"], item["finding"]) for item in summary["unowned_findings"]}
        for epic in REFRESHED:
            for item in latest(RECORDS[epic])["findings"]:
                if item["status"] == "open":
                    self.assertIn((epic, item["id"]), reported)
                    self.assertIsNone(item["owner_ticket"])
                elif item["status"] == "handed_off":
                    self.assertRegex(item["owner_ticket"], r"^PenniLogic/")
                    self.assertNotIn(item["owner_ticket"], {r["issue"] for r in RECORDS.values()})
                else:
                    self.assertTrue(item["resolution"])
        blocked = {e["epic"] for e in summary["epics"] if e["status"] == "blocked"}
        self.assertEqual(blocked, {epic for epic, _ in reported})

    def test_records_cover_exactly_the_epics_in_the_planning_inventory(self):
        self.assertEqual(set(module.inventory(ROOT)), set(RECORDS))
        self.assertEqual(len(RECORDS), 38)
        for epic, rec in RECORDS.items():
            self.assertEqual(rec["epic"], epic)

    def test_documents_name_every_category_cadence_and_trigger(self):
        module.check_documents(MODEL, ROOT)
        model = copy.deepcopy(MODEL)
        model["categories"].append(dict(model["categories"][0], id="unwritten_category"))
        with self.assertRaisesRegex(ValueError, "Template does not cover"):
            module.check_documents(model, ROOT)
        model = copy.deepcopy(MODEL)
        model["refresh_triggers"].append({"id": "unwritten_trigger", "description": "x"})
        with self.assertRaisesRegex(ValueError, "README does not publish"):
            module.check_documents(model, ROOT)
        model = copy.deepcopy(MODEL)
        model["cadence_weeks"] = 11
        with self.assertRaisesRegex(ValueError, "cadence"):
            module.check_documents(model, ROOT)

    def test_data_files_use_lf_line_endings_and_utf8(self):
        for file in [ROOT / module.MODEL, ROOT / module.SCHEMA, *(ROOT / module.RECORDS).glob("*.json")]:
            raw = file.read_bytes()
            self.assertNotIn(b"\r\n", raw, file.name)
            raw.decode("utf-8")

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "dup.json"
            target.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
                module.load_json(target)

    def test_main_reports_success_and_prints_the_summary(self):
        code, out, err = self.run_main(ROOT, ["--today", TODAY.isoformat()])
        self.assertEqual(code, 0, err)
        self.assertIn("13 categories, 12-week cadence", out)
        self.assertIn("of 38 epics", out)

    def test_main_gate_mode_passes_a_current_epic_and_fails_the_others(self):
        summary = module.run(ROOT, TODAY)
        by_status = {}
        for evaluation in summary["epics"]:
            by_status.setdefault(evaluation["status"], evaluation["epic"])
        code, out, _ = self.run_main(ROOT, ["--epic", by_status["current"], "--today", TODAY.isoformat()])
        self.assertEqual(code, 0)
        self.assertIn("current", out)
        code, _, err = self.run_main(ROOT, ["--epic", by_status["not_refreshed"], "--today", TODAY.isoformat()])
        self.assertEqual(code, 1)
        self.assertIn("not_refreshed", err)
        self.assertIn("basiltt", err)
        code, _, err = self.run_main(ROOT, ["--epic", "E99", "--today", TODAY.isoformat()])
        self.assertEqual(code, 1)
        self.assertIn("unknown epic", err)

    def test_main_reports_failure_for_missing_files(self):
        code, _, err = self.run_main(Path(tempfile.gettempdir()) / "pennilogic-missing-threat-model", [])
        self.assertEqual(code, 1)
        self.assertIn("Threat-model check failed", err)

    def test_main_rejects_an_invalid_clock(self):
        code, _, err = self.run_main(ROOT, ["--today", "2026-13-40"])
        self.assertEqual(code, 1)
        self.assertIn("not a calendar date", err)


class SchemaTests(unittest.TestCase):
    """Schema test on the refresh record (ticket Tests section)."""

    def test_published_records_and_model_satisfy_the_schema(self):
        module.validate_schema(MODEL, module.definition(SCHEMA, "model"))
        for rec in RECORDS.values():
            validate_record(rec)

    def test_unknown_property_is_rejected(self):
        rec = record()
        latest(rec)["extra"] = "x"
        with self.assertRaisesRegex(ValueError, "unexpected property 'extra'"):
            validate_record(rec)

    def test_missing_required_property_is_rejected(self):
        rec = record()
        del latest(rec)["findings"]
        with self.assertRaisesRegex(ValueError, "missing required property 'findings'"):
            validate_record(rec)

    def test_malformed_date_epic_id_and_severity_are_rejected(self):
        rec = record()
        latest(rec)["date"] = "30/09/2026"
        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_record(rec)
        rec = record()
        rec["epic"] = "EPIC33"
        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_record(rec)
        rec = record()
        latest(rec)["findings"][0]["severity"] = "urgent"
        with self.assertRaisesRegex(ValueError, "is not one of"):
            validate_record(rec)

    def test_owner_ticket_must_be_a_public_pennilogic_issue(self):
        rec = record()
        latest(rec)["findings"][0]["owner_ticket"] = "PenniLogic-old/docs#55"
        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_record(rec)
        rec = record()
        latest(rec)["findings"][0]["owner_ticket"] = "docs#65"
        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_record(rec)

    def test_session_and_role_formats_are_enforced(self):
        rec = record()
        latest(rec)["performed_by"]["session"] = "someone"
        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_record(rec)
        rec = record()
        latest(rec)["performed_by"]["role"] = "Security Lead"
        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_record(rec)

    def test_empty_strings_are_rejected(self):
        rec = record()
        latest(rec)["categories"][0]["analysis"] = ""
        with self.assertRaisesRegex(ValueError, "shorter than 1"):
            validate_record(rec)

    def test_unsupported_schema_keyword_is_an_error_not_a_pass(self):
        with self.assertRaises(module.SchemaError):
            module.validate_schema({"a": 1}, {"type": "object", "oneOf": [{"type": "object"}]})
        with self.assertRaises(module.SchemaError):
            module.validate_schema("x", {"$ref": "#/nowhere"})

    def test_model_rules_reject_missing_category_missing_owner_and_missing_trigger(self):
        model = copy.deepcopy(MODEL)
        model["categories"] = [c for c in model["categories"] if c["id"] != "prompt_injection"]
        with self.assertRaisesRegex(ValueError, "missing the required category 'prompt_injection'"):
            module.check_model(model)
        model = copy.deepcopy(MODEL)
        model["categories"][6]["owner"]["accountable"] = "nobody"
        with self.assertRaisesRegex(ValueError, "not an accountable owner"):
            module.check_model(model)
        model = copy.deepcopy(MODEL)
        model["categories"][6]["owner"]["review_role"] = "wizard"
        with self.assertRaisesRegex(ValueError, "not a published role"):
            module.check_model(model)
        model = copy.deepcopy(MODEL)
        model["refresh_triggers"] = [t for t in model["refresh_triggers"] if t["id"] != "cadence"]
        with self.assertRaisesRegex(ValueError, "missing the required trigger 'cadence'"):
            module.check_model(model)
        model = copy.deepcopy(MODEL)
        model["categories"][0]["added_in_model_version"] = 99
        with self.assertRaisesRegex(ValueError, "ahead of model_version"):
            module.check_model(model)


class InvalidRefreshTests(unittest.TestCase):
    """Invalid-refresh test omitting a required category (ticket Tests section) and its siblings."""

    def test_refresh_omitting_a_required_category_is_invalid_not_partially_credited(self):
        """AC: a refresh that reviews fewer than the required categories is invalid."""
        rec = record()
        refresh = latest(rec)
        refresh["categories"] = [c for c in refresh["categories"] if c["id"] != "prompt_injection"]
        found = problems(rec)
        self.assertTrue(any("reviews 12 of 13 required categories; missing: prompt_injection" in p for p in found), found)
        self.assertEqual(evaluate(rec)["status"], "invalid")

    def test_duplicate_and_unknown_category_reviews_are_invalid(self):
        rec = record()
        latest(rec)["categories"].append(copy.deepcopy(latest(rec)["categories"][0]))
        self.assertTrue(any("reviewed twice" in p for p in problems(rec)))
        rec = record()
        latest(rec)["categories"][0]["id"] = "phlogiston"
        found = problems(rec)
        self.assertTrue(any("outside model version" in p for p in found), found)
        self.assertTrue(any("missing" in p for p in found), found)

    def test_dispositions_require_their_evidence_or_findings(self):
        rec = record()
        item = review(latest(rec), "elevation_of_privilege")
        self.assertEqual(item["disposition"], "controlled")
        item["evidence"] = []
        self.assertTrue(any("controlled without evidence" in p for p in problems(rec)))
        rec = record()
        item = review(latest(rec), "denial_of_service")
        item["disposition"] = "accepted"
        self.assertTrue(any("accepted without evidence" in p for p in problems(rec)))
        rec = record()
        item = review(latest(rec), "spoofing")
        item["findings"] = []
        self.assertTrue(any("finding disposition without findings" in p for p in problems(rec)))
        rec = record()
        item = review(latest(rec), "denial_of_service")
        item["findings"] = ["E33-F01"]
        self.assertTrue(any("lists findings but its disposition" in p for p in problems(rec)))

    def test_findings_and_categories_must_reference_each_other(self):
        rec = record()
        review(latest(rec), "spoofing")["findings"] = ["E33-F99"]
        found = problems(rec)
        self.assertTrue(any("unknown finding E33-F99" in p for p in found), found)
        self.assertTrue(any("E33-F03 is not listed by its category" in p for p in found), found)
        rec = record()
        finding(latest(rec), "E33-F03")["category"] = "tampering"
        found = problems(rec)
        self.assertTrue(any("E33-F03 is not listed by its category 'tampering'" in p for p in found), found)

    def test_finding_must_belong_to_the_epic_and_to_a_reviewed_category(self):
        rec = record()
        item = finding(latest(rec), "E33-F03")
        item["id"] = "E01-F03"
        review(latest(rec), "spoofing")["findings"] = ["E01-F03"]
        self.assertTrue(any("E01-F03 does not belong to E33" in p for p in problems(rec)))
        rec = record()
        finding(latest(rec), "E33-F03")["category"] = "phlogiston"
        self.assertTrue(any("unreviewed category 'phlogiston'" in p for p in problems(rec)))

    def test_future_dated_refresh_is_invalid_beyond_the_one_day_tolerance(self):
        rec = record()
        refresh_date = datetime.date.fromisoformat(latest(rec)["date"])
        self.assertEqual(evaluate(rec, today=refresh_date - datetime.timedelta(days=1))["status"], "current")
        self.assertEqual(evaluate(rec, today=refresh_date - datetime.timedelta(days=2))["status"], "invalid")

    def test_refreshes_must_be_chronological_and_the_latest_is_effective(self):
        rec = record()
        older = copy.deepcopy(latest(rec))
        older["date"] = "2026-01-01"
        rec["refreshes"].append(older)
        self.assertTrue(any("ascending date order" in p for p in problems(rec)))
        rec = record()
        rec["refreshes"].insert(0, older)
        self.assertEqual(evaluate(rec)["latest_refresh"], latest(record())["date"])
        self.assertEqual(evaluate(rec)["status"], "current")

    def test_performer_trigger_and_model_version_are_checked(self):
        rec = record()
        latest(rec)["performed_by"]["accountable"] = "someone-else"
        self.assertTrue(any("not an accountable owner" in p for p in problems(rec)))
        rec = record()
        latest(rec)["trigger"] = "whim"
        self.assertTrue(any("unknown refresh trigger 'whim'" in p for p in problems(rec)))
        rec = record()
        latest(rec)["model_version"] = 7
        self.assertTrue(any("model_version 7 is not between 1 and 1" in p for p in problems(rec)))

    def test_record_level_rules(self):
        rec = record()
        rec["owner"]["accountable"] = "someone-else"
        self.assertTrue(any("record owner" in p for p in problems(rec)))
        rec = record()
        rec["issue"] = None
        self.assertTrue(any("no public epic issue and no note" in p for p in problems(rec)))
        rec["note"] = "Explained."
        self.assertFalse(any("no public epic issue" in p for p in problems(rec)))
        rec = record()
        self.assertTrue(any("file is E34.json" in p for p in problems(rec, epic="E34")))

    def test_records_may_not_contain_urls_or_live_endpoints(self):
        """Security and privacy: the model names attack paths and controls, never a live endpoint."""
        for url in ("https://api.example.test/v1/keys", "postgres://user:pw@db.internal:5432/ledger"):
            rec = record()
            latest(rec)["categories"][0]["evidence"].append(f"see {url}")
            self.assertTrue(any("contains a URL" in p for p in problems(rec)), url)
            self.assertEqual(evaluate(rec)["status"], "invalid")
        for rec in RECORDS.values():
            self.assertIsNone(module.URL.search(json.dumps(rec)), rec["epic"])


class OwnerlessFindingTests(TempRootMixin, unittest.TestCase):
    """Ownerless-finding rejection test (ticket Tests section)."""

    def open_finding(self, rec, finding_id="E33-F03"):
        item = finding(latest(rec), finding_id)
        item.update({"status": "open", "owner_ticket": None, "resolution": None})
        return rec

    def test_finding_with_no_owner_fails_the_refresh(self):
        """AC: a finding with no owner fails the refresh."""
        rec = self.open_finding(record())
        self.assertEqual(problems(rec), [])
        evaluation = evaluate(rec)
        self.assertEqual(evaluation["status"], "blocked")
        self.assertEqual(evaluation["unowned_findings"], ["E33-F03"])
        self.assertIn("E33-F03", evaluation["reasons"][0])

    def test_gate_mode_rejects_an_epic_with_an_unowned_finding_and_names_the_owner(self):
        root = self.temp_root({BASE_EPIC: self.open_finding(record())})
        code, _, err = self.run_main(root, ["--epic", BASE_EPIC, "--today", TODAY.isoformat()])
        self.assertEqual(code, 1)
        self.assertIn("blocked", err)
        self.assertIn("E33-F03", err)
        self.assertIn("basiltt", err)
        code, out, _ = self.run_main(root, ["--today", TODAY.isoformat()])
        self.assertEqual(code, 0, "an honest open finding is reported, not a data error")
        self.assertIn("unowned finding E33-F03 (E33) needs a ticket; owner basiltt", out)

    def test_handed_off_finding_without_a_ticket_is_invalid(self):
        rec = record()
        finding(latest(rec), "E33-F03")["owner_ticket"] = None
        self.assertTrue(any("handed off but names no owner ticket" in p for p in problems(rec)))
        self.assertEqual(evaluate(rec)["status"], "invalid")

    def test_finding_handed_to_an_epic_rather_than_a_ticket_is_invalid(self):
        rec = record()
        finding(latest(rec), "E33-F03")["owner_ticket"] = RECORDS["E01"]["issue"]
        self.assertTrue(any("handed to an epic rather than to a ticket" in p for p in problems(rec)))

    def test_closed_finding_requires_a_resolution_and_no_ticket(self):
        rec = record()
        finding(latest(rec), "E33-F03").update({"status": "closed", "owner_ticket": None, "resolution": None})
        self.assertTrue(any("closed without a resolution" in p for p in problems(rec)))
        rec = record()
        finding(latest(rec), "E33-F03").update({"status": "closed", "resolution": "Already covered by docs#64."})
        self.assertTrue(any("closed but also names an owner ticket" in p for p in problems(rec)))
        finding(latest(rec), "E33-F03")["owner_ticket"] = None
        self.assertEqual(problems(rec), [])
        self.assertEqual(evaluate(rec)["status"], "current")

    def test_status_and_fields_must_agree(self):
        rec = record()
        finding(latest(rec), "E33-F03")["resolution"] = "also resolved"
        self.assertTrue(any("handed off but also carries a resolution" in p for p in problems(rec)))
        rec = record()
        finding(latest(rec), "E33-F03")["status"] = "open"
        self.assertTrue(any("open but carries an owner ticket" in p for p in problems(rec)))

    def test_duplicate_finding_ids_are_invalid(self):
        rec = record()
        latest(rec)["findings"].append(copy.deepcopy(finding(latest(rec), "E33-F03")))
        self.assertTrue(any("duplicate finding id E33-F03" in p for p in problems(rec)))


class StalenessTests(TempRootMixin, unittest.TestCase):
    """Stale-refresh detection test with the clock advanced past the cadence (ticket Tests section)."""

    def test_cadence_is_published_as_a_number_of_weeks(self):
        """AC: the cadence is published as a number of weeks or a named trigger."""
        self.assertEqual(MODEL["cadence_weeks"], 12)
        self.assertIn("12 weeks", (ROOT / module.README).read_text(encoding="utf-8"))
        self.assertTrue({t["id"] for t in MODEL["refresh_triggers"]} >= set(module.REQUIRED_TRIGGERS))

    def test_refresh_older_than_the_cadence_is_reported_as_stale(self):
        """AC: an epic whose refresh is older than the cadence is reported as stale."""
        rec = record()
        refresh_date = datetime.date.fromisoformat(latest(rec)["date"])
        last_day = refresh_date + datetime.timedelta(weeks=MODEL["cadence_weeks"])
        self.assertEqual(evaluate(rec, today=last_day)["status"], "current")
        evaluation = evaluate(rec, today=last_day + datetime.timedelta(days=1))
        self.assertEqual(evaluation["status"], "stale")
        self.assertIn("older than the 12-week cadence", evaluation["reasons"][0])
        self.assertEqual(evaluation["next_refresh_due"], last_day.isoformat())

    def test_gate_mode_treats_a_stale_refresh_as_missing_with_the_clock_advanced(self):
        root = self.temp_root({BASE_EPIC: record()})
        code, _, err = self.run_main(root, ["--epic", BASE_EPIC, "--today", "2027-01-15"])
        self.assertEqual(code, 1)
        self.assertIn("stale", err)
        code, out, _ = self.run_main(root, ["--epic", BASE_EPIC, "--today", TODAY.isoformat()])
        self.assertEqual(code, 0, out)

    def test_stale_epic_still_lists_its_unowned_findings(self):
        rec = record()
        finding(latest(rec), "E33-F03").update({"status": "open", "owner_ticket": None, "resolution": None})
        evaluation = evaluate(rec, today=datetime.date(2027, 6, 1))
        self.assertEqual(evaluation["status"], "stale")
        self.assertTrue(any("unowned finding(s): E33-F03" in r for r in evaluation["reasons"]))

    def test_adding_a_category_makes_earlier_refreshes_stale_until_they_review_it(self):
        model = copy.deepcopy(MODEL)
        model["model_version"] = 2
        model["categories"].append(dict(
            copy.deepcopy(model["categories"][0]), id="new_category", name="New category",
            family="extension", stride_letter=None, added_in_model_version=2, baseline_threats=[],
        ))
        rec = record()
        evaluation = evaluate(rec, model=model)
        self.assertEqual(evaluation["status"], "stale")
        self.assertIn("model version 1", evaluation["reasons"][0])
        # A version-2 refresh that omits the new category is invalid, not stale.
        rec = record()
        latest(rec)["model_version"] = 2
        self.assertEqual(evaluate(rec, model=model)["status"], "invalid")
        self.assertTrue(any("missing: new_category" in p for p in problems(rec, model=model)))
        # Reviewing the new category makes it current again.
        latest(rec)["categories"].append({
            "id": "new_category", "disposition": "not_applicable",
            "analysis": "Nothing in this epic touches it.", "evidence": [], "findings": [],
        })
        self.assertEqual(evaluate(rec, model=model)["status"], "current")
        # The whole-repository run agrees, once the template covers the new category.
        root = self.temp_root({BASE_EPIC: record()}, model=model, template_suffix="\n### `new_category`\n")
        summary = module.run(root, TODAY)
        self.assertEqual(summary["counts"]["stale"], 1)


class InventoryTests(TempRootMixin, unittest.TestCase):
    def test_every_epic_on_the_board_needs_a_record(self):
        root = self.temp_root({"E01": record("E01"), "E02": record("E02")})
        (root / "governance" / "threat-model" / "records" / "E02.json").unlink()
        with self.assertRaisesRegex(ValueError, "Epics without a threat-model record: E02"):
            module.run(root, TODAY)

    def test_record_for_an_unknown_epic_or_with_a_bad_name_fails(self):
        root = self.temp_root({BASE_EPIC: record()})
        stray = root / "governance" / "threat-model" / "records" / "E99.json"
        stray.write_text(json.dumps(record()), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "E99.json has no epic in the planning inventory"):
            module.run(root, TODAY)
        stray.rename(stray.with_name("notes.json"))
        with self.assertRaisesRegex(ValueError, "not named after an epic"):
            module.run(root, TODAY)

    def test_schema_failure_in_one_record_is_reported_as_invalid_for_that_epic_only(self):
        broken = record("E34")
        del broken["owner"]
        impossible = record("E26")
        latest(impossible)["date"] = "2026-02-30"
        root = self.temp_root({BASE_EPIC: record(), "E34": broken, "E26": impossible})
        summary = module.run(root, TODAY)
        statuses = {e["epic"]: e["status"] for e in summary["epics"]}
        self.assertEqual(statuses, {"E33": "current", "E34": "invalid", "E26": "invalid"})
        reasons = {e["epic"]: e["reasons"] for e in summary["epics"]}
        self.assertIn("missing required property 'owner'", reasons["E34"][0])
        self.assertIn("not a calendar date", reasons["E26"][0])
        self.assertEqual(reasons["E33"], [])
        self.assertEqual({e["owner"] for e in summary["epics"]}, {"basiltt"})
        code, _, _ = self.run_main(root, ["--today", TODAY.isoformat()])
        self.assertEqual(code, 1, "invalid data fails the repository check")
        code, _, _ = self.run_main(root, ["--epic", BASE_EPIC, "--today", TODAY.isoformat()])
        self.assertEqual(code, 0, "the gate for a valid epic is not coupled to another epic's record")

    def test_inventory_reads_epics_from_the_preserved_board_and_source_files(self):
        epics = module.inventory(ROOT)
        self.assertEqual(epics["E01"], "Engineering foundations")
        self.assertEqual(epics["E31"], "Program governance and delivery protocol")
        self.assertEqual(len(epics), 38)


class ObservabilityTests(TempRootMixin, unittest.TestCase):
    """AC: counts of epics with a current, stale and no refresh without opening the board."""

    def test_summary_counts_and_lists_every_state(self):
        stale = record("E34")
        latest(stale)["date"] = "2026-01-05"
        blocked = record("E26")
        finding(latest(blocked), "E26-F01").update({"status": "open", "owner_ticket": None, "resolution": None})
        root = self.temp_root({
            "E33": record(), "E34": stale, "E26": blocked, "E05": record("E05"),
        })
        summary = module.run(root, TODAY)
        self.assertEqual(summary["counts"], {"current": 1, "stale": 1, "blocked": 1, "not_refreshed": 1, "invalid": 0})
        self.assertEqual(summary["unowned_findings"], [{"epic": "E26", "finding": "E26-F01", "owner": "basiltt"}])
        text = module.format_summary(summary)
        self.assertIn("1 current, 1 stale, 1 blocked, 1 not refreshed, 0 invalid of 4 epics", text)
        self.assertIn("E34 stale", text)
        self.assertIn("E26 blocked", text)
        self.assertIn("unowned finding E26-F01 (E26) needs a ticket; owner basiltt", text)

    def test_json_output_is_machine_readable(self):
        code, out, _ = self.run_main(ROOT, ["--json", "--today", TODAY.isoformat()])
        self.assertEqual(code, 0)
        summary = json.loads(out)
        self.assertEqual(summary["today"], TODAY.isoformat())
        self.assertEqual({e["epic"] for e in summary["epics"]}, set(RECORDS))
        for evaluation in summary["epics"]:
            self.assertIn(evaluation["status"], ("current", "stale", "blocked", "not_refreshed", "invalid"))
            self.assertEqual(evaluation["owner"], "basiltt")


if __name__ == "__main__":
    unittest.main()
