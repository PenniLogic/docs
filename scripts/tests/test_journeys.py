"""T-UXR-04 validator tests: synthetic journey blueprints against a synthetic pinned registry.

Every rule test builds a fresh deep copy of one synthetic document pair, proves it passes (the control), applies
exactly one mutation and asserts the exact static rule identifier and offending identifier. The registry pin is
served from memory; the committed issue inventory is read (never written) for reference resolution. Command-line
tests run against temporary directories outside this repository. Nothing here touches the network or writes
inside the repository. No fixture is research evidence, an approval, a review or a real blueprint.
"""

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_journeys", ROOT / "scripts/check_journeys.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SCHEMA = module.support.load_json(ROOT / module.SCHEMA)
INVENTORY = module.support.load_json(ROOT / module.INVENTORY)
REGISTRY_PATH = "planning/source/evidence/experience-coverage.json"
SYNTHETIC_COMMIT = "1" * 40
ADRS = frozenset({"ADR-015"})
EVENT = "pending:PenniLogic/contracts#3"


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def registry_fixture():
    """A small synthetic registry: J01 (customer) and J10 (rights, web plus admin), five owned diagrams."""
    flows = [
        ("F-AND-01", ["J01"], ["S-AND-001"]), ("F-WEB-01", ["J01"], ["S-WEB-001"]),
        ("F-WEB-02", ["J10"], ["S-WEB-002"]), ("F-ADM-01", ["J10"], ["S-ADM-001"]), ("F-AND-02", [], ["S-AND-002"]),
    ]
    return {
        "personas": [{"id": "P01", "name": "Synthetic persona one"}, {"id": "P10", "name": "Synthetic operator"}],
        "journeys": [
            {"id": "J01", "name": "Synthetic first run", "persona_ids": ["P01"], "flow_ids": ["F-AND-01", "F-WEB-01"]},
            {"id": "J10", "name": "Synthetic rights request", "persona_ids": ["P10"],
             "flow_ids": ["F-WEB-02", "F-ADM-01"]},
        ],
        "flows": [{"id": flow_id, "journey_ids": journeys, "screen_ids": screens, "critical": flow_id != "F-AND-02"}
                  for flow_id, journeys, screens in flows],
        "screens": [{"id": screen} for _, _, screens in flows for screen in screens],
        "diagrams": [{"id": identifier, "owner_ticket": "T-UXR-04"}
                     for identifier in ("D01", "D03", "D04", "D05", "D21")]
        + [{"id": "D02", "owner_ticket": "T-UXR-03"}],
    }


def pinned(registry):
    blob = encode(registry)
    return blob, {"commit": SYNTHETIC_COMMIT, "path": REGISTRY_PATH,
                  "sha256": "sha256:" + hashlib.sha256(blob).hexdigest()}


class Sources:
    """In-memory stand-in for GitSources."""

    def __init__(self, blobs):
        self.blobs = blobs

    def blob(self, commit, path):
        try:
            return self.blobs[(commit, path)]
        except KeyError:
            raise LookupError(path) from None


def step(identifier, channel, action, system, flow_id=None, screens=(), next_steps=(), branches=(), signal=None,
         handoff=None, controls=None, events=(), policies=()):
    lane = "customer" if ".C." in identifier else "team"
    return {
        "id": identifier, "lane": lane, "channel": channel, "actor": "synthetic actor", "action": action,
        "system": system, "flow_id": flow_id, "screen_ids": list(screens), "data_class": "confidential",
        "authorization": "Signed-in owner of the synthetic record", "event_refs": list(events),
        "policy_refs": list(policies),
        "telemetry": None if signal is None else {"signal": signal, "fields": ["journey_id", "step_id", "outcome"]},
        "handoff": None if handoff is None else {"authoritative_service": handoff,
                                                 "may_show": "Status and coded reason only"},
        "controls": None if controls is None else {
            "clock": "Synthetic statutory clock", "audit": "Append-only audit event",
            "notification": "Status notice without detail", "reversal": "Reopen through the operator queue"},
        "boundary": {"raw_message_egress": False, "client_money_arithmetic": False,
                     "unauthorized_detail_access": False},
        "branches": [{"kind": kind, "to": target, "recovery": "Synthetic recovery", "recovery_owner": "service_team"}
                     for kind, target in branches],
        "next": list(next_steps),
    }


def not_applicable(scope, *kinds):
    return [{"scope": scope, "kind": kind, "reason": "Synthetic reason"} for kind in kinds]


def blueprint(journey_id, name, personas, flows, audience, policy_class, steps, abuse_step, extra_na):
    identifier = f"BP-{journey_id}"
    return {
        "id": identifier, "journey_id": journey_id, "journey_name": name, "audience": audience,
        "persona_ids": personas, "persona_basis": "provisional", "persona_basis_ref": "pending:PenniLogic/docs#66",
        "flow_ids": flows, "diagram_ids": ["D03"], "policy_class": policy_class,
        "outcome": {"success": "Synthetic success", "failure_recovery": "Synthetic recovery",
                    "metric_ref": "pending:PenniLogic/docs#77"},
        "current_map": {"summary": "Synthetic current map", "basis": "planned_baseline"},
        "target_map": {"summary": "Synthetic target map", "supersedes": f"{identifier}.current_map"},
        "moments_of_truth": [{"step_id": steps[-1]["id"], "statement": "Synthetic moment"}],
        "steps": steps,
        "abuse_paths": [{"id": f"AB-{journey_id}-01", "step_id": abuse_step, "actor": "Synthetic adversary",
                         "threat": "Synthetic threat", "safe_failure": "Synthetic safe failure"}],
        "not_applicable": extra_na,
    }


def documents(pin):
    j01 = [
        step("J01.C.01", "android", "Opens the app", "android-client", "F-AND-01", ["S-AND-001"], ["J01.T.01"],
             [("permission_denied", None)], "abandonment"),
        step("J01.T.01", "service", "Stores the profile", "sync-api", None, (), ["J01.C.02"],
             [("failure", None), ("offline", None), ("timeout", None), ("partial", None)], "recovery",
             events=[EVENT], policies=["ADR-015"]),
        step("J01.C.02", "web", "Sees the plan", "web-client", "F-WEB-01", ["S-WEB-001"], (), (), "completion",
             handoff="sync-api"),
    ]
    j10 = [
        step("J10.C.01", "web", "Submits a request", "web-client", "F-WEB-02", ["S-WEB-002"], ["J10.T.01"], (),
             None),
        step("J10.T.01", "service", "Validates scope and clock", "rights-service", None, (), ["J10.T.02"],
             [("failure", None), ("escalation", None), ("rollback", None), ("revocation", None)], None,
             controls=True, events=[EVENT]),
        step("J10.T.02", "admin", "Fulfils in the queue", "admin-console", "F-ADM-01", ["S-ADM-001"], ["J10.C.02"],
             (), "escalation", handoff="rights-service"),
        step("J10.C.02", "notification", "Receives the outcome", "notification-service", None, (), (), (),
             "completion", handoff="rights-service"),
    ]
    document = {
        "kind": "journey_blueprints", "schema_version": 1, "blueprint_version": "0.1.0",
        "source_issue": "PenniLogic/docs#67", "plan_id": "T-UXR-04", "status": "provisional",
        "registry_ref": dict(pin),
        "research_gate": {"issue": "PenniLogic/docs#66", "status": "pending", "evidence": []},
        "approvals": [{"role": role, "status": "pending", "source": None}
                      for role in ("product", "architecture", "security", "operations", "ia")],
        "diagrams": [{"id": identifier, "rendering": "markdown_text", "figma": "held"}
                     for identifier in ("D01", "D03", "D04", "D05", "D21")],
        "blueprints": [
            blueprint("J01", "Synthetic first run", ["P01"], ["F-AND-01", "F-WEB-01"], "customer", None, j01,
                      "J01.C.01", not_applicable("branch", "revocation", "escalation", "rollback")
                      + not_applicable("signal", "correction", "escalation")),
            blueprint("J10", "Synthetic rights request", ["P10"], ["F-WEB-02", "F-ADM-01"], "customer", "rights",
                      j10, "J10.T.02", not_applicable("branch", "offline", "timeout", "partial", "permission_denied")
                      + not_applicable("signal", "abandonment", "correction", "recovery")),
        ],
    }
    gaps = {"kind": "journey_gaps", "schema_version": 1, "source_issue": "PenniLogic/docs#67", "gaps": [
        {"id": "GAP-J10-01", "journey_id": "J10", "step_id": "J10.T.02", "category": "registry_content",
         "owner_issue": "PenniLogic/docs#75", "summary": "Synthetic registry gap", "backlog_item": None,
         "status": "open"},
    ]}
    return document, gaps


REGISTRY = registry_fixture()
BLOB, PIN = pinned(REGISTRY)
SOURCES = Sources({(SYNTHETIC_COMMIT, REGISTRY_PATH): BLOB})
DOCUMENT, GAPS = documents(PIN)


def blueprint_of(document, journey_id):
    return next(item for item in document["blueprints"] if item["journey_id"] == journey_id)


def step_of(document, step_id):
    return next(item for bp in document["blueprints"] for item in bp["steps"] if item["id"] == step_id)


class JourneyCase(unittest.TestCase):
    def run_check(self, document=None, gaps=None, registry=None, inventory=None, pin=None):
        if registry is not None:
            blob, pin = pinned(registry)
            if document is not None:
                document["registry_ref"] = dict(pin)
            sources = Sources({(SYNTHETIC_COMMIT, REGISTRY_PATH): blob})
        else:
            sources = SOURCES
        return module.check(document or copy.deepcopy(DOCUMENT), gaps or copy.deepcopy(GAPS), SCHEMA,
                            INVENTORY if inventory is None else inventory, ADRS, sources, pin or PIN)

    def assertRefused(self, rule, subject, mutate, target="document", **kwargs):
        """The unmutated fixture passes; the single mutation fails with exactly this rule and subject."""
        self.run_check()
        document, gaps = copy.deepcopy(DOCUMENT), copy.deepcopy(GAPS)
        registry = copy.deepcopy(REGISTRY) if target == "registry" else None
        mutate({"document": document, "gaps": gaps, "registry": registry}[target])
        with self.assertRaises(module.Refused) as caught:
            self.run_check(document, gaps, registry=registry, **kwargs)
        self.assertEqual(caught.exception.rule, rule)
        self.assertEqual(caught.exception.subject, subject)
        self.assertIn(rule, module.STRUCTURE_RULES)


class ControlTests(JourneyCase):
    def test_synthetic_control_passes_with_exact_counts(self):
        model = self.run_check()
        self.assertEqual(
            module.structure_line(model),
            "Journey blueprints 0.1.0 structure valid: 2 blueprints, 7 steps (4 customer, 3 team), 9 branches, "
            "2 abuse paths, 1 gaps; registry " + SYNTHETIC_COMMIT + " checked")

    def test_schema_keywords_are_in_the_shared_subset(self):
        allowed = module.support.SUPPORTED | module.support.ANNOTATIONS

        def walk(node):
            if isinstance(node, dict):
                if "type" in node or "$ref" in node or "enum" in node or "const" in node:
                    self.assertLessEqual(set(node) - {"definitions"}, allowed)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)
        walk(SCHEMA)
        for definition in SCHEMA["definitions"].values():
            for value in definition.get("properties", {}).values():
                if "pattern" in value:
                    self.assertTrue(value["pattern"].startswith("^") and value["pattern"].endswith(r"(?![\s\S])"))



def setter(path, value):
    """A mutation that sets one nested key, path given as a tuple of keys, indexes or (step) IDs."""
    def mutate(document):
        node = document
        for key in path[:-1]:
            if isinstance(key, str) and "." in key and key[0] == "J":
                node = step_of(document, key)
            elif isinstance(key, str) and key.startswith("BP-"):
                node = blueprint_of(document, key[3:])
            else:
                node = node[key]
        node[path[-1]] = value
    return mutate


class ShapeAndContentTests(JourneyCase):
    def test_unknown_step_key_is_schema_invalid_with_step_id(self):
        self.assertRefused("schema.invalid", "J01.T.01", setter(("J01.T.01", "notes"), "x"))

    def test_unknown_gap_key_is_schema_invalid_with_gap_id(self):
        self.assertRefused("schema.invalid", "GAP-J10-01", lambda gaps: gaps["gaps"][0].update(extra=None), "gaps")

    def test_url_in_action_refused(self):
        self.assertRefused("content.url_shape", "J01.C.01", setter(("J01.C.01", "action"), "Opens www.example"))

    def test_email_shape_refused(self):
        self.assertRefused("content.email_shape", "J01.C.01", setter(("J01.C.01", "actor"), "user at x@y"))

    def test_amount_shape_refused(self):
        self.assertRefused("content.amount_shape", "J10.T.01", setter(("J10.T.01", "action"), "Charges INR 500"))

    def test_markup_character_refused(self):
        self.assertRefused("content.markup_character", "J01.C.02", setter(("J01.C.02", "action"), "Sees a | b"))

    def test_padded_text_refused(self):
        self.assertRefused("content.blank_or_padded", "AB-J01-01",
                           setter(("BP-J01", "abuse_paths", 0, "threat"), " Synthetic threat"))

    def test_text_limit_boundary(self):
        document = copy.deepcopy(DOCUMENT)
        setter(("J01.C.01", "action"), "ab " * 133 + "a")(document)
        self.assertEqual(len(step_of(document, "J01.C.01")["action"]), 400)
        self.run_check(document)
        self.assertRefused("content.too_long", "J01.C.01", setter(("J01.C.01", "action"), "ab " * 133 + "ab"))

    def test_secret_shape_refused(self):
        token = "ghp" + "_" + "A1b2" * 6
        self.assertRefused("content.secret_shape", "J01.C.01", setter(("J01.C.01", "action"), token))

    def test_number_outside_schema_version_refused_by_guard(self):
        module.guard_content({"schema_version": 1})
        with self.assertRaises(module.Refused) as caught:
            module.guard_content({"schema_version": 1, "blueprints": [{"id": "BP-J01", "count": 3}]})
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("content.unexpected_number", "BP-J01"))

    def test_refusal_never_echoes_input_text(self):
        error = module.Refused("schema.invalid", "free text subject")
        self.assertEqual(str(error), "schema.invalid")


class RegistryPinTests(JourneyCase):
    def test_ref_mismatch(self):
        self.assertRefused("registry.ref_mismatch", None, setter(("registry_ref", "commit"), "2" * 40))

    def test_unavailable(self):
        self.run_check()
        with self.assertRaises(module.Refused) as caught:
            module.check(copy.deepcopy(DOCUMENT), copy.deepcopy(GAPS), SCHEMA, INVENTORY, ADRS, Sources({}), PIN)
        self.assertEqual(caught.exception.rule, "registry.unavailable")

    def test_digest_mismatch(self):
        self.run_check()
        forged = Sources({(SYNTHETIC_COMMIT, REGISTRY_PATH): BLOB + b" "})
        with self.assertRaises(module.Refused) as caught:
            module.check(copy.deepcopy(DOCUMENT), copy.deepcopy(GAPS), SCHEMA, INVENTORY, ADRS, forged, PIN)
        self.assertEqual(caught.exception.rule, "registry.digest_mismatch")

    def test_invalid_registry(self):
        self.assertRefused("registry.invalid", None, lambda registry: registry["journeys"][0].update(flow_ids=["X"]),
                           "registry")

    def test_invalid_inventory(self):
        broken = copy.deepcopy(INVENTORY)
        broken["schema_version"] = 2
        self.run_check()
        with self.assertRaises(module.Refused) as caught:
            self.run_check(inventory=broken)
        self.assertEqual(caught.exception.rule, "inventory.invalid")

    def test_real_pin_matches_the_imported_registry_blob_at_base(self):
        sources = module.GitSources(ROOT)
        try:
            blob = sources.blob(module.REGISTRY_PIN["commit"], module.REGISTRY_PIN["path"])
        except LookupError:
            self.fail("pinned registry commit must be in the local object store")
        self.assertEqual(module.gates.digest(blob), module.REGISTRY_PIN["sha256"])

    def test_trusted_git_skips_relative_and_repository_entries(self):
        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join(["relative/bin", str(ROOT / "scripts")])}):
            with self.assertRaises(LookupError):
                module.trusted_git(ROOT)


class HeaderTests(JourneyCase):
    def test_duplicate_abuse_id(self):
        self.assertRefused("id.duplicate", "AB-J01-01", lambda d: blueprint_of(d, "J01")["abuse_paths"].append(
            copy.deepcopy(blueprint_of(d, "J01")["abuse_paths"][0])))

    def test_duplicate_gap_id(self):
        self.assertRefused("id.duplicate", "GAP-J10-01", lambda g: g["gaps"].append(copy.deepcopy(g["gaps"][0])),
                           "gaps")

    def test_approval_order(self):
        self.assertRefused("approval.order", None, lambda d: d["approvals"].reverse())

    def test_recorded_approval_without_source(self):
        self.assertRefused("approval.source_mismatch", "security", setter(("approvals", 2, "status"), "recorded"))

    def test_pending_approval_with_source(self):
        source = {"commit": "3" * 40, "path": "governance/synthetic.json", "sha256": "sha256:" + "b" * 64}
        self.assertRefused("approval.source_mismatch", "ia", setter(("approvals", 4, "source"), source))

    def test_research_complete_without_evidence(self):
        self.assertRefused("research.complete_without_evidence", "PenniLogic/docs#66",
                           setter(("research_gate", "status"), "complete"))

    def test_validated_status_with_pending_gates(self):
        self.assertRefused("status.validated_with_gaps", None, setter(("status",), "validated"))

    def test_diagram_set_mismatch(self):
        self.assertRefused("diagram.set_mismatch", None, lambda d: d["diagrams"].pop())

    def test_diagram_owned_elsewhere_in_registry(self):
        self.assertRefused("diagram.registry_mismatch", "D04",
                           lambda r: r["diagrams"][2].update(owner_ticket="T-UXR-05"), "registry")


class BlueprintTests(JourneyCase):
    def test_blueprint_id_must_name_its_journey(self):
        self.assertRefused("blueprint.journey_mismatch", "BP-J02", setter(("BP-J01", "id"), "BP-J02"))

    def test_unknown_journey(self):
        def mutate(registry):
            registry["journeys"] = registry["journeys"][:1]
            for flow in registry["flows"]:
                flow["journey_ids"] = [item for item in flow["journey_ids"] if item != "J10"]
        self.assertRefused("blueprint.unknown_journey", "BP-J10", mutate, "registry")

    def test_missing_journey(self):
        def mutate(document):
            document["blueprints"] = document["blueprints"][:1]
        self.assertRefused("blueprint.missing_journey", "J10", mutate)

    def test_name_mismatch(self):
        self.assertRefused("blueprint.name_mismatch", "BP-J01", setter(("BP-J01", "journey_name"), "Renamed"))

    def test_persona_mismatch(self):
        self.assertRefused("blueprint.persona_mismatch", "BP-J01", setter(("BP-J01", "persona_ids"), ["P10"]))

    def test_flow_mismatch(self):
        self.assertRefused("blueprint.flow_mismatch", "BP-J01", setter(("BP-J01", "flow_ids"), ["F-AND-01"]))

    def test_audience_mismatch(self):
        self.assertRefused("blueprint.audience_mismatch", "BP-J10", setter(("BP-J10", "audience"), "operator"))

    def test_blueprint_order(self):
        self.assertRefused("blueprint.order", None, lambda d: d["blueprints"].reverse())

    def test_provisional_basis_must_cite_docs66(self):
        self.assertRefused("persona.basis_ref", "BP-J01",
                           setter(("BP-J01", "persona_basis_ref"), "pending:PenniLogic/docs#65"))

    def test_validated_persona_basis_without_research(self):
        self.assertRefused("persona.validated_without_evidence", "BP-J01",
                           setter(("BP-J01", "persona_basis"), "validated"))

    def test_target_map_supersedes_its_own_current_map(self):
        self.assertRefused("map.supersedes_mismatch", "BP-J01",
                           setter(("BP-J01", "target_map", "supersedes"), "BP-J10.current_map"))

    def test_minted_metric_refused(self):
        self.assertRefused("metric.minted", "BP-J01", setter(("BP-J01", "outcome", "metric_ref"), "M-J01-01"))

    def test_metric_must_stay_pending_on_docs77(self):
        self.assertRefused("metric.ref_not_pending", "BP-J01",
                           setter(("BP-J01", "outcome", "metric_ref"), "pending:PenniLogic/docs#75"))

    def test_policy_class_pinned_per_journey(self):
        self.assertRefused("policy.class_mismatch", "BP-J10", setter(("BP-J10", "policy_class"), "billing"))


def rename_step(document, old, new):
    """Rename a step and every reference to it (a single logical mutation of one step ID)."""
    for bp in document["blueprints"]:
        for item in bp["steps"]:
            if item["id"] == old:
                item["id"] = new
            item["next"] = [new if target == old else target for target in item["next"]]
            for branch in item["branches"]:
                branch["to"] = new if branch["to"] == old else branch["to"]
        for entry in bp["moments_of_truth"] + bp["abuse_paths"]:
            entry["step_id"] = new if entry["step_id"] == old else entry["step_id"]


class StepTests(JourneyCase):
    def test_step_journey_mismatch(self):
        self.assertRefused("step.journey_mismatch", "J02.C.01", lambda d: rename_step(d, "J01.C.01", "J02.C.01"))

    def test_lane_letter_mismatch(self):
        self.assertRefused("step.lane_mismatch", "J01.C.01", setter(("J01.C.01", "lane"), "team"))

    def test_channel_outside_lane(self):
        self.assertRefused("step.channel_lane_mismatch", "J10.T.02", setter(("J10.T.02", "channel"), "web"))

    def test_surface_step_without_flow(self):
        self.assertRefused("step.flow_missing", "J01.C.01", setter(("J01.C.01", "flow_id"), None))

    def test_service_step_with_flow(self):
        self.assertRefused("step.flow_on_service", "J01.T.01", setter(("J01.T.01", "flow_id"), "F-AND-01"))

    def test_flow_outside_journey(self):
        self.assertRefused("step.flow_outside_journey", "J01.C.01 F-AND-02",
                           setter(("J01.C.01", "flow_id"), "F-AND-02"))

    def test_flow_platform_must_match_channel(self):
        self.assertRefused("step.flow_channel_mismatch", "J01.C.02 F-AND-01",
                           setter(("J01.C.02", "flow_id"), "F-AND-01"))

    def test_notification_may_cite_any_journey_flow(self):
        document = copy.deepcopy(DOCUMENT)
        setter(("J10.C.02", "flow_id"), "F-WEB-02")(document)
        self.run_check(document)

    def test_surface_step_without_screen(self):
        self.assertRefused("step.screen_missing", "J01.C.01", setter(("J01.C.01", "screen_ids"), []))

    def test_screen_outside_flow(self):
        self.assertRefused("step.screen_outside_flow", "J01.C.01 S-AND-002",
                           setter(("J01.C.01", "screen_ids"), ["S-AND-002"]))

    def test_screen_on_service_step(self):
        self.assertRefused("step.screen_outside_flow", "J01.T.01 S-AND-001",
                           setter(("J01.T.01", "screen_ids"), ["S-AND-001"]))

    def test_dangling_next(self):
        self.assertRefused("step.dangling_next", "J01.C.02", setter(("J01.C.02", "next"), ["J10.C.01"]))

    def test_dangling_branch_target(self):
        self.assertRefused("branch.dangling_target", "J01.T.01", setter(("J01.T.01", "branches", 0, "to"), "J01.T.09"))

    def test_service_step_without_branch(self):
        self.assertRefused("step.service_without_branch", "J10.T.01", setter(("J10.T.01", "branches"), []))

    def test_unreachable_step(self):
        def mutate(document):
            extra = copy.deepcopy(step_of(document, "J01.C.02"))
            extra["id"], extra["handoff"] = "J01.C.03", None
            blueprint_of(document, "J01")["steps"].append(extra)
        self.assertRefused("step.unreachable", "J01.C.03", mutate)

    def test_no_terminal_step(self):
        self.assertRefused("step.no_terminal", "BP-J01", setter(("J01.C.02", "next"), ["J01.T.01"]))

    def test_cross_channel_handoff_missing(self):
        self.assertRefused("handoff.missing", "J01.C.02", setter(("J01.C.02", "handoff"), None))

    def test_handoff_without_channel_change(self):
        self.assertRefused("handoff.unexpected", "J01.C.01", setter(
            ("J01.C.01", "handoff"), {"authoritative_service": "sync-api", "may_show": "Status only"}))

    def test_branch_edge_into_another_surface_needs_handoff(self):
        self.assertRefused("handoff.missing", "J01.C.01", setter(("J01.T.01", "branches", 0, "to"), "J01.C.01"))


class BoundaryAndReferenceTests(JourneyCase):
    def test_raw_message_egress(self):
        self.assertRefused("boundary.raw_message_egress", "J01.T.01",
                           setter(("J01.T.01", "boundary", "raw_message_egress"), True))

    def test_client_money_arithmetic(self):
        self.assertRefused("boundary.client_money_arithmetic", "J01.C.02",
                           setter(("J01.C.02", "boundary", "client_money_arithmetic"), True))

    def test_unauthorized_detail_access(self):
        self.assertRefused("boundary.unauthorized_detail_access", "J10.T.02",
                           setter(("J10.T.02", "boundary", "unauthorized_detail_access"), True))

    def test_restricted_data_on_notification(self):
        self.assertRefused("boundary.restricted_notification", "J10.C.02",
                           setter(("J10.C.02", "data_class"), "restricted"))

    def test_restricted_data_on_service_allowed(self):
        document = copy.deepcopy(DOCUMENT)
        setter(("J10.T.01", "data_class"), "restricted")(document)
        self.run_check(document)

    def test_content_bearing_telemetry_field(self):
        self.assertRefused("telemetry.content_field", "J01.C.01", setter(
            ("J01.C.01", "telemetry", "fields"), ["journey_id", "step_id", "merchant_name"]))

    def test_telemetry_without_step_identity(self):
        self.assertRefused("telemetry.identity_missing", "J01.C.01",
                           setter(("J01.C.01", "telemetry", "fields"), ["journey_id", "outcome"]))

    def test_minted_event_refused(self):
        self.assertRefused("event.minted", "J01.T.01", setter(("J01.T.01", "event_refs"), ["EV-001"]))

    def test_event_reference_grammar(self):
        self.assertRefused("event.ref_grammar", "J01.T.01",
                           setter(("J01.T.01", "event_refs"), ["contracts#3"]))

    def test_event_owner_must_be_an_inventory_issue(self):
        self.assertRefused("reference.unknown_issue", "J01.T.01 PenniLogic/contracts#999",
                           setter(("J01.T.01", "event_refs"), ["pending:PenniLogic/contracts#999"]))

    def test_policy_reference_grammar(self):
        self.assertRefused("policy.ref_grammar", "J01.T.01", setter(("J01.T.01", "policy_refs"), ["ADR 15"]))

    def test_unknown_adr(self):
        self.assertRefused("policy.unknown_adr", "J01.T.01 ADR-099", setter(("J01.T.01", "policy_refs"), ["ADR-099"]))

    def test_pending_policy_reference_allowed(self):
        document = copy.deepcopy(DOCUMENT)
        setter(("J01.T.01", "policy_refs"), ["pending:PenniLogic/docs#75"])(document)
        self.run_check(document)

    def test_controls_outside_policy_journey(self):
        self.assertRefused("policy.controls_unexpected", "J01.T.01", setter(
            ("J01.T.01", "controls"), copy.deepcopy(step_of(DOCUMENT, "J10.T.01")["controls"])))

    def test_policy_journey_without_controls(self):
        self.assertRefused("policy.controls_missing", "BP-J10", setter(("J10.T.01", "controls"), None))


class CoverageTests(JourneyCase):
    def test_flow_without_step(self):
        def mutate(document):
            # One mutation: the only F-WEB-01 step is replaced by a notification step that cites no flow.
            steps = blueprint_of(document, "J01")["steps"]
            steps[2] = step("J01.C.02", "notification", "Sees the plan", "notification-service", None, (), (), (),
                            "completion", handoff="sync-api")
        self.assertRefused("coverage.flow_without_step", "BP-J01 F-WEB-01", mutate)

    def test_missing_branch_kind(self):
        self.assertRefused("coverage.branch_missing", "BP-J01",
                           lambda d: blueprint_of(d, "J01")["not_applicable"].pop(0))

    def test_missing_signal(self):
        self.assertRefused("coverage.signal_missing", "BP-J01",
                           lambda d: blueprint_of(d, "J01")["not_applicable"].pop())

    def test_not_applicable_kind_outside_scope(self):
        self.assertRefused("coverage.not_applicable_kind", "BP-J01",
                           setter(("BP-J01", "not_applicable", 3, "kind"), "offline"))

    def test_not_applicable_contradicts_a_present_branch(self):
        self.assertRefused("coverage.not_applicable_contradiction", "BP-J01",
                           lambda d: blueprint_of(d, "J01")["not_applicable"].append(
                               {"scope": "branch", "kind": "failure", "reason": "Synthetic reason"}))

    def test_dangling_moment_of_truth(self):
        self.assertRefused("moment.dangling_step", "BP-J01",
                           setter(("BP-J01", "moments_of_truth", 0, "step_id"), "J01.C.09"))

    def test_journey_without_abuse_path(self):
        self.assertRefused("abuse.missing", "BP-J10", setter(("BP-J10", "abuse_paths"), []))

    def test_abuse_path_of_another_journey(self):
        self.assertRefused("abuse.journey_mismatch", "AB-J02-01", setter(("BP-J01", "abuse_paths", 0, "id"),
                                                                       "AB-J02-01"))

    def test_abuse_path_on_unknown_step(self):
        self.assertRefused("abuse.dangling_step", "AB-J10-01",
                           setter(("BP-J10", "abuse_paths", 0, "step_id"), "J01.C.01"))

    def test_critical_flow_outside_every_journey(self):
        self.assertRefused("coverage.critical_flow_unmapped", "F-AND-02",
                           lambda registry: registry["flows"][4].update(critical=True), "registry")


def gap_setter(key, value):
    def mutate(gaps):
        gaps["gaps"][0][key] = value
    return mutate


class GapTests(JourneyCase):
    def test_gap_id_names_its_journey(self):
        self.assertRefused("gap.journey_mismatch", "GAP-J01-01", gap_setter("id", "GAP-J01-01"), "gaps")

    def test_gap_unknown_journey(self):
        def mutate(gaps):
            gaps["gaps"][0].update(id="GAP-J05-01", journey_id="J05", step_id=None)
        self.assertRefused("gap.unknown_journey", "GAP-J05-01", mutate, "gaps")

    def test_gap_dangling_step(self):
        self.assertRefused("gap.dangling_step", "GAP-J10-01", gap_setter("step_id", "J01.C.01"), "gaps")

    def test_gap_owner_must_be_an_inventory_issue(self):
        self.assertRefused("reference.unknown_issue", "GAP-J10-01 PenniLogic/docs#9999",
                           gap_setter("owner_issue", "PenniLogic/docs#9999"), "gaps")

    def test_registry_gap_routed_to_docs75(self):
        self.assertRefused("gap.category_owner", "GAP-J10-01", gap_setter("owner_issue", "PenniLogic/docs#74"),
                           "gaps")

    def test_service_gap_may_route_to_any_inventory_owner(self):
        gaps = copy.deepcopy(GAPS)
        gaps["gaps"][0].update(category="service", owner_issue="PenniLogic/contracts#3")
        self.run_check(gaps=gaps)

    def test_backlog_item_must_be_an_inventory_issue(self):
        self.assertRefused("reference.unknown_issue", "GAP-J10-01 PenniLogic/docs#9999",
                           gap_setter("backlog_item", "PenniLogic/docs#9999"), "gaps")


EXPECTED_GAPS = {
    "readiness.registry_unintegrated": ["PenniLogic/docs#75"],
    "readiness.research_pending": ["PenniLogic/docs#66"],
    "readiness.persona_provisional": ["J01", "J10"],
    "readiness.approval_pending": ["architecture", "ia", "operations", "product", "security"],
    "readiness.metric_pending": ["J01", "J10"],
    "readiness.event_pending": ["J01.T.01", "J10.T.01"],
    "readiness.gap_open": ["GAP-J10-01"],
    "readiness.gap_backlog_missing": ["GAP-J10-01"],
    "readiness.figma_held": ["D01", "D03", "D04", "D05", "D21"],
}


class ReadinessTests(JourneyCase):
    def test_control_readiness_gaps_are_exact(self):
        self.assertEqual(module.readiness(self.run_check()), EXPECTED_GAPS)

    def test_backlog_item_clears_only_the_backlog_gap(self):
        gaps = copy.deepcopy(GAPS)
        gaps["gaps"][0]["backlog_item"] = "PenniLogic/docs#75"
        result = module.readiness(self.run_check(gaps=gaps))
        self.assertEqual(result["readiness.gap_backlog_missing"], [])
        self.assertEqual(result["readiness.gap_open"], ["GAP-J10-01"])

    def test_resolved_gap_is_not_counted(self):
        gaps = copy.deepcopy(GAPS)
        gaps["gaps"][0]["status"] = "resolved"
        result = module.readiness(self.run_check(gaps=gaps))
        self.assertEqual((result["readiness.gap_open"], result["readiness.gap_backlog_missing"]), ([], []))

    def test_reopen_index_lists_only_referencing_blueprints(self):
        index = module.reopen_index(self.run_check())
        self.assertEqual(index["system"]["sync-api"], ["BP-J01"])
        self.assertEqual(index["system"]["rights-service"], ["BP-J10"])
        self.assertEqual(index["event"][EVENT], ["BP-J01", "BP-J10"])
        self.assertEqual(index["policy"], {"ADR-015": ["BP-J01"]})


class SummaryAndCliTests(JourneyCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.assertNotIn(ROOT, self.root.resolve().parents)
        (self.root / "product").mkdir()
        (self.root / "adr").mkdir()
        (self.root / "planning").mkdir()
        (self.root / "adr" / "ADR-015.md").write_text("synthetic\n", encoding="utf-8", newline="\n")
        (self.root / module.DATA).write_bytes(encode(DOCUMENT))
        (self.root / module.GAPS).write_bytes(encode(GAPS))
        (self.root / module.SCHEMA).write_bytes((ROOT / module.SCHEMA).read_bytes())
        (self.root / module.INVENTORY).write_bytes((ROOT / module.INVENTORY).read_bytes())
        self.patches = [mock.patch.object(module, "ROOT", self.root),
                        mock.patch.object(module, "REGISTRY_PIN", PIN),
                        mock.patch.object(module, "GitSources", lambda root: SOURCES)]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.directory.cleanup()

    def main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_structure_mode(self):
        code, out, _ = self.main("--structure")
        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("checked; readiness not evaluated.\n"))

    def test_default_mode_refuses_a_missing_summary(self):
        self.assertEqual(self.main(), (1, "", "Journey blueprint check refused: summary.drift\n"))

    def test_write_then_default_reports_not_green_with_counts(self):
        self.assertEqual(self.main("--write-summary")[0], 0)
        code, out, _ = self.main()
        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertEqual(lines[0], module.NOT_GREEN)
        self.assertEqual(lines[2:], [f"{rule}: {len(EXPECTED_GAPS[rule])}" for rule in module.READINESS_RULES])
        self.assertEqual(self.main("--check-summary")[0], 0)

    def test_summary_drift_after_one_byte_edit(self):
        self.main("--write-summary")
        target = self.root / module.SUMMARY
        target.write_bytes(target.read_bytes() + b"\n")
        self.assertEqual(self.main("--check-summary"), (1, "", "Journey blueprint check refused: summary.drift\n"))

    def test_summary_is_deterministic_lf_and_free_of_timestamps(self):
        model = self.run_check()
        first = module.render_summary(model, module.readiness(model))
        self.assertEqual(first, module.render_summary(self.run_check(), module.readiness(self.run_check())))
        self.assertNotIn("\r", first)
        self.assertTrue(first.endswith("\n") and not first.endswith("\n\n"))
        self.assertNotRegex(first, r"20[0-9]{2}-[0-9]{2}-[0-9]{2}")
        self.assertIn("| readiness.gap_backlog_missing | 1 | GAP-J10-01 |", first)

    def refused(self, rule):
        return (1, "", f"Journey blueprint check refused: {rule}\n")

    def replace_data(self, old, new):
        target = self.root / module.DATA
        raw = target.read_bytes()
        self.assertEqual(raw.count(old), 1)
        target.write_bytes(raw.replace(old, new))

    def test_duplicate_key_in_data_fails_closed_without_echo(self):
        self.assertEqual(self.main("--structure")[0], 0)
        self.replace_data(b'"kind": "journey_blueprints",', b'"kind": "journey_blueprints",\n  "kind": "x",')
        self.assertEqual(self.main("--structure"), self.refused("input.unreadable_or_invalid"))

    def test_byte_order_mark_fails_closed(self):
        self.assertEqual(self.main("--structure")[0], 0)
        target = self.root / module.DATA
        target.write_bytes(b"\xef\xbb\xbf" + target.read_bytes())
        self.assertEqual(self.main("--structure"), self.refused("input.unreadable_or_invalid"))

    def test_nan_constant_is_schema_invalid(self):
        self.assertEqual(self.main("--structure")[0], 0)
        self.replace_data(b'"schema_version": 1,', b'"schema_version": NaN,')
        self.assertEqual(self.main("--structure"), self.refused("schema.invalid"))

    def test_symlinked_input_file_refused(self):
        self.assertEqual(self.main("--structure")[0], 0)
        with tempfile.TemporaryDirectory() as outside:
            copy_path = Path(outside) / "data.json"
            copy_path.write_bytes((self.root / module.DATA).read_bytes())
            (self.root / module.DATA).unlink()
            os.symlink(copy_path, self.root / module.DATA)
            self.assertEqual(self.main("--structure"), self.refused("input.unreadable_or_invalid"))

    def test_symlinked_parent_directory_refused(self):
        self.assertEqual(self.main("--structure")[0], 0)
        with tempfile.TemporaryDirectory() as outside:
            moved = Path(outside) / "product"
            (self.root / "product").rename(moved)
            os.symlink(moved, self.root / "product", target_is_directory=True)
            self.assertEqual(self.main("--structure"), self.refused("input.unreadable_or_invalid"))

    def test_write_summary_never_follows_a_symlinked_target(self):
        self.assertEqual(self.main("--write-summary")[0], 0)
        with tempfile.TemporaryDirectory() as outside:
            victim = Path(outside) / "victim.md"
            victim.write_bytes(b"unchanged\n")
            (self.root / module.SUMMARY).unlink()
            os.symlink(victim, self.root / module.SUMMARY)
            self.assertEqual(self.main("--write-summary"), self.refused("input.unreadable_or_invalid"))
            self.assertEqual(victim.read_bytes(), b"unchanged\n")

    def test_natural_key_orders_ascii_digits_and_tolerates_other_digits(self):
        self.assertEqual(sorted(["J10", "J02", "J1"], key=module.natural_key), ["J1", "J02", "J10"])
        self.assertEqual(module.natural_key("J01\u00b2"), [(0, "J"), (1, "01"), (0, "\u00b2")])

    def test_invalid_input_fails_closed_without_echo(self):
        (self.root / module.DATA).write_text("{\"kind\": \"secret-ish text\",", encoding="utf-8", newline="\n")
        self.assertEqual(self.main("--structure"),
                         (1, "", "Journey blueprint check refused: input.unreadable_or_invalid\n"))


def _ids(prefix, count):
    return [f"{prefix}{index:02d}" for index in range(1, count + 1)]


PUBLISHED_GAPS = ["GAP-J01-01", "GAP-J01-02", "GAP-J02-01", "GAP-J02-02", "GAP-J05-01", "GAP-J06-01", "GAP-J07-01",
                  "GAP-J07-02", "GAP-J07-03", "GAP-J09-01", "GAP-J10-01", "GAP-J11-01", "GAP-J11-02", "GAP-J12-01"]
PUBLISHED_READINESS = {
    "readiness.registry_unintegrated": ["PenniLogic/docs#75"],
    "readiness.research_pending": ["PenniLogic/docs#66"],
    "readiness.persona_provisional": _ids("J", 12),
    "readiness.approval_pending": ["architecture", "ia", "operations", "product", "security"],
    "readiness.metric_pending": _ids("J", 12),
    "readiness.event_pending": [
        "J01.T.02", "J01.T.03", "J03.T.02", "J03.T.03", "J03.T.04", "J03.T.05", "J04.T.01", "J04.T.02", "J05.T.01",
        "J05.T.02", "J05.T.03", "J06.T.01", "J06.T.02", "J06.T.03", "J06.T.04", "J07.T.01", "J07.T.02", "J07.T.03",
        "J07.T.04", "J08.C.04", "J08.T.01", "J08.T.03", "J09.T.01", "J09.T.02", "J09.T.03", "J10.T.01", "J10.T.04",
        "J10.T.06", "J10.T.08", "J11.T.04", "J11.T.06", "J12.T.02"],
    "readiness.gap_open": PUBLISHED_GAPS,
    "readiness.gap_backlog_missing": PUBLISHED_GAPS,
    "readiness.figma_held": ["D01", "D03", "D04", "D05", "D21"],
}


class PublishedDataTests(unittest.TestCase):
    """The committed J01-J12 blueprints and gaps, read (never written) and checked against the real pinned registry."""

    @classmethod
    def setUpClass(cls):
        cls.model = module.load_and_check(ROOT)
        cls.document, cls.gaps = cls.model.document, cls.model.gaps

    def test_structure_line_is_exact(self):
        self.assertEqual(
            module.structure_line(self.model),
            "Journey blueprints 0.1.0 structure valid: 12 blueprints, 125 steps (69 customer, 56 team), 94 branches, "
            "28 abuse paths, 14 gaps; registry " + module.REGISTRY_PIN["commit"] + " checked")

    def test_readiness_gaps_are_exact(self):
        self.assertEqual(module.readiness(self.model), PUBLISHED_READINESS)

    def test_committed_summary_matches_the_data(self):
        expected = module.render_summary(self.model, module.readiness(self.model))
        self.assertEqual((ROOT / module.SUMMARY).read_bytes(), expected.encode("utf-8"))

    def test_default_mode_reports_not_green_with_exact_counts(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main([])
        self.assertEqual((code, err.getvalue()), (1, ""))
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0], module.NOT_GREEN)
        self.assertEqual(lines[2:], [f"{rule}: {len(PUBLISHED_READINESS[rule])}" for rule in module.READINESS_RULES])

    def test_one_blueprint_per_registry_journey_in_order(self):
        self.assertEqual([item["id"] for item in self.document["blueprints"]], _ids("BP-J", 12))
        self.assertEqual(sorted(self.model.registry["journeys"]), _ids("J", 12))

    def test_every_critical_registry_flow_has_a_step(self):
        used = {step["flow_id"] for step in self.model.steps.values()}
        critical = {flow_id for flow_id, flow in self.model.registry["flows"].items() if flow["critical"]}
        self.assertEqual(len(critical), 35)
        self.assertLessEqual(critical, used)

    def test_held_inputs_stay_visibly_incomplete(self):
        self.assertEqual(self.document["status"], "provisional")
        self.assertEqual(self.document["research_gate"], {"issue": "PenniLogic/docs#66", "status": "pending",
                                                          "evidence": []})
        self.assertTrue(all(item["status"] == "pending" and item["source"] is None
                            for item in self.document["approvals"]))
        self.assertTrue(all(item["figma"] == "held" for item in self.document["diagrams"]))
        for blueprint in self.document["blueprints"]:
            self.assertEqual((blueprint["persona_basis"], blueprint["persona_basis_ref"]),
                             ("provisional", "pending:PenniLogic/docs#66"))
            self.assertEqual(blueprint["outcome"]["metric_ref"], "pending:PenniLogic/docs#77")

    def test_no_backlog_item_is_claimed_for_any_gap(self):
        # docs#67 criterion 5 stays unmet: this change creates no issue, so every gap is open without a backlog item.
        self.assertEqual([gap["id"] for gap in self.gaps["gaps"]], PUBLISHED_GAPS)
        self.assertTrue(all(gap["status"] == "open" and gap["backlog_item"] is None for gap in self.gaps["gaps"]))

    def test_event_references_are_pending_owner_issues_only(self):
        values = {value for step in self.model.steps.values() for value in step["event_refs"]}
        self.assertTrue(values)
        self.assertTrue(all(module.PENDING_REF.fullmatch(value) for value in values))

    def test_policy_operator_and_household_blueprints_carry_controls_and_abuse_paths(self):
        by_journey = self.model.blueprints
        for journey_id, policy_class in module.POLICY_CLASS.items():
            self.assertEqual(by_journey[journey_id]["policy_class"], policy_class)
            self.assertTrue(any(step["controls"] for step in by_journey[journey_id]["steps"]))
        for journey_id in ("J07", "J10", "J11", "J12"):
            self.assertGreaterEqual(len(by_journey[journey_id]["abuse_paths"]), 3)
        self.assertEqual([item["audience"] for item in by_journey.values()].count("operator"), 2)
        kinds = {branch["kind"] for step in by_journey["J07"]["steps"] for branch in step["branches"]}
        self.assertIn("revocation", kinds)


if __name__ == "__main__":
    unittest.main()
