"""Synthetic T-UXR-07 fixtures for scripts/check_direction.py (PenniLogic/docs#76).

Every fixture below is built in memory: seven synthetic candidates, four synthetic probes and a pending direction
record. They are not research evidence, personas, reviews, approvals or a D2 decision. Each negative test runs a
passing control, applies exactly one mutation and asserts the exact static rule identifier and printed subject.
No test touches the network or writes inside the repository.
"""

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_direction", ROOT / "scripts" / "check_direction.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SCHEMA = module.loads((ROOT / module.SCHEMA).read_bytes())

COMMIT = "1" * 40
SOURCE_PATH = "product/01-product-spec.md"
SOURCE_BYTES = b"synthetic product truth for direction tests\n"
SOURCE_DIGEST = "sha256:" + hashlib.sha256(SOURCE_BYTES).hexdigest()
MATERIALS = ("ledger_paper", "cut_paper", "woven_textile", "engraved_metal", "printed_map", "letterpress", "enamel")
GRAPHICS = ("swiss_grid", "editorial", "cartographic", "technical_drawing", "vernacular_signage", "woodcut",
            "modernist_poster")
VALUES = {
    "surface": "#FFFFFF", "text_primary": "#1A1A1A", "text_secondary": "#595959",
    "control_boundary": "#767676", "focus_indicator": "#1A1A1A", "warning": "#B3B3B3",
}
PAIRS = (
    ("text", "text_primary", "surface", "pass"), ("text", "text_secondary", "surface", "pass"),
    ("ui", "control_boundary", "surface", "pass"), ("ui", "focus_indicator", "surface", "pass"),
)
# The synthetic offline inventory: the only issue references the fixtures may resolve.
ISSUES = frozenset(f"PenniLogic/docs#{n}" for n in (53, 55, 66, 67, 74, 75, 76, 78)) | {"PenniLogic/infra#22"}
HELD_GATES = [f"pending:{reference}" for reference in (
    "PenniLogic/docs#53", "PenniLogic/docs#66", "PenniLogic/docs#67", "PenniLogic/docs#74", "PenniLogic/docs#75",
    "PenniLogic/infra#22")]
TOPICS = ("debt_progress", "transaction_clarification", "household_privacy", "operator_urgency")
DEPICTION = {"household_privacy": "explicit_revocable_grant", "operator_urgency": "audited_elevation"}


class FakeSources:
    """In-memory blob port: the only Git objects the synthetic fixtures may cite."""

    def __init__(self, blobs=None, accepted=(COMMIT,)):
        self.blobs = {(COMMIT, SOURCE_PATH): SOURCE_BYTES} if blobs is None else blobs
        self.accepted_commits = set(accepted)

    def accepted(self, commit):
        return commit in self.accepted_commits

    def blob(self, commit, path):
        try:
            return self.blobs[(commit, path)]
        except KeyError:
            raise LookupError("blob unavailable") from None


def candidate(number):
    index = number - 1
    return {
        "id": f"DIR-{number:02d}",
        "name": f"Synthetic direction {number}",
        "material_tradition": MATERIALS[index],
        "graphic_tradition": GRAPHICS[index],
        "category_default": False,
        "rationale": "Synthetic rationale grounded in the cited product truth.",
        "intended_feel": "Calm and plain.",
        "form_language": "Semantic roles only.",
        "signature_interaction": "Progress shown as a route walked.",
        "content_behavior": "Plain language with explicit provenance.",
        "risks": ["Synthetic risk."],
        "accessibility_notes": ["Synthetic accessibility note."],
        "persona_assumptions": [{"text": "Unvalidated synthetic assumption.", "validated": False}],
        "grounding": [{"commit": COMMIT, "path": SOURCE_PATH, "sha256": SOURCE_DIGEST}],
        "illustrative_values": {
            "binding": False, "values": [{"role": role, "srgb": srgb} for role, srgb in VALUES.items()],
        },
        "contrast_pairs": [
            {"kind": kind, "foreground": fore, "background": back, "result": result}
            for kind, fore, back, result in PAIRS
        ],
        "feasibility": {
            "density": "Synthetic.", "reduced_motion": "Synthetic.", "localization_expansion": "Synthetic.",
            "android": "Synthetic.", "web": "Synthetic.", "admin": "Synthetic.",
        },
    }


def candidates():
    return {
        "schema_version": 1, "kind": "direction_candidates", "source_issue": "PenniLogic/docs#76",
        "plan_id": "T-UXR-07", "status": "proposal", "candidates": [candidate(n) for n in range(1, 8)],
    }


def probes():
    return {
        "schema_version": 1, "kind": "direction_probes", "source_issue": "PenniLogic/docs#76",
        "probes": [
            {
                "id": f"PRB-{number:02d}", "topic": topic, "format": "text", "data_origin": "synthetic",
                "access_depiction": DEPICTION.get(topic, "none"),
                "scenario": "Synthetic scenario with round fictional figures such as INR 1,000.",
                "renderings": [
                    {"candidate": f"DIR-{n:02d}", "description": "Synthetic text rendering."} for n in range(1, 8)
                ],
            }
            for number, topic in enumerate(TOPICS, start=1)
        ],
    }


def record():
    return {
        "schema_version": 1, "kind": "direction_record", "version": "0.1.0", "gate": "D2",
        "artifact_class": "visual_direction", "source_issue": "PenniLogic/docs#76", "plan_id": "T-UXR-07",
        "status": "pending",
        "prepared_by": {"role": "systems", "ref": "PenniLogic/docs#76"},
        "candidates_considered": [f"DIR-{n:02d}" for n in range(1, 8)],
        "participant_count": None,
        "evidence": [{
            "kind": "representative_user_study", "study_ref": "pending:PenniLogic/docs#53",
            "data_origin": "pending", "state": "pending",
        }],
        "decision": None,
        "reviews": [
            {"role": role, "state": "pending", "reviewer_ref": None}
            for role in ("accessibility", "content", "android_design", "web_design", "admin_design")
        ],
        "semantic_roles": [
            {"role": role, "meaning": "Synthetic meaning."}
            for role in ("progress", "provenance", "uncertainty", "control")
        ],
        "platform_consequences": {"android": "Synthetic.", "web": "Synthetic.", "admin": "Synthetic."},
        "unresolved_risks": [
            {"text": "Synthetic unresolved risk.", "state": "open", "owner_ref": "PenniLogic/docs#53"},
        ],
        "implementation_consequences": ["Synthetic consequence."],
        "token_contract": {"state": "not_started", "owner_issue": "PenniLogic/docs#55", "reference": None},
        "supersession": {"supersedes": None, "requires": "A superseding D2 record and a migration plan."},
        "consumers": ["PenniLogic/docs#55", "PenniLogic/docs#78"],
        "held_gates": list(HELD_GATES),
    }


def decision(**changes):
    value = {
        "selected": "DIR-01", "rejected": [f"DIR-{n:02d}" for n in range(2, 8)],
        "approver_role": "decision_coordinator", "approver_ref": None, "signed_at": None, "signature_ref": None,
    }
    value.update(changes)
    return value


class Fixture:
    def __init__(self):
        self.candidates, self.probes, self.record = candidates(), probes(), record()
        self.schema, self.sources, self.issues = copy.deepcopy(SCHEMA), FakeSources(), set(ISSUES)

    def check(self):
        return module.check(self.candidates, self.probes, self.record, self.schema, self.sources, self.issues)


class Case(unittest.TestCase):
    def refuses(self, mutate, rule, subject=None):
        """Passing control, then exactly one mutation refused with the exact rule and printed subject."""
        self.assertIsInstance(Fixture().check(), module.Model)
        fixture = Fixture()
        mutate(fixture)
        with self.assertRaises(module.Refused) as caught:
            fixture.check()
        self.assertIn(rule, module.STRUCTURE_RULES)
        self.assertEqual((caught.exception.rule, caught.exception.subject), (rule, subject))
        return caught.exception


def at(fixture, number):
    return fixture.candidates["candidates"][number - 1]


def probe(fixture, number):
    return fixture.probes["probes"][number - 1]


class SchemaAndContentTests(Case):
    def test_rule_list_is_static_and_unique(self):
        self.assertEqual(len(module.STRUCTURE_RULES), len(set(module.STRUCTURE_RULES)))
        self.assertEqual(len(module.READINESS_RULES), len(set(module.READINESS_RULES)))

    def test_unexpected_property_is_schema_invalid(self):
        self.refuses(lambda f: at(f, 2).update(palette="anything"), "schema.invalid")

    def test_missing_rationale_is_schema_invalid(self):
        self.refuses(lambda f: at(f, 3).pop("rationale"), "schema.invalid")

    def test_lowercase_illustrative_value_is_schema_invalid(self):
        self.refuses(lambda f: at(f, 1)["illustrative_values"]["values"][0].update(srgb="#ffffff"),
                     "schema.invalid")

    def test_schema_patterns_are_anchored(self):
        self.refuses(lambda f: at(f, 1)["grounding"][0].update(commit=COMMIT + "\n"), "schema.invalid")

    def test_content_shapes(self):
        cases = (
            ("content.too_long", "x" * (module.TEXT_LIMIT + 1)),
            ("content.blank_or_padded", " padded"),
            ("content.unprintable_character", "tab\there"),
            ("content.secret_shape", "aB3" * 12),
            ("content.markup", "a <b>bold</b> word"),
            ("content.url_shape", "see www.example.org"),
            ("content.email_shape", "write to someone@example.org"),
            ("content.account_shape", "account 1234 5678 9012"),
            ("content.gamification", "Keep your streak alive."),
            ("content.shame_language", "You failed again."),
            ("content.trust_theater", "A shield shows safety."),
        )
        for rule, text in cases:
            with self.subTest(rule=rule):
                self.refuses(lambda f, text=text: at(f, 4).update(intended_feel=text), rule, "DIR-04")

    def test_compatibility_and_homoglyph_forms_cannot_carry_refused_content(self):
        cases = (
            ("content.mixed_script", "A \u0455hield shows safety."),  # Cyrillic dze for Latin s
            ("content.mixed_script", "Keep your \u03b1chievement."),  # Greek alpha for Latin a
            ("content.gamification", "Keep your \uff53\uff54\uff52\uff45\uff41\uff4b alive."),  # fullwidth
            ("content.trust_theater", "A \U0001d42c\U0001d421ield shows safety."),  # mathematical bold s, h
            ("content.account_shape", "account \u0967\u0968\u0969\u096a \u096b\u096c\u096d\u096e \u096f\u0966"),
        )
        for rule, text in cases:
            with self.subTest(text=text):
                self.refuses(lambda f, text=text: at(f, 4).update(intended_feel=text), rule, "DIR-04")

    def test_invisible_marks_refused(self):
        for mark in ("\ufe0f", "\u034f", "\u17b4", "\u3164", "\U000e0100", "\u180b"):
            with self.subTest(mark=hex(ord(mark))):
                self.refuses(lambda f, mark=mark: at(f, 4).update(intended_feel=f"Calm and pl{mark}ain."),
                             "content.invisible_character", "DIR-04")

    def test_whole_word_look_alikes_are_scanned_as_latin(self):
        cases = (
            ("content.trust_theater", "A \u0455\u04bb\u0456\u0435\u04cf\u0501 shows safety."),  # all-Cyrillic shield
            ("content.gamification", "Your \u03c7\u03a1 grows."),  # Greek chi and rho for xP
        )
        for rule, text in cases:
            with self.subTest(text=text):
                self.refuses(lambda f, text=text: at(f, 4).update(intended_feel=text), rule, "DIR-04")

    def test_fullwidth_category_default_name_refused(self):
        self.refuses(lambda f: at(f, 3).update(name="\uff2e\uff45\uff4f\uff42\uff41\uff4e\uff4b Direction"),
                     "candidate.category_default", "DIR-03")

    def test_fullwidth_dot_asset_reference_refused(self):
        self.refuses(lambda f: probe(f, 1)["renderings"][0].update(description="Shows hero\uff0epng full width."),
                     "probe.external_asset", "PRB-01")

    def test_greek_or_cyrillic_words_on_their_own_are_allowed(self):
        fixture = Fixture()
        at(fixture, 4)["intended_feel"] = "Calm, like \u03b7\u03c1\u03b5\u03bc\u03af\u03b1 or \u0441\u043f\u043e\u043a\u043e\u0439\u043d\u043e."
        self.assertIsInstance(fixture.check(), module.Model)

    def test_content_guard_scans_probes_and_record(self):
        self.refuses(lambda f: probe(f, 2).update(scenario="Earn points daily."), "content.gamification", "PRB-02")
        self.refuses(lambda f: f.record["unresolved_risks"][0].update(text="Bank-grade safety."),
                     "content.trust_theater")

    def test_refusal_never_echoes_input(self):
        error = self.refuses(lambda f: at(f, 4).update(id="DIR-99"), "candidate.id_sequence")
        self.assertNotIn("DIR-99", str(error))


class CandidateTests(Case):
    def test_six_or_eight_candidates_refused(self):
        self.refuses(lambda f: f.candidates["candidates"].pop(), "candidate.count")
        self.refuses(lambda f: f.candidates["candidates"].append(candidate(7)), "candidate.count")

    def test_out_of_order_ids_refused(self):
        def swap(f):
            items = f.candidates["candidates"]
            items[0], items[1] = items[1], items[0]
        self.refuses(swap, "candidate.id_sequence")

    def test_empty_risks_accessibility_or_assumptions_incomplete(self):
        for key in ("risks", "accessibility_notes", "persona_assumptions"):
            with self.subTest(key=key):
                self.refuses(lambda f, key=key: at(f, 5).update({key: []}), "candidate.incomplete", "DIR-05")

    def test_duplicate_name_refused_case_insensitively(self):
        self.refuses(lambda f: at(f, 6).update(name="SYNTHETIC DIRECTION 1"), "candidate.name_duplicate", "DIR-06")

    def test_shared_material_tradition_refused(self):
        self.refuses(lambda f: at(f, 7).update(material_tradition=MATERIALS[0]),
                     "candidate.material_not_distinct", "DIR-07")

    def test_shared_graphic_tradition_refused(self):
        self.refuses(lambda f: at(f, 2).update(graphic_tradition=GRAPHICS[0]),
                     "candidate.graphic_not_distinct", "DIR-02")

    def test_category_default_flag_refused(self):
        self.refuses(lambda f: at(f, 3).update(category_default=True), "candidate.category_default", "DIR-03")

    def test_category_default_tradition_refused(self):
        self.refuses(lambda f: at(f, 3).update(graphic_tradition="fintech_dashboard"),
                     "candidate.category_default", "DIR-03")

    def test_category_default_name_refused(self):
        self.refuses(lambda f: at(f, 3).update(name="Neobank Dashboard"), "candidate.category_default", "DIR-03")

    def test_tradition_merely_containing_a_default_word_is_allowed(self):
        fixture = Fixture()
        at(fixture, 3)["graphic_tradition"] = "dashboarding_free_poster"
        self.assertIsInstance(fixture.check(), module.Model)

    def test_binding_illustrative_values_refused(self):
        self.refuses(lambda f: at(f, 1)["illustrative_values"].update(binding=True),
                     "candidate.binding_values", "DIR-01")

    def test_validated_persona_assumption_refused(self):
        self.refuses(lambda f: at(f, 2)["persona_assumptions"][0].update(validated=True),
                     "held.persona_validation", "DIR-02")


class GroundingTests(Case):
    def test_missing_grounding_refused(self):
        self.refuses(lambda f: at(f, 4).update(grounding=[]), "grounding.missing", "DIR-04")

    def test_unavailable_blob_refused(self):
        self.refuses(lambda f: setattr(f, "sources", FakeSources({})), "grounding.unavailable", "DIR-01")

    def test_dot_segment_path_refused(self):
        self.refuses(lambda f: at(f, 2)["grounding"][0].update(path="product/../" + SOURCE_PATH),
                     "grounding.path_not_canonical", "DIR-02")
        self.refuses(lambda f: at(f, 2)["grounding"][0].update(path="./" + SOURCE_PATH),
                     "grounding.path_not_canonical", "DIR-02")

    def test_digest_mismatch_refused(self):
        self.refuses(lambda f: at(f, 5)["grounding"][0].update(sha256="sha256:" + "0" * 64),
                     "grounding.digest_mismatch", "DIR-05")

    def test_self_citation_refused(self):
        self.refuses(lambda f: at(f, 1)["grounding"][0].update(path=module.CANDIDATES),
                     "grounding.self_reference", "DIR-01")

    def test_path_outside_product_truth_refused(self):
        for path in (".gitignore", "scripts/check_direction.py", "productive/notes.md"):
            with self.subTest(path=path):
                self.refuses(lambda f: at(f, 2)["grounding"][0].update(path=path),
                             "grounding.not_product_truth", "DIR-02")

    def test_every_product_truth_root_is_accepted(self):
        for root in module.PRODUCT_TRUTH_ROOTS:
            fixture = Fixture()
            path = root + "source.md"
            fixture.sources.blobs[(COMMIT, path)] = SOURCE_BYTES
            at(fixture, 3)["grounding"][0].update(path=path)
            with self.subTest(root=root):
                self.assertIsInstance(fixture.check(), module.Model)

    def test_commit_not_on_accepted_main_refused(self):
        self.refuses(lambda f: setattr(f, "sources", FakeSources(accepted=())), "grounding.not_accepted", "DIR-01")

    def test_pinned_commit_and_digest_are_exempt_from_the_secret_scan(self):
        self.assertTrue(module._secret_token(SOURCE_DIGEST))
        self.assertIsInstance(Fixture().check(), module.Model)


def pair(fixture, number, index):
    return at(fixture, number)["contrast_pairs"][index]


def value(fixture, number, role):
    return next(item for item in at(fixture, number)["illustrative_values"]["values"] if item["role"] == role)


class ContrastTests(Case):
    def test_relative_luminance_reference_points(self):
        self.assertAlmostEqual(module.relative_luminance("#FFFFFF"), 1.0)
        self.assertAlmostEqual(module.relative_luminance("#000000"), 0.0)
        self.assertAlmostEqual(module.contrast_ratio("#000000", "#FFFFFF"), 21.0)
        self.assertAlmostEqual(module.contrast_ratio("#FFFFFF", "#000000"), 21.0)
        self.assertAlmostEqual(module.contrast_ratio("#777777", "#777777"), 1.0)

    def test_text_threshold_boundary_pair(self):
        self.assertTrue(module.contrast_passes("text", "#767676", "#FFFFFF"))  # 4.54:1
        self.assertFalse(module.contrast_passes("text", "#777777", "#FFFFFF"))  # 4.48:1
        self.assertTrue(module.contrast_passes("large_text", "#777777", "#FFFFFF"))
        self.assertTrue(module.contrast_passes("ui", "#949494", "#FFFFFF"))  # 3.03:1
        self.assertFalse(module.contrast_passes("ui", "#959595", "#FFFFFF"))  # 2.99:1

    def test_claimed_pass_that_computes_fail_refused(self):
        self.refuses(lambda f: value(f, 2, "text_secondary").update(srgb="#777777"),
                     "contrast.result_mismatch", "DIR-02 text_secondary:surface")

    def test_claimed_fail_that_computes_pass_refused(self):
        self.refuses(lambda f: pair(f, 3, 0).update(result="fail"),
                     "contrast.result_mismatch", "DIR-03 text_primary:surface")

    def test_honest_failing_pair_is_a_readiness_gap_not_a_structure_failure(self):
        fixture = Fixture()
        at(fixture, 4)["contrast_pairs"].append(
            {"kind": "ui", "foreground": "warning", "background": "surface", "result": "fail"})
        model = fixture.check()
        self.assertEqual(module.readiness(model)["readiness.contrast_failing"], ["DIR-04 warning:surface"])

    def test_unknown_role_refused(self):
        self.refuses(lambda f: pair(f, 1, 2).update(foreground="emphasis"),
                     "contrast.unknown_role", "DIR-01 emphasis")

    def test_duplicate_role_value_refused(self):
        self.refuses(lambda f: at(f, 1)["illustrative_values"]["values"].append(
            {"role": "surface", "srgb": "#000000"}), "contrast.duplicate_role", "DIR-01 surface")

    def test_duplicate_pair_refused(self):
        self.refuses(lambda f: at(f, 6)["contrast_pairs"].append(dict(pair(f, 6, 0))),
                     "contrast.duplicate_pair", "DIR-06 text_primary:surface")

    def test_required_pair_missing_refused(self):
        self.refuses(lambda f: at(f, 7)["contrast_pairs"].pop(3),
                     "contrast.required_pair_missing", "DIR-07 focus_indicator:surface")

    def test_required_pair_with_wrong_kind_is_missing(self):
        self.refuses(lambda f: pair(f, 7, 1).update(kind="large_text"),
                     "contrast.required_pair_missing", "DIR-07 text_secondary:surface")


class ProbeTests(Case):
    def test_three_or_five_probes_refused(self):
        self.refuses(lambda f: f.probes["probes"].pop(), "probe.count")
        self.refuses(lambda f: f.probes["probes"].append(copy.deepcopy(probe(f, 1))), "probe.count")

    def test_topic_mismatch_refused(self):
        self.refuses(lambda f: probe(f, 1).update(topic="household_privacy", access_depiction="none"),
                     "probe.topic_mismatch", "PRB-01")

    def test_unknown_probe_id_refused_without_echo(self):
        self.refuses(lambda f: probe(f, 4).update(id="PRB-05"), "probe.topic_mismatch")

    def test_markup_or_script_format_refused(self):
        for kind in ("html", "svg", "script"):
            with self.subTest(kind=kind):
                self.refuses(lambda f, kind=kind: probe(f, 2).update(format=kind), "probe.markup", "PRB-02")

    def test_non_synthetic_origin_refused(self):
        for origin in ("restricted_live", "production"):
            with self.subTest(origin=origin):
                self.refuses(lambda f, origin=origin: probe(f, 1).update(data_origin=origin),
                             "probe.not_synthetic", "PRB-01")

    def test_external_asset_reference_refused(self):
        self.refuses(lambda f: probe(f, 1)["renderings"][2].update(description="Shows hero.png large."),
                     "probe.external_asset", "PRB-01")

    def test_raw_values_refused_in_probes(self):
        for text in ("Ledger rows on #F7F3E8 paper.", "Ink is rgb(31, 42, 68).", "Rows have 16dp padding.",
                     "Set in font-family Georgia.", "Rows use 16 \uff50\uff58 padding.", "Ink is tone#1a2b3c."):
            with self.subTest(text=text):
                self.refuses(lambda f, text=text: probe(f, 2)["renderings"][3].update(description=text),
                             "probe.raw_value", "PRB-02")
        self.refuses(lambda f: probe(f, 4).update(scenario="An operator sees margin 8 pt."), "probe.raw_value",
                     "PRB-04")

    def test_issue_references_and_amounts_in_probes_are_not_raw_values(self):
        fixture = Fixture()
        probe(fixture, 1)["scenario"] = "Synthetic plan tracked in docs#53 and PenniLogic/infra#22: INR 1,000 left."
        self.assertIsInstance(fixture.check(), module.Model)

    def test_sharing_as_ordinary_browsing_refused(self):
        self.refuses(lambda f: probe(f, 3).update(access_depiction="ordinary_browsing"),
                     "probe.unsafe_access_depiction", "PRB-03")

    def test_admin_access_without_audited_elevation_refused(self):
        self.refuses(lambda f: probe(f, 4).update(access_depiction="none"),
                     "probe.unsafe_access_depiction", "PRB-04")

    def test_ordinary_browsing_refused_on_any_probe(self):
        self.refuses(lambda f: probe(f, 2).update(access_depiction="ordinary_browsing"),
                     "probe.unsafe_access_depiction", "PRB-02")

    def test_missing_candidate_rendering_refused(self):
        self.refuses(lambda f: probe(f, 2)["renderings"].pop(), "probe.candidate_coverage", "PRB-02")

    def test_duplicate_candidate_rendering_refused(self):
        self.refuses(lambda f: probe(f, 2)["renderings"].__setitem__(6, {"candidate": "DIR-06",
                                                                         "description": "Synthetic."}),
                     "probe.candidate_coverage", "PRB-02")


def evidence(fixture):
    return fixture.record["evidence"][0]


def review(fixture, role):
    return next(item for item in fixture.record["reviews"] if item["role"] == role)


class RecordTests(Case):
    def test_version_must_be_semver(self):
        for version in ("1.0", "01.0.0", "1.0.0-rc.1", "v1.0.0"):
            with self.subTest(version=version):
                self.refuses(lambda f, version=version: f.record.update(version=version), "record.version_grammar")

    def test_raw_tokens_refused_in_the_record(self):
        for text in ("Surface is #1A1A1A.", "Use rgb(0, 0, 0).", "Pad 16dp.", "Set font-family here.",
                     "Use color.primary.", "Use --surface-bg.",
                     "Surface is \uff03\uff11A1A1A.", "Pad \uff11\uff16dp.", "Pad \u0967\u096cdp.",
                     "Platform themes reuse tone#F7F3E8.", "Use 48  dp touch targets.", "Pad 16   px.",
                     "See docs#55abc.", "Ink is #fff."):
            with self.subTest(text=text):
                self.refuses(lambda f, text=text: f.record["implementation_consequences"].append(text),
                             "record.raw_token")

    def test_invisible_mark_inside_a_dimension_refused(self):
        self.refuses(lambda f: f.record["implementation_consequences"].append("Pad 16\ufe0fdp around controls."),
                     "content.invisible_character")

    def test_duplicate_references_refused(self):
        self.refuses(lambda f: f.record["held_gates"].append("pending:PenniLogic/docs#66"), "record.duplicate_entry")
        self.refuses(lambda f: f.record["consumers"].append("PenniLogic/docs#55"), "record.duplicate_entry")
        self.refuses(lambda f: f.record["evidence"].append(dict(evidence(f))), "record.duplicate_entry")

    def test_empty_risks_consequences_or_consumers_incomplete(self):
        for key in ("unresolved_risks", "implementation_consequences", "consumers"):
            with self.subTest(key=key):
                self.refuses(lambda f: f.record.update({key: []}), "record.incomplete")

    def test_dangling_references_refused(self):
        dangling = "PenniLogic/docs#99999"
        mutations = {
            "consumer": lambda f: f.record["consumers"].__setitem__(1, dangling),
            "held gate": lambda f: f.record["held_gates"].append("pending:" + dangling),
            "study": lambda f: evidence(f).update(study_ref="pending:" + dangling),
            "preparer": lambda f: f.record["prepared_by"].update(ref=dangling),
            "risk owner": lambda f: f.record["unresolved_risks"][0].update(owner_ref=dangling),
        }
        for name, mutate in mutations.items():
            subject = dangling if name in ("consumer", "preparer", "risk owner") else "pending:" + dangling
            with self.subTest(field=name):
                self.refuses(mutate, "record.dangling_reference", subject)

    def test_reference_missing_from_the_inventory_snapshot_is_dangling(self):
        self.refuses(lambda f: f.issues.discard("PenniLogic/docs#78"), "record.dangling_reference",
                     "PenniLogic/docs#78")

    def test_token_consumer_required(self):
        self.refuses(lambda f: f.record["consumers"].remove("PenniLogic/docs#55"), "record.consumer_missing",
                     "PenniLogic/docs#55")

    def test_every_retained_and_d1_gate_required_while_pending(self):
        for gate in HELD_GATES:
            with self.subTest(gate=gate):
                self.refuses(lambda f: f.record["held_gates"].remove(gate), "record.held_gate_missing", gate)
        self.refuses(lambda f: f.record.update(held_gates=[]), "record.held_gate_missing", HELD_GATES[0])

    def test_mitigated_or_accepted_risk_cannot_be_recorded_here(self):
        for state in ("mitigated", "accepted"):
            with self.subTest(state=state):
                self.refuses(lambda f: f.record["unresolved_risks"][0].update(state=state), "held.risk_disposition")

    def test_risk_without_owner_is_schema_invalid(self):
        self.refuses(lambda f: f.record["unresolved_risks"][0].pop("owner_ref"), "schema.invalid")

    def test_issue_references_are_not_raw_tokens(self):
        fixture = Fixture()
        fixture.record["implementation_consequences"].append("Consumed by PenniLogic/docs#126 later.")
        self.assertIsInstance(fixture.check(), module.Model)

    def test_candidate_scoped_values_are_allowed_outside_the_record(self):
        fixture = Fixture()
        at(fixture, 1)["form_language"] = "Ink near #1A1A1A on paper, illustrative only."
        self.assertIsInstance(fixture.check(), module.Model)

    def test_considered_candidates_must_be_all_seven(self):
        self.refuses(lambda f: f.record["candidates_considered"].pop(), "record.candidate_mismatch")

    def test_unknown_preparer_role_refused(self):
        self.refuses(lambda f: f.record["prepared_by"].update(role="chief_designer"), "record.unknown_role")

    def test_semantic_roles_must_cover_legibility_roles(self):
        self.refuses(lambda f: f.record["semantic_roles"].pop(1), "record.semantic_roles_incomplete")

    def test_duplicate_semantic_role_refused(self):
        self.refuses(lambda f: f.record["semantic_roles"].append({"role": "progress", "meaning": "Again."}),
                     "record.semantic_roles_incomplete")

    def test_final_token_contract_refused(self):
        self.refuses(lambda f: f.record["token_contract"].update(state="final"), "record.final_token_contract")

    def test_token_contract_reference_refused(self):
        self.refuses(lambda f: f.record["token_contract"].update(reference="tokens"), "record.final_token_contract")

    def test_participant_count_zero_refused(self):
        self.refuses(lambda f: f.record.update(participant_count=0), "record.participant_count_zero")

    def test_negative_participant_count_refused(self):
        self.refuses(lambda f: f.record.update(participant_count=-1), "record.participant_count_zero")

    def test_pending_record_with_participant_count_refused(self):
        self.refuses(lambda f: f.record.update(participant_count=12), "record.participant_count_pending")

    def test_pending_record_with_decision_refused(self):
        self.refuses(lambda f: f.record.update(decision=decision()), "record.pending_with_decision")


class EvidenceTests(Case):
    def test_refused_evidence_kinds(self):
        cases = (("ai_preference", "evidence.ai"), ("internal_vote", "evidence.internal_vote"),
                 ("synthetic_participant", "evidence.synthetic"), ("mood_board_preference", "evidence.mood_board"))
        for kind, rule in cases:
            with self.subTest(kind=kind):
                self.refuses(lambda f, kind=kind: evidence(f).update(kind=kind), rule)

    def test_refused_kind_is_refused_even_beside_a_pending_study(self):
        self.refuses(lambda f: f.record["evidence"].append(dict(evidence(f), kind="internal_vote")),
                     "evidence.internal_vote")

    def test_synthetic_fixture_origin_refused(self):
        self.refuses(lambda f: evidence(f).update(data_origin="synthetic_fixture"), "evidence.synthetic")

    def test_no_evidence_entry_refused(self):
        self.refuses(lambda f: f.record.update(evidence=[]), "evidence.missing")

    def test_accepted_study_cannot_be_recorded_here(self):
        self.refuses(lambda f: evidence(f).update(state="accepted"), "held.study_evidence")

    def test_resolved_study_reference_cannot_be_recorded_here(self):
        self.refuses(lambda f: evidence(f).update(study_ref="PenniLogic/docs#53"), "held.study_evidence")


class ReviewTests(Case):
    def test_missing_review_role_refused(self):
        self.refuses(lambda f: f.record["reviews"].pop(1), "review.missing_role", "content")

    def test_duplicate_review_role_refused(self):
        self.refuses(lambda f: f.record["reviews"].append(dict(review(f, "web_design"))),
                     "review.duplicate_role", "web_design")

    def test_unknown_review_role_refused(self):
        self.refuses(lambda f: review(f, "content").update(role="brand_council"), "record.unknown_role")

    def test_preparer_cannot_review(self):
        self.refuses(lambda f: review(f, "accessibility").update(reviewer_ref="PenniLogic/docs#76"),
                     "review.self_review", "accessibility")

    def test_recorded_review_cannot_be_recorded_here(self):
        self.refuses(lambda f: review(f, "admin_design").update(state="recorded"),
                     "held.review_record", "admin_design")

    def test_named_reviewer_cannot_be_recorded_here(self):
        self.refuses(lambda f: review(f, "admin_design").update(reviewer_ref="PenniLogic/docs#53"),
                     "held.review_record", "admin_design")


def decide(**changes):
    def mutate(fixture):
        fixture.record.update(status="approved", decision=decision(**changes))
    return mutate


class DecisionTests(Case):
    def test_well_formed_decision_is_still_held(self):
        self.refuses(decide(), "held.d2_decision", "D2")

    def test_superseded_status_is_held_too(self):
        self.refuses(lambda f: f.record.update(status="superseded", decision=decision()), "held.d2_decision", "D2")

    def test_approved_without_decision_refused(self):
        self.refuses(lambda f: f.record.update(status="approved"), "record.decision_missing")

    def test_malformed_decision_refused(self):
        def mutate(fixture):
            fixture.record.update(status="approved", decision=dict(decision(), vote_tally="x"))
        self.refuses(mutate, "decision.invalid")

    def test_unknown_selected_candidate_refused(self):
        self.refuses(decide(selected="DIR-08"), "decision.unknown_candidate")

    def test_rejected_alternatives_must_be_the_other_six(self):
        self.refuses(decide(rejected=["DIR-02", "DIR-03"]), "decision.rejected_mismatch", "DIR-01")

    def test_duplicate_rejected_alternative_refused(self):
        rejected = ["DIR-02", "DIR-02", "DIR-04", "DIR-05", "DIR-06", "DIR-07"]
        self.refuses(decide(rejected=rejected), "decision.rejected_mismatch", "DIR-01")

    def test_preparer_role_self_approval_refused(self):
        self.refuses(decide(approver_role="systems"), "decision.self_approval")

    def test_responsible_content_role_self_approval_refused(self):
        self.refuses(decide(approver_role="content"), "decision.self_approval")

    def test_preparer_reference_self_approval_refused(self):
        self.refuses(decide(approver_ref="PenniLogic/docs#76"), "decision.self_approval")

    def test_platform_lead_self_approval_refused(self):
        for role in ("android_design", "web_design", "admin_design"):
            with self.subTest(role=role):
                self.refuses(decide(approver_role=role), "decision.platform_self_approval", role)

    def test_other_approver_role_refused(self):
        self.refuses(decide(approver_role="product_owner"), "decision.wrong_approver")


class ReadinessTests(Case):
    def test_synthetic_baseline_reports_exact_gaps(self):
        gaps = module.readiness(Fixture().check())
        self.assertEqual(gaps, {
            "readiness.user_evidence_missing": ["pending:PenniLogic/docs#53"],
            "readiness.persona_unvalidated": [f"DIR-{n:02d}" for n in range(1, 8)],
            "readiness.review_pending": ["accessibility", "content", "android_design", "web_design", "admin_design"],
            "readiness.contrast_failing": [],
            "readiness.decision_pending": ["D2"],
            "readiness.held_gate": HELD_GATES,
        })

    def test_green_is_unreachable_while_the_decision_is_held(self):
        # Clearing the pending decision needs a non-pending status, which is always refused as held.
        self.refuses(decide(), "held.d2_decision", "D2")


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


class FilesCase(Case):
    def layout(self, fixture, raw=None):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        files = {
            module.CANDIDATES: encode(fixture.candidates), module.PROBES: encode(fixture.probes),
            module.RECORD: encode(fixture.record), module.SCHEMA: encode(fixture.schema),
            module.INVENTORY: encode({"issues": [{"reference": item} for item in sorted(fixture.issues)]}),
        }
        files.update(raw or {})
        for relative, data in files.items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_bytes(data)
        return root

    def run_main(self, root, *argv, sources=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main(list(argv), root=root, sources=sources or FakeSources())
        return code, out.getvalue(), err.getvalue()


class CliTests(FilesCase):
    def test_default_mode_is_not_green_with_exact_counts(self):
        code, out, err = self.run_main(self.layout(Fixture()))
        self.assertEqual((code, err), (1, ""))
        self.assertEqual(out.splitlines(), [
            "NOT GREEN: readiness incomplete",
            "Direction structure valid: 7 candidates, 4 probes, 28 contrast pairs (0 failing), record 0.1.0 pending",
            "readiness.user_evidence_missing: 1", "readiness.persona_unvalidated: 7", "readiness.review_pending: 5",
            "readiness.contrast_failing: 0", "readiness.decision_pending: 1", "readiness.held_gate: 6",
        ])

    def test_structure_mode_passes(self):
        code, out, err = self.run_main(self.layout(Fixture()), "--structure")
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(out.endswith("record 0.1.0 pending; readiness not evaluated.\n"))

    def test_refusal_is_printed_with_rule_only(self):
        fixture = Fixture()
        fixture.record["evidence"][0]["kind"] = "ai_preference"
        self.assertEqual(self.run_main(self.layout(fixture), "--structure"),
                         (1, "", "Direction check refused: evidence.ai\n"))

    def test_duplicate_key_fails_closed(self):
        fixture = Fixture()
        raw = encode(fixture.record).replace(b'"gate": "D2",', b'"gate": "D2", "gate": "D2",', 1)
        self.assertEqual(self.run_main(self.layout(fixture, {module.RECORD: raw}), "--structure"),
                         (1, "", "Direction check refused: input.unreadable_or_invalid\n"))

    def test_non_finite_number_fails_closed(self):
        fixture = Fixture()
        raw = encode(fixture.record).replace(b'"participant_count": null', b'"participant_count": NaN', 1)
        self.assertEqual(self.run_main(self.layout(fixture, {module.RECORD: raw}), "--structure"),
                         (1, "", "Direction check refused: input.unreadable_or_invalid\n"))

    def test_oversized_input_fails_closed(self):
        fixture = Fixture()
        raw = encode(fixture.probes)
        raw = raw + b" " * (module.MAX_INPUT_BYTES + 1 - len(raw))
        self.assertEqual(self.run_main(self.layout(fixture, {module.PROBES: raw}), "--structure"),
                         (1, "", "Direction check refused: input.unreadable_or_invalid\n"))

    def test_symlinked_input_fails_closed(self):
        root = self.layout(Fixture())
        self.assertEqual(self.run_main(root, "--structure")[0], 0)
        target = root / module.CANDIDATES
        moved = root / "elsewhere.json"
        target.rename(moved)
        try:
            os.symlink(moved, target)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links unavailable on this platform")
        self.assertEqual(self.run_main(root, "--structure"),
                         (1, "", "Direction check refused: input.unreadable_or_invalid\n"))

    def test_missing_file_fails_closed(self):
        root = self.layout(Fixture())
        (root / module.PROBES).unlink()
        self.assertEqual(self.run_main(root), (1, "", "Direction check refused: input.unreadable_or_invalid\n"))

    def test_missing_or_malformed_inventory_fails_closed(self):
        self.assertEqual(self.run_main(self.layout(Fixture()), "--structure")[0], 0)
        refused = (1, "", "Direction check refused: input.unreadable_or_invalid\n")
        for raw in (None, encode({"issues": []}), encode({"issues": [{"reference": "docs#55"}]}), encode([])):
            with self.subTest(raw=raw):
                root = self.layout(Fixture(), {module.INVENTORY: raw} if raw is not None else None)
                if raw is None:
                    (root / module.INVENTORY).unlink()
                self.assertEqual(self.run_main(root, "--structure"), refused)


def git(root, *args):
    """Run git for a hermetic synthetic fixture repository outside this repository."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
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


class GitTests(FilesCase):
    def repository(self, fixture):
        """A temporary docs-like checkout whose first commit holds the cited product truth."""
        root = self.layout(fixture)
        git(root, "init", "-q", "--template=", "-b", "main")
        (root / SOURCE_PATH).parent.mkdir(parents=True, exist_ok=True)
        (root / SOURCE_PATH).write_bytes(SOURCE_BYTES)
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "synthetic base")
        commit = git(root, "rev-parse", "HEAD")
        for item in fixture.candidates["candidates"]:
            item["grounding"][0]["commit"] = commit
        (root / module.CANDIDATES).write_bytes(encode(fixture.candidates))
        # The synthetic first commit stands in for accepted main for the duration of the test.
        patcher = mock.patch.object(module, "ACCEPTED_BASE", commit)
        patcher.start()
        self.addCleanup(patcher.stop)
        return root, commit

    def run_git(self, root, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main(list(argv), root=root)
        return code, out.getvalue(), err.getvalue()

    def test_grounding_resolves_from_the_local_object_store(self):
        root, commit = self.repository(Fixture())
        self.assertEqual(module.GitSources(root).blob(commit, SOURCE_PATH), SOURCE_BYTES)
        code, out, err = self.run_git(root, "--structure")
        self.assertEqual((code, err), (0, ""))

    def test_changed_source_bytes_are_a_digest_mismatch(self):
        fixture = Fixture()
        for item in fixture.candidates["candidates"]:
            item["grounding"][0]["sha256"] = "sha256:" + "0" * 64
        root, _ = self.repository(fixture)
        self.assertEqual(self.run_git(root, "--structure"),
                         (1, "", "Direction check refused: grounding.digest_mismatch DIR-01\n"))

    def test_commit_after_the_accepted_base_is_not_accepted(self):
        fixture = Fixture()
        root, base = self.repository(fixture)
        self.assertEqual(self.run_git(root, "--structure")[0], 0)
        git(root, "commit", "-q", "--allow-empty", "-m", "synthetic unmerged change")
        later = git(root, "rev-parse", "HEAD")
        sources = module.GitSources(root)
        self.assertEqual((sources.accepted(base), sources.accepted(later)), (True, False))
        with self.assertRaises(LookupError):
            sources.accepted("2" * 40)
        fixture.candidates["candidates"][0]["grounding"][0]["commit"] = later
        (root / module.CANDIDATES).write_bytes(encode(fixture.candidates))
        self.assertEqual(self.run_git(root, "--structure"),
                         (1, "", "Direction check refused: grounding.not_accepted DIR-01\n"))

    def test_unknown_commit_or_path_is_unavailable(self):
        root, commit = self.repository(Fixture())
        sources = module.GitSources(root)
        for pin in (("2" * 40, SOURCE_PATH), (commit, "product/absent.md"), ("HEAD", SOURCE_PATH)):
            with self.subTest(pin=pin), self.assertRaises(LookupError):
                sources.blob(*pin)

    def test_inherited_git_dir_cannot_redirect_the_object_store(self):
        root, commit = self.repository(Fixture())
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        git(other.name, "init", "-q", "--template=", "-b", "main")
        with mock.patch.dict(os.environ, {"GIT_DIR": str(Path(other.name) / ".git")}):
            self.assertEqual(module.GitSources(root).blob(commit, SOURCE_PATH), SOURCE_BYTES)

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
        for path in ([str(planted), str(real)], ["", ".", "tools", str(real)], [str(root), str(real)]):
            with self.subTest(path=path), mock.patch.dict(os.environ, {"PATH": os.pathsep.join(path)}):
                self.assertEqual(Path(module.trusted_git(root)).parent, real)
        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join([str(planted), "."])}):
            with self.assertRaises(LookupError):
                module.trusted_git(root)
            with self.assertRaises(LookupError):
                module.GitSources(root).blob(COMMIT, SOURCE_PATH)



class RenderTests(FilesCase):
    def test_render_mode_prints_the_markdown_view(self):
        fixture = Fixture()
        code, out, err = self.run_main(self.layout(fixture), "--render")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, module.render_markdown(fixture.check()))
        self.assertTrue(out.startswith("# Concept directions and pending D2 direction record (T-UXR-07)\n"))
        self.assertIn("reports **NOT GREEN: readiness incomplete**.", out)

    def test_render_refuses_like_the_check(self):
        fixture = Fixture()
        fixture.record["participant_count"] = 0
        self.assertEqual(self.run_main(self.layout(fixture), "--render"),
                         (1, "", "Direction check refused: record.participant_count_zero\n"))

    def test_render_and_structure_are_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            module.main(["--render", "--structure"], root=self.layout(Fixture()), sources=FakeSources())
        self.assertEqual(caught.exception.code, 2)

    def test_render_emits_utf8_bytes_with_lf_through_a_binary_buffer(self):
        fixture = Fixture()
        raw = io.BytesIO()
        stdout = io.TextIOWrapper(raw, encoding="cp1252", newline="\r\n")
        with contextlib.redirect_stdout(stdout):
            code = module.main(["--render"], root=self.layout(fixture), sources=FakeSources())
        self.assertEqual(code, 0)
        self.assertEqual(raw.getvalue(), module.render_markdown(fixture.check()).encode("utf-8"))
        self.assertNotIn(b"\r", raw.getvalue())

    def test_record_paragraph_follows_the_record(self):
        record = Fixture().check().record
        self.assertIn("Participant count: not recorded (null; no study has run). Decision: none (null).",
                      "\n".join(module.render_record(record)))
        record["participant_count"], record["decision"] = 12, {"selected": "DIR-03"}
        self.assertIn("Participant count: 12. Decision: `DIR-03`.", "\n".join(module.render_record(record)))

    def test_table_cells_escape_pipes(self):
        self.assertEqual(module.table(("A",), [("x | y",)]), ["| A |", "|---|", "| x \\| y |"])

    def test_table_cells_escape_backslashes_before_pipes(self):
        self.assertEqual(module.cell("a \\| b"), "a \\\\\\| b")

    def test_displayed_ratio_never_overstates(self):
        # #777777 on white computes 4.478:1; rounding would display 4.48, truncation displays 4.47.
        self.assertEqual(module.ratio_text("#777777", "#FFFFFF"), "4.47")
        self.assertEqual(module.ratio_text("#000000", "#FFFFFF"), "21.00")

    def test_rendered_view_is_deterministic(self):
        self.assertEqual(module.render_markdown(Fixture().check()), module.render_markdown(Fixture().check()))


PUBLISHED_FAILING = [
    "DIR-01 control_boundary:surface", "DIR-02 uncertainty:surface", "DIR-04 control_boundary:surface",
    "DIR-04 progress:surface", "DIR-04 provenance:surface", "DIR-05 uncertainty:surface",
    "DIR-07 control_boundary:surface", "DIR-07 uncertainty:surface",
]


class PublishedDataTests(unittest.TestCase):
    """The committed data, grounded against this repository's own Git object store (read-only)."""

    @classmethod
    def setUpClass(cls):
        cls.model = module.load_and_check(ROOT)

    def test_published_data_reports_exact_readiness_gaps(self):
        self.assertEqual(module.readiness(self.model), {
            "readiness.user_evidence_missing": ["pending:PenniLogic/docs#53"],
            "readiness.persona_unvalidated": [f"DIR-{n:02d}" for n in range(1, 8)],
            "readiness.review_pending": ["accessibility", "content", "android_design", "web_design", "admin_design"],
            "readiness.contrast_failing": PUBLISHED_FAILING,
            "readiness.decision_pending": ["D2"],
            "readiness.held_gate": HELD_GATES,
        })

    def test_published_structure_line(self):
        self.assertEqual(module.structure_line(self.model), (
            "Direction structure valid: 7 candidates, 4 probes, 42 contrast pairs (8 failing), record 0.1.0 pending"))

    def test_published_record_is_pending_and_undecided(self):
        record = self.model.record
        self.assertEqual((record["status"], record["participant_count"], record["decision"]), ("pending", None, None))
        self.assertEqual(record["token_contract"], {
            "state": "not_started", "owner_issue": "PenniLogic/docs#55", "reference": None})
        self.assertEqual(record["prepared_by"], {"role": "systems", "ref": "PenniLogic/docs#76"})
        self.assertEqual(record["consumers"], ["PenniLogic/docs#55", "PenniLogic/docs#78"])
        self.assertEqual(record["held_gates"], HELD_GATES)
        self.assertEqual([(item["state"], item["owner_ref"]) for item in record["unresolved_risks"]], [
            ("open", "PenniLogic/docs#53"), ("open", "PenniLogic/docs#66"), ("open", "PenniLogic/docs#76"),
            ("open", "PenniLogic/docs#55"), ("open", "PenniLogic/docs#76"), ("open", "PenniLogic/docs#76"),
        ])
        self.assertIn("D1", record["unresolved_risks"][2]["text"])

    def test_published_candidates_are_pairwise_distinct(self):
        candidates = self.model.candidates["candidates"]
        for key in ("name", "material_tradition", "graphic_tradition"):
            self.assertEqual(len({item[key] for item in candidates}), 7, key)
        self.assertFalse(any(item["category_default"] for item in candidates))

    def test_published_markdown_matches_the_rendered_view(self):
        self.assertEqual((ROOT / module.MARKDOWN).read_bytes().decode("utf-8"), module.render_markdown(self.model),
                         "regenerate with: " + module.RENDER_COMMAND)

    def test_published_default_mode_output(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main([])
        self.assertEqual((code, err.getvalue()), (1, ""))
        self.assertEqual(out.getvalue().splitlines(), [
            "NOT GREEN: readiness incomplete",
            "Direction structure valid: 7 candidates, 4 probes, 42 contrast pairs (8 failing), record 0.1.0 pending",
            "readiness.user_evidence_missing: 1", "readiness.persona_unvalidated: 7", "readiness.review_pending: 5",
            "readiness.contrast_failing: 8", "readiness.decision_pending: 1", "readiness.held_gate: 6",
        ])


if __name__ == "__main__":
    unittest.main()
