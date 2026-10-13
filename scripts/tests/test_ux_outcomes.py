"""Tests for scripts/check_ux_outcomes.py (PenniLogic/docs#77, T-UXR-08).

Every negative starts from the synthetic catalogue built in this file, which passes (its control test is
`test_synthetic_catalogue_passes`), applies exactly one mutation and asserts the exact static rule and, where the
rule names one, the offending identifier. The pinned registry is a synthetic in-memory blob served by a fake source;
the Git tests use throwaway repositories under the system temporary directory. `PublishedCatalogueTests` read the
committed catalogue through the real loader and assert its exact readiness gaps and summary bytes. Nothing is
written inside the repository and nothing touches the network.
"""

import contextlib
import copy
from datetime import date
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("check_ux_outcomes_under_test", ROOT / "scripts" / "check_ux_outcomes.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
SCHEMA = module.support.load_json(ROOT / module.SCHEMA)
REGISTRY_PATH = "planning/source/evidence/experience-coverage.json"
COMMIT = "a" * 40


def registry_bytes(journeys=(("J01", True), ("J02", True), ("J03", False))):
    registry = {"journeys": [{"id": identifier, "name": "Synthetic journey", "critical": critical}
                             for identifier, critical in journeys]}
    return (json.dumps(registry, indent=2) + "\n").encode("utf-8")


class Sources:
    """An in-memory stand-in for GitSources: serves exactly one pinned blob and an optional base catalogue."""

    def __init__(self, blob=None, base=None):
        self.blobs = {(COMMIT, REGISTRY_PATH): registry_bytes() if blob is None else blob}
        self.base = base

    def blob(self, commit, path):
        if (commit, path) not in self.blobs:
            raise LookupError("blob unavailable")
        return self.blobs[(commit, path)]

    def base_file(self, path):
        return self.base


def pin_for(blob):
    return {"commit": COMMIT, "path": REGISTRY_PATH, "sha256": module.digest(blob)}


def ratio(numerator, denominator):
    return (
        {"event_ids": numerator, "definition": "Eligible sessions that complete the step"},
        {"event_ids": denominator, "eligibility": "Opted-in sessions that reached the step",
         "excludes_opted_out": True},
    )


def event(identifier, name, incentive=None):
    return {
        "id": identifier, "name": name, "purpose": "Synthetic outcome signal",
        "fields": [
            {"name": "step_outcome", "kind": "enum", "values": ["completed", "abandoned", "corrected"]},
            {"name": "elapsed", "kind": "duration_bucket", "values": ["short", "medium", "long"]},
            {"name": "assisted", "kind": "boolean", "values": []},
        ],
        "incentive": incentive, "opt_out_honoured": True, "enabled": False, "payload_review": "pending",
    }


def metric(identifier, journey, role, kind, threshold, guardrails, numerator=("EV-001",), denominator=("EV-002",)):
    num, den = ratio(list(numerator), list(denominator))
    return {
        "id": identifier, "journey_id": journey, "role": role, "kind": kind,
        "statement": "Share of eligible sessions that finish the task", "numerator": num, "denominator": den,
        "unit": "proportion", "direction": "increase", "benefit_context": None, "guardrail_ids": list(guardrails),
        "baseline": {"value": None, "source": "unmeasured"}, "target": {"value": None, "source": "unset"},
        "sample_limitation": "Synthetic catalogue only", "threshold_id": threshold, "status": "unvalidated",
    }


def guardrail(identifier, journey, klass, concern, threshold):
    num, den = ratio(["EV-003"], ["EV-002"])
    return {
        "id": identifier, "journey_id": journey, "class": klass, "concern": concern,
        "signal": "Share of eligible sessions that reverse the step", "numerator": num, "denominator": den,
        "baseline": {"value": None, "source": "unmeasured"}, "threshold_id": threshold, "status": "unvalidated",
    }


def threshold(identifier):
    return {
        "id": identifier, "warn": {"value": None, "source": "unset"}, "kill": {"value": None, "source": "unset"},
        "minimum_sample_ref": module.PLATFORM_REF, "on_cross": "product_decision_review",
        "reviewers": ["product_owner", "research", "privacy"], "decision_record": None,
    }


def benchmark(journey):
    steps = ["Open the synthetic scenario", "Complete the task without help"]
    return {
        "id": f"BM-{journey}", "journey_id": journey, "version": "1.0.0", "scenario": "Synthetic scenario",
        "task_steps": steps, "task_script_sha256": module.digest(steps),
        "success_definition": "Task completed without assistance", "entry_criteria": "moderated_defects_closed",
        "moderated_defects_ref": "pending:PenniLogic/docs#66", "baseline": {"value": None, "source": "unmeasured"},
        "results": None,
    }


def debt(identifier="DEBT-001", severity="high", status="open", exception=None):
    return {
        "id": identifier, "title": "Synthetic debt item", "journey_ids": ["J01"], "severity": severity,
        "owner_role": "design_ops", "due_date": "2026-12-01", "release_impact": "blocks_release",
        "status": status, "exception": exception,
    }


def exception(recorded="2026-10-01", expires="2026-11-01", role="decision_coordinator"):
    return {"recorded_by_role": role, "recorded_on": recorded, "expires_on": expires,
            "reason": "Synthetic dated exception"}


def catalogue(pin):
    """A synthetic catalogue that passes every structure rule against the synthetic registry (J01, J02 critical)."""
    classes = ("permission_coercion", "harmful_sharing", "support_demand", "accessibility", "dark_pattern")
    guardrails = [guardrail("G-J01-01", "J01", classes[0], "harm", "TH-002"),
                  guardrail("G-J01-02", "J01", classes[1], "harm", "TH-002"),
                  guardrail("G-J02-01", "J02", classes[2], "trust", "TH-002"),
                  guardrail("G-J02-02", "J02", classes[3], "trust", "TH-002"),
                  guardrail("G-J02-03", "J02", classes[4], "harm", "TH-002")]
    return {
        "schema_version": "1.0.0", "catalogue_version": "0.1.0", "source_issue": "PenniLogic/docs#77",
        "plan_id": "T-UXR-08", "status": "proposed", "registry_ref": dict(pin),
        "collection": {"enabled": False, "enable_requires": ["consent", "payload_allowlist", "cohort_minimum"],
                       "rollback": "Stop collection and keep only approved aggregate history"},
        "privacy": {
            "payload_allowlist_refs": ["pending:PenniLogic/android#18", "pending:PenniLogic/api#82"],
            "consent_ref": "pending:PenniLogic/docs#65",
            "opt_out": {"honoured": True, "rule": "Opted-out users emit nothing and leave every denominator"},
            "cohort_minimum_ref": module.PLATFORM_REF, "retention_ref": module.PLATFORM_REF,
            "aggregation_ref": module.PLATFORM_REF, "access_ref": module.PLATFORM_REF,
            "session_recording": "prohibited",
            "privacy_budget": {"max_fields_per_event": 6, "max_values_per_field": 8},
        },
        "events": [event("EV-001", "task_step_finished"), event("EV-002", "task_step_shown"),
                   event("EV-003", "task_step_reversed"), event("EV-004", "share_offer_accepted", "sharing")],
        "metrics": [metric("M-J01-01", "J01", "primary", "task_success", "TH-001", ["G-J01-01"]),
                    metric("M-J01-02", "J01", "secondary", "time_on_task", "TH-001", []),
                    metric("M-J02-01", "J02", "primary", "comprehension", "TH-001", ["G-J02-01"]),
                    # An incentive event counted as a secondary signal, with benefit and safety context (criterion 2).
                    dict(metric("M-J01-03", "J01", "secondary", "trust", "TH-001", ["G-J01-02"], ("EV-004",)),
                         benefit_context="Sharing completes a split the user started")],
        "guardrails": guardrails,
        "thresholds": [threshold("TH-001"), threshold("TH-002")],
        "research_triggers": [
            {"id": "RT-001", "journey_ids": ["J01", "J02"], "condition": "threshold_crossed", "source_id": "TH-001",
             "follow_up": "moderated_study", "owner_role": "research", "status": "dormant"},
            {"id": "RT-002", "journey_ids": ["J01", "J02"], "condition": "threshold_crossed", "source_id": "TH-002",
             "follow_up": "guardrail_review", "owner_role": "research", "status": "dormant"},
            {"id": "RT-003", "journey_ids": ["J01"], "condition": "benchmark_regression", "source_id": "BM-J01",
             "follow_up": "unmoderated_benchmark", "owner_role": "research", "status": "dormant"},
        ],
        "research_calendar": {
            "operations_ref": "pending:PenniLogic/docs#65",
            "cadences": [{"study": study, "cadence": cadence, "journey_ids": ["J01", "J02"], "next_session": None}
                         for study, cadence in (("moderated_usability", "quarterly"),
                                                ("unmoderated_benchmark", "per_release"),
                                                ("diary_follow_up", "post_beta"),
                                                ("panel_health_review", "monthly"))],
            "panel_health": ["attrition", "coverage", "recency"],
        },
        "benchmarks": [benchmark("J01"), benchmark("J02")],
        "longitudinal_plan": {
            "cohort": "Opted-in beta participants recruited through the research operations route",
            "cohort_minimum_ref": module.PLATFORM_REF, "cadence": "monthly", "retention_ref": module.PLATFORM_REF,
            "stop_criteria": ["Participant withdrawal or consent expiry"],
            "decisions_it_may_change": ["M-J01-01", "TH-001"], "privacy_review_ref": "pending:PenniLogic/docs#65",
            "status": "unrun",
        },
        "design_debt": [],
        "approvals": [{"role": role, "status": "pending", "decision_ref": None}
                      for role in ("privacy", "product_owner", "research", "decision_coordinator")],
    }


class CatalogueCase(unittest.TestCase):
    """Builds the passing synthetic control; each negative mutates one thing and asserts the exact rule."""

    def setUp(self):
        self.blob = registry_bytes()
        self.pin = pin_for(self.blob)
        self.document = catalogue(self.pin)

    def run_check(self, document=None, base=None, fixture=False, sources=None):
        return module.check(copy.deepcopy(self.document if document is None else document), SCHEMA,
                            sources or Sources(self.blob), self.pin, base, fixture)

    def assertRefused(self, rule, subject=None, document=None, **kwargs):
        with self.assertRaises(module.Refused) as caught:
            self.run_check(document, **kwargs)
        self.assertEqual(caught.exception.rule, rule)
        self.assertEqual(caught.exception.subject, subject)


class ControlTests(CatalogueCase):
    def test_synthetic_catalogue_passes(self):
        model = self.run_check()
        self.assertEqual(sorted(model["pinned"]), ["J01", "J02", "J03"])
        self.assertEqual(len(model["indexed"]["metrics"]), 4)



def mutate(document, change):
    result = copy.deepcopy(document)
    change(result)
    return result


def add_field(name, kind="enum", values=("low", "high")):
    return lambda d: d["events"][0]["fields"].append({"name": name, "kind": kind, "values": list(values)})


class EventPrivacyTests(CatalogueCase):
    """Ticket criterion 3 and E33-F04: planted sensitive telemetry fields are refused with their category."""

    def test_planted_fields_are_refused_by_category(self):
        cases = (
            ("amount_bucket", "event.money_field"), ("txnamount", "event.money_field"),
            ("merchant_category", "event.money_field"), ("balance_band", "event.money_field"),
            ("message_text", "event.content_field"), ("transcript_kind", "event.content_field"),
            ("prompt_length", "event.prompt_field"), ("chat_turns", "event.prompt_field"),
            ("user_id", "event.identity_field"), ("email_domain", "event.identity_field"),
            ("household_role", "event.household_field"), ("partner_present", "event.household_field"),
        )
        for name, rule in cases:
            with self.subTest(name=name):
                self.assertRefused(rule, "EV-001", mutate(self.document, add_field(name)))

    def test_planted_sensitive_value_is_refused(self):
        self.assertRefused("event.money_field", "EV-001", mutate(self.document, lambda d: d["events"][0]["fields"][0]
                                                                  ["values"].append("merchant_known")))

    def test_planted_sensitive_event_name_is_refused(self):
        self.assertRefused("event.money_field", "EV-001",
                           mutate(self.document, lambda d: d["events"][0].update(name="balance_viewed")))

    def test_free_text_kind_is_refused(self):
        self.assertRefused("event.kind_not_allowlisted", "EV-001",
                           mutate(self.document, add_field("step_detail", "string", ())))

    def test_number_kind_is_refused(self):
        self.assertRefused("event.kind_not_allowlisted", "EV-001",
                           mutate(self.document, add_field("step_count", "integer", ())))

    def test_raw_value_is_refused(self):
        self.assertRefused("event.value_grammar", "EV-001",
                           mutate(self.document, add_field("step_state", values=("Completed Task", "open"))))

    def test_money_shaped_value_is_refused_by_the_content_guard(self):
        self.assertRefused("content.amount_shape", "EV-001",
                           mutate(self.document, add_field("step_state", values=("over 500 INR", "open"))))

    def test_boolean_with_values_is_refused(self):
        self.assertRefused("event.values_mismatch", "EV-001",
                           mutate(self.document, add_field("retried", "boolean", ("yes", "no"))))

    def test_single_valued_enum_is_refused(self):
        self.assertRefused("event.values_mismatch", "EV-001",
                           mutate(self.document, add_field("step_state", values=("open",))))

    def test_field_budget_is_enforced(self):
        self.assertRefused("event.privacy_budget", "EV-001", mutate(
            self.document, lambda d: d["privacy"]["privacy_budget"].update(max_fields_per_event=2)))

    def test_field_budget_boundary_passes(self):
        self.run_check(mutate(self.document, lambda d: d["privacy"]["privacy_budget"].update(max_fields_per_event=3)))

    def test_value_budget_is_enforced(self):
        self.assertRefused("event.privacy_budget", "EV-001", mutate(
            self.document, lambda d: d["privacy"]["privacy_budget"].update(max_values_per_field=2)))

    def test_value_budget_boundary_passes(self):
        self.run_check(mutate(self.document, lambda d: d["privacy"]["privacy_budget"].update(max_values_per_field=3)))

    def test_budget_caps_are_bounded(self):
        self.assertRefused("privacy.budget_bounds", document=mutate(
            self.document, lambda d: d["privacy"]["privacy_budget"].update(max_fields_per_event=9)))

    def test_budget_cap_upper_boundary_passes(self):
        self.run_check(mutate(self.document, lambda d: d["privacy"]["privacy_budget"].update(max_fields_per_event=8)))

    def test_duplicate_field_is_refused(self):
        self.assertRefused("event.field_duplicate", "EV-001",
                           mutate(self.document, add_field("assisted", "enum", ("yes", "no"))))

    def test_event_name_grammar(self):
        self.assertRefused("event.name_grammar", "EV-001",
                           mutate(self.document, lambda d: d["events"][0].update(name="TaskStep")))

    def test_event_must_honour_opt_out(self):
        self.assertRefused("event.opt_out_not_honoured", "EV-001",
                           mutate(self.document, lambda d: d["events"][0].update(opt_out_honoured=False)))

    def test_event_must_stay_disabled(self):
        self.assertRefused("collection.enabled", "EV-001",
                           mutate(self.document, lambda d: d["events"][0].update(enabled=True)))

    def test_unused_event_is_refused(self):
        self.assertRefused("event.unused", "EV-005",
                           mutate(self.document, lambda d: d["events"].append(event("EV-005", "task_step_paused"))))


class FrameTests(CatalogueCase):
    """Collection disabled, opt-out, T-PLT-03 references, session recording and held approvals."""

    def test_collection_must_stay_disabled(self):
        self.assertRefused("collection.enabled", document=mutate(
            self.document, lambda d: d["collection"].update(enabled=True)))

    def test_enable_conditions_must_name_consent_payload_and_cohort(self):
        self.assertRefused("collection.enable_conditions", document=mutate(
            self.document, lambda d: d["collection"]["enable_requires"].remove("consent")))

    def test_platform_values_are_references_not_numbers(self):
        for key in ("cohort_minimum_ref", "retention_ref", "aggregation_ref", "access_ref"):
            with self.subTest(key=key):
                self.assertRefused("privacy.platform_ref", document=mutate(
                    self.document, lambda d: d["privacy"].update({key: "pending:PenniLogic/infra#99"})))

    def test_invented_retention_text_is_refused(self):
        self.assertRefused("privacy.platform_ref", document=mutate(
            self.document, lambda d: d["privacy"].update(retention_ref="Thirty days")))

    def test_opt_out_must_be_honoured(self):
        self.assertRefused("privacy.opt_out", document=mutate(
            self.document, lambda d: d["privacy"]["opt_out"].update(honoured=False)))

    def test_session_recording_is_prohibited(self):
        self.assertRefused("privacy.session_recording", document=mutate(
            self.document, lambda d: d["privacy"].update(session_recording="allowed")))

    def test_catalogue_stays_proposed(self):
        self.assertRefused("held.catalogue_status", document=mutate(
            self.document, lambda d: d.update(status="approved")))

    def test_catalogue_version_grammar(self):
        self.assertRefused("catalogue.version", document=mutate(
            self.document, lambda d: d.update(catalogue_version="v1")))

    def test_approval_cannot_be_recorded(self):
        self.assertRefused("held.approval_recorded", document=mutate(
            self.document, lambda d: d["approvals"][0].update(status="approved")))

    def test_approval_roles_are_exact(self):
        self.assertRefused("approval.roles", document=mutate(self.document, lambda d: d["approvals"].pop()))

    def test_invented_baseline_number_is_refused(self):
        self.assertRefused("schema.invalid", document=mutate(
            self.document, lambda d: d["metrics"][0]["baseline"].update(value=0.4)))

    def test_number_outside_the_budget_is_refused_by_the_guard(self):
        document = mutate(self.document, lambda d: d["metrics"][0]["baseline"].update(value=0.4))
        with self.assertRaises(module.Refused) as caught:
            module.guard_content(document)
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("content.unexpected_number", "M-J01-01"))

    def test_secret_shaped_text_is_refused(self):
        planted = "ghp_" + "Ab1" * 12
        self.assertRefused("content.secret_shape", "M-J01-01", mutate(
            self.document, lambda d: d["metrics"][0].update(sample_limitation=planted)))

    def test_url_and_email_text_are_refused(self):
        for text, rule in (("See example.com", "content.url_shape"), ("Ask someone at host", None)):
            with self.subTest(text=text):
                if rule is None:
                    self.run_check(mutate(self.document, lambda d: d["metrics"][0].update(sample_limitation=text)))
                else:
                    self.assertRefused(rule, "M-J01-01", mutate(
                        self.document, lambda d: d["metrics"][0].update(sample_limitation=text)))
        self.assertRefused("content.email_shape", "M-J01-01", mutate(
            self.document, lambda d: d["metrics"][0].update(sample_limitation="Ask someone" + chr(64) + "host")))

    def test_registry_pin_mismatch(self):
        self.assertRefused("registry.ref_mismatch", document=mutate(
            self.document, lambda d: d["registry_ref"].update(commit="b" * 40)))

    def test_registry_digest_mismatch(self):
        self.assertRefused("registry.digest_mismatch", sources=Sources(registry_bytes((("J01", True),))))

    def test_registry_unavailable(self):
        sources = Sources(self.blob)
        sources.blobs.clear()
        self.assertRefused("registry.unavailable", sources=sources)


class MeasureTests(CatalogueCase):
    """Explicit denominators, held validation, journey agreement and perverse-incentive rules (criterion 2)."""

    def test_denominator_is_required(self):
        self.assertRefused("ratio.denominator_missing", "M-J01-01", mutate(
            self.document, lambda d: d["metrics"][0]["denominator"].update(event_ids=[])))

    def test_numerator_is_required(self):
        self.assertRefused("ratio.numerator_missing", "G-J01-01", mutate(
            self.document, lambda d: d["guardrails"][0]["numerator"].update(event_ids=[])))

    def test_denominator_must_differ_from_numerator(self):
        self.assertRefused("ratio.denominator_same_as_numerator", "M-J01-01", mutate(
            self.document, lambda d: d["metrics"][0]["denominator"].update(event_ids=["EV-001"])))

    def test_denominator_must_exclude_opted_out(self):
        self.assertRefused("ratio.opt_out_not_excluded", "G-J02-01", mutate(
            self.document, lambda d: d["guardrails"][2]["denominator"].update(excludes_opted_out=False)))

    def test_dangling_event_reference(self):
        self.assertRefused("reference.dangling", "M-J01-01", mutate(
            self.document, lambda d: d["metrics"][0]["numerator"].update(event_ids=["EV-009"])))

    def test_dangling_threshold_reference(self):
        self.assertRefused("reference.dangling", "G-J01-01", mutate(
            self.document, lambda d: d["guardrails"][0].update(threshold_id="TH-009")))

    def test_validated_status_is_held(self):
        self.assertRefused("held.validation", "M-J02-01", mutate(
            self.document, lambda d: d["metrics"][2].update(status="validated")))

    def test_journey_infix_must_agree(self):
        self.assertRefused("id.journey_mismatch", "M-J01-02", mutate(
            self.document, lambda d: d["metrics"][1].update(journey_id="J02")))

    def test_id_grammar(self):
        self.assertRefused("id.grammar", document=mutate(self.document, lambda d: d["metrics"][1].update(id="M-1")))

    def test_duplicate_id(self):
        # Records identical in every field are refused earlier by the schema's uniqueItems; these differ by name.
        self.assertRefused("id.duplicate", "EV-001", mutate(
            self.document, lambda d: d["events"][2].update(id="EV-001")))

    def test_primary_must_be_an_outcome(self):
        self.assertRefused("metric.primary_kind", "M-J02-01", mutate(
            self.document, lambda d: d["metrics"][2].update(kind="time_on_task")))

    def test_metric_guardrail_must_share_the_journey(self):
        self.assertRefused("metric.guardrail_other_journey", "M-J01-01", mutate(
            self.document, lambda d: d["metrics"][0].update(guardrail_ids=["G-J02-01"])))


class IncentiveTests(CatalogueCase):
    """Criterion 2: no success metric rewards permission grant, AI use, subscription or sharing on its own."""

    def test_incentive_event_cannot_be_the_primary(self):
        self.assertRefused("incentive.primary", "M-J01-01", mutate(
            self.document, lambda d: d["events"][0].update(incentive="permission_grant")))

    def test_incentive_without_benefit_context_is_refused(self):
        self.assertRefused("incentive.without_safety_context", "M-J01-03", mutate(
            self.document, lambda d: d["metrics"][3].update(benefit_context=None)))

    def test_incentive_without_guardrail_is_refused(self):
        self.assertRefused("incentive.without_safety_context", "M-J01-03", mutate(
            self.document, lambda d: d["metrics"][3].update(guardrail_ids=[])))

    def test_incentive_promoted_to_primary_is_refused(self):
        self.assertRefused("incentive.primary", "M-J01-03", mutate(
            self.document, lambda d: d["metrics"][3].update(role="primary")))

    def test_every_incentive_class_is_caught(self):
        for incentive in ("permission_grant", "ai_use", "subscription", "sharing"):
            with self.subTest(incentive=incentive):
                self.assertRefused("incentive.primary", "M-J01-01", mutate(
                    self.document, lambda d: d["events"][0].update(incentive=incentive)))


class CoverageTests(CatalogueCase):
    """Criterion 1 and 5 coverage over the pinned critical journeys."""

    def test_primary_missing(self):
        self.assertRefused("coverage.primary_missing", "J02", mutate(
            self.document, lambda d: d["metrics"][2].update(role="secondary")))

    def test_primary_duplicate(self):
        self.assertRefused("coverage.primary_duplicate", "J01", mutate(
            self.document, lambda d: d["metrics"][1].update(role="primary", kind="correction")))

    def test_guardrail_missing(self):
        # Control: J03 made critical in the pinned registry, with its own primary, guardrail and benchmark.
        blob = registry_bytes((("J01", True), ("J02", True), ("J03", True)))
        self.pin = pin_for(blob)
        document = mutate(catalogue(self.pin), lambda d: (
            d["metrics"].append(metric("M-J03-01", "J03", "primary", "recovery", "TH-001", [])),
            d["guardrails"].append(guardrail("G-J03-01", "J03", "accessibility", "trust", "TH-002")),
            d["benchmarks"].append(benchmark("J03"))))
        self.run_check(document, sources=Sources(blob))
        self.assertRefused("coverage.guardrail_missing", "J03",
                           mutate(document, lambda d: d["guardrails"].pop()), sources=Sources(blob))

    def test_benchmark_missing(self):
        self.assertRefused("coverage.benchmark_missing", "J02", mutate(
            self.document, lambda d: d["benchmarks"].pop()))

    def test_non_critical_journey_needs_no_coverage(self):
        model = self.run_check()
        self.assertFalse(model["pinned"]["J03"])

    def test_guardrail_class_missing(self):
        self.assertRefused("coverage.guardrail_class_missing", document=mutate(
            self.document, lambda d: d["guardrails"][4].update({"class": "accessibility"})))

    def test_journey_outside_the_pin_is_a_readiness_gap_not_a_failure(self):
        document = mutate(self.document, lambda d: d["research_triggers"][0]["journey_ids"].append("J40"))
        gaps = module.readiness(self.run_check(document), date(2026, 10, 13))
        self.assertEqual(gaps["readiness.journey_outside_pin"], ["J40"])


class ThresholdTriggerTests(CatalogueCase):
    """Criterion 4: a crossed kill threshold opens a reviewed product decision, never an automatic nudge."""

    def test_automatic_action_is_refused(self):
        for action in ("auto_nudge", "auto_disable", "notify_user"):
            with self.subTest(action=action):
                self.assertRefused("threshold.automatic_action", "TH-001", mutate(
                    self.document, lambda d: d["thresholds"][0].update(on_cross=action)))

    def test_product_owner_review_is_required(self):
        self.assertRefused("threshold.review_missing", "TH-002", mutate(
            self.document, lambda d: d["thresholds"][1]["reviewers"].remove("product_owner")))

    def test_unknown_reviewer_role_is_refused(self):
        self.assertRefused("threshold.unknown_role", "TH-001", mutate(
            self.document, lambda d: d["thresholds"][0]["reviewers"].append("growth_team")))

    def test_minimum_sample_is_a_platform_reference(self):
        self.assertRefused("privacy.platform_ref", "TH-001", mutate(
            self.document, lambda d: d["thresholds"][0].update(minimum_sample_ref="pending:PenniLogic/docs#77")))

    def test_threshold_value_cannot_be_invented(self):
        self.assertRefused("schema.invalid", document=mutate(
            self.document, lambda d: d["thresholds"][0]["kill"].update(value="low")))

    def test_decision_record_cannot_be_recorded(self):
        self.assertRefused("schema.invalid", document=mutate(
            self.document, lambda d: d["thresholds"][0].update(decision_record="approved")))

    def test_unused_threshold(self):
        self.assertRefused("threshold.unused", "TH-002", mutate(self.document, lambda d: [
            g.update(threshold_id="TH-001") for g in d["guardrails"]]))

    def test_threshold_without_trigger(self):
        self.assertRefused("threshold.without_trigger", "TH-002", mutate(
            self.document, lambda d: d["research_triggers"][1].update(source_id="TH-001")))

    def test_trigger_source_must_match_condition(self):
        self.assertRefused("trigger.source_mismatch", "RT-003", mutate(
            self.document, lambda d: d["research_triggers"][2].update(source_id="TH-001")))

    def test_trigger_owner_is_research(self):
        self.assertRefused("trigger.owner_role", "RT-001", mutate(
            self.document, lambda d: d["research_triggers"][0].update(owner_role="product_owner")))

    def test_trigger_needs_a_journey(self):
        self.assertRefused("trigger.journey_missing", "RT-003", mutate(
            self.document, lambda d: d["research_triggers"][2].update(journey_ids=[])))


class ResearchTests(CatalogueCase):
    """Research calendar, panel health, benchmarks (criterion 5) and the longitudinal plan."""

    def test_calendar_operations_reference(self):
        self.assertRefused("calendar.operations_ref", document=mutate(
            self.document, lambda d: d["research_calendar"].update(operations_ref="pending:PenniLogic/docs#66")))

    def test_calendar_study_missing(self):
        self.assertRefused("calendar.study_missing", document=mutate(
            self.document, lambda d: d["research_calendar"]["cadences"].pop(2)))

    def test_calendar_duplicate_study(self):
        self.assertRefused("calendar.duplicate_study", document=mutate(
            self.document, lambda d: d["research_calendar"]["cadences"][0].update(study="diary_follow_up")))

    def test_panel_health_missing(self):
        self.assertRefused("calendar.panel_health_missing", document=mutate(
            self.document, lambda d: d["research_calendar"]["panel_health"].remove("attrition")))

    def test_session_cannot_be_scheduled(self):
        self.assertRefused("schema.invalid", document=mutate(
            self.document, lambda d: d["research_calendar"]["cadences"][0].update(next_session="2026-11-02")))

    def test_benchmark_version_grammar(self):
        self.assertRefused("benchmark.version_grammar", "BM-J01", mutate(
            self.document, lambda d: d["benchmarks"][0].update(version="v1")))

    def test_benchmark_script_missing(self):
        self.assertRefused("benchmark.script_missing", "BM-J02", mutate(
            self.document, lambda d: d["benchmarks"][1].update(task_steps=[])))

    def test_benchmark_script_digest_mismatch(self):
        self.assertRefused("benchmark.script_digest_mismatch", "BM-J01", mutate(
            self.document, lambda d: d["benchmarks"][0]["task_steps"].append("Return to the start")))

    def test_benchmark_results_cannot_be_fabricated(self):
        self.assertRefused("schema.invalid", document=mutate(
            self.document, lambda d: d["benchmarks"][0].update(results="passed")))

    def test_benchmark_journey_infix(self):
        self.assertRefused("id.journey_mismatch", "BM-J02", mutate(
            self.document, lambda d: d["benchmarks"][1].update(journey_id="J01")))

    def test_changed_script_at_published_version_is_refused(self):
        published = {("BM-J01", "1.0.0"): module.digest(["An earlier script"])}
        self.run_check(base={("BM-J01", "0.9.0"): published[("BM-J01", "1.0.0")]})  # control: older version only
        self.assertRefused("benchmark.version_not_bumped", "BM-J01", base=published)

    def test_unchanged_script_at_published_version_passes(self):
        self.run_check(base={("BM-J01", "1.0.0"): self.document["benchmarks"][0]["task_script_sha256"]})

    def test_longitudinal_retention_reference(self):
        self.assertRefused("longitudinal.retention_ref", document=mutate(
            self.document, lambda d: d["longitudinal_plan"].update(retention_ref="Ninety days")))

    def test_longitudinal_cohort_reference(self):
        self.assertRefused("longitudinal.cohort_ref", document=mutate(
            self.document, lambda d: d["longitudinal_plan"].update(cohort_minimum_ref="pending:PenniLogic/docs#66")))

    def test_longitudinal_cadence(self):
        self.assertRefused("longitudinal.cadence", document=mutate(
            self.document, lambda d: d["longitudinal_plan"].update(cadence="whenever")))

    def test_longitudinal_stop_criteria(self):
        self.assertRefused("longitudinal.stop_criteria_missing", document=mutate(
            self.document, lambda d: d["longitudinal_plan"].update(stop_criteria=[])))

    def test_longitudinal_decisions(self):
        self.assertRefused("longitudinal.decisions_missing", document=mutate(
            self.document, lambda d: d["longitudinal_plan"].update(decisions_it_may_change=[])))

    def test_longitudinal_dangling_decision(self):
        self.assertRefused("reference.dangling", document=mutate(
            self.document, lambda d: d["longitudinal_plan"]["decisions_it_may_change"].append("M-J02-09")))

    def test_longitudinal_cannot_be_marked_run(self):
        self.assertRefused("schema.invalid", document=mutate(
            self.document, lambda d: d["longitudinal_plan"].update(status="complete")))


class DesignDebtTests(CatalogueCase):
    """Criterion 6: open high-severity design debt blocks D8 unless the CDO-equivalent records a dated exception."""

    def with_debt(self, item):
        return mutate(self.document, lambda d: d["design_debt"].append(item))

    def test_debt_without_exception_passes(self):
        self.run_check(self.with_debt(debt()))

    def test_recorded_exception_is_held_in_published_data(self):
        document = self.with_debt(debt(exception=exception()))
        self.run_check(document, fixture=True)  # control: the same record is well formed
        self.assertRefused("held.cdo_exception", "DEBT-001", document)

    def test_debt_namespace_is_never_d(self):
        self.assertRefused("id.grammar", document=self.with_debt(debt(identifier="D-001")))

    def test_debt_owner_role(self):
        self.assertRefused("debt.owner_role", "DEBT-001", self.with_debt(dict(debt(), owner_role="cdo")))

    def test_debt_due_date(self):
        self.assertRefused("debt.due_date", "DEBT-001", self.with_debt(dict(debt(), due_date="2026-13-01")))

    def test_debt_journey_missing(self):
        self.assertRefused("debt.journey_missing", "DEBT-001", self.with_debt(dict(debt(), journey_ids=[])))

    def test_exception_role(self):
        self.assertRefused("debt.exception_role", "DEBT-001",
                           self.with_debt(debt(exception=exception(role="design_ops"))), fixture=True)

    def test_exception_dates_reversed(self):
        self.assertRefused("debt.exception_dates", "DEBT-001",
                           self.with_debt(debt(exception=exception("2026-11-01", "2026-10-01"))), fixture=True)

    def test_exception_undated(self):
        self.assertRefused("debt.exception_dates", "DEBT-001",
                           self.with_debt(debt(exception=exception(recorded="undated"))), fixture=True)

    def test_exception_without_reason(self):
        item = debt(exception=exception())
        del item["exception"]["reason"]
        self.assertRefused("schema.invalid", document=self.with_debt(item), fixture=True)


class D8FunctionTests(unittest.TestCase):
    """`d8_blocking_debt` with an injected date; the boundary pairs sit on recorded_on and expires_on."""

    def test_open_high_and_critical_block(self):
        items = [debt("DEBT-002", "critical"), debt("DEBT-001", "high"), debt("DEBT-003", "medium"),
                 debt("DEBT-004", "low"), debt("DEBT-005", "high", "closed")]
        self.assertEqual(module.d8_blocking_debt(items, date(2026, 10, 13)), ["DEBT-001", "DEBT-002"])

    def test_current_exception_unblocks(self):
        items = [debt(exception=exception("2026-10-01", "2026-11-01"))]
        self.assertEqual(module.d8_blocking_debt(items, date(2026, 10, 1)), [])
        self.assertEqual(module.d8_blocking_debt(items, date(2026, 10, 31)), [])

    def test_exception_expires_on_its_expiry_date(self):
        items = [debt(exception=exception("2026-10-01", "2026-11-01"))]
        self.assertEqual(module.d8_blocking_debt(items, date(2026, 11, 1)), ["DEBT-001"])

    def test_exception_not_yet_recorded_does_not_unblock(self):
        items = [debt(exception=exception("2026-10-01", "2026-11-01"))]
        self.assertEqual(module.d8_blocking_debt(items, date(2026, 9, 30)), ["DEBT-001"])

    def test_exception_by_another_role_does_not_unblock(self):
        items = [debt(exception=exception(role="product_owner"))]
        self.assertEqual(module.d8_blocking_debt(items, date(2026, 10, 13)), ["DEBT-001"])

    def test_undated_exception_does_not_unblock(self):
        items = [debt(exception=exception(recorded="undated"))]
        self.assertEqual(module.d8_blocking_debt(items, date(2026, 10, 13)), ["DEBT-001"])

    def test_clock_must_be_a_date(self):
        from datetime import datetime, timezone
        with self.assertRaises(TypeError):
            module.d8_blocking_debt([], datetime(2026, 10, 13, tzinfo=timezone.utc))


class ReadinessTests(CatalogueCase):
    def test_exact_readiness_gaps_of_the_synthetic_catalogue(self):
        gaps = module.readiness(self.run_check(), date(2026, 10, 13))
        self.assertEqual(tuple(gaps), module.READINESS_RULES)
        self.assertEqual(gaps["readiness.approval_pending"],
                         ["decision_coordinator", "privacy", "product_owner", "research"])
        self.assertEqual(gaps["readiness.collection_disabled"], ["collection"])
        self.assertEqual(gaps["readiness.payload_review_pending"], ["EV-001", "EV-002", "EV-003", "EV-004"])
        self.assertEqual(gaps["readiness.pending_reference"], [
            "pending:PenniLogic/android#18", "pending:PenniLogic/api#82", "pending:PenniLogic/docs#65",
            "pending:PenniLogic/docs#66", "pending:PenniLogic/infra#27"])
        self.assertEqual(len(gaps["readiness.baseline_unmeasured"]), 11)
        self.assertEqual(gaps["readiness.threshold_unset"], ["TH-001", "TH-002"])
        self.assertEqual(len(gaps["readiness.measure_unvalidated"]), 9)
        self.assertEqual(gaps["readiness.benchmark_unrun"], ["BM-J01", "BM-J02"])
        self.assertEqual(gaps["readiness.longitudinal_unrun"], ["longitudinal_plan"])
        self.assertEqual(gaps["readiness.journey_outside_pin"], [])
        self.assertEqual(gaps["readiness.registry_import_pin"], ["registry_ref"])
        self.assertEqual(gaps["readiness.d8_blocking_debt"], [])

    def test_open_high_debt_is_a_d8_readiness_gap(self):
        model = self.run_check(mutate(self.document, lambda d: d["design_debt"].append(debt())))
        self.assertEqual(module.readiness(model, date(2026, 10, 13))["readiness.d8_blocking_debt"], ["DEBT-001"])


class CliTests(CatalogueCase):
    """Modes default, --structure, --write-summary and --check-summary against a temporary root (never the repo)."""

    def setUp(self):
        super().setUp()
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "governance").mkdir()
        self.addCleanup(self.temporary.cleanup)

    def main(self, *argv, document=None):
        def loader(root, base):
            return self.run_check(document)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main(list(argv), root=self.root, loader=loader, today=date(2026, 10, 13))
        return code, out.getvalue(), err.getvalue()

    def test_structure_mode_passes(self):
        code, out, err = self.main("--structure")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("readiness not evaluated", out)

    def test_default_mode_is_not_green_with_exact_counts(self):
        self.assertEqual(self.main("--write-summary")[0], 0)
        code, out, err = self.main()
        self.assertEqual((code, err), (1, ""))
        lines = out.splitlines()
        self.assertEqual(lines[0], module.NOT_GREEN)
        self.assertIn("readiness.approval_pending: 4", lines)
        self.assertIn("readiness.baseline_unmeasured: 11", lines)
        self.assertIn("readiness.d8_blocking_debt: 0", lines)

    def test_summary_round_trip_and_drift(self):
        self.assertEqual(self.main("--write-summary")[0], 0)
        self.assertEqual(self.main("--check-summary")[0], 0)
        target = self.root / module.SUMMARY
        target.write_bytes(target.read_bytes() + b"hand edit\n")
        code, out, err = self.main("--check-summary")
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(err.strip(), "UX outcomes check refused: summary.drift")

    def test_missing_summary_is_drift(self):
        code, _, err = self.main()
        self.assertEqual((code, err.strip()), (1, "UX outcomes check refused: summary.drift"))

    def test_summary_is_deterministic_lf_and_date_independent(self):
        model = self.run_check(mutate(self.document, lambda d: d["design_debt"].append(debt())))
        first = module.render_summary(model, module.readiness(model, date(2026, 10, 13)))
        second = module.render_summary(model, module.readiness(model, date(2030, 1, 1)))
        self.assertEqual(first, second)
        self.assertTrue(first.endswith("\n") and "\r" not in first)
        self.assertIn("`M-J01-01`", first)

    def test_summary_neutralises_table_markup(self):
        model = self.run_check(mutate(self.document, lambda d: d["metrics"][0].update(statement="Done | <b>bold</b>")))
        rendered = module.render_summary(model, module.readiness(model, date(2026, 10, 13)))
        self.assertIn("Done \\| &lt;b&gt;bold&lt;/b&gt;", rendered)

    def test_refusal_never_echoes_input(self):
        planted = "ghp_" + "Zx9" * 12
        document = mutate(self.document, lambda d: d["metrics"][0].update(sample_limitation=planted))
        code, out, err = self.main("--structure", document=document)
        self.assertEqual(code, 1)
        self.assertEqual(err.strip(), "UX outcomes check refused: content.secret_shape M-J01-01")
        self.assertNotIn(planted, out + err)

    def test_unreadable_input_fails_closed(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main(["--structure"], root=self.root)  # the real loader: the catalogue file is absent
        self.assertEqual((code, out.getvalue()), (1, ""))
        self.assertEqual(err.getvalue().strip(), "UX outcomes check refused: input.unreadable_or_invalid")

    def test_write_summary_refuses_a_symlink(self):
        target = self.root / module.SUMMARY
        try:
            target.symlink_to(self.root / "elsewhere.md")
        except (OSError, NotImplementedError):
            target.write_text("placeholder\n", encoding="utf-8")
            self.assertEqual(self.main("--write-summary")[0], 0)
            return
        code, _, err = self.main("--write-summary")
        self.assertEqual((code, err.strip()), (1, "UX outcomes check refused: input.unreadable_or_invalid"))
        self.assertFalse((self.root / "elsewhere.md").exists())


GIT = shutil.which("git")
GIT_ENV = {key: value for key, value in os.environ.items() if key not in module.SCRUBBED_GIT_VARIABLES}
GIT_ENV.update(GIT_AUTHOR_NAME="Synthetic", GIT_AUTHOR_EMAIL="synthetic", GIT_COMMITTER_NAME="Synthetic",
               GIT_COMMITTER_EMAIL="synthetic", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)


def git(root, *args):
    result = subprocess.run([GIT, "-c", "commit.gpgsign=false", "-c", f"core.hooksPath={os.devnull}", *args],
                            cwd=root, capture_output=True, env=GIT_ENV, check=True, timeout=30)
    return result.stdout.decode("ascii").strip()


class GitSourceTests(CatalogueCase):
    """The hardened local Git reads, in throwaway repositories under the system temporary directory."""

    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "clone"
        self.root.mkdir()
        git(self.root, "init", "-q", "-b", "main")
        target = self.root / REGISTRY_PATH
        target.parent.mkdir(parents=True)
        target.write_bytes(self.blob)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "synthetic registry")
        self.commit = git(self.root, "rev-parse", "HEAD")
        self.pin = {"commit": self.commit, "path": REGISTRY_PATH, "sha256": module.digest(self.blob)}
        self.document = catalogue(self.pin)

    def test_pinned_registry_is_read_from_the_object_store(self):
        model = self.run_check(sources=module.GitSources(self.root))
        self.assertEqual(model["pinned"], {"J01": True, "J02": True, "J03": False})

    def test_registry_changed_after_the_pin_is_ignored(self):
        (self.root / REGISTRY_PATH).write_bytes(registry_bytes((("J01", True),)))
        git(self.root, "commit", "-q", "-am", "later change")
        self.run_check(sources=module.GitSources(self.root))

    def test_unknown_commit_is_unavailable(self):
        self.pin = dict(self.pin, commit="0" * 40)
        self.assertRefused("registry.unavailable", document=catalogue(self.pin), sources=module.GitSources(self.root))

    def test_git_environment_redirection_is_scrubbed(self):
        with unittest.mock.patch.dict(os.environ, {"GIT_DIR": str(self.root / "missing")}):
            self.run_check(sources=module.GitSources(self.root))

    def test_base_without_catalogue_is_none(self):
        git(self.root, "update-ref", "refs/remotes/origin/main", self.commit)
        self.assertIsNone(module.read_base(module.GitSources(self.root)))

    def test_base_benchmarks_are_read(self):
        (self.root / module.DATA).parent.mkdir(parents=True)
        (self.root / module.DATA).write_text(json.dumps(self.document, indent=2) + "\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "catalogue")
        git(self.root, "update-ref", "refs/remotes/origin/main", git(self.root, "rev-parse", "HEAD"))
        base = module.read_base(module.GitSources(self.root))
        self.assertEqual(sorted(base), [("BM-J01", "1.0.0"), ("BM-J02", "1.0.0")])

    def test_missing_base_ref_fails_closed(self):
        with self.assertRaises(module.Refused) as caught:
            module.read_base(module.GitSources(self.root))
        self.assertEqual(caught.exception.rule, "base.unavailable")

    def test_unsafe_base_revision_fails_closed(self):
        with self.assertRaises(module.Refused) as caught:
            module.read_base(module.GitSources(self.root, base="--output=x"))
        self.assertEqual(caught.exception.rule, "base.unavailable")

    def test_git_inside_the_repository_is_never_used(self):
        planted = self.root / "bin"
        planted.mkdir()
        fake = planted / ("git.exe" if os.name == "nt" else "git")
        fake.write_text("planted\n", encoding="utf-8")
        fake.chmod(0o755)
        path = os.pathsep.join(("bin", str(planted), str(Path(GIT).parent)))
        with unittest.mock.patch.dict(os.environ, {"PATH": path}):
            chosen = module.trusted_git(self.root)
        self.assertEqual(Path(chosen).parent.resolve(), Path(GIT).parent.resolve())


class PublishedSchemaTests(unittest.TestCase):
    def test_schema_file_is_canonical(self):
        raw = (ROOT / module.SCHEMA).read_bytes()
        self.assertEqual(raw, (json.dumps(SCHEMA, indent=2, ensure_ascii=True) + "\n").encode("ascii"))

    def test_schema_patterns_are_anchored(self):
        patterns = []

        def walk(value):
            if isinstance(value, dict):
                if isinstance(value.get("pattern"), str):
                    patterns.append(value["pattern"])
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(SCHEMA)
        self.assertTrue(patterns)
        for pattern in patterns:
            self.assertTrue(pattern.startswith("^") and pattern.endswith(r"(?![\s\S])"), pattern)


class ContentGuardTests(CatalogueCase):
    def test_personal_shapes_are_refused(self):
        # Built at runtime so no personal-data shape sits in the source as a literal.
        for text, rule in (("Call " + "9" * 5 + " " + "4" * 5, "content.phone_shape"),
                           ("Holder " + "ABCDE" + "1234" + "F", "content.personal_id_shape"),
                           ("Costs 2 lakh", "content.amount_shape"), ("Pay Rs 500", "content.amount_shape")):
            with self.subTest(rule=rule):
                self.assertRefused(rule, "G-J01-01", mutate(
                    self.document, lambda d: d["guardrails"][0].update(signal=text)))

    def test_padded_text_is_refused(self):
        self.assertRefused("content.blank_or_padded", "G-J01-01", mutate(
            self.document, lambda d: d["guardrails"][0].update(signal=" padded")))

    def test_non_ascii_text_is_refused(self):
        self.assertRefused("content.unprintable_character", "G-J01-01", mutate(
            self.document, lambda d: d["guardrails"][0].update(signal="Pay " + chr(0x20B9) + "5")))


class SummaryTextTests(CatalogueCase):
    def render(self, document):
        model = self.run_check(document)
        return module.render_summary(model, module.readiness(model, date(2026, 10, 13)))

    def test_free_text_is_closed_before_generated_prose(self):
        summary = self.render(self.document)
        self.assertIn("Rollback: Stop collection and keep only approved aggregate history.\n", summary)
        self.assertIn("route. Minimum: `pending:PenniLogic/infra#27`.", summary)
        self.assertIn("- Stop criterion: Participant withdrawal or consent expiry.\n", summary)

    def test_free_text_already_closed_is_not_doubled(self):
        summary = self.render(mutate(self.document, lambda d: d["collection"].update(rollback="Stop collection.")))
        self.assertIn("Rollback: Stop collection.\n", summary)


JOURNEYS = [f"J{number:02d}" for number in range(1, 13)]
INCENTIVE_JOURNEYS = ("J01", "J06", "J08", "J09")


class PublishedCatalogueTests(unittest.TestCase):
    """The committed catalogue, read through the real loader (pinned registry from local Git), never written."""

    @classmethod
    def setUpClass(cls):
        cls.model = module.load_and_check(ROOT)
        cls.document = cls.model["document"]
        cls.gaps = module.readiness(cls.model, date(2026, 10, 13))

    def test_pinned_registry_has_twelve_critical_journeys(self):
        self.assertEqual(self.model["pinned"], {journey: True for journey in JOURNEYS})
        self.assertEqual(self.document["registry_ref"], module.REGISTRY_PIN)

    def test_every_critical_journey_has_primary_guardrail_and_benchmark(self):
        indexed = self.model["indexed"]
        for journey in JOURNEYS:
            with self.subTest(journey=journey):
                primaries = [m["id"] for m in indexed["metrics"].values()
                             if m["journey_id"] == journey and m["role"] == "primary"]
                self.assertEqual(primaries, [f"M-{journey}-01"])
                self.assertEqual(indexed["metrics"][f"M-{journey}-01"]["guardrail_ids"], [f"G-{journey}-01"])
                self.assertIn(indexed["guardrails"][f"G-{journey}-01"]["concern"], ("trust", "harm"))
                self.assertIsNone(indexed["benchmarks"][f"BM-{journey}"]["results"])

    def test_exact_readiness_gaps(self):
        measures = sorted([*(f"M-{j}-0{n}" for j in JOURNEYS for n in range(1, 5)),
                           *(f"M-{j}-05" for j in INCENTIVE_JOURNEYS), *(f"G-{j}-01" for j in JOURNEYS)],
                          key=lambda identifier: (identifier[2:5], identifier))
        benchmarks = [f"BM-{journey}" for journey in JOURNEYS]
        expected = {
            "readiness.approval_pending": ["decision_coordinator", "privacy", "product_owner", "research"],
            "readiness.collection_disabled": ["collection"],
            "readiness.payload_review_pending": [f"EV-{number:03d}" for number in range(1, 16)],
            "readiness.pending_reference": [
                "pending:PenniLogic/android#18", "pending:PenniLogic/android#38", "pending:PenniLogic/api#82",
                "pending:PenniLogic/docs#65", "pending:PenniLogic/docs#66", "pending:PenniLogic/infra#27"],
            "readiness.baseline_unmeasured": sorted([*measures, *benchmarks],
                                                    key=lambda identifier: (module.journey_of(identifier),
                                                                            identifier)),
            "readiness.threshold_unset": [f"TH-{number:03d}" for number in range(1, 9)],
            "readiness.measure_unvalidated": measures,
            "readiness.benchmark_unrun": benchmarks,
            "readiness.longitudinal_unrun": ["longitudinal_plan"],
            "readiness.journey_outside_pin": [],
            "readiness.registry_import_pin": ["registry_ref"],
            "readiness.d8_blocking_debt": [],
        }
        self.assertEqual(self.gaps, expected)
        self.assertEqual({rule: len(items) for rule, items in self.gaps.items()}, {
            "readiness.approval_pending": 4, "readiness.collection_disabled": 1,
            "readiness.payload_review_pending": 15, "readiness.pending_reference": 6,
            "readiness.baseline_unmeasured": 76, "readiness.threshold_unset": 8,
            "readiness.measure_unvalidated": 64, "readiness.benchmark_unrun": 12,
            "readiness.longitudinal_unrun": 1, "readiness.journey_outside_pin": 0,
            "readiness.registry_import_pin": 1, "readiness.d8_blocking_debt": 0})

    def test_summary_matches_the_catalogue_byte_for_byte(self):
        expected = module.render_summary(self.model, self.gaps).encode("utf-8")
        self.assertEqual((ROOT / module.SUMMARY).read_bytes(), expected)


    def test_held_values_stay_unmeasured_unset_and_pending(self):
        indexed = self.model["indexed"]
        for record in [*indexed["metrics"].values(), *indexed["guardrails"].values(),
                       *indexed["benchmarks"].values()]:
            with self.subTest(record=record["id"]):
                self.assertEqual(record["baseline"], {"value": None, "source": "unmeasured"})
        for metric in indexed["metrics"].values():
            self.assertEqual(metric["target"], {"value": None, "source": "unset"})
        for threshold in indexed["thresholds"].values():
            self.assertEqual((threshold["warn"]["value"], threshold["kill"]["value"]), (None, None))
            self.assertIsNone(threshold["decision_record"])
            self.assertEqual(threshold["on_cross"], "product_decision_review")
        self.assertEqual({item["status"] for item in self.document["approvals"]}, {"pending"})
        self.assertEqual({item["decision_ref"] for item in self.document["approvals"]}, {None})
        self.assertFalse(self.document["collection"]["enabled"])
        self.assertEqual({event["enabled"] for event in indexed["events"].values()}, {False})
        self.assertEqual(self.document["status"], "proposed")
        self.assertEqual({item["next_session"] for item in self.document["research_calendar"]["cadences"]}, {None})

    def test_published_register_records_no_debt_or_exception(self):
        # No accepted source lists a design-debt item, so the register stays empty rather than invented.
        self.assertEqual(self.document["design_debt"], [])
        for today in (date(2026, 1, 1), date(2026, 10, 13), date(2030, 12, 31)):
            self.assertEqual(module.d8_blocking_debt(self.document["design_debt"], today), [])

    def test_incentive_events_are_never_primary_and_carry_safety_context(self):
        indexed = self.model["indexed"]
        incentives = {identifier for identifier, event in indexed["events"].items() if event["incentive"]}
        self.assertEqual(incentives, {"EV-010", "EV-011", "EV-012", "EV-013"})
        users = sorted(m["id"] for m in indexed["metrics"].values()
                       if set(m["numerator"]["event_ids"]) & incentives)
        self.assertEqual(users, [f"M-{journey}-05" for journey in INCENTIVE_JOURNEYS])
        for identifier in users:
            metric = indexed["metrics"][identifier]
            self.assertEqual(metric["role"], "secondary")
            self.assertIsNotNone(metric["benefit_context"])
            self.assertNotEqual(metric["guardrail_ids"], [])

    def test_every_event_field_is_coarsened_and_non_sensitive(self):
        for event in self.model["indexed"]["events"].values():
            for field in event["fields"]:
                with self.subTest(event=event["id"], field=field["name"]):
                    self.assertIn(field["kind"], module.FIELD_KINDS)
                    for token in (event["name"], field["name"], *field["values"]):
                        self.assertIsNone(module.sensitive_rule(token))

    def test_default_mode_reports_not_green_with_counts(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main([], root=ROOT, today=date(2026, 10, 13))
        self.assertEqual((code, err.getvalue()), (1, ""))
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0], module.NOT_GREEN)
        self.assertIn("readiness.measure_unvalidated: 64", lines)
        self.assertIn("readiness.d8_blocking_debt: 0", lines)
        self.assertEqual(len(lines), 1 + len(module.READINESS_RULES))


if __name__ == "__main__":
    unittest.main()
