"""T-UXR-06 validator tests: synthetic rule fixtures plus read-only checks of the published registry files.

Every rule test builds a fresh deep copy of one synthetic registry, proves it passes (the control), applies exactly
one mutation and asserts the exact static rule identifier and offending identifier. The registry is complete except
for the held interfaces: no D6, handoff, route or verified-QA reference can be resolved yet, so none is recorded and
the baseline keeps exactly those readiness gaps. The synthetic fixtures hold no real coverage, approvals, gate
records, people, money or contact data. Command-line tests run
against hermetic temporary Git checkouts outside this repository. PublishedDataTests read this checkout's committed
product/experience-coverage.* files and inputs (and, for the real-Git paths, its local object store and
refs/remotes/origin/main) without writing anything. Nothing here touches the network.
"""

import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "check_experience_coverage", ROOT / "scripts/check_experience_coverage.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SCHEMA = module.support.load_json(ROOT / module.SCHEMA)
SCHEMA_BYTES = (ROOT / module.SCHEMA).read_bytes()
PLANNING_SCHEMA = module.support.load_json(ROOT / "planning/source/schema/experience-coverage.schema.json")
GATES_SCHEMA = module.support.load_json(ROOT / module.gates.SCHEMA)
EMPTY_GAPS = {rule: [] for rule in module.READINESS_RULES}
# References to held interfaces are refused, so the synthetic registry keeps these gaps and is never GREEN.
SCREEN_IDS = ["S-AND-001", "S-AND-002", "S-AND-003", "S-AND-004", "S-WEB-001", "S-ADM-001"]
HELD_GAPS = {
    "readiness.d6_missing": SCREEN_IDS, "readiness.route_missing": SCREEN_IDS,
    "readiness.qa_unverified": ["F-AND-01", "F-WEB-01", "F-ADM-01"],
}
BASELINE_GAPS = {**EMPTY_GAPS, **HELD_GAPS}
IMPORT_COMMIT = "1" * 40
EVIDENCE_COMMIT = "2" * 40
EVIDENCE_PATH = "research/fixtures/qa-independence-synthetic.txt"
EVIDENCE_BYTES = b"Synthetic independent QA verification fixture; not a review or an approval.\n"


def ticket(plan_id, issue):
    return {"plan_id": plan_id, "issue": issue}


PERSONA_OWNER = ticket("T-SYN-PER-01", "PenniLogic/docs#901")
JOURNEY_OWNER = ticket("T-SYN-JRN-01", "PenniLogic/docs#902")
STORY_OWNER = ticket("T-SYN-STY-01", "PenniLogic/docs#903")
DESIGN = ticket("T-SYN-DSN-01", "PenniLogic/docs#904")
QA = ticket("T-SYN-QA-01", "PenniLogic/docs#905")
COMPONENT_DESIGN = ticket("T-SYN-CMP-01", "PenniLogic/docs#906")
DIAGRAM_OWNER = ticket("T-SYN-DGM-01", "PenniLogic/docs#907")
AUTHOR = ticket("T-UXR-06", "PenniLogic/docs#75")
AND1 = ticket("T-SYN-AND-01", "PenniLogic/android#901")
AND3 = ticket(None, "PenniLogic/android#903")
WEB1 = ticket("T-SYN-WEB-01", "PenniLogic/web#901")
ADM1 = ticket("T-SYN-ADM-01", "PenniLogic/admin#901")


def issue(repository, number, plan_id=None, state="open", reason=None, source=None):
    return {
        "reference": f"PenniLogic/{repository}#{number}", "repository": f"PenniLogic/{repository}", "number": number,
        "title": f"Synthetic fixture issue {number}", "state": state, "state_reason": reason, "source": source,
        "plan_id": plan_id,
    }


def build_inventory(issues):
    counts = dict.fromkeys(module.strategy.REPOSITORY_IDS, 0)
    for item in issues:
        counts[item["repository"]] += 1
    return {
        "schema_version": 1, "organization": module.strategy.ORGANIZATION,
        "organization_id": module.strategy.ORGANIZATION_ID, "operator": module.strategy.OPERATOR,
        "snapshot_at": "2026-09-30T01:15:16Z", "issue_count": len(issues),
        "repositories": {
            name: {"id": identifier, "issue_count": counts[name], "total_count": counts[name]}
            for name, identifier in module.strategy.REPOSITORY_IDS.items()
        },
        "issues": issues,
    }


ISSUES = [
    issue("docs", 75, "T-UXR-06"),
    issue("docs", 901, "T-SYN-PER-01"), issue("docs", 902, "T-SYN-JRN-01"), issue("docs", 903, "T-SYN-STY-01"),
    issue("docs", 904, "T-SYN-DSN-01"), issue("docs", 905, "T-SYN-QA-01"), issue("docs", 906, "T-SYN-CMP-01"),
    issue("docs", 907, "T-SYN-DGM-01"),
    issue("android", 901, "T-SYN-AND-01"), issue("android", 902, "T-SYN-AND-02"),
    issue("android", 903, source="PenniLogic-old/android#902"),
    issue("android", 904, "T-SYN-AND-04", "closed", "completed"),
    issue("web", 901, "T-SYN-WEB-01"), issue("web", 902, "T-SYN-WEB-02"),
    issue("admin", 901, "T-SYN-ADM-01"),
]
STATES = ["empty", "loading", "error", "offline", "stale", "permission-denied", "quota-exceeded", "degraded",
          "success", "revoked"]
TAXONOMY = {"states": [{"id": state, "name": state.replace("_", "-")} for state in module.support.REQUIRED_STATES]}


def d6_reference(identifier):
    """A well-formed design-gates dependency for a screen; refused while no D6 gate record can be resolved."""
    scope = module.gates.digest(f"synthetic D6 scope {identifier}")
    return {"artifact_id": identifier, "gate_id": "D6", "scope_sha256": scope}


def verified_qa():
    """A verified QA independence with pinned, matching evidence; refused while docs#126 defines no record."""
    return {"status": "verified", "evidence": {
        "commit": EVIDENCE_COMMIT, "path": EVIDENCE_PATH, "sha256": module.gates.digest(EVIDENCE_BYTES),
    }}


def screen(identifier, flow, components, states, route_hint, implementation, *, critical=True, surface="page",
           security=None):
    platform = module.INFIX[identifier.split("-")[1]]
    reason, privacy, authorization = security or (None, [], [])
    return {
        "id": identifier, "platform": platform, "name": f"Synthetic screen {identifier[-3:]}", "surface_type": surface,
        "route_hint": route_hint, "route_id": None, "flow_ids": [flow],
        "component_ids": components, "states": states, "critical": critical, "security_critical": reason is not None,
        "security_reason": reason, "privacy_states": privacy, "authorization_states": authorization,
        "d6_dependency": None, "handoff_ref": None, "design_ticket": copy.deepcopy(DESIGN),
        "implementation_tickets": [copy.deepcopy(implementation)], "qa_ticket": copy.deepcopy(QA), "proposal": None,
    }


def flow(identifier, journey, screens, implementation, critical=True):
    return {
        "id": identifier, "platform": module.INFIX[identifier.split("-")[1]], "name": f"Synthetic flow {identifier}",
        "critical": critical, "journey_ids": [journey], "screen_ids": screens, "design_ticket": copy.deepcopy(DESIGN),
        "implementation_tickets": [copy.deepcopy(implementation)], "qa_ticket": copy.deepcopy(QA),
        "qa_independence": {"status": "unverified", "evidence": None},
    }


def story(identifier, flow_id, personas, journeys):
    return {
        "id": identifier, "platform": module.INFIX[identifier.split("-")[1]], "as_a": "synthetic fixture persona",
        "i_want": "a synthetic outcome", "so_that": "the validator has a complete chain", "persona_ids": personas,
        "journey_ids": journeys, "flow_id": flow_id, "owner_ticket": copy.deepcopy(STORY_OWNER),
    }


def component(identifier, platforms, states, foundational=False):
    return {
        "id": identifier, "name": f"Synthetic component {identifier}", "platforms": platforms,
        "required_states": states, "foundational": foundational, "design_ticket": copy.deepcopy(COMPONENT_DESIGN),
        "proposal": None,
    }


SECURITY = ("Synthetic fixture: grants and revokes shared access.", ["revoked"], ["permission-denied"])
OPERATOR = ("Synthetic fixture: operator queue behind role checks.", ["permission-denied"], ["permission-denied"])
COLLECTIONS = {
    "personas": [
        {"id": "P01", "name": "Synthetic persona one", "jobs": ["Synthetic job one"], "platforms": ["android", "web"],
         "owner_ticket": copy.deepcopy(PERSONA_OWNER)},
        {"id": "P02", "name": "Synthetic persona two", "jobs": ["Synthetic job two"], "platforms": ["admin"],
         "owner_ticket": copy.deepcopy(PERSONA_OWNER)},
        {"id": "P03", "name": "Synthetic persona three", "jobs": ["Synthetic job three"], "platforms": ["shared"],
         "owner_ticket": copy.deepcopy(PERSONA_OWNER)},
    ],
    "journeys": [
        {"id": "J01", "name": "Synthetic journey one", "critical": True, "persona_ids": ["P01"],
         "flow_ids": ["F-AND-01", "F-AND-02", "F-WEB-01"], "owner_ticket": copy.deepcopy(JOURNEY_OWNER)},
        {"id": "J02", "name": "Synthetic journey two", "critical": True, "persona_ids": ["P02", "P03"],
         "flow_ids": ["F-ADM-01"], "owner_ticket": copy.deepcopy(JOURNEY_OWNER)},
    ],
    "user_stories": [
        story("US-AND-01", "F-AND-01", ["P01"], ["J01"]), story("US-AND-02", "F-AND-02", ["P01"], ["J01"]),
        story("US-WEB-01", "F-WEB-01", ["P01"], ["J01"]), story("US-ADM-01", "F-ADM-01", ["P02"], ["J02"]),
    ],
    "flows": [
        flow("F-AND-01", "J01", ["S-AND-001", "S-AND-002"], AND1),
        flow("F-AND-02", "J01", ["S-AND-003", "S-AND-004"], AND3, critical=False),
        flow("F-WEB-01", "J01", ["S-WEB-001"], WEB1),
        flow("F-ADM-01", "J02", ["S-ADM-001"], ADM1),
    ],
    "screens": [
        screen("S-AND-001", "F-AND-01", ["C-NAV-ANDROID", "C-ACTION-PRIMARY"],
               ["loading", "error", "permission-denied", "revoked", "success"], "android://home", AND1,
               security=SECURITY),
        screen("S-AND-002", "F-AND-01", ["C-ACTION-PRIMARY"], ["loading", "error"], "android://settings/:id", AND1),
        screen("S-AND-003", "F-AND-02", ["C-ACTION-PRIMARY"], ["empty", "success"], "android-widget://balance", AND3,
               critical=False, surface="widget"),
        screen("S-AND-004", "F-AND-02", ["C-NAV-ANDROID"], ["offline", "stale"], "android://balance/history", AND3,
               critical=False),
        screen("S-WEB-001", "F-WEB-01", ["C-ACTION-PRIMARY"], ["loading", "error", "empty"], "/home", WEB1),
        screen("S-ADM-001", "F-ADM-01", ["C-OP-QUEUE", "C-ACTION-PRIMARY"], ["loading", "error", "permission-denied"],
               "/operator/*", ADM1, security=OPERATOR),
    ],
    "components": [
        component("C-NAV-ANDROID", ["android"], ["default", "focus"]),
        component("C-ACTION-PRIMARY", ["shared"], ["default", "focus", "disabled", "loading"]),
        component("C-OP-QUEUE", ["admin"], ["default", "empty", "error"]),
        component("C-TRUST-FOUNDATION", ["android", "web"], ["default"], foundational=True),
    ],
    "diagrams": [
        {"id": "D01", "type": "context", "name": "Synthetic context diagram", "artifact_path": "Synthetic location",
         "owner_ticket": copy.deepcopy(DIAGRAM_OWNER)},
        {"id": "D20", "type": "coverage-matrix", "name": "Synthetic coverage matrix", "artifact_path": module.SUMMARY,
         "owner_ticket": copy.deepcopy(DIAGRAM_OWNER)},
    ],
}


def identity(record):
    """The identifying text the ledger fingerprints: the record's name, or a user story's i_want."""
    return record["i_want"] if "i_want" in record else record["name"]


def fingerprint(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


# The frozen import predates S-AND-004, so only the base registry can protect that ID.
IMPORT = {"kind": "experience_coverage", "schema_version": 1, **{
    collection: [{"id": record["id"], "i_want" if collection == "user_stories" else "name": identity(record)}
                 for record in records if record["id"] != "S-AND-004"]
    for collection, records in COLLECTIONS.items()
}}
IMPORT_BYTES = (json.dumps(IMPORT, indent=2) + "\n").encode("utf-8")
RANGES = [
    {"kind": "persona", "platform": None, "first": 1, "last": 99, "owner_role": "service_design"},
    {"kind": "journey", "platform": None, "first": 1, "last": 99, "owner_role": "service_design"},
    {"kind": "component", "platform": None, "first": None, "last": None, "owner_role": "systems"},
    {"kind": "diagram", "platform": None, "first": 1, "last": 99, "owner_role": "design_ops"},
] + [
    {"kind": kind, "platform": platform, "first": 1, "last": last, "owner_role": f"{platform}_design"}
    for kind, last in (("user_story", 99), ("flow", 99), ("screen", 999)) for platform in module.PLATFORMS
]
REGISTRY = {
    "kind": "experience_coverage", "schema_version": 2, "registry_version": "1.0.0",
    "source_issue": "PenniLogic/docs#75", "description": "Synthetic experience-coverage registry for validator tests.",
    "imported_from": {"commit": IMPORT_COMMIT, "path": module.IMPORT_PATH, "sha256": module.gates.digest(IMPORT_BYTES)},
    "required_states": STATES, "component_states": ["default", "focus", "disabled", "empty", "loading", "error"],
    "taxonomy_state_map": [{"state": item["name"], "taxonomy_state": item["id"]} for item in TAXONOMY["states"]],
    "id_ranges": RANGES,
    "id_ledger": [
        {"id": record["id"], "kind": kind, "platform": module.classify(record["id"])[1],
         "name_sha256": fingerprint(identity(record)), "status": "active", "retired_reason": None}
        for collection, kind in module.COLLECTIONS for record in COLLECTIONS[collection]
    ],
    **COLLECTIONS,
}


def entry(reference, plan_id, rationale_class=None, rationale=None):
    disposition = "frontend" if rationale_class is None else "non_frontend"
    return {"issue": reference, "plan_id": plan_id, "disposition": disposition, "rationale_class": rationale_class,
            "rationale": rationale, "proposed_by": None}


PARTITION = {
    "kind": "experience_coverage_partition", "schema_version": 1, "source_issue": "PenniLogic/docs#75",
    "description": "Synthetic partition of the synthetic client issues.",
    "repositories": ["PenniLogic/android", "PenniLogic/web", "PenniLogic/admin"], "post_snapshot_issues": [],
    "scope_questions": [],
    "entries": [
        entry("PenniLogic/android#901", "T-SYN-AND-01"),
        entry("PenniLogic/android#902", "T-SYN-AND-02", "quality_or_test_infrastructure",
              "Synthetic fixture: harness work without a screen."),
        entry("PenniLogic/android#903", None),
        entry("PenniLogic/android#904", "T-SYN-AND-04", "build_or_release",
              "Synthetic fixture: release packaging without a screen."),
        entry("PenniLogic/web#901", "T-SYN-WEB-01"),
        entry("PenniLogic/web#902", "T-SYN-WEB-02", "governance_or_tooling",
              "Synthetic fixture: repository tooling without a screen."),
        entry("PenniLogic/admin#901", "T-SYN-ADM-01"),
    ],
}


class Sources:
    """In-memory stand-in for GitSources: pinned blobs and the ledger base registry and partition bytes."""

    def __init__(self, blobs, base=None, base_error=False, partition=None):
        self.blobs, self.base, self.base_error, self.partition = blobs, base, base_error, partition

    def blob(self, commit, path):
        try:
            return self.blobs[(commit, path)]
        except KeyError:
            raise LookupError(path) from None

    def base_registry(self):
        if self.base_error:
            raise LookupError("no base")
        return self.base

    def base_partition(self):
        return self.partition


class Fixture:
    """A fresh deep copy of the synthetic registry (complete except for the held interfaces) and its inputs."""

    def __init__(self):
        self.registry, self.partition = copy.deepcopy(REGISTRY), copy.deepcopy(PARTITION)
        self.schema, self.taxonomy = copy.deepcopy(SCHEMA), copy.deepcopy(TAXONOMY)
        self.inventory = build_inventory(copy.deepcopy(ISSUES))
        self.blobs = {
            (IMPORT_COMMIT, module.IMPORT_PATH): IMPORT_BYTES, (EVIDENCE_COMMIT, EVIDENCE_PATH): EVIDENCE_BYTES,
        }
        self.pin = (module.IMPORT_PATH, module.gates.digest(IMPORT_BYTES))
        self.base, self.base_error, self.partition_base, self.synthetic_ok = None, False, None, False

    def check(self):
        return module.check(
            self.registry, self.partition, self.schema, self.inventory, self.taxonomy,
            Sources(self.blobs, self.base, self.base_error, self.partition_base), import_pin=self.pin,
            synthetic_ok=self.synthetic_ok,
        )

    def gaps(self):
        return module.readiness(self.check())

    def record(self, identifier):
        return next(item for collection, _ in module.COLLECTIONS for item in self.registry[collection]
                    if item["id"] == identifier)

    def ledger(self, identifier):
        return next(item for item in self.registry["id_ledger"] if item["id"] == identifier)

    def issue(self, reference):
        return next(item for item in self.inventory["issues"] if item["reference"] == reference)

    def entry(self, reference):
        return next(item for item in self.partition["entries"] if item["issue"] == reference)

    def freeze_base(self):
        """Record the current registry and partition as the committed base the ledger must extend."""
        self.base = json.dumps(self.registry).encode("utf-8")
        self.partition_base = json.dumps(self.partition).encode("utf-8")

    def drop_screen(self, identifier):
        """Remove a screen consistently: record, its ledger entry and its flow links."""
        self.registry["screens"].remove(self.record(identifier))
        self.registry["id_ledger"].remove(self.ledger(identifier))
        for item in self.registry["flows"]:
            if identifier in item["screen_ids"]:
                item["screen_ids"].remove(identifier)

    def set_import(self, raw):
        self.blobs[(IMPORT_COMMIT, module.IMPORT_PATH)] = raw
        self.registry["imported_from"]["sha256"] = module.gates.digest(raw)
        self.pin = (module.IMPORT_PATH, module.gates.digest(raw))


def planted_token():
    """A GitHub-token-shaped string built at runtime so no secret-shaped literal exists in source."""
    return "gh" + "p_" + "A1b2C3d4" * 5


class CoverageCase(unittest.TestCase):
    def refused(self, mutate, rule, subject=None, prepare=None):
        """Passing control, exactly one mutation, then the exact static rule and offending identifier."""
        fixture = Fixture()
        if prepare is not None:
            prepare(fixture)
        fixture.check()
        mutate(fixture)
        with self.assertRaises(module.Refused) as caught:
            fixture.check()
        self.assertIn(rule, module.STRUCTURE_RULES)
        self.assertEqual((caught.exception.rule, caught.exception.subject), (rule, subject))
        return fixture

    def gap(self, mutate, rule, subject, prepare=None):
        """The baseline has only the held-interface gaps; one mutation adds exactly one gap of one other rule."""
        self.assertNotIn(rule, HELD_GAPS)
        fixture = Fixture()
        if prepare is not None:
            prepare(fixture)
        self.assertEqual(fixture.gaps(), BASELINE_GAPS)
        mutate(fixture)
        self.assertEqual(fixture.gaps(), {**BASELINE_GAPS, rule: [subject]})


class BaselineAndSchemaTests(CoverageCase):
    def test_synthetic_registry_is_ready_except_the_held_interfaces(self):
        """The in-test baseline: structurally complete with only the held-interface gaps, so never GREEN."""
        model = Fixture().check()
        gaps = module.readiness(model)
        self.assertEqual(gaps, BASELINE_GAPS)
        self.assertEqual(model.ledger_base, "frozen import")
        self.assertEqual(module.render_summary(model, gaps).splitlines()[0], module.NOT_GREEN)
        # The GREEN line stays for a later registry version that resolves the held interfaces' records.
        self.assertEqual(module.render_summary(model, EMPTY_GAPS).splitlines()[0], module.GREEN)

    def test_schema_is_a_self_contained_subset_with_its_own_identity(self):
        keywords, refs, patterns = set(), [], []

        def walk(node):
            """Visit subschemas only: property and definition names are not keywords."""
            self.assertIsInstance(node, dict)
            keywords.update(node)
            refs.extend([node["$ref"]] if "$ref" in node else [])
            patterns.extend([node["pattern"]] if "pattern" in node else [])
            for section in ("properties", "definitions"):
                for child in node.get(section, {}).values():
                    walk(child)
            for key in ("items", "additionalProperties"):
                if isinstance(node.get(key), dict):
                    walk(node[key])

        walk(SCHEMA)
        self.assertLessEqual(keywords - set(module.support.ANNOTATIONS), set(module.support.SUPPORTED))
        self.assertTrue(refs and all(ref.startswith("#/definitions/") and ref[14:] in SCHEMA["definitions"]
                                     for ref in refs))
        self.assertTrue(patterns and all(pattern.startswith("^") and pattern.endswith("$(?![\\s\\S])")
                                         for pattern in patterns))
        self.assertEqual(SCHEMA["$schema"], "http://json-schema.org/draft-07/schema#")
        self.assertNotEqual(SCHEMA["$id"], PLANNING_SCHEMA.get("$id"))
        self.assertNotEqual(SCHEMA["title"], PLANNING_SCHEMA["title"])
        self.assertTrue(SCHEMA["$id"].endswith("/product/experience-coverage.schema.json"))

    def test_free_text_allowlist_matches_the_schema_exactly(self):
        self.assertEqual(module.unconstrained_text(SCHEMA), module.FREE_TEXT | module.GRAMMAR_CHECKED)

    def test_source_and_dependency_shapes_agree_with_design_gates(self):
        source = {"commit": "a" * 40, "path": "governance/example.json", "sha256": "sha256:" + "b" * 64}
        dependency = {"artifact_id": "S-AND-001", "gate_id": "D6", "scope_sha256": "sha256:" + "c" * 64}
        cases = [
            ("source", "optional_source", source, True),
            ("source", "optional_source", {**source, "commit": "a" * 39}, False),
            ("source", "optional_source", {**source, "sha256": "sha256:" + "b" * 64 + "\n"}, False),
            ("source", "optional_source", {**source, "extra": 1}, False),
            ("dependency", "optional_dependency", dependency, True),
            ("dependency", "optional_dependency", {**dependency, "gate_id": "D6\n"}, False),
            ("dependency", "optional_dependency", {**dependency, "scope_sha256": "sha256:" + "C" * 64}, False),
        ]
        for gates_definition, own_definition, value, valid in cases:
            with self.subTest(definition=own_definition, value=value):
                for check in (
                    lambda: module.gates.shape(value, GATES_SCHEMA, gates_definition),
                    lambda: module.shape(value, SCHEMA, own_definition),
                ):
                    if valid:
                        check()
                    else:
                        with self.assertRaises(ValueError):
                            check()

    def test_rule_ids_are_static_registered_and_tested(self):
        source = (ROOT / "scripts/check_experience_coverage.py").read_text(encoding="utf-8")
        constants, dynamic = set(), []
        for node in ast.walk(ast.parse(source)):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ("require", "Refused")):
                argument = node.args[1] if node.func.id == "require" else node.args[0]
                if isinstance(argument, ast.Constant):
                    constants.add(argument.value)
                else:
                    dynamic.append(ast.unparse(argument))
        # Only require() forwarding its parameter and the content-shape loop pass a non-literal rule.
        self.assertEqual(dynamic, ["rule", "rule"])
        shapes = {rule for rule, _ in module.CONTENT_SHAPES}
        self.assertEqual(constants | shapes | {"input.unreadable_or_invalid"}, set(module.STRUCTURE_RULES))
        for rules in (module.STRUCTURE_RULES, module.READINESS_RULES):
            self.assertEqual(len(rules), len(set(rules)))
            self.assertTrue(all(re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", rule) for rule in rules))
        self.assertTrue(all(rule.startswith("readiness.") for rule in module.READINESS_RULES))
        self.assertFalse(set(module.STRUCTURE_RULES) & set(module.READINESS_RULES))
        tests = Path(__file__).read_text(encoding="utf-8")
        self.assertEqual([rule for rule in module.STRUCTURE_RULES + module.READINESS_RULES if rule not in tests], [])

    def test_registry_checksum_canonical(self):
        registry = Fixture().registry
        canonical = json.dumps(registry, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        checksum = module.registry_checksum(registry)
        self.assertEqual(checksum, "sha256:" + hashlib.sha256(canonical).hexdigest())
        reordered = json.loads(json.dumps(registry, indent=3), object_pairs_hook=lambda pairs: dict(reversed(pairs)))
        self.assertEqual(list(reordered), list(reversed(list(registry))))
        self.assertEqual(module.registry_checksum(reordered), checksum)
        changed = copy.deepcopy(registry)
        changed["screens"][0]["route_id"] = "route-s-and-009"
        self.assertNotEqual(module.registry_checksum(changed), checksum)
        reordered_list = copy.deepcopy(registry)
        reordered_list["screens"].reverse()
        self.assertNotEqual(module.registry_checksum(reordered_list), checksum)


class InputAndSchemaRuleTests(CoverageCase):
    def test_wrapped_schema_error_names_only_the_record(self):
        def mutate(fixture):
            fixture.record("S-AND-002")["name"] = ""
        self.refused(mutate, "schema.invalid", "S-AND-002")

    def test_bare_legacy_reference_rejected(self):
        def mutate(fixture):
            fixture.record("S-AND-003")["implementation_tickets"] = [ticket(None, "android#902")]
        self.refused(mutate, "schema.invalid", "S-AND-003")

    def test_unknown_property_and_partition_shape_rejected(self):
        def registry(fixture):
            fixture.record("F-WEB-01")["release_gate_ids"] = ["D6"]
        self.refused(registry, "schema.invalid", "F-WEB-01")

        def partition(fixture):
            fixture.entry("PenniLogic/web#902")["disposition"] = "excluded"
        self.refused(partition, "schema.invalid", "PenniLogic/web#902")

    def test_schema_versions_are_integers(self):
        """AV-11: an equal float or boolean would pass a bare const and change the canonical registry digest."""
        self.refused(lambda f: f.registry.update(schema_version=2.0), "schema.invalid")
        self.refused(lambda f: f.partition.update(schema_version=True), "schema.invalid")

    def test_published_json_files_are_canonical(self):
        """F1 / plan data hygiene: json.dumps(indent=2, ensure_ascii=True) plus a final newline, LF only."""
        for relative in (module.SCHEMA, module.REGISTRY, module.PARTITION):
            with self.subTest(path=relative):
                raw = (ROOT / relative).read_bytes()
                self.assertEqual(raw, encode(json.loads(raw.decode("utf-8"))))

    def test_identifier_with_terminal_newline_is_refused_without_echo(self):
        def mutate(fixture):
            fixture.record("S-AND-002")["id"] = "S-AND-002\n"
        self.refused(mutate, "schema.invalid", None)

    def test_free_text_field_must_be_allowlisted(self):
        def mutate(fixture):
            fixture.schema["definitions"]["screen"]["properties"]["notes"] = {"type": "string"}
        self.refused(mutate, "schema.free_text_unlisted")

        def free_map(fixture):
            fixture.schema["definitions"]["screen"]["additionalProperties"] = {"type": "string"}
        self.refused(free_map, "schema.free_text_unlisted")
        # AV-09: an untyped property, a pattern that accepts whitespace and an open object all admit free text.
        self.refused(lambda f: f.schema["definitions"]["screen"]["properties"].update(notes={}),
                     "schema.free_text_unlisted")
        self.refused(lambda f: f.schema["definitions"]["screen"]["properties"].update(
            notes={"type": "string", "pattern": "^[\\s\\S]*$(?![\\s\\S])"}), "schema.free_text_unlisted")
        self.refused(lambda f: f.schema["definitions"]["screen"].pop("additionalProperties"),
                     "schema.free_text_unlisted")

    def test_forbidden_content_pattern_fails(self):
        cases = {
            "content.secret_shape": [
                planted_token(), "Key " + "a1" * 16, "Token " + "Zq9" * 11, "-----" + "BEGIN key",
                "Key " + "Ab1" * 6 + "-" + "Cd2" * 6, "Key " + "Ab1" * 6 + "/" + "Cd2" * 6, "Key " + "Ab1_" * 9,
            ],
            "content.url_shape": [
                "See https://example.invalid/x", "See www.example.invalid", "See drive.example.com/file/d/abc",
                "Open mailto" + ":someone", "javascript" + ":alert(1)", "Load data" + ":text/html,x",
            ],
            "content.email_shape": ["Mail fixture" + "@" + "example.invalid", "Pay someone" + "@okaxis",
                                    "Mail someone" + "@localhost"],
            "content.phone_shape": ["Call +91 98765 43210", "Call 98765/43210", "Call 030/12345678",
                                    "Call 98765_43210"],
            "content.amount_shape": ["Pays Rs. 500", "Pays 500 rupees", "Owes $12", "Owes USD 12", "Owes 500 dollars",
                                     "Pays 10k INR", "Refund of 500 paise", "Fee AED 500"],
            "content.personal_id_shape": ["PAN ABCDE" + "1234F"],
            "content.blank_or_padded": [" ", " Padded job", "Padded job "],
            "content.unprintable_character": [
                "Tab\tinside", "Line\u2028break", "Pays \u20b9500", "Call \uff19\uff18\uff17", "Mail a\uff20b.example",
                "Caf\u00e9 visit",
            ],
        }
        for rule, texts in cases.items():
            for text in texts:
                with self.subTest(rule=rule, text=text):
                    self.refused(lambda fixture: fixture.record("P02")["jobs"].append(text), rule, "P02")
        self.refused(lambda fixture: fixture.entry("PenniLogic/web#902").update(rationale="Mail a" + "@" + "b.example"),
                     "content.email_shape", "PenniLogic/web#902")
        # AV-10: a required rationale or security reason must say something.
        self.refused(lambda fixture: fixture.entry("PenniLogic/web#902").update(rationale=" "),
                     "content.blank_or_padded", "PenniLogic/web#902")
        self.refused(lambda fixture: fixture.record("S-AND-001").update(security_reason=" "),
                     "content.blank_or_padded", "S-AND-001")

    def test_plan_ids_follow_the_stable_id_grammar_and_are_scanned(self):
        key = "AKIA" + "ABCDEFGHIJKLMNOP"
        self.refused(lambda f: f.record("S-AND-002").update(design_ticket=ticket(key, None)), "schema.invalid",
                     "S-AND-002")
        self.refused(lambda f: f.record("S-AND-002").update(design_ticket=ticket("T-" + key, None)),
                     "content.secret_shape", "S-AND-002")
        self.refused(lambda f: f.record("S-AND-002").update(design_ticket=ticket("T-" + "AB12" * 8, None)),
                     "content.secret_shape", "S-AND-002")
        self.refused(lambda f: f.entry("PenniLogic/android#903").update(plan_id="t-syn-and-03"), "schema.invalid",
                     "PenniLogic/android#903")
        fixture = Fixture()
        fixture.record("S-AND-002")["design_ticket"] = ticket("E33", None)
        self.assertEqual(fixture.gaps(), {**BASELINE_GAPS, "readiness.ticket_unresolved": ["S-AND-002"]})

    def test_content_boundaries(self):
        fixture = Fixture()
        fixture.record("D01")["artifact_path"] = "x" * module.FREE_TEXT_LIMIT  # a name change would be a repoint
        fixture.record("US-ADM-01")["so_that"] = "the phone digit run 1234-5678 stays below nine digits"
        fixture.record("P01")["jobs"].append("Release plan path design/android/handoff-and-001-v1-2-0-final-review")
        fixture.check()
        self.refused(lambda f: f.record("D01").update(artifact_path="x" * (module.FREE_TEXT_LIMIT + 1)),
                     "content.too_long", "D01")
        self.refused(lambda f: f.record("US-ADM-01").update(so_that="runs 123-456-789 in a row"),
                     "content.phone_shape", "US-ADM-01")
        self.refused(lambda f: f.record("US-ADM-01").update(so_that="runs 1234/5678_9 in a row"),
                     "content.phone_shape", "US-ADM-01")

    def test_route_hint_is_exempt_from_the_url_scan_but_grammar_checked(self):
        fixture = Fixture()
        self.assertEqual(fixture.record("S-AND-001")["route_hint"], "android://home")
        fixture.check()
        valid = ["android://a", "android://a/:id/b-c", "android-widget://w", "/a", "/a/:token/b", "/a/*",
                 "/" + "a" * (module.ROUTE_HINT_LIMIT - 1)]
        invalid = ["android://Home", "android://", "android:/a", "/a/", "/a/*/b", "/a/:", "/a/:1", "https://a",
                   "/a b", "/a\n", "/" + "a" * module.ROUTE_HINT_LIMIT,
                   "/9876543210", "/refund/500rupees", "/a/" + "0f" * 24, "android://a1", "/a/:id2"]
        for hint in valid + invalid:
            target = "S-WEB-001" if hint.startswith("/") or hint.startswith("https") else "S-AND-002"
            with self.subTest(hint=hint):
                if hint in valid:
                    candidate = Fixture()
                    candidate.record(target)["route_hint"] = hint
                    candidate.check()
                else:
                    self.refused(lambda f: f.record(target).update(route_hint=hint), "route.hint_grammar", target)

    def test_import_pin_and_digest(self):
        self.refused(lambda f: f.registry["imported_from"].update(sha256="sha256:" + "0" * 64), "import.mismatch")
        self.refused(lambda f: f.registry["imported_from"].update(path="planning/source/evidence/other.json"),
                     "import.mismatch")
        self.refused(lambda f: f.blobs.pop((IMPORT_COMMIT, module.IMPORT_PATH)), "import.unavailable")
        self.refused(lambda f: f.blobs.update({(IMPORT_COMMIT, module.IMPORT_PATH): IMPORT_BYTES + b" "}),
                     "import.digest_mismatch")
        self.refused(lambda f: f.set_import(b'{"kind": 1, "kind": 2}'), "import.invalid")
        self.refused(lambda f: f.set_import(b"[]"), "import.invalid")

    def test_import_must_list_every_collection_with_ids_of_its_kind(self):
        def wrong_kind(fixture):
            imported = copy.deepcopy(IMPORT)
            imported["personas"].append({"id": "J01"})
            fixture.set_import(json.dumps(imported).encode("utf-8"))
        self.refused(wrong_kind, "import.invalid")

        def missing_collection(fixture):
            imported = copy.deepcopy(IMPORT)
            del imported["diagrams"]
            fixture.set_import(json.dumps(imported).encode("utf-8"))
        self.refused(missing_collection, "import.invalid")

        def unnamed(fixture):
            imported = copy.deepcopy(IMPORT)
            del imported["screens"][0]["name"]
            fixture.set_import(json.dumps(imported).encode("utf-8"))
        self.refused(unnamed, "import.invalid")

        def duplicated(fixture):
            imported = copy.deepcopy(IMPORT)
            imported["screens"].append(copy.deepcopy(imported["screens"][0]))
            fixture.set_import(json.dumps(imported).encode("utf-8"))
        self.refused(duplicated, "import.invalid")

    def test_inventory_and_taxonomy_inputs(self):
        self.refused(lambda f: f.inventory.update(operator="someone-else"), "inventory.invalid")
        self.refused(lambda f: f.inventory["issues"].append(copy.deepcopy(f.inventory["issues"][0])),
                     "inventory.invalid")
        self.refused(lambda f: setattr(f, "taxonomy", {"states": "empty"}), "taxonomy.unreadable")
        self.refused(lambda f: setattr(f, "taxonomy", {"states": []}), "taxonomy.unreadable")


class IdentityAndLedgerTests(CoverageCase):
    def test_duplicate_id_fails(self):
        self.refused(lambda f: f.registry["personas"].append(copy.deepcopy(f.record("P02"))), "id.duplicate", "P02")

    def test_platform_infix_must_match_platform(self):
        self.refused(lambda f: f.record("US-WEB-01").update(platform="admin"), "id.platform_infix_mismatch",
                     "US-WEB-01")

    def test_synthetic_prefix_rejected_in_published_registry(self):
        def mutate(fixture):
            fixture.record("C-OP-QUEUE")["id"] = "C-SYN-QUEUE"
        fixture = self.refused(mutate, "id.synthetic_reserved", "C-SYN-QUEUE")
        fixture.synthetic_ok = True
        with self.assertRaises(module.Refused) as caught:
            fixture.check()
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("ledger.missing_record", "C-SYN-QUEUE"))

        def retired_fixture_id(fixture):
            fixture.registry["id_ledger"].append({
                "id": "C-SYN-FIXTURE", "kind": "component", "platform": None,
                "name_sha256": fingerprint("Synthetic fixture"), "status": "retired",
                "retired_reason": "Synthetic test fixture identifier.",
            })
        fixture = self.refused(retired_fixture_id, "id.synthetic_reserved", "C-SYN-FIXTURE")
        fixture.synthetic_ok = True
        fixture.check()  # test fixtures may hold it

    def test_component_ids_are_bounded_and_letter_led(self):
        """AV-08: a component ID passes its grammar only as letter-led segments of at most 12 characters, so it
        cannot carry a key, card or phone number into refusals or the summary (and is refused without echo)."""
        def component_id(value):
            def mutate(fixture):
                fixture.registry["components"].append(component(value, ["web"], ["default"], foundational=True))
                fixture.registry["id_ledger"].append({
                    "id": value, "kind": "component", "platform": None, "status": "active", "retired_reason": None,
                    "name_sha256": fingerprint(f"Synthetic component {value}"),
                })
            return mutate
        fixture = Fixture()
        component_id("C-OPERATORQUEU-A-B-C")(fixture)
        fixture.check()
        for value in ("C-AKIA" + "ABCDEFGHIJKLMNOP", "C-98765-43210", "C-4111111111111111", "C-A-B-C-D-E",
                      "C-OPERATORQUEUE"):
            with self.subTest(value=value):
                self.refused(component_id(value), "schema.invalid", None)
        self.assertIsNone(module.classify("C-AKIA" + "ABCDEFGHIJKLMNOP"))

    def test_id_outside_platform_range_fails(self):
        def narrow(last):
            def mutate(fixture):
                for item in fixture.registry["id_ranges"]:
                    if (item["kind"], item["platform"]) == ("screen", "android"):
                        item["last"] = last
            return mutate
        fixture = Fixture()
        narrow(4)(fixture)
        fixture.check()
        self.refused(narrow(3), "id.out_of_range", "S-AND-004")
        self.refused(lambda f: f.registry["id_ranges"].pop(0), "id.out_of_range", "P01")

    def test_range_records_are_bounded_owned_and_disjoint(self):
        self.refused(lambda f: f.registry["id_ranges"][0].update(owner_role="product_manager"), "range.unknown_role")
        self.refused(lambda f: f.registry["id_ranges"][0].update(platform="android"), "range.invalid")
        self.refused(lambda f: f.registry["id_ranges"][0].update(first=50, last=49), "range.invalid")
        self.refused(lambda f: f.registry["id_ranges"][0].update(last=100), "range.invalid")
        self.refused(lambda f: f.registry["id_ranges"][2].update(first=1), "range.invalid")
        self.refused(lambda f: f.registry["id_ranges"].append(dict(f.registry["id_ranges"][0], first=99)),
                     "range.overlap")
        self.refused(lambda f: f.registry["id_ranges"].append(copy.deepcopy(f.registry["id_ranges"][2])),
                     "range.overlap")

    def test_ledger_entries_are_consistent(self):
        self.refused(lambda f: f.registry["id_ledger"].append(copy.deepcopy(f.ledger("P01"))), "ledger.duplicate",
                     "P01")
        self.refused(lambda f: f.ledger("P01").update(retired_reason="Synthetic note."), "ledger.retired_reason", "P01")

    def test_repointed_id_kind_or_platform_rejected(self):
        self.refused(lambda f: f.ledger("S-AND-001").update(platform="web"), "ledger.kind_or_platform_mismatch",
                     "S-AND-001")
        self.refused(lambda f: f.ledger("D01").update(kind="journey"), "ledger.kind_or_platform_mismatch", "D01")
        self.refused(lambda f: f.ledger("C-OP-QUEUE").update(platform="admin"), "ledger.kind_or_platform_mismatch",
                     "C-OP-QUEUE")

    def test_repointed_id_same_kind_rejected(self):
        """E33-F05 "repointed": the first-issued identity fingerprint pins what each ID names (TS-M3)."""
        def swap(fixture):
            first, second = fixture.record("S-AND-001"), fixture.record("S-AND-002")
            first["name"], second["name"] = second["name"], first["name"]
        self.refused(swap, "ledger.fingerprint_mismatch", "S-AND-001")
        self.refused(lambda f: f.record("S-AND-002").update(name="Synthetic screen renamed"),
                     "ledger.fingerprint_mismatch", "S-AND-002")
        self.refused(lambda f: f.record("US-WEB-01").update(i_want="a different synthetic outcome"),
                     "ledger.fingerprint_mismatch", "US-WEB-01")

        def swap_with_ledger(fixture):
            swap(fixture)
            first, second = fixture.ledger("S-AND-001"), fixture.ledger("S-AND-002")
            first["name_sha256"], second["name_sha256"] = second["name_sha256"], first["name_sha256"]
        self.refused(swap_with_ledger, "ledger.import_discontinuity", "S-AND-001")
        self.refused(swap_with_ledger, "ledger.entry_changed", "S-AND-001", prepare=Fixture.freeze_base)

        def rename_new_id(fixture):
            fixture.record("S-AND-004")["name"] = "Synthetic screen renamed"
            fixture.ledger("S-AND-004")["name_sha256"] = fingerprint("Synthetic screen renamed")
        fixture = Fixture()
        rename_new_id(fixture)
        fixture.check()  # S-AND-004 postdates the import: only a base registry pins it (documented limit)
        self.refused(rename_new_id, "ledger.entry_changed", "S-AND-004", prepare=Fixture.freeze_base)

    def test_record_without_active_ledger_entry_fails(self):
        self.refused(lambda f: f.registry["id_ledger"].remove(f.ledger("D01")), "ledger.missing_record", "D01")

    def test_dropped_ledger_id_rejected(self):
        self.refused(lambda f: f.registry["id_ledger"].append(
            {"id": "S-AND-009", "kind": "screen", "platform": "android",
             "name_sha256": fingerprint("Synthetic screen 009"), "status": "active", "retired_reason": None}),
            "ledger.dropped_record", "S-AND-009")

    def test_retired_id_reuse_rejected(self):
        def retire(fixture):
            fixture.drop_screen("S-AND-004")
            fixture.registry["id_ledger"].append({
                "id": "S-AND-004", "kind": "screen", "platform": "android",
                "name_sha256": fingerprint("Synthetic screen 004"), "status": "retired",
                "retired_reason": "Synthetic retirement.",
            })
        reused = copy.deepcopy(REGISTRY["screens"][3])

        def reuse(fixture):
            fixture.registry["screens"].append(copy.deepcopy(reused))
            fixture.record("F-AND-02")["screen_ids"].append("S-AND-004")
        self.refused(reuse, "ledger.retired_in_use", "S-AND-004", prepare=retire)

        def reactivate(fixture):
            reuse(fixture)
            fixture.ledger("S-AND-004").update(status="active", retired_reason=None)
        fixture = Fixture()
        retire(fixture)
        fixture.freeze_base()
        fixture.check()
        reactivate(fixture)
        with self.assertRaises(module.Refused) as caught:
            fixture.check()
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("ledger.entry_changed", "S-AND-004"))

    def test_ledger_record_and_entry_removed_together_fails(self):
        for identifier in ("S-AND-004", "S-AND-002"):
            with self.subTest(screen=identifier):
                self.refused(lambda f: f.drop_screen(identifier), "ledger.entry_removed", identifier,
                             prepare=Fixture.freeze_base)

    def test_imported_id_continuity(self):
        """Without a base registry, every ID of the frozen import must stay in the ledger."""
        self.refused(lambda f: f.drop_screen("S-AND-002"), "ledger.import_discontinuity", "S-AND-002")
        fixture = Fixture()
        fixture.drop_screen("S-AND-004")
        fixture.check()  # S-AND-004 postdates the import: only the base registry protects it (documented limit)

    def test_ledger_is_append_only_against_the_base(self):
        def append(fixture):
            fixture.registry["id_ledger"].append({
                "id": "S-WEB-009", "kind": "screen", "platform": "web",
                "name_sha256": fingerprint("Synthetic screen 009"), "status": "retired",
                "retired_reason": "Synthetic, never used.",
            })
        fixture = Fixture()
        fixture.freeze_base()
        append(fixture)
        self.assertEqual(fixture.check().ledger_base, "base registry")
        self.refused(lambda f: f.registry["id_ledger"].reverse(), "ledger.reordered", prepare=Fixture.freeze_base)
        self.refused(lambda f: f.registry["id_ledger"].insert(0, f.registry["id_ledger"].pop()), "ledger.reordered",
                     prepare=Fixture.freeze_base)

        def retired_base(fixture):
            append(fixture)
            fixture.freeze_base()
        self.refused(lambda f: f.ledger("S-WEB-009").update(retired_reason="Synthetic, rewritten."),
                     "ledger.entry_changed", "S-WEB-009", prepare=retired_base)
        self.refused(lambda f: f.registry["id_ledger"].remove(f.ledger("S-WEB-009")), "ledger.entry_removed",
                     "S-WEB-009", prepare=retired_base)

    def test_base_registry_must_be_readable(self):
        self.refused(lambda f: setattr(f, "base_error", True), "ledger.base_unavailable")
        self.refused(lambda f: setattr(f, "base", b"{not json"), "ledger.base_invalid")
        self.refused(lambda f: setattr(f, "base", b'{"id_ledger": {}}'), "ledger.base_invalid")

        def inconsistent(fixture):
            base = copy.deepcopy(fixture.registry)
            base["id_ledger"][0]["platform"] = "web"
            fixture.base = json.dumps(base).encode("utf-8")
        self.refused(inconsistent, "ledger.base_invalid")
        for partition in (b"[]", b'{"entries": {}}', b'{"entries": [{"issue": "PenniLogic/web#901"}]}',
                          b'{"entries": [{"issue": "web#901", "disposition": "frontend"}]}',
                          b'{"entries": [{"issue": "PenniLogic/web#901", "disposition": "excluded"}]}'):
            with self.subTest(partition=partition):
                self.refused(lambda f: setattr(f, "partition_base", partition), "partition.base_invalid",
                             prepare=Fixture.freeze_base)


class ReferenceAndOwnershipTests(CoverageCase):
    def test_dangling_reference_fails(self):
        self.refused(lambda f: f.record("S-AND-002")["component_ids"].append("C-MISSING-PART"), "reference.dangling",
                     "S-AND-002 C-MISSING-PART")
        self.refused(lambda f: f.record("US-WEB-01").update(flow_id="F-WEB-09"), "reference.dangling",
                     "US-WEB-01 F-WEB-09")

    def test_ticket_references_resolve_offline(self):
        self.refused(lambda f: f.record("S-AND-002").update(design_ticket=ticket(None, None)), "ticket.empty",
                     "S-AND-002")
        self.refused(lambda f: f.record("S-AND-002").update(design_ticket=ticket("T-SYN-DSN-01", None)),
                     "ticket.issue_missing", "S-AND-002")
        self.refused(lambda f: f.record("S-AND-002").update(
            design_ticket=ticket("T-SYN-DSN-01", "PenniLogic/docs#999")),
                     "ticket.dangling", "S-AND-002 PenniLogic/docs#999")

    def test_plan_id_issue_mismatch_rejected(self):
        self.refused(lambda f: f.record("S-AND-002").update(design_ticket=ticket("T-SYN-QA-01", "PenniLogic/docs#904")),
                     "ticket.plan_id_mismatch", "S-AND-002 PenniLogic/docs#904")
        self.refused(lambda f: f.record("S-AND-003").update(
            implementation_tickets=[ticket("T-SYN-AND-03", AND3["issue"])]),
                     "ticket.plan_id_mismatch", "S-AND-003 PenniLogic/android#903")

    def test_renounced_owner_issue_rejected(self):
        self.refused(lambda f: f.issue("PenniLogic/docs#904").update(state="closed", state_reason="not_planned"),
                     "ticket.renounced", "F-AND-01 PenniLogic/docs#904")

    def test_screen_without_design_dependency_fails(self):
        self.refused(lambda f: f.record("S-AND-002").update(design_ticket=None), "ownership.design_missing",
                     "S-AND-002")
        self.refused(lambda f: f.record("C-OP-QUEUE").update(design_ticket=None), "ownership.design_missing",
                     "C-OP-QUEUE")

    def test_missing_implementation_owner_fails(self):
        self.refused(lambda f: f.record("S-AND-002").update(implementation_tickets=[]),
                     "ownership.implementation_missing", "S-AND-002")

    def test_missing_qa_owner_fails(self):
        self.refused(lambda f: f.record("F-AND-02").update(qa_ticket=None), "ownership.qa_missing", "F-AND-02")
        self.refused(lambda f: f.record("S-ADM-001").update(qa_ticket=None), "ownership.qa_missing", "S-ADM-001")

    def test_qa_owner_equals_implementation_owner_fails(self):
        self.refused(lambda f: f.record("F-WEB-01").update(qa_ticket=copy.deepcopy(WEB1)),
                     "ownership.qa_not_independent", "F-WEB-01")
        self.refused(lambda f: f.record("F-WEB-01").update(qa_ticket=copy.deepcopy(DESIGN)),
                     "ownership.qa_not_independent", "F-WEB-01")
        self.refused(lambda f: f.record("F-WEB-01").update(qa_ticket=copy.deepcopy(AUTHOR)),
                     "ownership.qa_not_independent", "F-WEB-01")
        fixture = Fixture()
        fixture.record("F-AND-02")["qa_ticket"] = copy.deepcopy(AUTHOR)
        fixture.check()  # independence is required of critical flows; F-AND-02 is not critical

    def test_critical_flow_needs_a_persona(self):
        self.refused(lambda f: f.record("US-AND-01").update(flow_id="F-AND-02"), "flow.critical_without_persona",
                     "F-AND-01")


class GraphAndPlatformTests(CoverageCase):
    def test_journey_without_persona_fails(self):
        self.refused(lambda f: f.record("J02").update(persona_ids=[]), "graph.journey_without_persona", "J02")

    def test_flow_without_screens_fails(self):
        self.refused(lambda f: f.record("F-WEB-01").update(screen_ids=[]), "graph.flow_without_screens", "F-WEB-01")

    def test_flow_without_journey_fails(self):
        self.refused(lambda f: f.record("J01")["flow_ids"].remove("F-AND-02"), "graph.flow_without_journey", "F-AND-02")

    def test_orphan_screen_fails(self):
        self.refused(lambda f: f.record("F-AND-01")["screen_ids"].remove("S-AND-002"), "graph.orphan_screen",
                     "S-AND-002")

    def test_one_sided_links_fail(self):
        self.refused(lambda f: f.record("S-AND-002")["flow_ids"].append("F-AND-02"), "graph.link_mismatch",
                     "S-AND-002 F-AND-02")
        self.refused(lambda f: f.record("F-AND-02")["journey_ids"].append("J02"), "graph.link_mismatch", "F-AND-02 J02")
        self.refused(lambda f: f.record("J02")["flow_ids"].append("F-AND-02"), "graph.link_mismatch", "J02 F-AND-02")
        self.refused(lambda f: f.record("F-AND-02")["screen_ids"].append("S-AND-002"), "graph.link_mismatch",
                     "F-AND-02 S-AND-002")

    def test_story_lists_exactly_its_flow_journeys(self):
        """Relisting a story's journeys must not move it away from its flow's journeys (and their personas)."""
        def link_second_journey(fixture):
            fixture.record("F-AND-01")["journey_ids"].append("J02")
            fixture.record("J02")["flow_ids"].append("F-AND-01")
        self.refused(link_second_journey, "graph.link_mismatch", "US-AND-01 F-AND-01")
        self.refused(lambda f: f.record("US-AND-01").update(journey_ids=["J02"]), "graph.link_mismatch",
                     "US-AND-01 F-AND-01")

    def test_platform_mismatch_fails(self):
        self.refused(lambda f: f.record("US-WEB-01").update(flow_id="F-AND-01"), "platform.story_flow", "US-WEB-01")
        self.refused(lambda f: f.record("US-AND-01")["persona_ids"].append("P02"), "platform.story_persona",
                     "US-AND-01 P02")

        def move(fixture):
            fixture.record("F-AND-01")["screen_ids"].append("S-WEB-001")
            fixture.record("S-WEB-001")["flow_ids"].append("F-AND-01")
        self.refused(move, "platform.flow_screen", "F-AND-01 S-WEB-001")
        self.refused(lambda f: f.record("S-WEB-001")["component_ids"].append("C-NAV-ANDROID"),
                     "platform.screen_component", "S-WEB-001 C-NAV-ANDROID")
        self.refused(lambda f: f.record("S-AND-002").update(implementation_tickets=[copy.deepcopy(WEB1)]),
                     "platform.implementation_repository", "S-AND-002 PenniLogic/web#901")
        self.refused(lambda f: f.record("S-WEB-001").update(route_hint="android://home"), "platform.route_hint",
                     "S-WEB-001")
        self.refused(lambda f: f.record("S-AND-002").update(route_hint="/settings"), "platform.route_hint", "S-AND-002")

    def test_shared_platform_semantics(self):
        fixture = Fixture()
        self.assertEqual(fixture.record("C-ACTION-PRIMARY")["platforms"], ["shared"])
        fixture.check()  # shared covers the android, web and admin screens that use it
        self.refused(lambda f: f.record("C-ACTION-PRIMARY")["platforms"].append("web"), "platform.shared_mixed",
                     "C-ACTION-PRIMARY")
        self.refused(lambda f: f.record("P03")["platforms"].insert(0, "admin"), "platform.shared_mixed", "P03")


class StateComponentScreenTests(CoverageCase):
    def test_unknown_state_fails(self):
        self.refused(lambda f: f.record("S-AND-002")["states"].append("hover"), "state.unknown_screen_state",
                     "S-AND-002")
        self.refused(lambda f: f.record("C-OP-QUEUE")["required_states"].append("recovery"),
                     "state.unknown_component_state", "C-OP-QUEUE")

    def test_taxonomy_state_map_mismatch_rejected(self):
        self.refused(lambda f: f.registry["taxonomy_state_map"].pop(), "taxonomy.map_mismatch")
        self.refused(lambda f: f.registry["taxonomy_state_map"][5].update(taxonomy_state="permission_blocked"),
                     "taxonomy.map_mismatch")
        self.refused(lambda f: f.registry["taxonomy_state_map"][0].update(state="loading"), "taxonomy.map_mismatch")
        self.refused(lambda f: f.registry["required_states"].remove("quota-exceeded"), "taxonomy.map_mismatch")
        self.refused(lambda f: f.taxonomy["states"].append({"id": "suspended", "name": "suspended"}),
                     "taxonomy.map_mismatch")

    def test_unused_component_fails_unless_foundational(self):
        self.refused(lambda f: f.record("C-TRUST-FOUNDATION").update(foundational=False), "component.unused",
                     "C-TRUST-FOUNDATION")

    def test_screen_criticality_is_derived_from_flows(self):
        self.refused(lambda f: f.record("S-AND-003").update(critical=True), "screen.critical_mismatch", "S-AND-003")
        self.refused(lambda f: f.record("S-AND-002").update(critical=False), "screen.critical_mismatch", "S-AND-002")

    def test_security_critical_needs_a_reason_and_own_states(self):
        self.refused(lambda f: f.record("S-AND-002").update(security_critical=True), "security.reason_mismatch",
                     "S-AND-002")
        self.refused(lambda f: f.record("S-AND-002").update(security_reason="Synthetic stale reason."),
                     "security.reason_mismatch", "S-AND-002")
        self.refused(lambda f: f.record("S-AND-001")["privacy_states"].append("offline"),
                     "security.state_not_on_screen",
                     "S-AND-001")
        self.refused(lambda f: f.record("S-ADM-001")["authorization_states"].append("revoked"),
                     "security.state_not_on_screen", "S-ADM-001")

    def test_proposal_lists_only_fields_that_carry_a_value(self):
        """A proposal awaits confirmation of authored values; it cannot name a null reason or an empty state list."""
        fixture = Fixture()
        fixture.record("S-AND-001")["proposal"] = {"proposed_by": "design_ops", "fields": list(
            SCHEMA["definitions"]["screen_proposal"]["properties"]["fields"]["items"]["enum"])}
        fixture.record("S-AND-002")["proposal"] = {"proposed_by": "design_ops", "fields": ["security_critical"]}
        fixture.check()  # S-AND-002 is a proposed security_critical false: a value, not an absence
        for field in ("security_reason", "privacy_states", "authorization_states"):
            with self.subTest(field=field):
                self.refused(lambda f: f.record("S-AND-002").update(
                    proposal={"proposed_by": "design_ops", "fields": ["security_critical", field]}),
                             "proposal.field_without_value", "S-AND-002")

    def test_d6_dependency_uses_the_design_gates_shape_for_this_screen(self):
        def dependency(**changes):
            return lambda f: f.record("S-AND-001").update(d6_dependency={**d6_reference("S-AND-001"), **changes})
        self.refused(dependency(gate_id="D5"), "d6.dependency_mismatch", "S-AND-001")
        self.refused(dependency(artifact_id="S-AND-002"), "d6.dependency_mismatch", "S-AND-001")
        self.refused(dependency(scope_sha256="sha256:abc"), "schema.invalid", "S-AND-001")
        # A well-formed dependency is still a self-asserted digest until a D6 gate record can be resolved (AV-01).
        self.refused(dependency(), "held.d6_reference", "S-AND-001")

    def test_handoff_grammar_and_platform_infix(self):
        self.refused(lambda f: f.record("S-AND-001").update(handoff_ref="HND-WEB-001@1.0.0"),
                     "handoff.platform_mismatch", "S-AND-001")
        malformed = ("HND-AND-001", "HND-AND-01@1.0.0", "HND-AND-001@1.0", "HND-AND-001@01.0.0", "HND-AND-001@1.0.0\n")
        for value in malformed:
            with self.subTest(value=value):
                self.refused(lambda f: f.record("S-AND-001").update(handoff_ref=value), "schema.invalid", "S-AND-001")
        self.refused(lambda f: f.record("S-AND-001").update(handoff_ref="HND-AND-001@1.0.0"), "held.d6_reference",
                     "S-AND-001")

    def test_qa_independence_needs_pinned_evidence(self):
        self.refused(lambda f: f.record("F-AND-02")["qa_independence"].update(status="verified"),
                     "qa.independence_evidence", "F-AND-02")
        self.refused(lambda f: f.record("F-WEB-01")["qa_independence"].update(evidence=verified_qa()["evidence"]),
                     "qa.independence_evidence", "F-WEB-01")

        def missing_blob(fixture):
            fixture.record("F-AND-01")["qa_independence"] = verified_qa()
            fixture.blobs.pop((EVIDENCE_COMMIT, EVIDENCE_PATH))
        self.refused(missing_blob, "qa.evidence_unavailable", "F-AND-01")

        def wrong_digest(fixture):
            fixture.record("F-ADM-01")["qa_independence"] = verified_qa()
            fixture.record("F-ADM-01")["qa_independence"]["evidence"]["sha256"] = "sha256:" + "d" * 64
        self.refused(wrong_digest, "qa.evidence_digest_mismatch", "F-ADM-01")
        # Any pinned, matching blob would pass, so verified is refused until docs#126 defines its record (AV-06).
        self.refused(lambda f: f.record("F-WEB-01").update(qa_independence=verified_qa()), "held.qa_verification",
                     "F-WEB-01")

    def test_d20_points_at_the_generated_summary(self):
        self.refused(lambda f: f.record("D20").update(artifact_path="planning-automation/backlog-v2/evidence/x.json"),
                     "diagram.d20_artifact", "D20")
        self.refused(lambda f: f.registry["diagrams"].remove(f.record("D20")), "ledger.dropped_record", "D20")


class PartitionAndReleaseGateTests(CoverageCase):
    def test_unclassified_client_ticket_fails(self):
        self.refused(lambda f: f.partition["entries"].remove(f.entry("PenniLogic/android#902")),
                     "partition.unclassified_issue", "PenniLogic/android#902")

    def test_partition_count_mismatch_vs_inventory_fails(self):
        self.refused(lambda f: setattr(f, "inventory", build_inventory(f.inventory["issues"] + [issue("admin", 905)])),
                     "partition.unclassified_issue", "PenniLogic/admin#905")
        self.refused(lambda f: f.partition["entries"].append(entry("PenniLogic/web#950", None, "other", "Synthetic.")),
                     "partition.unknown_issue", "PenniLogic/web#950")
        self.refused(lambda f: f.partition["entries"].append(copy.deepcopy(f.entry("PenniLogic/web#901"))),
                     "partition.duplicate_issue", "PenniLogic/web#901")

    def test_partition_identity_must_match_inventory(self):
        self.refused(lambda f: f.entry("PenniLogic/web#902").update(plan_id="T-SYN-WEB-09"),
                     "partition.plan_id_mismatch",
                     "PenniLogic/web#902")
        self.refused(lambda f: f.entry("PenniLogic/android#903").update(plan_id="T-SYN-AND-03"),
                     "partition.plan_id_mismatch", "PenniLogic/android#903")

    def test_nonfrontend_exclusion_without_rationale_fails(self):
        self.refused(lambda f: f.entry("PenniLogic/web#902").update(rationale=None), "partition.rationale_missing",
                     "PenniLogic/web#902")
        self.refused(lambda f: f.entry("PenniLogic/web#902").update(rationale_class=None),
                     "partition.rationale_missing",
                     "PenniLogic/web#902")
        self.refused(lambda f: f.entry("PenniLogic/web#901").update(rationale="Synthetic."),
                     "partition.rationale_on_frontend", "PenniLogic/web#901")

    def test_unmapped_implementation_ticket_fails(self):
        self.refused(lambda f: f.entry("PenniLogic/android#903").update(
            disposition="non_frontend", rationale_class="other", rationale="Synthetic misclassification."),
            "partition.unmapped_implementation_ticket", "PenniLogic/android#903")

    def test_frontend_entry_must_be_derived_from_the_registry(self):
        self.refused(lambda f: f.entry("PenniLogic/web#902").update(disposition="frontend", rationale_class=None,
                                                                    rationale=None),
                     "partition.frontend_without_mapping", "PenniLogic/web#902")

    def test_post_snapshot_disclosure_boundaries(self):
        fixture = Fixture()
        fixture.partition["post_snapshot_issues"] = ["PenniLogic/android#905"]
        fixture.check()
        self.refused(lambda f: f.partition.update(post_snapshot_issues=["PenniLogic/android#904"]),
                     "partition.post_snapshot_invalid", "PenniLogic/android#904")
        self.refused(lambda f: f.partition.update(post_snapshot_issues=["PenniLogic/android#900"]),
                     "partition.post_snapshot_invalid", "PenniLogic/android#900")
        self.refused(lambda f: f.partition.update(post_snapshot_issues=["PenniLogic/docs#999"]), "schema.invalid")
        # AV-08: at most POST_SNAPSHOT_MARGIN past the snapshot, and never a phone-length number.
        fixture.partition["post_snapshot_issues"] = [f"PenniLogic/android#{904 + module.POST_SNAPSHOT_MARGIN}"]
        fixture.check()
        self.refused(lambda f: f.partition.update(
            post_snapshot_issues=[f"PenniLogic/android#{905 + module.POST_SNAPSHOT_MARGIN}"]),
                     "partition.post_snapshot_invalid", f"PenniLogic/android#{905 + module.POST_SNAPSHOT_MARGIN}")
        self.refused(lambda f: f.partition.update(post_snapshot_issues=["PenniLogic/android#9876543210"]),
                     "schema.invalid")

    def test_release_gate_bypass_closed_issue_without_d6_fails(self):
        """No screen can carry D6 yet, so an implementation issue closed as delivered always bypassed the gate."""
        self.refused(lambda f: f.issue("PenniLogic/android#901").update(state="closed", state_reason="completed"),
                     "release_gate.bypass", "PenniLogic/android#901 S-AND-001")
        self.refused(lambda f: f.issue("PenniLogic/web#901").update(state="closed", state_reason=None),
                     "release_gate.bypass", "PenniLogic/web#901 S-WEB-001")

        def asserted_d6(fixture):
            """AV-01: self-asserted references on every screen of the closed issue cannot clear the gate."""
            fixture.issue("PenniLogic/android#901").update(state="closed", state_reason="completed")
            for identifier in ("S-AND-001", "S-AND-002"):
                fixture.record(identifier).update(d6_dependency=d6_reference(identifier),
                                                  handoff_ref="HND-AND-001@1.0.0")
        self.refused(asserted_d6, "held.d6_reference", "S-AND-001")
        # An open implementation issue without D6 is a readiness gap, not a bypass.
        self.assertIn("S-WEB-001", Fixture().gaps()["readiness.d6_missing"])


    def test_delivered_frontend_issue_cannot_be_relabeled(self):
        """AV-05: unmapping a delivered issue and relabelling it non-frontend would hide its release-gate bypass."""
        def relabel(fixture):
            fixture.issue("PenniLogic/android#903").update(state="closed", state_reason="completed")
            for identifier in ("F-AND-02", "S-AND-003", "S-AND-004"):
                fixture.record(identifier)["implementation_tickets"] = [copy.deepcopy(AND1)]
            fixture.entry("PenniLogic/android#903").update(
                disposition="non_frontend", rationale_class="other", rationale="Synthetic relabel of delivered work.")
        self.refused(relabel, "release_gate.relabeled", "PenniLogic/android#903", prepare=Fixture.freeze_base)
        fixture = Fixture()
        relabel(fixture)
        fixture.check()  # no base partition yet (the registry's first PR): reviewed by hand, documented limit
        fixture = Fixture()
        fixture.freeze_base()
        relabel(fixture)
        fixture.issue("PenniLogic/android#903").update(state="open", state_reason=None)
        fixture.check()  # relabelling open work stays an ordinary, reviewed disposition change


class ReadinessTests(CoverageCase):
    def test_missing_d6_dependency_fails(self):
        """Every screen lacks D6 (a reference is refused until it can be resolved); the default mode exits 1."""
        self.assertEqual(Fixture().gaps()["readiness.d6_missing"], SCREEN_IDS)
        checkout = Checkout(self, Fixture())
        self.assertEqual(checkout.run("--write-summary")[0], 0)
        self.assertEqual(checkout.run("--structure")[0], 0)
        code, out, err = checkout.run()
        self.assertEqual((code, err, out.splitlines()[0]), (1, "", module.NOT_GREEN))
        self.assertIn("readiness.d6_missing: 6", out.splitlines())

    def test_missing_route_id_is_a_readiness_gap(self):
        self.assertEqual(Fixture().gaps()["readiness.route_missing"], SCREEN_IDS)
        self.refused(lambda f: f.record("S-WEB-001").update(route_id="route-s-web-001"), "held.route_id", "S-WEB-001")

    def test_unverified_critical_flow_qa_is_a_readiness_gap(self):
        flows = Fixture().gaps()["readiness.qa_unverified"]
        self.assertEqual(flows, ["F-AND-01", "F-WEB-01", "F-ADM-01"])  # F-AND-02 is not critical

    def test_persona_outside_its_journey_is_a_readiness_gap(self):
        self.gap(lambda f: f.record("US-AND-01")["persona_ids"].append("P03"), "readiness.persona_outside_journey",
                 "US-AND-01")

    def test_persona_rule_uses_the_union_of_the_flow_journeys(self):
        """TS-M1: P01 is only in J01 and P03 only in J02, so neither journey alone covers US-AND-01 but the union
        of its flow's journeys does; the per-journey reading would report two gaps here."""
        def two_journeys(fixture):
            fixture.record("F-AND-01")["journey_ids"].append("J02")
            fixture.record("J02")["flow_ids"].append("F-AND-01")
            fixture.record("US-AND-01").update(journey_ids=["J01", "J02"], persona_ids=["P01", "P03"])
        self.gap(lambda f: f.record("J02")["persona_ids"].remove("P03"), "readiness.persona_outside_journey",
                 "US-AND-01", prepare=two_journeys)

    def test_screen_ticket_outside_its_flows_is_a_readiness_gap(self):
        self.gap(lambda f: f.record("S-AND-003")["implementation_tickets"].append(copy.deepcopy(AND1)),
                 "readiness.screen_ticket_outside_flows", "S-AND-003 PenniLogic/android#901")

    def test_screen_ticket_rule_uses_the_union_of_the_screen_flows(self):
        """S-AND-002 on two flows carries each flow's ticket; each ticket is on only one flow but within the union."""
        def two_flows(fixture):
            fixture.record("F-AND-02")["screen_ids"].append("S-AND-002")
            fixture.record("S-AND-002").update(flow_ids=["F-AND-01", "F-AND-02"],
                                               implementation_tickets=[copy.deepcopy(AND1), copy.deepcopy(AND3)])

        def unlink(fixture):
            fixture.record("F-AND-02")["screen_ids"].remove("S-AND-002")
            fixture.record("S-AND-002")["flow_ids"].remove("F-AND-02")
        self.gap(unlink, "readiness.screen_ticket_outside_flows", "S-AND-002 PenniLogic/android#903", prepare=two_flows)

    def test_security_critical_screen_missing_privacy_authorization_states_fails(self):
        self.gap(lambda f: f.record("S-AND-001").update(privacy_states=[]), "readiness.security_states_missing",
                 "S-AND-001")
        self.gap(lambda f: f.record("S-ADM-001").update(authorization_states=[]), "readiness.security_states_missing",
                 "S-ADM-001")

    def test_unconfirmed_proposals_are_readiness_gaps(self):
        proposal = {"proposed_by": "design_ops", "fields": ["surface_type"]}
        self.gap(lambda f: f.record("S-AND-002").update(proposal=proposal), "readiness.proposal_unconfirmed",
                 "S-AND-002")
        self.gap(lambda f: f.record("C-OP-QUEUE").update(
            proposal={"proposed_by": "design_ops", "fields": ["foundational"]}),
                 "readiness.proposal_unconfirmed", "C-OP-QUEUE")
        self.gap(lambda f: f.entry("PenniLogic/web#902").update(proposed_by="design_ops"),
                 "readiness.proposal_unconfirmed", "PenniLogic/web#902")
        self.refused(lambda f: f.record("C-OP-QUEUE").update(
            proposal={"proposed_by": "design_ops", "fields": ["name"]}),
                     "schema.invalid", "C-OP-QUEUE")

    def test_unresolved_ticket_is_a_readiness_gap(self):
        self.gap(lambda f: f.record("S-AND-002").update(design_ticket=ticket("T-SYN-NEW-01", None)),
                 "readiness.ticket_unresolved", "S-AND-002")

    def test_partition_scope_question_is_a_readiness_gap(self):
        """SC-3: an exclusion whose rationale names unmapped user-visible scope is an open owner question, counted
        apart from the generic proposal gap; clearing proposed_by alone does not close it."""
        self.gap(lambda f: f.partition.update(scope_questions=["PenniLogic/web#902"]),
                 "readiness.partition_scope_question", "PenniLogic/web#902",
                 prepare=lambda f: f.entry("PenniLogic/web#902").update(proposed_by=None))
        self.refused(lambda f: f.partition.update(scope_questions=["PenniLogic/web#901"]),
                     "partition.scope_question_invalid", "PenniLogic/web#901")
        self.refused(lambda f: f.partition.update(scope_questions=["PenniLogic/web#950"]),
                     "partition.scope_question_invalid", "PenniLogic/web#950")

    def test_post_snapshot_issue_is_a_readiness_gap(self):
        self.gap(lambda f: f.partition.update(post_snapshot_issues=["PenniLogic/android#905"]),
                 "readiness.post_snapshot_issue", "PenniLogic/android#905")

    def test_partial_registry_not_green(self):
        fixture = Fixture()
        fixture.partition["post_snapshot_issues"] = ["PenniLogic/android#905"]
        gaps = fixture.gaps()
        self.assertEqual(gaps, {**BASELINE_GAPS, "readiness.post_snapshot_issue": ["PenniLogic/android#905"]})
        summary = module.render_summary(fixture.check(), gaps)
        self.assertEqual(summary.splitlines()[0], module.NOT_GREEN)
        self.assertIn("| `readiness.d6_missing` | 6 |", summary)
        self.assertIn("- `readiness.d6_missing` (6): " + ", ".join(SCREEN_IDS), summary)
        self.assertIn("- `readiness.post_snapshot_issue` (1): PenniLogic/android#905", summary)


class SummaryTests(CoverageCase):
    def test_summary_snapshot_deterministic(self):
        fixture = Fixture()
        model = fixture.check()
        summary = module.render_summary(model, module.readiness(model))
        shuffled = Fixture()
        shuffled.registry = json.loads(json.dumps(fixture.registry), object_pairs_hook=lambda p: dict(reversed(p)))
        shuffled.partition = json.loads(json.dumps(fixture.partition), object_pairs_hook=lambda p: dict(reversed(p)))
        again = shuffled.check()
        self.assertEqual(module.render_summary(again, module.readiness(again)), summary)
        self.assertTrue(summary.endswith("\n") and "\r" not in summary and summary.isascii())
        self.assertEqual(summary.splitlines()[0], module.NOT_GREEN)
        for line in (
            "| Registry checksum | `" + module.registry_checksum(fixture.registry) + "` |",
            "| `readiness.route_missing` | 6 |",
            "| android | 4 | 0 | 0 | 0 | 0 |",
            "| critical | 4 | 0 | 0 | 0 | 0 |",
            "| standard | 2 | 0 | 0 | 0 | 0 |",
            "| `loading` | 4 | 0 | 0 | 0 | 0 |",
            "| `PenniLogic/android#903` | none | 2 | 0 | 0 | 0 | 0 |",
            "| `PenniLogic/docs#904` | `T-SYN-DSN-01` | 6 | 0 | 0 | 0 | 0 |",
            "| android | 2 | 1 | 0 | 0 |",
            "| `PenniLogic/android` | 4 | 2 | 2 | 0 | 0 |",
            "- `readiness.route_missing` (6): " + ", ".join(SCREEN_IDS),
        ):
            self.assertIn(line, summary.splitlines())
        self.assertNotIn("Synthetic screen", summary)
        self.assertNotIn("Synthetic fixture issue", summary)
        self.assertIsNone(re.search(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", summary))

    def test_basis_points_round_down_and_handle_empty_groups(self):
        self.assertEqual([module.basis_points(*pair) for pair in ((0, 0), (1, 3), (2, 3), (3, 3))],
                         [0, 3333, 6666, 10000])
        # Coverage counting for a later version that resolves references (none can be recorded in 1.0.0).
        resolved = {"d6_dependency": d6_reference("S-AND-001"), "handoff_ref": "HND-AND-001@1.0.0", "route_id": "r"}
        empty = {"d6_dependency": None, "handoff_ref": None, "route_id": None}
        self.assertEqual(module._coverage([resolved, empty, {**resolved, "handoff_ref": None}]), [3, 1, 3333, 2, 6666])


def git(root, *args):
    env = {key: value for key, value in os.environ.items() if key not in module.SCRUBBED_GIT_VARIABLES}
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_AUTHOR_NAME": "Synthetic Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@invalid", "GIT_COMMITTER_NAME": "Synthetic Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@invalid", "GIT_AUTHOR_DATE": "2026-10-01T00:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-10-01T00:00:00+00:00",
    })
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30,
                            env=env)
    if result.returncode != 0:
        raise AssertionError(f"fixture git {args[0]} failed: {result.stderr}")
    return result.stdout.strip()


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


class Checkout:
    """A hermetic temporary Git checkout laid out like docs, created outside this repository."""

    def __init__(self, case, fixture, base_registry=None, origin=True):
        folder = tempfile.TemporaryDirectory()
        case.addCleanup(folder.cleanup)
        self.root, self.fixture = Path(folder.name), fixture
        git(self.root, "init", "-q", "--template=", "-b", "main")
        self.write(module.IMPORT_PATH, fixture.blobs[(IMPORT_COMMIT, module.IMPORT_PATH)])
        self.write(EVIDENCE_PATH, EVIDENCE_BYTES)
        if base_registry is not None:
            self.write(module.REGISTRY, encode(base_registry))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "synthetic base")
        self.base = git(self.root, "rev-parse", "HEAD")
        if origin:
            git(self.root, "update-ref", "refs/remotes/origin/main", self.base)
        self.save()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "synthetic candidate")
        case.addCleanup(setattr, module, "ROOT", module.ROOT)
        case.addCleanup(setattr, module, "IMPORT_SHA256", module.IMPORT_SHA256)
        module.ROOT, module.IMPORT_SHA256 = self.root, fixture.pin[1]

    def write(self, relative, raw):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def save(self):
        """Write the fixture inputs, repointing pinned commits at this checkout's base commit."""
        registry = copy.deepcopy(self.fixture.registry)
        registry["imported_from"]["commit"] = self.base
        for item in registry["flows"]:
            if item["qa_independence"]["evidence"] is not None:
                item["qa_independence"]["evidence"]["commit"] = self.base
        self.registry = registry
        self.write(module.REGISTRY, encode(registry))
        self.write(module.PARTITION, encode(self.fixture.partition))
        self.write(module.SCHEMA, SCHEMA_BYTES)
        self.write(module.TAXONOMY, encode(self.fixture.taxonomy))
        self.write(module.INVENTORY, encode(self.fixture.inventory))

    def run(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main(list(argv))
        return code, out.getvalue(), err.getvalue()


class CommandLineTests(unittest.TestCase):
    def assertRun(self, result, code, stdout=None, stderr=""):
        self.assertEqual(result[0], code, result)
        if stdout is not None:
            self.assertEqual(result[1], stdout)
        self.assertEqual(result[2], stderr)

    def test_main_modes_on_the_synthetic_registry(self):
        checkout = Checkout(self, Fixture())
        code, out, _ = checkout.run("--structure")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("Experience coverage 1.0.0 structure valid: 3 personas, 2 journeys, "))
        self.assertTrue(out.endswith("; readiness not evaluated.\n"))
        self.assertIn("checked against the frozen import", out)
        self.assertRun(checkout.run("--check-summary"), 1, "", "Experience coverage check refused: summary.drift\n")
        self.assertRun(checkout.run("--write-summary"), 0,
                       f"Experience coverage summary written to {module.SUMMARY} ({module.NOT_GREEN}).\n")
        written = (checkout.root / module.SUMMARY).read_bytes()
        self.assertEqual(written.splitlines()[0], module.NOT_GREEN.encode("ascii"))
        self.assertNotIn(b"\r", written)
        self.assertRun(checkout.run("--check-summary"), 0,
                       f"Experience coverage summary {module.SUMMARY} matches the registry ({module.NOT_GREEN}).\n")
        code, out, _ = checkout.run()
        self.assertEqual((code, out.splitlines()[0]), (1, module.NOT_GREEN))
        # No registry can reach GREEN while the interfaces are held; the branch runs with readiness stubbed.
        with mock.patch.object(module, "readiness", return_value=EMPTY_GAPS):
            self.assertRun(checkout.run("--write-summary"), 0,
                           f"Experience coverage summary written to {module.SUMMARY} ({module.GREEN}).\n")
            code, out, _ = checkout.run()
            self.assertEqual((code, out.splitlines()[0], len(out.splitlines())), (0, module.GREEN, 2))

    def test_partial_registry_default_mode_is_not_green_with_exact_counts(self):
        fixture = Fixture()
        fixture.partition["post_snapshot_issues"] = ["PenniLogic/android#905"]
        checkout = Checkout(self, fixture)
        self.assertEqual(checkout.run("--write-summary")[0], 0)
        self.assertEqual(checkout.run("--structure")[0], 0)
        code, out, err = checkout.run()
        self.assertEqual((code, err), (1, ""))
        lines = out.splitlines()
        self.assertEqual(lines[0], module.NOT_GREEN)
        self.assertTrue(lines[1].startswith("Experience coverage 1.0.0 structure valid: "))
        expected = {rule: len(subjects) for rule, subjects in BASELINE_GAPS.items()}
        expected["readiness.post_snapshot_issue"] = 1
        self.assertEqual(lines[2:], [f"{rule}: {count}" for rule, count in expected.items()])
        self.assertEqual((checkout.root / module.SUMMARY).read_text(encoding="utf-8").splitlines()[0], module.NOT_GREEN)

    def test_summary_drift_fails(self):
        checkout = Checkout(self, Fixture())
        self.assertEqual(checkout.run("--write-summary")[0], 0)
        summary = checkout.root / module.SUMMARY
        summary.write_bytes(summary.read_bytes().replace(b"\n", b"\r\n", 1))
        refusal = "Experience coverage check refused: summary.drift\n"
        self.assertRun(checkout.run("--check-summary"), 1, "", refusal)
        self.assertRun(checkout.run(), 1, "", refusal)
        self.assertEqual(checkout.run("--write-summary")[0], 0)
        self.assertEqual(checkout.run("--check-summary")[0], 0)
        checkout.fixture.partition["post_snapshot_issues"] = ["PenniLogic/android#905"]
        checkout.save()
        self.assertRun(checkout.run("--check-summary"), 1, "", refusal)
        summary.unlink()
        self.assertRun(checkout.run(), 1, "", refusal)

    def test_write_summary_refuses_invalid_structure_and_writes_nothing(self):
        fixture = Fixture()
        fixture.record("C-TRUST-FOUNDATION")["foundational"] = False
        checkout = Checkout(self, fixture)
        self.assertRun(checkout.run("--write-summary"), 1, "",
                       "Experience coverage check refused: component.unused C-TRUST-FOUNDATION\n")
        self.assertFalse((checkout.root / module.SUMMARY).exists())

    def test_errors_print_only_validated_ids(self):
        token = planted_token()
        self.assertEqual(str(module.Refused("id.duplicate", "S-AND-001")), "id.duplicate S-AND-001")
        self.assertEqual(str(module.Refused("ticket.dangling", "S-AND-001", "PenniLogic/docs#9")),
                         "ticket.dangling S-AND-001 PenniLogic/docs#9")
        for subjects in (("S-AND-001\n",), (token,), ("S-AND-001", token), ("T-SYN-DSN-01",), ("docs#9",), (None,),
                         ("PenniLogic/android#9876543210",), ("C-AKIA" + "ABCDEFGHIJKLMNOP",)):
            with self.subTest(subjects=subjects):
                error = module.Refused("id.duplicate", *subjects)
                self.assertEqual((str(error), error.subject), ("id.duplicate", None))
        fixture = Fixture()
        fixture.record("S-AND-001")["name"] = "Synthetic " + token
        checkout = Checkout(self, fixture)
        self.assertRun(checkout.run("--structure"), 1, "",
                       "Experience coverage check refused: content.secret_shape S-AND-001\n")
        fixture = Fixture()
        fixture.record("S-AND-001")["id"] = token
        checkout = Checkout(self, fixture)
        self.assertRun(checkout.run("--structure"), 1, "", "Experience coverage check refused: schema.invalid\n")
        (checkout.root / module.PARTITION).write_text('{"kind": "x", "kind": "' + token + '"}', encoding="utf-8")
        self.assertRun(checkout.run("--structure"), 1, "",
                       "Experience coverage check refused: input.unreadable_or_invalid\n")
        (checkout.root / module.REGISTRY).unlink()
        self.assertRun(checkout.run(), 1, "", "Experience coverage check refused: input.unreadable_or_invalid\n")

    def test_ledger_base_is_the_merge_base_with_origin_main(self):
        fixture = Fixture()
        fixture.drop_screen("S-AND-004")
        checkout = Checkout(self, fixture, base_registry=REGISTRY)
        removed = "Experience coverage check refused: ledger.entry_removed S-AND-004\n"
        self.assertRun(checkout.run("--structure"), 1, "", removed)
        self.assertRun(checkout.run("--structure", "--base", checkout.base), 1, "", removed)
        self.assertRun(checkout.run("--structure", "--base", "origin/main"), 1, "", removed)
        git(checkout.root, "update-ref", "-d", "refs/remotes/origin/main")
        unavailable = "Experience coverage check refused: ledger.base_unavailable\n"
        self.assertRun(checkout.run("--structure"), 1, "", unavailable)
        for revision in ("HEAD@{0}", "-n", "0" * 40, "HEAD~1"):
            with self.subTest(revision=revision):
                self.assertRun(checkout.run("--structure", f"--base={revision}"), 1, "", unavailable)
        self.assertRun(checkout.run("--structure", "--base", checkout.base), 1, "", removed)

    def test_missing_base_registry_blob_fails_closed(self):
        """AV-03: the base tree lists the registry but its blob is absent locally (a blobless clone or a pruned
        object); that must not pass as a base that predates the registry."""
        fixture = Fixture()
        fixture.drop_screen("S-AND-004")
        checkout = Checkout(self, fixture, base_registry=REGISTRY)
        self.assertRun(checkout.run("--structure"), 1, "",
                       "Experience coverage check refused: ledger.entry_removed S-AND-004\n")
        blob = git(checkout.root, "rev-parse", f"{checkout.base}:{module.REGISTRY}")
        (checkout.root / ".git/objects" / blob[:2] / blob[2:]).unlink()
        self.assertEqual(git(checkout.root, "ls-tree", "--name-only", checkout.base, "--", module.REGISTRY),
                         module.REGISTRY)
        self.assertRun(checkout.run("--structure"), 1, "",
                       "Experience coverage check refused: ledger.base_unavailable\n")

    def test_ledger_base_ignores_a_local_branch_named_origin_main(self):
        fixture = Fixture()
        fixture.drop_screen("S-AND-004")
        checkout = Checkout(self, fixture, base_registry=REGISTRY)
        removed = "Experience coverage check refused: ledger.entry_removed S-AND-004\n"
        self.assertRun(checkout.run("--structure"), 1, "", removed)
        git(checkout.root, "branch", "origin/main", "HEAD")
        self.assertRun(checkout.run("--structure"), 1, "", removed)

    def test_replace_refs_cannot_forge_the_base_registry(self):
        """The base registry blob is not pinned by digest, so a replace ref must not substitute its bytes."""
        fixture = Fixture()
        fixture.drop_screen("S-AND-004")
        checkout = Checkout(self, fixture, base_registry=REGISTRY)
        removed = "Experience coverage check refused: ledger.entry_removed S-AND-004\n"
        self.assertRun(checkout.run("--structure"), 1, "", removed)
        original = git(checkout.root, "rev-parse", f"{checkout.base}:{module.REGISTRY}")
        git(checkout.root, "replace", original, git(checkout.root, "rev-parse", f"HEAD:{module.REGISTRY}"))
        self.assertRun(checkout.run("--structure"), 1, "", removed)

    def test_grafts_cannot_move_the_ledger_base(self):
        """A graft re-parenting the candidate onto a pre-registry commit must not downgrade the base check."""
        checkout = Checkout(self, Fixture())  # base commit without a registry, candidate commit with one
        before = checkout.base
        git(checkout.root, "update-ref", "refs/remotes/origin/main", "HEAD")
        checkout.fixture.drop_screen("S-AND-004")  # S-AND-004 postdates the frozen import
        checkout.save()
        git(checkout.root, "add", "-A")
        git(checkout.root, "commit", "-q", "-m", "synthetic removal")
        removed = "Experience coverage check refused: ledger.entry_removed S-AND-004\n"
        self.assertRun(checkout.run("--structure"), 1, "", removed)
        (checkout.root / ".git/info").mkdir(parents=True, exist_ok=True)
        (checkout.root / ".git/info/grafts").write_text(f"{git(checkout.root, 'rev-parse', 'HEAD')} {before}\n",
                                                        encoding="utf-8")
        self.assertRun(checkout.run("--structure"), 1, "", removed)

    def test_base_without_a_registry_falls_back_to_import_continuity(self):
        fixture = Fixture()
        fixture.drop_screen("S-AND-004")
        checkout = Checkout(self, fixture)
        code, out, _ = checkout.run("--structure")
        self.assertEqual(code, 0)
        self.assertIn("checked against the frozen import", out)
        fixture.drop_screen("S-AND-002")
        checkout.save()
        self.assertRun(checkout.run("--structure"), 1, "",
                       "Experience coverage check refused: ledger.import_discontinuity S-AND-002\n")

    def test_imported_blob_is_read_from_the_pinned_commit(self):
        checkout = Checkout(self, Fixture())
        self.assertEqual(checkout.run("--structure")[0], 0)
        registry = copy.deepcopy(checkout.registry)
        registry["imported_from"]["commit"] = "f" * 40
        checkout.write(module.REGISTRY, encode(registry))
        self.assertRun(checkout.run("--structure"), 1, "", "Experience coverage check refused: import.unavailable\n")

    def test_git_is_resolved_outside_the_repository(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name) / "candidate"
        planted = root / "tools"
        planted.mkdir(parents=True)
        name = "git.exe" if os.name == "nt" else "git"
        (planted / name).write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (planted / name).chmod(0o755)
        real = Path(shutil.which("git")).parent
        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join([str(real)])}):
            self.assertEqual(Path(module.trusted_git(root)).parent, real)
        for path in ([str(planted), str(real)], ["", ".", "tools", str(real)], [str(root), str(real)]):
            with self.subTest(path=path), mock.patch.dict(os.environ, {"PATH": os.pathsep.join(path)}):
                self.assertEqual(Path(module.trusted_git(root)).parent, real)
        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join([str(planted), "."])}):
            with self.assertRaises(LookupError):
                module.trusted_git(root)
            with self.assertRaises(module.Refused) as caught:
                module.read_base(module.GitSources(root), SCHEMA)
            self.assertEqual(caught.exception.rule, "ledger.base_unavailable")

    def test_unexpected_errors_fail_closed_without_echo(self):
        checkout = Checkout(self, Fixture())
        self.assertEqual(checkout.run("--structure")[0], 0)
        token = planted_token()
        for error in (KeyError(token), TypeError(token), AttributeError(token), IndexError(token)):
            with self.subTest(error=type(error).__name__), mock.patch.object(module, "load_and_check",
                                                                              side_effect=error):
                self.assertRun(checkout.run("--structure"), 1, "",
                               "Experience coverage check refused: input.unreadable_or_invalid\n")

    def test_write_summary_never_follows_a_symlink(self):
        checkout = Checkout(self, Fixture())
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        victim = Path(outside.name) / "victim.md"
        victim.write_text("unchanged\n", encoding="utf-8")
        self.assertEqual(checkout.run("--write-summary")[0], 0)
        summary = checkout.root / module.SUMMARY
        summary.unlink()
        summary.symlink_to(victim)
        self.assertRun(checkout.run("--write-summary"), 1, "",
                       "Experience coverage check refused: input.unreadable_or_invalid\n")
        self.assertEqual(victim.read_text(encoding="utf-8"), "unchanged\n")

    def test_main_exit_codes(self):
        """0 complete or structurally sound as asked, 1 refused or NOT GREEN, 2 usage error."""
        fixture = Fixture()
        checkout = Checkout(self, fixture)
        self.assertEqual(checkout.run("--write-summary")[0], 0)
        self.assertEqual([checkout.run(*argv)[0] for argv in ([], ["--structure"], ["--check-summary"])], [1, 0, 0])
        with mock.patch.object(module, "readiness", return_value=EMPTY_GAPS):  # GREEN is unreachable from data
            self.assertEqual(checkout.run("--write-summary")[0], 0)
            self.assertEqual([checkout.run(*argv)[0] for argv in ([], ["--structure"], ["--check-summary"])],
                             [0, 0, 0])
        self.assertEqual(checkout.run("--write-summary")[0], 0)
        fixture.record("C-TRUST-FOUNDATION")["foundational"] = False
        checkout.save()
        self.assertEqual([checkout.run(*argv)[0] for argv in ([], ["--structure"], ["--check-summary"])], [1, 1, 1])
        for argv in (["--structure", "--check-summary"], ["--write-summary", "--structure"], ["--unknown"]):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    module.main(argv)
                self.assertEqual(caught.exception.code, 2)


# The recorded state of the published registry (HC-B1): changing any count is a reviewed change to this file.
PUBLISHED_GAPS = {
    "readiness.d6_missing": 141, "readiness.route_missing": 141, "readiness.qa_unverified": 35,
    "readiness.persona_outside_journey": 3, "readiness.screen_ticket_outside_flows": 1,
    "readiness.security_states_missing": 7, "readiness.proposal_unconfirmed": 232, "readiness.ticket_unresolved": 0,
    "readiness.post_snapshot_issue": 1, "readiness.partition_scope_question": 5,
}
PUBLISHED_STRUCTURE = re.escape(
    "Experience coverage 1.0.0 structure valid: 12 personas, 12 journeys, 38 user stories, 38 flows (35 critical), "
    "141 screens, 57 components, 21 diagrams, 319 ledger IDs checked against the "
) + r"(?:frozen import|base registry)" + re.escape(
    "; 108 client issues partitioned (74 frontend, 34 non-frontend); registry checksum "
) + r"sha256:[0-9a-f]{64}"


class Published:
    """Fresh copies of this checkout's committed registry, partition and inputs; the frozen import is read from the
    working tree (the validator still checks it against the pinned sha256), so no Git state is needed."""

    def __init__(self):
        load = module.support.load_json
        self.registry, self.partition = load(ROOT / module.REGISTRY), load(ROOT / module.PARTITION)
        self.inventory, self.taxonomy = load(ROOT / module.INVENTORY), load(ROOT / module.TAXONOMY)
        self.blobs = {(self.registry["imported_from"]["commit"], module.IMPORT_PATH): (ROOT / module.IMPORT_PATH)
                      .read_bytes()}
        self.base = self.partition_base = None

    def check(self):
        return module.check(self.registry, self.partition, SCHEMA, self.inventory, self.taxonomy,
                            Sources(self.blobs, self.base, partition=self.partition_base))

    def drop_screen(self, identifier):
        """Remove a screen consistently: record, its ledger entry and its flow links."""
        self.registry["screens"] = [item for item in self.registry["screens"] if item["id"] != identifier]
        self.registry["id_ledger"] = [item for item in self.registry["id_ledger"] if item["id"] != identifier]
        for item in self.registry["flows"]:
            if identifier in item["screen_ids"]:
                item["screen_ids"].remove(identifier)


class PublishedDataTests(unittest.TestCase):
    """The committed product/experience-coverage.* files of this checkout; read-only, nothing is written."""

    def run_main(self, *argv):
        self.assertEqual(module.ROOT, ROOT)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_published_registry_structure_passes(self):
        """Real files and the local Git object store: pinned import blob and the merge base with origin/main."""
        model = module.load_and_check(ROOT)
        merge_base = git(ROOT, "merge-base", "HEAD", module.BASE_REF)
        listed = git(ROOT, "ls-tree", "--name-only", merge_base, "--", module.REGISTRY)
        self.assertEqual(model.ledger_base, "base registry" if listed else "frozen import")
        self.assertEqual({collection: len(model.registry[collection]) for collection, _ in module.COLLECTIONS}, {
            "personas": 12, "journeys": 12, "user_stories": 38, "flows": 38, "screens": 141, "components": 57,
            "diagrams": 21,
        })
        entries = model.partition["entries"]
        self.assertEqual((len(entries), sum(entry["disposition"] == "frontend" for entry in entries)), (108, 74))
        code, out, err = self.run_main("--structure")
        self.assertEqual((code, err), (0, ""))
        self.assertRegex(out, r"\A" + PUBLISHED_STRUCTURE + re.escape("; readiness not evaluated.\n") + r"\Z")
        self.assertEqual(Published().check().ledger_base, "frozen import")  # hermetic fallback path

    def test_published_registry_reports_exact_readiness_gaps(self):
        model = Published().check()
        gaps = module.readiness(model)
        self.assertEqual({rule: len(subjects) for rule, subjects in gaps.items()}, PUBLISHED_GAPS)
        screens = sorted(model.screens, key=module.natural_key)
        self.assertEqual(gaps["readiness.d6_missing"], screens)
        self.assertEqual(gaps["readiness.route_missing"], screens)
        self.assertEqual(gaps["readiness.qa_unverified"],
                         sorted((key for key, flow in model.flows.items() if flow["critical"]), key=module.natural_key))
        # TS-M1 union rule: the final plan's "(7)" came from the critique's one-journey-per-story table; US-AND-16,
        # US-WEB-01, US-WEB-03 and US-ADM-07 are covered by the union of their flows' journeys.
        self.assertEqual(gaps["readiness.persona_outside_journey"], ["US-WEB-02", "US-WEB-05", "US-ADM-06"])
        self.assertEqual(gaps["readiness.screen_ticket_outside_flows"], ["S-AND-041 PenniLogic/android#42"])
        self.assertEqual(gaps["readiness.security_states_missing"], [
            "S-AND-005", "S-AND-057", "S-WEB-009", "S-WEB-035", "S-ADM-021", "S-ADM-022", "S-ADM-024",
        ])
        self.assertEqual(gaps["readiness.post_snapshot_issue"], ["PenniLogic/android#69"])
        # SC-3: the five DesignOps exclusions whose own rationale names unmapped user-visible scope.
        self.assertEqual(gaps["readiness.partition_scope_question"], [
            "PenniLogic/android#7", "PenniLogic/android#19", "PenniLogic/android#27", "PenniLogic/android#37",
            "PenniLogic/android#57",
        ])
        proposals = gaps["readiness.proposal_unconfirmed"]
        self.assertEqual([sum(subject.startswith(prefix) for subject in proposals)
                          for prefix in ("S-", "C-", "PenniLogic/")], [141, 57, 34])
        # The recorded DesignOps security proposal: 58 screens, each with a stated basis; only the screen's own
        # denial, revocation and (for export, erasure and safe exit) destructive states are named, so filling a
        # gap with any other state is a reviewed change to this test.
        critical = [screen for screen in model.screens.values() if screen["security_critical"]]
        self.assertEqual([sum(screen["platform"] == platform for screen in critical) for platform in module.PLATFORMS],
                         [25, 13, 20])
        for screen in critical:
            with self.subTest(screen=screen["id"]):
                self.assertIn(" Basis: ", screen["security_reason"])
                self.assertLessEqual(set(screen["privacy_states"]) | set(screen["authorization_states"]),
                                     {"permission-denied", "revoked", "destructive"})
        code, out, err = self.run_main()
        self.assertEqual((code, err), (1, ""), out)  # the complete check: a refusal would name its rule in err
        lines = out.splitlines()
        self.assertEqual(lines[0], module.NOT_GREEN)
        self.assertRegex(lines[1], r"\A" + PUBLISHED_STRUCTURE + r"\Z")
        self.assertEqual(lines[2:], [f"{rule}: {count}" for rule, count in PUBLISHED_GAPS.items()])

    def test_published_summary_matches_registry(self):
        model = Published().check()
        summary = module.render_summary(model, module.readiness(model))
        self.assertEqual((ROOT / module.SUMMARY).read_bytes(), summary.encode("utf-8"))
        lines = summary.splitlines()
        self.assertEqual(lines[0], module.NOT_GREEN)
        canonical = json.dumps(model.registry, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        self.assertIn(f"| Registry checksum | `sha256:{hashlib.sha256(canonical).hexdigest()}` |", lines)
        for rule, count in PUBLISHED_GAPS.items():
            self.assertIn(f"| `{rule}` | {count} |", lines)
        self.assertIn("- `readiness.security_states_missing` (7): S-AND-005, S-AND-057, S-WEB-009, S-WEB-035, "
                      "S-ADM-021, S-ADM-022, S-ADM-024", lines)
        self.assertEqual(self.run_main("--check-summary"), (
            0, f"Experience coverage summary {module.SUMMARY} matches the registry ({module.NOT_GREEN}).\n", ""))

    def test_published_ledger_record_and_entry_removed_together_fails(self):
        """Against the published registry as base, and against the frozen import when no base registry exists."""
        base = (ROOT / module.REGISTRY).read_bytes()
        for committed, rule in ((base, "ledger.entry_removed"), (None, "ledger.import_discontinuity")):
            with self.subTest(rule=rule):
                fixture = Published()
                fixture.base = committed
                self.assertEqual(fixture.check().ledger_base, "base registry" if committed else "frozen import")
                fixture.drop_screen("S-AND-041")
                with self.assertRaises(module.Refused) as caught:
                    fixture.check()
                self.assertEqual((caught.exception.rule, caught.exception.subject), (rule, "S-AND-041"))

    def test_published_repointed_id_fails(self):
        """AV-02 on the published registry: two screens swap identities, with or without their fingerprints."""
        base = (ROOT / module.REGISTRY).read_bytes()
        keys = ("name", "route_hint", "surface_type", "states", "component_ids", "security_critical", "security_reason",
                "privacy_states", "authorization_states", "implementation_tickets", "proposal")
        for committed, with_ledger, rule in ((base, False, "ledger.fingerprint_mismatch"),
                                             (None, True, "ledger.import_discontinuity"),
                                             (base, True, "ledger.entry_changed")):
            with self.subTest(base=committed is not None, ledger=with_ledger):
                fixture = Published()
                fixture.base = committed
                fixture.check()
                screens = {item["id"]: item for item in fixture.registry["screens"]}
                entries = {item["id"]: item for item in fixture.registry["id_ledger"]}
                for key in keys:
                    screens["S-AND-001"][key], screens["S-AND-002"][key] = screens["S-AND-002"][key], screens[
                        "S-AND-001"][key]
                if with_ledger:
                    first, second = entries["S-AND-001"], entries["S-AND-002"]
                    first["name_sha256"], second["name_sha256"] = second["name_sha256"], first["name_sha256"]
                with self.assertRaises(module.Refused) as caught:
                    fixture.check()
                self.assertEqual((caught.exception.rule, caught.exception.subject), (rule, "S-AND-001"))

    def test_published_relabel_of_delivered_issue_fails(self):
        """AV-05 on the published registry: admin#10 closed, unmapped and relabelled non-frontend."""
        fixture = Published()
        fixture.base = (ROOT / module.REGISTRY).read_bytes()
        fixture.partition_base = (ROOT / module.PARTITION).read_bytes()
        fixture.check()
        issue = next(item for item in fixture.inventory["issues"] if item["reference"] == "PenniLogic/admin#10")
        issue.update(state="closed", state_reason="completed")
        for collection in ("flows", "screens"):
            for record in fixture.registry[collection]:
                kept = [item for item in record["implementation_tickets"] if item["issue"] != "PenniLogic/admin#10"]
                record["implementation_tickets"] = kept or [{"plan_id": "T-ADM-14", "issue": "PenniLogic/admin#11"}]
        entry = next(item for item in fixture.partition["entries"] if item["issue"] == "PenniLogic/admin#10")
        entry.update(disposition="non_frontend", rationale_class="other", rationale="Delivered without a screen.",
                     proposed_by="design_ops")
        with self.assertRaises(module.Refused) as caught:
            fixture.check()
        self.assertEqual((caught.exception.rule, caught.exception.subject),
                         ("release_gate.relabeled", "PenniLogic/admin#10"))

    def test_published_release_gate_bypass_fails(self):
        """An implementation issue closed as completed while its screens lack D6 is a bypass of the gate."""
        fixture = Published()
        fixture.check()
        issue = next(item for item in fixture.inventory["issues"] if item["reference"] == "PenniLogic/admin#10")
        self.assertEqual((issue["plan_id"], issue["state"]), ("T-ADM-13", "open"))
        issue.update(state="closed", state_reason="completed")
        with self.assertRaises(module.Refused) as caught:
            fixture.check()
        self.assertEqual((caught.exception.rule, caught.exception.subject),
                         ("release_gate.bypass", "PenniLogic/admin#10 S-ADM-018"))
        # AV-01: self-asserted D6 references on every screen of the closed issue cannot clear the gate.
        for record in fixture.registry["screens"]:
            if record["id"] in ("S-ADM-018", "S-ADM-019", "S-ADM-020"):
                record.update(handoff_ref="HND-ADM-999@9.9.9", d6_dependency={
                    "artifact_id": record["id"], "gate_id": "D6", "scope_sha256": "sha256:" + "0" * 64})
        with self.assertRaises(module.Refused) as caught:
            fixture.check()
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("held.d6_reference", "S-ADM-018"))


if __name__ == "__main__":
    unittest.main()
