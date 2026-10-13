"""T-DSY-02 validator tests: synthetic library, component, release and tabletop fixtures.

Every rule test builds a fresh deep copy of one synthetic document, proves it passes (the control), applies exactly
one mutation and asserts the exact static rule identifier and offending identifier. Fixture-mode documents use only
the reserved C-SYN-* component prefix and a synthetic registry pin served from memory; they may publish so that the
published-component, breaking-change and deprecation rules are exercised. Real-mode documents (the mode the command
line uses) hold no components and only draft releases, proving the held rules: no publication, no recorded CDO
decision, no direction or token reference. No fixture is an approval, a Figma permission, a live verification or a
real component. Command-line tests run against temporary directories outside this repository. The published-data
tests read the committed governance/figma-libraries.json and the real pinned registry from this checkout's local Git
object store, assert the exact readiness gaps and fail when the governance document's generated section drifts from
the JSON. Nothing here touches the network or writes inside the repository.
"""

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
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_figma_libraries", ROOT / "scripts/check_figma_libraries.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SCHEMA = module.support.load_json(ROOT / module.SCHEMA)
POLICY = module.support.load_json(ROOT / module.GATES)
POLICY_SCHEMA = module.support.load_json(ROOT / module.gates.SCHEMA)
REGISTRY_PATH = "planning/source/evidence/experience-coverage.json"
SYNTHETIC_COMMIT = "1" * 40
DECISION = {"commit": "2" * 40, "path": "governance/synthetic-decision.json", "sha256": "sha256:" + "a" * 64}


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


NAMES = {"C-SYN-BUTTON": "Button", "C-SYN-CHIP": "Chip", "C-SYN-DRAFT": "Draft banner"}


def pinned(components):
    """A synthetic registry blob and its {commit, path, sha256} pin; names follow the fixture's records."""
    blob = encode({"components": [{"id": key, "name": NAMES.get(key, "Synthetic pinned component"),
                                   "platforms": value} for key, value in components]})
    return blob, {"commit": SYNTHETIC_COMMIT, "path": REGISTRY_PATH,
                  "sha256": "sha256:" + hashlib.sha256(blob).hexdigest()}


FIXTURE_BLOB, FIXTURE_PIN = pinned([
    ("C-SYN-BUTTON", ["android", "web", "admin"]), ("C-SYN-CHIP", ["android", "web", "admin"]),
    ("C-SYN-DRAFT", ["web"]), ("C-SYN-PINNED", ["admin"]),
])
REAL_BLOB, REAL_PIN = pinned([])


class Sources:
    """In-memory stand-in for GitSources."""

    def __init__(self, blobs):
        self.blobs = blobs

    def blob(self, commit, path):
        try:
            return self.blobs[(commit, path)]
        except KeyError:
            raise LookupError(path) from None


SOURCES = Sources({(SYNTHETIC_COMMIT, REGISTRY_PATH): FIXTURE_BLOB})
REAL_SOURCES = Sources({(SYNTHETIC_COMMIT, REGISTRY_PATH): REAL_BLOB})


def library(identifier, kind, figma_file, page, publish, consumes):
    return {"id": identifier, "kind": kind, "figma_file": figma_file, "figma_page": page, "owner_role": "systems",
            "publish_roles": publish, "consumes": consumes, "status": "shell"}


def release(name, previous, change, status, breaking=False, migration=None, approval="recorded"):
    library_id, version = name.split("@")
    cdo = None
    if change == "major":
        cdo = {"role": "decision_coordinator", "scope": "shared_system_major", "status": approval,
               "decision_source": copy.deepcopy(DECISION) if approval == "recorded" else None}
    return {"library": library_id, "version": version, "previous": previous, "change_class": change,
            "breaking": breaking, "status": status, "migration_plan_ref": migration, "cdo_approval": cdo,
            "rollback_to": None}


def component(identifier, name, library_id="LIB-COMPONENTS", status="published", role=None, platforms=None,
              properties=None, variant_of=None, since="1.0.0"):
    return {
        "id": identifier, "name": name, "library": library_id, "status": status,
        "semantic_role": role or name.lower(), "owner_role": "systems",
        "description": f"Synthetic {name.lower()} fixture; not a real component.",
        "platforms": platforms or ["android", "web", "admin"],
        "properties": properties if properties is not None else [
            {"name": "emphasis", "type": "enum", "values": ["primary", "secondary"], "default": "primary",
             "required": True},
        ],
        "accessibility": {"role": "button", "accessible_name": "Visible label", "focus": "Focusable in reading order",
                          "announcements": "Announces state changes"},
        "variant_of": variant_of, "since_version": since, "deprecation": None, "proposal_branch": None,
        "token_refs": [],
    }


def libraries():
    return [
        library("LIB-FOUNDATION", "foundation", "02 - Foundations library", "Foundations", ["systems"], []),
        library("LIB-COMPONENTS", "shared_semantic", "03 - Components library", "Components", ["systems"],
                ["LIB-FOUNDATION"]),
        library("LIB-ANDROID", "platform_variant", "03 - Components library", "Android variants", ["systems"],
                ["LIB-FOUNDATION", "LIB-COMPONENTS"]),
        library("LIB-WEB", "platform_variant", "03 - Components library", "Web variants", ["systems"],
                ["LIB-FOUNDATION", "LIB-COMPONENTS"]),
        library("LIB-ADMIN", "platform_variant", "03 - Components library", "Admin variants", ["systems"],
                ["LIB-FOUNDATION", "LIB-COMPONENTS"]),
        library("LIB-CANDIDATE", "candidate", None, None, [], ["LIB-FOUNDATION", "LIB-COMPONENTS"]),
    ]


def tabletop():
    rows = []
    for name in module.SHARED:
        rows.append(("publish", "android_design", name, False, "refused"))
        rows.append(("publish", "systems", name, True, "refused"))
    rows += [
        ("publish", "systems", "LIB-COMPONENTS", False, "model_permitted"),
        ("edit", "web_design", "LIB-COMPONENTS", False, "refused"),
        ("comment", "admin_design", "LIB-COMPONENTS", False, "model_permitted"),
        ("public_link", "systems", "LIB-COMPONENTS", False, "refused"),
        ("export", "systems", "LIB-FOUNDATION", False, "refused"),
        ("edit", "android_design", "LIB-CANDIDATE", False, "model_permitted"),
        ("external_share", "web_design", "LIB-WEB", False, "refused"),
    ]
    return [{"id": f"TT-{index:02d}", "action": action, "role": role, "library": name, "offboarded": offboarded,
             "expected": expected, "evidence_class": "tabletop", "live_verified": False}
            for index, (action, role, name, offboarded, expected) in enumerate(rows, start=1)]


def fixture():
    """Fixture mode: synthetic published components, a recorded synthetic CDO decision and a pending breaking major."""
    chip = component("C-SYN-CHIP", "Chip", status="deprecated", role="filter toggle", properties=[
        {"name": "selected", "type": "boolean", "values": [], "default": "false", "required": False},
    ])
    chip["deprecation"] = {"replacement": "C-SYN-BUTTON", "removal_version": "2.0.0", "available_until_removal": True}
    draft = component("C-SYN-DRAFT", "Draft banner", status="draft", since=None, platforms=["web"])
    draft.update(semantic_role=None, owner_role=None, description=None, properties=[], accessibility=None)
    local = component("C-SYN-LOCAL", "Local card", library_id="LIB-CANDIDATE", status="candidate",
                      role="summary card", since=None, properties=[
                          {"name": "body", "type": "slot", "values": [], "default": None, "required": True},
                      ])
    local.update(owner_role="android_design", platforms=["android"], proposal_branch="T-DSY-02__android__local-card")
    return {
        "schema_version": 1, "contract_version": "1.0.0", "source_issue": "PenniLogic/docs#78", "plan_id": "T-DSY-02",
        "registry_ref": copy.deepcopy(FIXTURE_PIN), "direction_ref": None,
        "access": {"public_links_enabled": False, "external_sharing_enabled": False, "asset_export_enabled": False,
                   "offboarding_revokes": True},
        "libraries": [dict(item, status="active") if item["id"] in ("LIB-COMPONENTS", "LIB-ANDROID") else item
                      for item in libraries()],
        "releases": [
            release("LIB-COMPONENTS@1.0.0", None, "major", "published"),
            release("LIB-COMPONENTS@2.0.0", "1.0.0", "major", "draft", breaking=True,
                    migration="pending:PenniLogic/docs#78", approval="pending"),
            release("LIB-ANDROID@1.0.0", None, "major", "published"),
        ],
        "components": [
            component("C-SYN-BUTTON", "Button", role="primary action"), chip, draft,
            component("C-SYN-BUTTON-AND", "Android button", library_id="LIB-ANDROID", platforms=["android"],
                      variant_of="C-SYN-BUTTON", role="primary action"),
            local,
        ],
        "tabletop": tabletop(),
        "approvals": [{"role": role, "status": "not_recorded"} for role in module.APPROVAL_ROLES],
    }


def real():
    """Real mode (the command line's): no components, draft releases, pending CDO approvals only."""
    document = fixture()
    document["registry_ref"] = copy.deepcopy(REAL_PIN)
    document["libraries"] = libraries()
    document["components"] = []
    document["releases"] = [
        release("LIB-COMPONENTS@1.0.0", None, "major", "draft", approval="pending"),
        release("LIB-COMPONENTS@1.1.0", "1.0.0", "minor", "draft"),
    ]
    return document


def run_check(document, fixture_mode=True):
    if fixture_mode:
        return module.check(document, SCHEMA, POLICY, POLICY_SCHEMA, SOURCES, pin=FIXTURE_PIN, fixture=True)
    return module.check(document, SCHEMA, POLICY, POLICY_SCHEMA, REAL_SOURCES, pin=REAL_PIN)


def planted_token():
    """A key-shaped value built at run time so no secret-shaped literal is committed."""
    return "".join(chr(ord("A") + index % 26) + str(index % 10) for index in range(20))


class RuleCase(unittest.TestCase):
    def assertRefused(self, mutate, rule, *subjects, fixture_mode=True, base=None):
        """Control passes, exactly one mutation, then the exact rule and offending IDs (and no echoed input).
        `base` builds a different passing control than the plain fixture or real document."""
        document = base() if base is not None else fixture() if fixture_mode else real()
        run_check(copy.deepcopy(document), fixture_mode)
        mutate(document)
        with self.assertRaises(module.Refused) as caught:
            run_check(document, fixture_mode)
        self.assertEqual(caught.exception.rule, rule)
        self.assertEqual(caught.exception.subject, " ".join(subjects) if subjects else None)
        self.assertEqual(str(caught.exception), " ".join((rule, *subjects)))
        return caught.exception


def find(document, collection, identifier):
    return next(item for item in document[collection] if item.get("id") == identifier)


def find_release(document, name):
    library_id, version = name.split("@")
    return next(item for item in document["releases"] if (item["library"], item["version"]) == (library_id, version))


class BaselineTests(unittest.TestCase):
    def test_fixture_and_real_documents_pass_structure(self):
        model = run_check(fixture())
        self.assertEqual(len(model.components), 5)
        self.assertEqual(len(run_check(real(), False).releases), 2)

    def test_pending_migration_plan_is_a_visible_gap(self):
        document = real()
        self.assertEqual(module.readiness(run_check(copy.deepcopy(document), False))[
            "readiness.migration_plan_pending"], [])
        append_release(document, "LIB-COMPONENTS@1.1.1", "1.1.0", "patch", "draft",
                       migration="pending:PenniLogic/docs#79")
        self.assertEqual(module.readiness(run_check(document, False))["readiness.migration_plan_pending"],
                         ["LIB-COMPONENTS@1.1.1"])

    def test_rule_identifiers_are_static_and_unique(self):
        rules = module.STRUCTURE_RULES + module.READINESS_RULES
        self.assertEqual(len(rules), len(set(rules)))
        source = (ROOT / "scripts/check_figma_libraries.py").read_text(encoding="utf-8")
        for rule in rules:
            self.assertIn(f'"{rule}"', source)

    def test_fixture_readiness_gaps_are_exact(self):
        gaps = module.readiness(run_check(fixture()))
        self.assertEqual(gaps, {
            "readiness.direction_missing": ["PenniLogic/docs#76"],
            "readiness.tokens_unpublished": ["PenniLogic/docs#55"],
            "readiness.approval_not_recorded": sorted(module.APPROVAL_ROLES),
            "readiness.cdo_decision_pending": ["LIB-COMPONENTS@2.0.0"],
            "readiness.cdo_decision_unverified": ["LIB-ANDROID@1.0.0", "LIB-COMPONENTS@1.0.0"],
            "readiness.migration_plan_pending": ["LIB-COMPONENTS@2.0.0"],
            "readiness.migration_plan_unverified": [],
            "readiness.live_verification_missing": sorted(module.SHARED),
            "readiness.continuity_unchecked": sorted(module.SHARED),
            "readiness.component_not_in_registry": ["C-SYN-BUTTON-AND", "C-SYN-LOCAL"],
            "readiness.registry_component_ungoverned": ["C-SYN-PINNED"],
        })

    def test_refused_never_prints_unvalidated_subjects(self):
        self.assertEqual(str(module.Refused("schema.invalid", "free text")), "schema.invalid")
        self.assertEqual(str(module.Refused("schema.invalid", "C-SYN-BUTTON", "x")), "schema.invalid")
        self.assertEqual(str(module.Refused("id.duplicate", "C-SYN-BUTTON")), "id.duplicate C-SYN-BUTTON")
        self.assertFalse(module.printable("LIB-OTHER@1.0.0"))
        self.assertTrue(module.printable("LIB-WEB@1.0.0"))
        self.assertFalse(module.printable("not_a_role"))


class StructureTests(RuleCase):
    def test_unknown_field_is_schema_invalid(self):
        self.assertRefused(lambda d: d.update(extra=True), "schema.invalid")

    def test_nullable_object_shape_is_checked_in_code(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-BUTTON")["accessibility"].pop("focus"),
                           "schema.invalid", "C-SYN-BUTTON")

    def test_nullable_deprecation_and_decision_source_shapes_are_checked_in_code(self):
        """SC2-02: the other nullable objects are shape-checked with their record ID."""
        self.assertRefused(lambda d: chip_deprecation(d).pop("available_until_removal"), "schema.invalid",
                           "C-SYN-CHIP")
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@1.0.0")["cdo_approval"]["decision_source"].pop(
            "path"), "schema.invalid", "LIB-COMPONENTS@1.0.0")

    def test_secret_shape_is_refused_without_echo(self):
        token = planted_token()
        error = self.assertRefused(lambda d: find(d, "components", "C-SYN-BUTTON").update(description=token),
                                   "content.secret_shape", "C-SYN-BUTTON")
        self.assertNotIn(token, str(error))

    def test_public_link_shape_is_refused(self):
        link = "https" + "://" + "example" + ".com/file/abc"
        self.assertRefused(lambda d: find(d, "components", "C-SYN-BUTTON").update(description=link),
                           "content.url_shape", "C-SYN-BUTTON")

    def test_email_shape_is_refused(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-DRAFT").update(name="owner" + "@" + "team"),
                           "content.email_shape", "C-SYN-DRAFT")

    def test_padded_text_is_refused(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-DRAFT").update(name=" Draft banner"),
                           "content.blank_or_padded", "C-SYN-DRAFT")

    def test_unprintable_character_is_refused(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-DRAFT").update(name="Draft\u00a0banner"),
                           "content.unprintable_character", "C-SYN-DRAFT")

    def test_text_length_is_bounded(self):
        document = fixture()
        find(document, "components", "C-SYN-BUTTON")["description"] = "Draft " * 66 + "word"  # 400 characters pass
        run_check(document)
        self.assertRefused(lambda d: button(d).update(description="Draft " * 66 + "words"),  # 401 characters
                           "content.too_long", "C-SYN-BUTTON")

    def test_host_and_link_shapes_are_refused(self):
        samples = ("see www" + ".example", "visit www" + ".", "mail" + "to:someone", "Prototype at bit" + ".ly/3xYzAbC",
                   "host pl" + ".figma" + ".site", "files" + ".example" + ".de/proto", "local" + "host:8080/proto",
                   "10" + ".0.0.7/proto")
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertRefused(lambda d: button(d).update(description=sample), "content.url_shape",
                                   "C-SYN-BUTTON")

    def test_key_shapes_are_refused(self):
        samples = ("key " + "FP7lqd1V00" + "LUaT5zvdklkk", "a" * 34, "fig" + "d_" + "Ab3-" * 6)
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertRefused(lambda d: button(d).update(description=sample), "content.secret_shape",
                                   "C-SYN-BUTTON")

    def test_camel_case_property_names_are_exempt_from_the_key_scan(self):
        """AV2-5: schema-valid word-built property names pass; a key-shaped property name is still refused."""
        def named(name):
            return lambda d: button(d)["properties"].append(
                {"name": name, "type": "text", "values": [], "default": None, "required": False})
        for name in ("iconSize24Enabled", "showSupportingTextWhenErrorVisible", "maxLines2"):
            with self.subTest(name=name):
                document = fixture()
                named(name)(document)
                self.assertIn(name, [item["name"] for item in run_check(document).components["C-SYN-BUTTON"][
                    "properties"]])
        for name in ("fp7lqd1V00" + "LUaT5zvdklkk", "aB3dE5fG7hJ9" + "kL1mN2pQ4", "x" + "1a2b3c4d" * 4):
            with self.subTest(name=name):
                self.assertRefused(named(name), "content.secret_shape", "C-SYN-BUTTON")
        self.assertRefused(lambda d: button(d).update(description="iconSize24" + "EnabledAndVisible"),
                           "content.secret_shape", "C-SYN-BUTTON")  # exempt only at a property name

    def test_file_paths_are_exempt_only_at_their_fields(self):
        self.assertIn("C-SYN-BUTTON", run_check(fixture()).components)  # registry and decision paths pass
        self.assertRefused(lambda d: button(d).update(description="see governance/synthetic-decision" + ".json"),
                           "content.url_shape", "C-SYN-BUTTON")
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@1.0.0")["cdo_approval"][
            "decision_source"].update(path="pl" + ".figma" + ".site/x" + ".json"), "content.url_shape",
            "LIB-COMPONENTS@1.0.0")

    def test_phone_shape_is_refused(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-DRAFT").update(name="Call 98 7654 3210"),
                           "content.phone_shape", "C-SYN-DRAFT")

    def test_numbers_only_at_the_schema_version(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-WEB")["publish_roles"].append(7), "schema.invalid")
        self.assertRefused(lambda d: d.update(schema_version=1.0), "schema.invalid")

    def test_registry_digest_hex_is_exempt_only_at_its_path(self):
        digest = FIXTURE_PIN["sha256"]
        self.assertRefused(lambda d: find(d, "components", "C-SYN-DRAFT").update(name=digest),
                           "content.secret_shape", "C-SYN-DRAFT")

    def test_policy_must_be_the_accepted_design_gates_vocabulary(self):
        document = fixture()
        run_check(copy.deepcopy(document))
        policy = copy.deepcopy(POLICY)
        policy["cdo_equivalent_scopes"].remove("shared_system_major")
        with self.assertRaises(module.Refused) as caught:
            module.check(document, SCHEMA, policy, POLICY_SCHEMA, SOURCES, pin=FIXTURE_PIN, fixture=True)
        self.assertEqual(str(caught.exception), "policy.invalid")


class RegistryTests(RuleCase):
    def test_registry_ref_must_equal_the_pin(self):
        self.assertRefused(lambda d: d["registry_ref"].update(path="product/experience-coverage.json"),
                           "registry.ref_mismatch")

    def test_unavailable_pinned_blob_is_refused(self):
        document = fixture()
        run_check(copy.deepcopy(document))
        with self.assertRaises(module.Refused) as caught:
            module.check(document, SCHEMA, POLICY, POLICY_SCHEMA, Sources({}), pin=FIXTURE_PIN, fixture=True)
        self.assertEqual(str(caught.exception), "registry.unavailable")

    def test_digest_mismatch_is_refused(self):
        document = fixture()
        run_check(copy.deepcopy(document))
        forged = Sources({(SYNTHETIC_COMMIT, REGISTRY_PATH): FIXTURE_BLOB + b" "})
        with self.assertRaises(module.Refused) as caught:
            module.check(document, SCHEMA, POLICY, POLICY_SCHEMA, forged, pin=FIXTURE_PIN, fixture=True)
        self.assertEqual(str(caught.exception), "registry.digest_mismatch")

    def test_synthetic_ids_in_a_real_registry_are_invalid(self):
        blob, pin = pinned([("C-SYN-BUTTON", ["web"])])
        document = real()
        run_check(copy.deepcopy(document), False)
        document["registry_ref"] = pin
        with self.assertRaises(module.Refused) as caught:
            module.check(document, SCHEMA, POLICY, POLICY_SCHEMA, Sources({(SYNTHETIC_COMMIT, REGISTRY_PATH): blob}),
                         pin=pin)
        self.assertEqual(str(caught.exception), "registry.invalid")

    def refused_registry(self, blob):
        """A fixture-mode document re-pinned to `blob` (control: the plain fixture passes); fixture mode admits the
        reserved C-SYN-* IDs, so no real registry ID appears in a synthetic registry."""
        document = fixture()
        run_check(copy.deepcopy(document))
        pin = {"commit": SYNTHETIC_COMMIT, "path": REGISTRY_PATH,
               "sha256": "sha256:" + hashlib.sha256(blob).hexdigest()}
        document["registry_ref"] = pin
        with self.assertRaises(module.Refused) as caught:
            module.check(document, SCHEMA, POLICY, POLICY_SCHEMA, Sources({(SYNTHETIC_COMMIT, REGISTRY_PATH): blob}),
                         pin=pin, fixture=True)
        return str(caught.exception)

    def test_duplicate_registry_ids_are_invalid(self):
        record = {"id": "C-SYN-ACTION", "name": "Action", "platforms": ["web"]}
        self.assertEqual(self.refused_registry(encode({"components": [record, record]})), "registry.invalid")

    def test_duplicate_registry_keys_are_invalid(self):
        blob = b'{"components": [{"id": "C-SYN-ACTION", "id": "C-SYN-OTHER", "name": "Action", "platforms": ["web"]}]}'
        self.assertEqual(self.refused_registry(blob), "registry.invalid")

    def test_registry_names_are_required(self):
        self.assertEqual(self.refused_registry(encode({"components": [{"id": "C-SYN-ACTION", "platforms": ["web"]}]})),
                         "registry.invalid")

    def test_registry_grammar_ids_are_gaps_not_failures(self):
        ids = ("C-SYN-OP-2FA", "C-SYN-DATA-VISUALIZATION", "C-SYN-INPUT-OTP-6", "C-SYN--B")
        blob, pin = pinned([(identifier, ["admin"]) for identifier in ids])
        document = fixture()
        document["registry_ref"] = pin
        sources = Sources({(SYNTHETIC_COMMIT, REGISTRY_PATH): blob})
        model = module.check(document, SCHEMA, POLICY, POLICY_SCHEMA, sources, pin=pin, fixture=True)
        self.assertEqual(module.readiness(model)["readiness.registry_component_ungoverned"], sorted(ids))
        record = component("C-SYN-OP-2FA", "Synthetic pinned component", status="draft", platforms=["admin"],
                           since=None)
        record.update(semantic_role=None, description=None, properties=[], accessibility=None)
        document["components"].append(record)
        self.assertIn("C-SYN-OP-2FA", module.check(document, SCHEMA, POLICY, POLICY_SCHEMA, sources, pin=pin,
                                                   fixture=True).components)
        self.assertFalse(module.printable("C-SYN--B"))

    def test_record_name_is_the_registry_name(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-DRAFT").update(name="Floating banner"),
                           "component.registry_name_mismatch", "C-SYN-DRAFT")

    def test_ids_outside_the_pin_are_readiness_gaps_not_failures(self):
        document = fixture()
        find(document, "components", "C-SYN-DRAFT")["id"] = "C-SYN-NEW"
        gaps = module.readiness(run_check(document))
        self.assertEqual(gaps["readiness.component_not_in_registry"], ["C-SYN-BUTTON-AND", "C-SYN-LOCAL", "C-SYN-NEW"])
        self.assertEqual(gaps["readiness.registry_component_ungoverned"], ["C-SYN-DRAFT", "C-SYN-PINNED"])


class RealRegistryTests(unittest.TestCase):
    def test_pinned_registry_is_read_from_the_local_object_store(self):
        document = {"registry_ref": copy.deepcopy(module.REGISTRY_PIN)}
        components = module.read_registry(document, module.GitSources(ROOT), module.REGISTRY_PIN, False)
        self.assertEqual(len(components), 57)
        self.assertFalse(any(key.startswith(module.SYNTHETIC_PREFIX) for key in components))

    def test_git_is_resolved_outside_the_repository(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name) / "candidate"
        planted = root / "tools"
        planted.mkdir(parents=True)
        name = "git.exe" if os.name == "nt" else "git"
        (planted / name).write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (planted / name).chmod(0o755)
        real_git = Path(shutil.which("git")).parent
        for path in ([str(real_git)], [str(planted), str(real_git)], ["", ".", "tools", str(real_git)],
                     [str(root), str(real_git)]):
            with self.subTest(path=path), mock.patch.dict(os.environ, {"PATH": os.pathsep.join(path)}):
                self.assertEqual(Path(module.trusted_git(root)).parent, real_git)
        outside = Path(folder.name) / "outside"
        outside.mkdir()
        (outside / name).symlink_to(planted / name)  # outside the repository, resolving into it
        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join([str(outside), str(real_git)])}):
            self.assertEqual(Path(module.trusted_git(root)).parent, real_git)
        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join([str(planted), "."])}):
            with self.assertRaises(LookupError):
                module.trusted_git(root)
            with self.assertRaises(module.Refused) as caught:
                module.read_registry({"registry_ref": module.REGISTRY_PIN}, module.GitSources(root),
                                     module.REGISTRY_PIN, False)
            self.assertEqual(str(caught.exception), "registry.unavailable")


class LibraryTests(RuleCase):
    def test_library_set_is_exact(self):
        self.assertRefused(lambda d: d["libraries"].pop(), "library.set_mismatch")

    def test_duplicate_library_is_refused(self):
        self.assertRefused(lambda d: d["libraries"].append(copy.deepcopy(d["libraries"][0])), "library.set_mismatch",
                           "LIB-FOUNDATION")

    def test_kind_follows_the_identifier(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-WEB").update(kind="shared_semantic"),
                           "library.kind_mismatch", "LIB-WEB")

    def test_location_is_the_reserved_file_and_page(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-ADMIN").update(figma_page="Web variants"),
                           "library.location_mismatch", "LIB-ADMIN")

    def test_candidates_have_no_shared_file(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-CANDIDATE").update(
            figma_file="03 - Components library", figma_page="Components"), "library.location_mismatch",
            "LIB-CANDIDATE")

    def test_owner_is_the_artifact_class_accountable_role(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-COMPONENTS").update(owner_role="design_ops"),
                           "library.owner_mismatch", "LIB-COMPONENTS")

    def test_consumption_only_of_lower_layers(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-COMPONENTS")["consumes"].append("LIB-WEB"),
                           "topology.invalid_consumption", "LIB-COMPONENTS", "LIB-WEB")

    def test_platform_libraries_cannot_consume_each_other(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-WEB")["consumes"].append("LIB-ANDROID"),
                           "topology.invalid_consumption", "LIB-WEB", "LIB-ANDROID")

    def test_shared_libraries_never_consume_candidates(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-ADMIN")["consumes"].append("LIB-CANDIDATE"),
                           "topology.invalid_consumption", "LIB-ADMIN", "LIB-CANDIDATE")

    def test_shell_library_has_no_published_release(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-ANDROID").update(status="shell"),
                           "library.status_mismatch", "LIB-ANDROID")

    def test_active_library_has_a_published_release(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-WEB").update(status="active"),
                           "library.status_mismatch", "LIB-WEB")

    def test_frozen_library_keeps_its_releases(self):
        run_check(rolled_back())

    def test_rollback_freezes_its_library(self):
        self.assertRefused(lambda d: roll_back(d, freeze=False), "library.freeze_mismatch", "LIB-COMPONENTS")

    def test_only_a_rollback_freezes_a_library(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-ANDROID").update(status="frozen"),
                           "library.freeze_mismatch", "LIB-ANDROID")

    def test_real_library_is_never_frozen_without_a_rollback(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-WEB").update(status="frozen"),
                           "library.freeze_mismatch", "LIB-WEB", fixture_mode=False)

    def test_platform_library_must_consume_the_semantic_library(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-ANDROID")["consumes"].remove("LIB-COMPONENTS"),
                           "topology.missing_dependency", "LIB-ANDROID", "LIB-COMPONENTS")


class PermissionTests(RuleCase):
    def test_feature_squad_can_never_publish_to_a_shared_library(self):
        for name in module.SHARED:
            with self.subTest(library=name):
                self.assertRefused(lambda d: find(d, "libraries", name)["publish_roles"].append("web_design"),
                                   "permission.feature_squad_publish", name, "web_design")

    def test_only_named_maintainer_roles_publish(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-COMPONENTS")["publish_roles"].append("design_ops"),
                           "permission.publish_not_maintainer", "LIB-COMPONENTS", "design_ops")

    def test_unknown_publish_role_is_refused(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-COMPONENTS")["publish_roles"].append("cdo"),
                           "role.unknown", "LIB-COMPONENTS")

    def test_candidate_library_has_no_publishers(self):
        self.assertRefused(lambda d: find(d, "libraries", "LIB-CANDIDATE")["publish_roles"].append("systems"),
                           "permission.candidate_publish", "LIB-CANDIDATE", "systems")

    def test_public_links_are_disabled(self):
        self.assertRefused(lambda d: d["access"].update(public_links_enabled=True), "access.public_links")

    def test_external_sharing_is_disabled(self):
        self.assertRefused(lambda d: d["access"].update(external_sharing_enabled=True), "access.external_sharing")

    def test_asset_export_is_disabled(self):
        self.assertRefused(lambda d: d["access"].update(asset_export_enabled=True), "access.asset_export")

    def test_offboarding_revokes(self):
        self.assertRefused(lambda d: d["access"].update(offboarding_revokes=False), "access.offboarding_not_revoking")


class TabletopTests(RuleCase):
    def test_tabletop_never_claims_live_verification(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-11").update(live_verified=True), "tabletop.live_claim",
                           "TT-11")

    def test_feature_squad_publish_outcome_is_refused(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-01").update(expected="model_permitted"),
                           "tabletop.outcome_mismatch", "TT-01")

    def test_offboarded_maintainer_is_refused(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-04").update(expected="model_permitted"),
                           "tabletop.outcome_mismatch", "TT-04")

    def test_offboarding_revokes_a_permitted_request(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-11").update(offboarded=True),
                           "tabletop.outcome_mismatch", "TT-11")

    def test_feature_squad_cannot_edit_a_shared_library(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-12").update(expected="model_permitted"),
                           "tabletop.outcome_mismatch", "TT-12")

    def test_public_link_request_is_refused_even_for_maintainers(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-14").update(expected="model_permitted"),
                           "tabletop.outcome_mismatch", "TT-14")

    def test_unknown_role_is_refused(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-13").update(role="cdo"), "role.unknown", "TT-13")

    def test_duplicate_scenario_is_refused(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-02").update(id="TT-01"), "tabletop.duplicate", "TT-01")

    def test_every_shared_library_has_a_feature_squad_publish_case(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-03").update(role="design_ops"),
                           "tabletop.coverage_missing", "LIB-COMPONENTS")

    def test_every_shared_library_has_an_offboarding_case(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-10").update(offboarded=False, expected="model_permitted"),
                           "tabletop.coverage_missing", "LIB-ADMIN")

    def test_offboarding_case_is_a_maintainer(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-10").update(role="design_ops"),
                           "tabletop.coverage_missing", "LIB-ADMIN")

    def test_feature_squad_edits_its_candidate(self):
        policy = module.Policy(POLICY, POLICY_SCHEMA)
        known = {item["id"]: item for item in libraries()}
        request = {"action": "edit", "role": "android_design", "library": "LIB-CANDIDATE", "offboarded": False}
        self.assertEqual(module.decide(request, policy, known), "model_permitted")
        self.assertEqual(module.decide(dict(request, library="LIB-COMPONENTS"), policy, known), "refused")
        self.assertEqual(module.decide(dict(request, offboarded=True), policy, known), "refused")
        self.assertRefused(lambda d: find(d, "tabletop", "TT-16").update(expected="refused"),
                           "tabletop.outcome_mismatch", "TT-16")

    def test_coverage_cases_are_live_requests(self):
        """SC2-02: an offboarded feature-squad publish or candidate edit covers neither required case."""
        self.assertRefused(lambda d: find(d, "tabletop", "TT-03").update(offboarded=True),
                           "tabletop.coverage_missing", "LIB-COMPONENTS")
        self.assertRefused(lambda d: find(d, "tabletop", "TT-16").update(offboarded=True, expected="refused"),
                           "tabletop.coverage_missing", "LIB-CANDIDATE")

    def test_public_link_case_is_required(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-14").update(action="export"),
                           "tabletop.coverage_missing")

    def test_contribution_path_case_is_required(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-16").update(role="systems"),
                           "tabletop.coverage_missing", "LIB-CANDIDATE")

    def test_external_share_case_is_required(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-17").update(action="export"),
                           "tabletop.coverage_missing")

    def test_external_share_is_refused_even_for_maintainers(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-17").update(role="systems", expected="model_permitted"),
                           "tabletop.outcome_mismatch", "TT-17")

    def test_more_tabletop_rows_do_not_change_live_verification_gaps(self):
        document = fixture()
        document["tabletop"].append(dict(find(document, "tabletop", "TT-13"), id="TT-18"))
        self.assertEqual(module.readiness(run_check(document))["readiness.live_verification_missing"],
                         sorted(module.SHARED))

    def test_export_case_is_required(self):
        self.assertRefused(lambda d: find(d, "tabletop", "TT-15").update(action="public_link"),
                           "tabletop.coverage_missing")


class HeldTests(RuleCase):
    def test_direction_reference_is_held_until_docs_76(self):
        self.assertRefused(lambda d: d.update(direction_ref="synthetic direction"), "held.direction_ref",
                           fixture_mode=False)

    def test_token_references_are_held_until_docs_55(self):
        # A dotted token path would be refused as a host shape; docs#55's grammar must be exempted when it lands.
        self.assertRefused(lambda d: find(d, "components", "C-SYN-DRAFT")["token_refs"].append("color-action"),
                           "held.token_refs", "C-SYN-DRAFT")

    def test_real_data_never_publishes_a_release(self):
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@1.0.0").update(status="published"),
                           "held.publication", "LIB-COMPONENTS@1.0.0", fixture_mode=False)

    def test_real_data_never_records_a_cdo_decision(self):
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@1.0.0")["cdo_approval"].update(status="recorded"),
                           "held.cdo_recorded", "LIB-COMPONENTS@1.0.0", fixture_mode=False)

    def test_real_data_never_publishes_a_component(self):
        record = component("C-SYN-PUBLISHED", "Published synthetic", since="1.0.0")
        self.assertRefused(lambda d: d["components"].append(record), "held.publication", "C-SYN-PUBLISHED",
                           fixture_mode=False)

    def test_real_data_refuses_synthetic_component_ids(self):
        draft = fixture()["components"][2]
        self.assertRefused(lambda d: d["components"].append(draft), "id.synthetic_reserved", "C-SYN-DRAFT",
                           fixture_mode=False)

    def test_approval_records_are_exactly_the_required_roles(self):
        self.assertRefused(lambda d: d["approvals"].pop(), "approval.roles_mismatch")

    def test_approvals_are_never_recorded_here(self):
        self.assertRefused(lambda d: d["approvals"][0].update(status="approved"), "schema.invalid")


def append_release(document, name, previous, change, status, **options):
    document["releases"].append(release(name, previous, change, status, **options))


def roll_back(document, freeze=True):
    """Roll back the fixture's LIB-COMPONENTS@2.0.0 to 1.0.0; the rollback freezes the library. The release was
    published first, so it carries the criterion 3 prerequisites: a synthetic recorded CDO decision and a migration
    plan reference that is no longer pending (synthetic fixture values, not a real decision or plan)."""
    find_release(document, "LIB-COMPONENTS@2.0.0").update(
        status="rolled_back", rollback_to="1.0.0", migration_plan_ref="PenniLogic/docs#78",
        cdo_approval={"role": "decision_coordinator", "scope": "shared_system_major", "status": "recorded",
                      "decision_source": copy.deepcopy(DECISION)})
    if freeze:
        find(document, "libraries", "LIB-COMPONENTS")["status"] = "frozen"


def rolled_back():
    document = fixture()
    roll_back(document)
    return document


class ReleaseTests(RuleCase):
    def test_release_key_is_library_and_version(self):
        self.assertRefused(lambda d: d["releases"].append(copy.deepcopy(find_release(d, "LIB-ANDROID@1.0.0"))),
                           "release.duplicate", "LIB-ANDROID@1.0.0")

    def test_candidate_library_never_releases(self):
        self.assertRefused(lambda d: append_release(d, "LIB-CANDIDATE@1.0.0", None, "major", "draft"),
                           "release.candidate_library", "LIB-CANDIDATE@1.0.0")

    def test_previous_version_must_exist(self):
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@2.0.0").update(previous="1.5.0"),
                           "release.previous_unknown", "LIB-COMPONENTS@2.0.0")

    def test_version_must_increase(self):
        self.assertRefused(lambda d: append_release(d, "LIB-COMPONENTS@0.5.0", "1.0.0", "minor", "draft"),
                           "release.version_not_increasing", "LIB-COMPONENTS@0.5.0")

    def test_breaking_change_requires_a_major_version(self):
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@2.0.0").update(change_class="minor"),
                           "release.breaking_not_major", "LIB-COMPONENTS@2.0.0")

    def test_change_class_follows_the_version_step(self):
        self.assertRefused(lambda d: append_release(d, "LIB-ANDROID@1.1.0", "1.0.0", "patch", "draft"),
                           "release.class_mismatch", "LIB-ANDROID@1.1.0")

    def test_minor_step_is_exactly_one(self):
        self.assertRefused(lambda d: append_release(d, "LIB-ANDROID@1.7.0", "1.0.0", "minor", "draft"),
                           "release.class_mismatch", "LIB-ANDROID@1.7.0")

    def test_major_step_is_exactly_one(self):
        self.assertRefused(lambda d: append_release(d, "LIB-ANDROID@9.0.0", "1.0.0", "major", "draft"),
                           "release.class_mismatch", "LIB-ANDROID@9.0.0")

    def test_patch_step_is_exactly_one(self):
        self.assertRefused(lambda d: append_release(d, "LIB-ANDROID@1.0.2", "1.0.0", "patch", "draft"),
                           "release.class_mismatch", "LIB-ANDROID@1.0.2")

    def test_minor_and_patch_steps_pass(self):
        document = fixture()
        append_release(document, "LIB-ANDROID@1.1.0", "1.0.0", "minor", "draft")
        append_release(document, "LIB-ANDROID@1.1.1", "1.1.0", "patch", "draft")
        self.assertEqual(len(run_check(document).releases), 5)

    def test_a_library_has_one_root_release(self):
        self.assertRefused(lambda d: append_release(d, "LIB-ANDROID@2.0.0", None, "major", "draft"),
                           "release.chain_invalid", "LIB-ANDROID@2.0.0")

    def test_real_library_has_one_root_release(self):
        self.assertRefused(lambda d: append_release(d, "LIB-COMPONENTS@3.0.0", None, "major", "draft",
                                                    approval="pending"),
                           "release.chain_invalid", "LIB-COMPONENTS@3.0.0", fixture_mode=False)

    def test_a_release_has_one_successor(self):
        self.assertRefused(lambda d: append_release(d, "LIB-COMPONENTS@1.1.0", "1.0.0", "minor", "draft"),
                           "release.chain_invalid", "LIB-COMPONENTS@1.1.0")

    def test_published_release_never_sits_on_a_pending_major(self):
        def publish_over_pending(document):
            find(document, "components", "C-SYN-CHIP")["deprecation"]["removal_version"] = "3.0.0"
            append_release(document, "LIB-COMPONENTS@2.1.0", "2.0.0", "minor", "published")
        document = fixture()
        find(document, "components", "C-SYN-CHIP")["deprecation"]["removal_version"] = "3.0.0"
        append_release(document, "LIB-COMPONENTS@2.1.0", "2.0.0", "minor", "draft")
        run_check(document)  # control: the same chain with the minor still a draft
        self.assertRefused(publish_over_pending, "release.previous_unpublished", "LIB-COMPONENTS@2.1.0")

    def test_first_release_is_a_major_at_one_or_later(self):
        self.assertRefused(lambda d: append_release(d, "LIB-WEB@0.1.0", None, "major", "draft"),
                           "release.class_mismatch", "LIB-WEB@0.1.0")

    def test_breaking_change_requires_a_migration_plan(self):
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@2.0.0").update(migration_plan_ref=None),
                           "release.migration_plan_missing", "LIB-COMPONENTS@2.0.0")

    def test_migration_plan_reference_grammar(self):
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@2.0.0").update(migration_plan_ref="see plan"),
                           "schema.invalid")

    def test_migration_plan_reference_names_a_public_repository(self):
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@2.0.0").update(
            migration_plan_ref="pending:PenniLogic/figma#5"), "reference.invalid", "LIB-COMPONENTS@2.0.0")

    def test_major_requires_a_cdo_approval_reference(self):
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@2.0.0").update(cdo_approval=None),
                           "release.cdo_approval_missing", "LIB-COMPONENTS@2.0.0")

    def test_cdo_is_decision_coordinator_within_shared_system_major(self):
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@2.0.0")["cdo_approval"].update(
            role="systems"), "schema.invalid", "LIB-COMPONENTS@2.0.0")

    def test_resolved_migration_plan_is_held_in_real_data(self):
        """R3-AV-6: global rule 8 writes null or `pending:` here; a resolved reference is held, like a recorded CDO
        decision."""
        def base():
            document = real()
            append_release(document, "LIB-COMPONENTS@1.1.1", "1.1.0", "patch", "draft",
                           migration="pending:PenniLogic/docs#79")
            return document
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@1.1.1").update(
            migration_plan_ref="PenniLogic/docs#79"), "held.migration_plan_ref", "LIB-COMPONENTS@1.1.1",
            fixture_mode=False, base=base)

    def test_resolved_migration_plan_is_an_unverified_gap(self):
        """R3-AV-6: in fixture mode a resolved reference is admitted but never closes its gap."""
        document = fixture()
        find_release(document, "LIB-COMPONENTS@2.0.0")["migration_plan_ref"] = "PenniLogic/docs#79"
        gaps = module.readiness(run_check(document))
        self.assertEqual((gaps["readiness.migration_plan_pending"], gaps["readiness.migration_plan_unverified"]),
                         ([], ["LIB-COMPONENTS@2.0.0"]))

    def test_cdo_records_only_major_releases(self):
        """DF-R3-01: a minor or patch release carries no coordinator record (each control release has none)."""
        pending = {"role": "decision_coordinator", "scope": "shared_system_major", "status": "pending",
                   "decision_source": None}
        for name, change in (("LIB-ANDROID@1.1.0", "minor"), ("LIB-ANDROID@1.0.1", "patch")):
            with self.subTest(change=change):
                def base(name=name, change=change):
                    document = fixture()
                    append_release(document, name, "1.0.0", change, "draft")
                    return document
                self.assertRefused(lambda d: find_release(d, name).update(cdo_approval=copy.deepcopy(pending)),
                                   "release.cdo_scope_invalid", name, base=base)

    def test_recorded_approval_names_its_decision_source(self):
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@1.0.0")["cdo_approval"].update(
            decision_source=None), "approval.source_mismatch", "LIB-COMPONENTS@1.0.0")

    def test_pending_cdo_approval_blocks_publishing(self):
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@2.0.0").update(status="published"),
                           "release.cdo_pending_published", "LIB-COMPONENTS@2.0.0")

    def test_pending_migration_plan_blocks_publishing(self):
        self.assertRefused(lambda d: append_release(d, "LIB-ANDROID@1.1.0", "1.0.0", "minor", "published",
                                                    migration="pending:PenniLogic/docs#78"),
                           "release.migration_plan_pending_published", "LIB-ANDROID@1.1.0")

    def test_rollback_restores_the_prior_published_version(self):
        model = run_check(rolled_back())
        self.assertEqual(model.releases[("LIB-COMPONENTS", "1.0.0")]["status"], "published")
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@2.0.0").update(rollback_to=None),
                           "release.rollback_target", "LIB-COMPONENTS@2.0.0", base=rolled_back)

    def test_rollback_target_is_the_published_previous_release(self):
        def chain(rolled_back_to, middle="published"):
            def build(document):
                append_release(document, "LIB-ANDROID@1.1.0", "1.0.0", "minor", middle)
                append_release(document, "LIB-ANDROID@1.2.0", "1.1.0", "minor", "rolled_back")
                find_release(document, "LIB-ANDROID@1.2.0")["rollback_to"] = rolled_back_to
                find(document, "libraries", "LIB-ANDROID")["status"] = "frozen"
            return build
        # A rolled-back release was published, so it never sits on a draft (SC2-01).
        self.assertRefused(chain("1.1.0", middle="draft"), "release.previous_unpublished", "LIB-ANDROID@1.2.0")

        def two_back():
            document = fixture()
            chain("1.1.0")(document)
            return document
        # SC2-02 M4: restoring a version two steps back skips the published 1.1.0.
        self.assertRefused(lambda d: find_release(d, "LIB-ANDROID@1.2.0").update(rollback_to="1.0.0"),
                           "release.rollback_target", "LIB-ANDROID@1.2.0", base=two_back)

    def test_nothing_is_published_after_a_rollback(self):
        def publish_after(document):
            roll_back(document)
            append_release(document, "LIB-COMPONENTS@2.0.1", "2.0.0", "patch", "published")
        document = rolled_back()
        append_release(document, "LIB-COMPONENTS@2.0.1", "2.0.0", "patch", "draft")
        run_check(document)  # control: a restoration draft above the rolled-back version
        self.assertRefused(publish_after, "release.previous_unpublished", "LIB-COMPONENTS@2.0.1")

    def test_rolled_back_release_met_the_publication_prerequisites(self):
        """SC2-01: a rolled-back release was published, so a pending CDO decision or migration plan is refused."""
        def pending_cdo(document):
            find_release(document, "LIB-COMPONENTS@2.0.0")["cdo_approval"].update(status="pending",
                                                                                 decision_source=None)
        self.assertRefused(pending_cdo, "release.cdo_pending_published", "LIB-COMPONENTS@2.0.0", base=rolled_back)
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@2.0.0").update(
            migration_plan_ref="pending:PenniLogic/docs#78"), "release.migration_plan_pending_published",
            "LIB-COMPONENTS@2.0.0", base=rolled_back)

    def test_rollback_target_only_on_rolled_back_releases(self):
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@2.0.0").update(rollback_to="1.0.0"),
                           "release.rollback_target", "LIB-COMPONENTS@2.0.0")


def button(document):
    return find(document, "components", "C-SYN-BUTTON")


def chip_deprecation(document):
    return find(document, "components", "C-SYN-CHIP")["deprecation"]


def first_property(document):
    return button(document)["properties"][0]


class ComponentTests(RuleCase):
    def test_duplicate_component_id_is_refused(self):
        self.assertRefused(lambda d: d["components"].append(copy.deepcopy(find(d, "components", "C-SYN-DRAFT"))),
                           "id.duplicate", "C-SYN-DRAFT")

    def test_foundation_library_holds_no_components(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-DRAFT").update(library="LIB-FOUNDATION"),
                           "component.library_invalid", "C-SYN-DRAFT")

    def test_candidates_stay_unpublished(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-LOCAL").update(status="published"),
                           "component.candidate_published", "C-SYN-LOCAL")

    def test_platform_variant_supports_only_its_platform(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-BUTTON-AND").update(platforms=["web"]),
                           "component.platform_mismatch", "C-SYN-BUTTON-AND")

    def test_pinned_component_keeps_the_registry_platforms(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-DRAFT").update(platforms=["web", "admin"]),
                           "component.registry_platform_mismatch", "C-SYN-DRAFT")
        self.assertRefused(lambda d: button(d).update(platforms=["android", "web"]),
                           "component.registry_platform_mismatch", "C-SYN-BUTTON")

    def test_unknown_owner_role_is_refused(self):
        self.assertRefused(lambda d: button(d).update(owner_role="cdo"), "role.unknown", "C-SYN-BUTTON")

    def test_shared_component_owner_is_a_maintainer(self):
        self.assertRefused(lambda d: button(d).update(owner_role="android_design"),
                           "component.owner_not_maintainer", "C-SYN-BUTTON")

    def test_property_contract(self):
        mutations = (
            lambda d: first_property(d).update(values=["primary"], default=None),
            lambda d: first_property(d).update(default="tertiary"),
            lambda d: first_property(d).update(type="boolean", default=None),
            lambda d: first_property(d).update(type="slot", values=[], default="primary"),
            lambda d: button(d)["properties"].append(copy.deepcopy(first_property(d))),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                self.assertRefused(mutate, "component.property_contract", "C-SYN-BUTTON")

    def test_property_names_differing_only_in_case_collide(self):
        self.assertRefused(lambda d: button(d)["properties"].append(
            {"name": "emphasiS", "type": "text", "values": [], "default": None, "required": False}),
            "component.property_contract", "C-SYN-BUTTON")

    def test_variant_supports_only_its_parents_platforms(self):
        self.assertRefused(lambda d: d["components"].append(component(
            "C-SYN-DRAFT-AND", "Android notice", library_id="LIB-ANDROID", status="draft", role="notice strip",
            platforms=["android"], variant_of="C-SYN-DRAFT", since=None, properties=[])),
            "component.variant_invalid", "C-SYN-DRAFT-AND")

    def test_published_variant_needs_a_published_parent(self):
        def web_active():
            document = fixture()
            find(document, "libraries", "LIB-WEB")["status"] = "active"
            append_release(document, "LIB-WEB@1.0.0", None, "major", "published")
            return document
        self.assertRefused(lambda d: d["components"].append(component(
            "C-SYN-DRAFT-WEB", "Web notice", library_id="LIB-WEB", platforms=["web"], variant_of="C-SYN-DRAFT",
            role="notice strip", properties=[{"name": "tone", "type": "enum", "values": ["info", "warning"],
                                              "default": "info", "required": True}])),
            "component.variant_parent_unpublished", "C-SYN-DRAFT-WEB", base=web_active)

    def test_variant_names_a_shared_semantic_component(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-BUTTON-AND").update(variant_of=None),
                           "component.variant_invalid", "C-SYN-BUTTON-AND")
        self.assertRefused(lambda d: find(d, "components", "C-SYN-BUTTON-AND").update(variant_of="C-SYN-LOCAL"),
                           "component.variant_invalid", "C-SYN-BUTTON-AND")

    def test_variant_of_a_deprecated_parent_is_deprecated(self):
        """R3-AV-5: a published variant never hangs on a deprecated parent; the control's variant of the deprecated
        C-SYN-CHIP is deprecated in its own library (replacement there, removal a later LIB-ANDROID major)."""
        def deprecated_variant():
            document = fixture()
            variant = component("C-SYN-CHIP-AND", "Android chip", library_id="LIB-ANDROID", status="deprecated",
                                role="filter toggle", platforms=["android"], variant_of="C-SYN-CHIP", properties=[
                                    {"name": "selected", "type": "boolean", "values": [], "default": "false",
                                     "required": False}])
            variant["deprecation"] = {"replacement": "C-SYN-BUTTON-AND", "removal_version": "2.0.0",
                                      "available_until_removal": True}
            document["components"].append(variant)
            return document
        self.assertRefused(lambda d: find(d, "components", "C-SYN-CHIP-AND").update(status="published",
                                                                                   deprecation=None),
                           "component.variant_parent_deprecated", "C-SYN-CHIP-AND", base=deprecated_variant)

    def test_only_platform_libraries_hold_variants(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-DRAFT").update(variant_of="C-SYN-BUTTON"),
                           "component.variant_invalid", "C-SYN-DRAFT")


class PublishedComponentTests(RuleCase):
    """Criterion 1: owner, description, property contract, accessibility behaviour and supported platforms."""

    def test_published_component_completeness(self):
        cases = (
            ("owner_role", None, "published.owner_missing"),
            ("description", None, "published.description_missing"),
            ("semantic_role", None, "published.semantic_role_missing"),
            ("properties", [], "published.properties_missing"),
            ("accessibility", None, "published.accessibility_missing"),
            ("platforms", [], "published.platforms_missing"),
            ("since_version", None, "published.release_missing"),
            ("since_version", "2.0.0", "published.release_missing"),
        )
        for field, value, rule in cases:
            with self.subTest(field=field, value=value):
                self.assertRefused(lambda d: button(d).update({field: value}), rule, "C-SYN-BUTTON")

    def test_placeholder_text_is_missing_text(self):
        """AV2-4: a punctuation-only placeholder satisfies no criterion 1 field."""
        cases = (("name", "published.name_missing"), ("description", "published.description_missing"),
                 ("semantic_role", "published.semantic_role_missing"))
        for field, rule in cases:
            with self.subTest(field=field):
                self.assertRefused(lambda d: button(d).update({field: "-"}), rule, "C-SYN-BUTTON")
        for field in ("role", "accessible_name", "focus", "announcements"):
            with self.subTest(field=field):
                self.assertRefused(lambda d: button(d)["accessibility"].update({field: "-"}),
                                   "published.accessibility_missing", "C-SYN-BUTTON")

    def test_drafts_may_be_incomplete(self):
        draft = find(run_check(fixture()).document, "components", "C-SYN-DRAFT")
        self.assertIsNone(draft["owner_role"])
        self.assertEqual(draft["properties"], [])


class DeprecationTests(RuleCase):
    """Criterion 4: a replacement, a removal version and continued availability through migration."""

    def test_deprecation_only_on_deprecated_components(self):
        self.assertRefused(lambda d: button(d).update(deprecation=copy.deepcopy(chip_deprecation(d))),
                           "deprecation.unexpected", "C-SYN-BUTTON")

    def test_deprecated_component_records_its_deprecation(self):
        self.assertRefused(lambda d: button(d).update(status="deprecated"), "deprecation.missing", "C-SYN-BUTTON")

    def test_replacement_is_required(self):
        self.assertRefused(lambda d: chip_deprecation(d).update(replacement=None), "deprecation.replacement_missing",
                           "C-SYN-CHIP")

    def test_replacement_is_another_published_component_of_the_library(self):
        for replacement in ("C-SYN-CHIP", "C-SYN-DRAFT", "C-SYN-ABSENT", "C-SYN-BUTTON-AND"):
            with self.subTest(replacement=replacement):
                self.assertRefused(lambda d: chip_deprecation(d).update(replacement=replacement),
                                   "deprecation.replacement_invalid", "C-SYN-CHIP")

    def test_replacement_supports_every_deprecated_platform(self):
        """SC3-02/R3-AV-4: consumers on each platform of the deprecated record can migrate to its replacement (the
        control's replacement supports more platforms than the deprecated record)."""
        def android_deprecation():
            document = fixture()
            document["components"].append(component("C-SYN-PILL", "Pill", role="mode selector", properties=[
                {"name": "label", "type": "text", "values": [], "default": None, "required": True}]))
            old = component("C-SYN-OLD", "Legacy toggle", status="deprecated", role="legacy setting",
                            platforms=["android"], properties=[
                                {"name": "pressed", "type": "boolean", "values": [], "default": "false",
                                 "required": False}])
            old["deprecation"] = {"replacement": "C-SYN-PILL", "removal_version": "2.0.0",
                                  "available_until_removal": True}
            document["components"].append(old)
            return document
        self.assertRefused(lambda d: find(d, "components", "C-SYN-PILL").update(platforms=["web"]),
                           "deprecation.replacement_invalid", "C-SYN-OLD", base=android_deprecation)

    def test_recorded_removal_release_is_breaking(self):
        """AV2-3: the removal release a deprecation names, when recorded here, is declared breaking."""
        self.assertRefused(lambda d: find_release(d, "LIB-COMPONENTS@2.0.0").update(breaking=False,
                                                                                    migration_plan_ref=None),
                           "deprecation.removal_not_breaking", "C-SYN-CHIP")

    def test_replacement_is_not_itself_deprecated(self):
        """SC2-02 N1: a deprecated component never names a deprecated replacement."""
        def second_deprecation():
            document = fixture()
            old = component("C-SYN-OLD", "Legacy toggle", status="deprecated", role="legacy setting", properties=[
                {"name": "pressed", "type": "boolean", "values": [], "default": "false", "required": False}])
            old["deprecation"] = {"replacement": "C-SYN-BUTTON", "removal_version": "2.0.0",
                                  "available_until_removal": True}
            document["components"].append(old)
            return document
        self.assertRefused(lambda d: find(d, "components", "C-SYN-OLD")["deprecation"].update(
            replacement="C-SYN-CHIP"), "deprecation.replacement_invalid", "C-SYN-OLD", base=second_deprecation)

    def test_removal_version_is_required(self):
        self.assertRefused(lambda d: chip_deprecation(d).update(removal_version=None),
                           "deprecation.removal_version_missing", "C-SYN-CHIP")

    def test_removal_version_is_a_later_major(self):
        for removal in ("1.0.0", "2.1.0", "0.9.0"):
            with self.subTest(removal=removal):
                self.assertRefused(lambda d: chip_deprecation(d).update(removal_version=removal),
                                   "deprecation.removal_version_invalid", "C-SYN-CHIP")
        document = fixture()
        chip_deprecation(document).update(removal_version="3.0.0")
        run_check(document)

    def test_deprecated_component_stays_available_until_removal(self):
        self.assertRefused(lambda d: chip_deprecation(d).update(available_until_removal=False),
                           "deprecation.unavailable", "C-SYN-CHIP")


def local(document):
    return find(document, "components", "C-SYN-LOCAL")


LABEL = [{"name": "label", "type": "text", "values": [], "default": None, "required": True}]
SLOT = [{"name": "items", "type": "slot", "values": [], "default": None, "required": True}]


def with_web_library():
    """The fixture with LIB-WEB active at a published 1.0.0, so Web variants may be drafted or published."""
    document = fixture()
    find(document, "libraries", "LIB-WEB")["status"] = "active"
    document["releases"].append(release("LIB-WEB@1.0.0", None, "major", "published"))
    return document


class DuplicateTests(RuleCase):
    """Criterion 2: a local duplicate of a published semantic component is rejected by the registry lint."""

    def test_same_semantic_role_is_a_duplicate(self):
        self.assertRefused(lambda d: local(d).update(semantic_role="Primary  Action"), "duplicate.semantic_component",
                           "C-SYN-LOCAL", "C-SYN-BUTTON")

    def test_same_normalized_name_is_a_duplicate(self):
        self.assertRefused(lambda d: local(d).update(name="BUTTON"), "duplicate.semantic_component", "C-SYN-LOCAL",
                           "C-SYN-BUTTON")

    def test_published_signature_with_a_shared_word_is_a_duplicate(self):
        def superset(document):
            local(document).update(name="Action card", properties=[
                *copy.deepcopy(button(document)["properties"]),
                {"name": "body", "type": "slot", "values": [], "default": None, "required": True}])
        self.assertRefused(superset, "duplicate.semantic_component", "C-SYN-LOCAL", "C-SYN-BUTTON")

    def test_equal_signature_alone_is_not_a_duplicate(self):
        document = fixture()
        document["components"].append(component("C-SYN-LINK", "Link", role="navigation link", properties=[
            {"name": "emphasis", "type": "enum", "values": ["subtle", "strong"], "default": "subtle",
             "required": True}]))
        self.assertIn("C-SYN-LINK", run_check(document).components)

    def test_word_order_does_not_hide_a_duplicate(self):
        self.assertRefused(lambda d: local(d).update(semantic_role="action primary"), "duplicate.semantic_component",
                           "C-SYN-LOCAL", "C-SYN-BUTTON")

    def test_plurals_do_not_hide_a_duplicate(self):
        self.assertRefused(lambda d: local(d).update(name="Buttons"), "duplicate.semantic_component", "C-SYN-LOCAL",
                           "C-SYN-BUTTON")

    def test_copy_of_a_published_platform_variant_is_a_duplicate(self):
        def distinct_variant():
            document = fixture()
            find(document, "components", "C-SYN-BUTTON-AND").update(
                name="Android floating button", semantic_role="floating primary action", properties=[
                    {"name": "extended", "type": "boolean", "values": [], "default": "false", "required": False}])
            return document

        def copy_variant(document):
            variant = find(document, "components", "C-SYN-BUTTON-AND")
            local(document).update(name=variant["name"], semantic_role=variant["semantic_role"],
                                   properties=copy.deepcopy(variant["properties"]))
        self.assertRefused(copy_variant, "duplicate.semantic_component", "C-SYN-LOCAL", "C-SYN-BUTTON-AND",
                           base=distinct_variant)

    def test_twin_platform_variants_are_duplicates(self):
        def twin(document):
            other = copy.deepcopy(find(document, "components", "C-SYN-BUTTON-AND"))
            other["id"] = "C-SYN-BUTTON-ANDTWO"
            document["components"].append(other)
        self.assertRefused(twin, "duplicate.semantic_component", "C-SYN-BUTTON-AND", "C-SYN-BUTTON-ANDTWO")

    def test_replacement_pair_sharing_a_role_is_exempt(self):
        """AV2-2 F2b, DF-R2-01: the replacement's variant (C-SYN-BUTTON-AND) stays in the document."""
        document = fixture()
        run_check(copy.deepcopy(document))
        find(document, "components", "C-SYN-CHIP")["semantic_role"] = "primary action"  # shared with its replacement
        self.assertEqual(run_check(document).components["C-SYN-CHIP"]["semantic_role"], "primary action")

    def test_duplicate_of_a_deprecated_published_component(self):
        self.assertRefused(lambda d: local(d).update(semantic_role="filter toggle"), "duplicate.semantic_component",
                           "C-SYN-LOCAL", "C-SYN-CHIP")

    def test_platform_library_duplicate_without_variant_link(self):
        self.assertRefused(lambda d: d["components"].append(component(
            "C-SYN-WEB-ACTION", "Web action", library_id="LIB-WEB", status="draft", role="primary action",
            platforms=["web"], variant_of="C-SYN-DRAFT", since=None)), "duplicate.semantic_component",
            "C-SYN-WEB-ACTION", "C-SYN-BUTTON")

    def test_spelling_does_not_hide_a_duplicate(self):
        """AV2-1, DF-R2-02: camelCase or run-together spellings, -es/-ies plurals and dropped function words."""
        def published(identifier, name, role, properties):
            def build():
                document = fixture()
                document["components"].append(component(identifier, name, role=role, properties=properties))
                return document
            return build
        field = published("C-SYN-FIELD", "Text field", "text entry", LABEL)
        cases = (
            (field, "C-SYN-FIELD", dict(name="TextField")),
            (field, "C-SYN-FIELD", dict(semantic_role="TextEntry")),
            (fixture, "C-SYN-BUTTON", dict(semantic_role="PrimaryAction")),
            (published("C-SYN-SWITCH", "Switch", "boolean switch", LABEL), "C-SYN-SWITCH", dict(name="Switches")),
            (published("C-SYN-CATEGORY", "Category", "grouping heading", LABEL), "C-SYN-CATEGORY",
             dict(name="Categories")),
            (published("C-SYN-ACTIONS", "Primary secondary tonal text and icon actions", "command trigger", LABEL),
             "C-SYN-ACTIONS", dict(name="Primary secondary tonal text icon actions")),
        )
        for base, other, change in cases:
            with self.subTest(change=change):
                self.assertRefused(lambda d: local(d).update(change), "duplicate.semantic_component", "C-SYN-LOCAL",
                                   other, base=base)

    def test_function_words_alone_are_not_shared_words(self):
        """DF-R2-02: two names sharing only 'and', with an equal signature, are not duplicates."""
        document = fixture()
        document["components"] += [
            component("C-SYN-CONSENT", "Purpose consent and withdrawal", role="consent request", properties=LABEL),
            component("C-SYN-AMOUNT", "Currency amount balance and delta", role="money figure", properties=LABEL)]
        self.assertIn("C-SYN-AMOUNT", run_check(document).components)

    def test_sibling_platform_variants_share_their_parents_semantics(self):
        """AV2-2 F2a, DF-R2-01: Android and Web variants of one parent share its role and contract."""
        document = with_web_library()
        run_check(copy.deepcopy(document))
        for status in ("draft", "published"):
            with self.subTest(status=status):
                trial = copy.deepcopy(document)
                trial["components"].append(component(
                    "C-SYN-BUTTON-WEB", "Web button", library_id="LIB-WEB", status=status, platforms=["web"],
                    variant_of="C-SYN-BUTTON", role="primary action", since="1.0.0" if status != "draft" else None))
                self.assertIn("C-SYN-BUTTON-WEB", run_check(trial).components)

    def test_single_platform_counterparts_are_compared_only_on_a_shared_platform(self):
        """DF-R2-01: single-platform records of one library with disjoint platforms (the C-NAV-* pair) pass."""
        def counterparts():
            document = fixture()
            document["components"] += [
                component("C-SYN-NAV-ANDROID", "Android navigation", role="primary navigation", platforms=["android"],
                          properties=SLOT),
                component("C-SYN-NAV-WEB", "Web navigation", role="primary navigation", platforms=["web"],
                          properties=SLOT)]
            return document
        self.assertRefused(lambda d: find(d, "components", "C-SYN-NAV-WEB").update(platforms=["web", "android"]),
                           "duplicate.semantic_component", "C-SYN-NAV-ANDROID", "C-SYN-NAV-WEB", base=counterparts)

    def test_candidates_are_compared_across_platforms(self):
        """A candidate is never a cross-platform counterpart: the contribution lint compares every platform."""
        def distinct_variant():
            document = fixture()
            find(document, "components", "C-SYN-BUTTON-AND").update(
                name="Android floating button", semantic_role="floating primary action")
            return document
        # The candidate is Web only and the published variant Android only: disjoint, and still compared.
        self.assertRefused(lambda d: local(d).update(platforms=["web"], name="Android floating button"),
                           "duplicate.semantic_component", "C-SYN-LOCAL", "C-SYN-BUTTON-AND", base=distinct_variant)

    def test_variants_and_replacements_are_not_duplicates(self):
        model = run_check(fixture())
        self.assertEqual(model.components["C-SYN-BUTTON-AND"]["semantic_role"],
                         model.components["C-SYN-BUTTON"]["semantic_role"])
        self.assertEqual(model.components["C-SYN-CHIP"]["deprecation"]["replacement"], "C-SYN-BUTTON")

    def test_semantic_duplicates_within_the_shared_library(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-DRAFT").update(semantic_role="primary action"),
                           "duplicate.semantic_component", "C-SYN-DRAFT", "C-SYN-BUTTON")


class ContributionTests(RuleCase):
    def test_candidate_status_belongs_to_the_candidate_library(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-DRAFT").update(status="candidate"),
                           "contribution.candidate_library", "C-SYN-DRAFT")

    def test_candidate_library_holds_only_candidates(self):
        self.assertRefused(lambda d: local(d).update(status="draft"), "contribution.candidate_library", "C-SYN-LOCAL")

    def test_candidate_names_its_proposal_branch(self):
        self.assertRefused(lambda d: local(d).update(proposal_branch=None), "contribution.candidate_incomplete",
                           "C-SYN-LOCAL")

    def test_candidate_names_its_proposing_owner(self):
        self.assertRefused(lambda d: local(d).update(owner_role=None), "contribution.candidate_incomplete",
                           "C-SYN-LOCAL")

    def test_candidate_cannot_omit_its_semantic_role(self):
        self.assertRefused(lambda d: local(d).update(name="Primary CTA", semantic_role=None),
                           "contribution.candidate_incomplete", "C-SYN-LOCAL")

    def test_candidate_cannot_write_a_placeholder_name_or_role(self):
        """AV2-1 F1b: a '-' name or role carries no word for the duplicate lint to compare."""
        for field in ("name", "semantic_role"):
            with self.subTest(field=field):
                self.assertRefused(lambda d: local(d).update({field: "-"}), "contribution.candidate_incomplete",
                                   "C-SYN-LOCAL")

    def test_candidate_cannot_omit_its_property_contract(self):
        self.assertRefused(lambda d: local(d).update(properties=[]), "contribution.candidate_incomplete",
                           "C-SYN-LOCAL")

    def test_proposal_branches_belong_to_candidates(self):
        self.assertRefused(lambda d: find(d, "components", "C-SYN-DRAFT").update(
            proposal_branch="T-DSY-02__systems__draft-banner"), "contribution.branch_outside_candidates",
            "C-SYN-DRAFT")

    def test_branch_follows_the_design_operations_grammar(self):
        for branch in ("feature/local-card", "T-DSY-02__marketing__local-card", "T-DSY-02__android__Local"):
            with self.subTest(branch=branch):
                self.assertRefused(lambda d: local(d).update(proposal_branch=branch), "contribution.branch_grammar",
                                   "C-SYN-LOCAL")

    def test_branch_squad_is_the_owner_roles_squad(self):
        self.assertRefused(lambda d: local(d).update(proposal_branch="T-DSY-02__web__local-card"),
                           "contribution.squad_mismatch", "C-SYN-LOCAL")
        self.assertRefused(lambda d: local(d).update(owner_role="web_design"), "contribution.squad_mismatch",
                           "C-SYN-LOCAL")

    def test_candidate_owner_is_a_feature_squad(self):
        # Each role keeps its own squad's branch, so only the owner rule can refuse it; decide() refuses it the edit.
        for role, squad in (("research", "research"), ("service_design", "service"), ("content", "content"),
                            ("design_qa", "qa"), ("design_ops", "design-ops"), ("systems", "systems")):
            with self.subTest(role=role):
                self.assertRefused(lambda d: local(d).update(
                    owner_role=role, proposal_branch=f"T-DSY-02__{squad}__local-card"),
                    "contribution.owner_not_squad", "C-SYN-LOCAL")
        for role in ("android_design", "web_design", "admin_design"):
            with self.subTest(role=role):
                document = fixture()
                squad = role.removesuffix("_design")
                local(document).update(owner_role=role, proposal_branch=f"T-DSY-02__{squad}__local-card")
                run_check(document)

    def test_proposal_branch_is_not_reused(self):
        def reuse(document):
            other = copy.deepcopy(local(document))
            other.update(id="C-SYN-LOCAL-TWO", name="Other card", semantic_role="other summary", properties=[
                {"name": "content", "type": "slot", "values": [], "default": None, "required": True}])
            document["components"].append(other)
        self.assertRefused(reuse, "contribution.branch_duplicate", "C-SYN-LOCAL-TWO")


class CommandLineTests(unittest.TestCase):
    """main() in process against a temporary root outside the repository; the registry comes from memory."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        (self.root / "governance").mkdir()
        for name in (module.SCHEMA, module.GATES, module.gates.SCHEMA):
            (self.root / name).write_bytes((ROOT / name).read_bytes())
        self.write(real())
        for patcher in (mock.patch.object(module, "ROOT", self.root),
                        mock.patch.object(module, "REGISTRY_PIN", REAL_PIN),
                        mock.patch.object(module, "GitSources", lambda root: REAL_SOURCES)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def write(self, document):
        (self.root / module.DATA).write_bytes(encode(document))

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_default_mode_is_not_green_with_exact_counts(self):
        code, out, err = self.run_main()
        self.assertEqual((code, err), (1, ""))
        lines = out.splitlines()
        self.assertEqual(lines[0], module.NOT_GREEN)
        self.assertEqual(lines[1], module.structure_line(run_check(real(), False)))
        self.assertEqual(lines[2:], [
            "readiness.direction_missing: 1", "readiness.tokens_unpublished: 1", "readiness.approval_not_recorded: 5",
            "readiness.cdo_decision_pending: 1", "readiness.cdo_decision_unverified: 0",
            "readiness.migration_plan_pending: 0", "readiness.migration_plan_unverified: 0",
            "readiness.live_verification_missing: 5", "readiness.continuity_unchecked: 5",
            "readiness.component_not_in_registry: 0",
            "readiness.registry_component_ungoverned: 0",
        ])

    def test_structure_mode_passes_without_readiness(self):
        code, out, err = self.run_main("--structure")
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(out.endswith("; readiness not evaluated.\n"))

    def test_refusal_prints_only_the_rule(self):
        document = real()
        document["access"]["public_links_enabled"] = True
        self.write(document)
        self.assertEqual(self.run_main("--structure"), (1, "", "Figma library check refused: access.public_links\n"))

    def test_real_mode_refuses_synthetic_components(self):
        document = real()
        document["components"].append(fixture()["components"][2])
        self.write(document)
        self.assertEqual(self.run_main(), (1, "", "Figma library check refused: id.synthetic_reserved C-SYN-DRAFT\n"))

    def test_mirror_prints_the_generated_section_of_validated_data_only(self):
        expected = module.render_mirror(run_check(real(), False))
        self.assertEqual(self.run_main("--mirror"), (0, expected, ""))
        document = real()
        document["tabletop"][0]["live_verified"] = True
        self.write(document)
        self.assertEqual(self.run_main("--mirror"), (1, "", "Figma library check refused: tabletop.live_claim TT-01\n"))

    def test_mirror_and_structure_are_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            module.main(["--mirror", "--structure"])
        self.assertEqual(caught.exception.code, 2)

    def test_missing_or_duplicate_key_input_fails_closed(self):
        (self.root / module.DATA).write_bytes(b'{"schema_version": 1, "schema_version": 1}\n')
        self.assertEqual(self.run_main(), (1, "", "Figma library check refused: input.unreadable_or_invalid\n"))
        (self.root / module.DATA).unlink()
        self.assertEqual(self.run_main(), (1, "", "Figma library check refused: input.unreadable_or_invalid\n"))

    def test_unexpected_errors_fail_closed_without_echo(self):
        token = planted_token()
        for error in (KeyError(token), TypeError(token), AttributeError(token), IndexError(token)):
            with self.subTest(error=type(error).__name__), mock.patch.object(module, "load_and_check",
                                                                              side_effect=error):
                self.assertEqual(self.run_main(),
                                 (1, "", "Figma library check refused: input.unreadable_or_invalid\n"))


class PublishedDataTests(unittest.TestCase):
    """The committed governance/figma-libraries.json against the real pinned registry (read from local Git)."""

    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / module.DATA).read_bytes()
        cls.model = module.load_and_check(ROOT)

    def test_published_data_passes_structure(self):
        model = self.model
        self.assertEqual(tuple(model.libraries), module.LIBRARIES)
        self.assertEqual({item["status"] for item in model.libraries.values()}, {"shell"})
        self.assertEqual(sorted(model.releases), [(name, "1.0.0") for name in sorted(module.SHARED)])
        self.assertEqual({item["status"] for item in model.releases.values()}, {"draft"})
        self.assertEqual(len(model.components), 57)
        self.assertEqual({(item["library"], item["status"]) for item in model.components.values()},
                         {("LIB-COMPONENTS", "draft")})
        self.assertEqual(len(model.document["tabletop"]), 29)
        self.assertFalse(any(item["live_verified"] for item in model.document["tabletop"]))
        self.assertIsNone(model.document["direction_ref"])

    def test_every_pinned_component_is_an_unpublished_draft_with_its_platforms(self):
        self.assertEqual(sorted(self.model.components), sorted(self.model.pinned))
        for identifier, component in self.model.components.items():
            with self.subTest(component=identifier):
                self.assertEqual(set(component["platforms"]), set(self.model.pinned[identifier][0]))
                self.assertEqual(component["name"], self.model.pinned[identifier][1])
                self.assertEqual(component["token_refs"], [])
                self.assertIsNone(component["since_version"])

    def test_published_readiness_gaps_are_exact(self):
        self.assertEqual(module.readiness(self.model), {
            "readiness.direction_missing": ["PenniLogic/docs#76"],
            "readiness.tokens_unpublished": ["PenniLogic/docs#55"],
            "readiness.approval_not_recorded": sorted(module.APPROVAL_ROLES),
            "readiness.cdo_decision_pending": sorted(f"{name}@1.0.0" for name in module.SHARED),
            "readiness.cdo_decision_unverified": [],
            "readiness.migration_plan_pending": [],
            "readiness.migration_plan_unverified": [],
            "readiness.live_verification_missing": sorted(module.SHARED),
            "readiness.continuity_unchecked": sorted(module.SHARED),
            "readiness.component_not_in_registry": [],
            "readiness.registry_component_ungoverned": [],
        })

    def test_published_data_bytes_are_canonical(self):
        self.assertEqual(self.raw, encode(json.loads(self.raw.decode("utf-8"))))

    def test_governance_document_mirrors_the_json(self):
        text = (ROOT / module.MIRROR).read_bytes().decode("utf-8")
        self.assertNotIn("\r", text)
        self.assertFalse(text.startswith("\ufeff"))
        self.assertTrue(text.isascii() and text.endswith("\n") and not text.endswith("\n\n"))
        self.assertEqual(module.mirror_section(text), module.render_mirror(self.model))

    def test_command_line_reports_not_green_with_exact_counts(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main([])
        lines = out.getvalue().splitlines()
        self.assertEqual((code, err.getvalue(), lines[0]), (1, "", module.NOT_GREEN))
        self.assertEqual(lines[2:], [
            "readiness.direction_missing: 1", "readiness.tokens_unpublished: 1",
            "readiness.approval_not_recorded: 5", "readiness.cdo_decision_pending: 5",
            "readiness.cdo_decision_unverified: 0", "readiness.migration_plan_pending: 0",
            "readiness.migration_plan_unverified: 0",
            "readiness.live_verification_missing: 5", "readiness.continuity_unchecked: 5",
            "readiness.component_not_in_registry: 0", "readiness.registry_component_ungoverned: 0",
        ])


class MirrorTests(unittest.TestCase):
    """The generated section: deterministic, escaped, and located only between exactly one pair of markers."""

    def render(self, document):
        return module.render_mirror(run_check(document))

    def test_rendering_is_deterministic_and_round_trips(self):
        text = self.render(fixture())
        self.assertEqual(text, self.render(copy.deepcopy(fixture())))
        self.assertEqual(module.mirror_section("# Title\n\n" + text + "\nAfter.\n"), text)

    def test_hostile_names_cannot_break_cells_or_markers(self):
        document = fixture()
        self.render(copy.deepcopy(document))
        # The full end marker names a dotted file and is refused as content; its opening cannot pass either.
        local(document)["name"] = "A | b `c` *d* [e] &amp; <!-- END GENERATED: x -->"  # not pinned: no registry name
        text = self.render(document)
        self.assertEqual((text.count(module.MIRROR_BEGIN), text.count(module.MIRROR_END)), (1, 1))
        row = next(line for line in text.splitlines() if line.startswith("| C-SYN-LOCAL |"))
        self.assertIn("A \\| b \\`c\\` \\*d\\* \\[e\\] &amp;amp; &lt;!-- END GENERATED", row)
        # Eight columns: nine unescaped pipes.
        self.assertEqual(len(re.findall(r"(?<!\\)\|", row)), 9)
        self.assertEqual(module.mirror_section(text), text)

    def test_emphasis_and_strikethrough_are_escaped(self):
        document = fixture()
        self.render(copy.deepcopy(document))
        local(document)["name"] = "Draft _banner_ ~~old~~"
        row = next(line for line in self.render(document).splitlines() if line.startswith("| C-SYN-LOCAL |"))
        self.assertIn("| Draft \\_banner\\_ \\~\\~old\\~\\~ |", row)
        self.assertIn("| android_design |", row)  # an intraword underscore cannot open emphasis

    def test_missing_or_ambiguous_markers_have_no_section(self):
        text = self.render(fixture())
        self.assertEqual(module.mirror_section(text), text)
        for broken in (text.replace(module.MIRROR_END, ""), text + text, text.rstrip("\n"),
                       module.MIRROR_END + "\n" + text.replace(module.MIRROR_END + "\n", ""), ""):
            with self.subTest(broken=broken[-40:]):
                self.assertIsNone(module.mirror_section(broken))

    def test_drift_is_detected(self):
        document = fixture()
        text = self.render(copy.deepcopy(document))
        self.assertEqual(module.mirror_section(text), self.render(copy.deepcopy(document)))
        find(document, "tabletop", "TT-01")["role"] = "web_design"
        self.assertNotEqual(module.mirror_section(text), self.render(document))


if __name__ == "__main__":
    unittest.main()
