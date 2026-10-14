"""Tests of scripts/check_content.py (T-CNT-01, PenniLogic/docs#84).

Every rule test builds a synthetic, in-memory content set that passes (the control), applies exactly one mutation and
asserts the exact static rule identifier and subject. No test reads the network or writes inside the repository; the
clock and the qualified-owner assignment are injected. The one exception to the injected clock is PublishedGitPathTests,
which checks the published documents exactly as an integration gate would: the real clock (deterministic while no
record is approved) and the real merge base with origin/main from the local Git object store.
"""

import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_content", ROOT / "scripts" / "check_content.py")
content = importlib.util.module_from_spec(spec)
spec.loader.exec_module(content)

NOW = datetime(2026, 10, 13, 12, 0, 0, tzinfo=timezone.utc)
OWNER = {"role": "legal"}  # a synthetic assignment; the published loader never supplies one
CLIENTS = ["android", "web", "admin"]
COMPREHENSION = ["payoff", "projected", "available", "pending", "reversed", "aggregate", "revoked"]
CATEGORIES = ["consent", "permission", "disclaimer", "plan_change", "refund", "deletion", "access", "incident",
              "ai_disclosure"]


def taxonomy():
    """A synthetic taxonomy with the imported fields only: forbidden terms, copy rules, placeholders, states."""
    def state(identifier, variants=(), causes=()):
        return {
            "id": identifier,
            "copy": {"headline": "Synthetic", "body": "Synthetic",
                     **({"variants": {name: {} for name in variants}} if variants else {})},
            "recovery_action": {"id": "retry", "label": "Synthetic",
                                **({"label_by_cause": {name: "x" for name in causes}} if causes else {})},
        }
    return {
        "forbidden_terms": ["oops", "because", "wrong", "!"],
        "copy_rules": [{"id": "no_blame", "rule": "x"}, {"id": "one_action", "rule": "x"}],
        "placeholders": [{"id": "item"}, {"id": "attempt"}],
        "states": [state("empty"), state("loading"), state("error"), state("stale"),
                   state("permission_denied", ("device",), ("device",))],
    }


def gates():
    return {"roles": [{"id": "content"}, {"id": "legal"}, {"id": "accessibility"}]}


def term(slug, label, required=False):
    return {
        "id": f"term.{slug}", "preferred_label": label, "definition": f"Synthetic definition of {label}.",
        "status": "provisional", "surfaces": ["android", "web", "admin", "contracts", "support"],
        "forbidden_aliases": [], "contract_field_names": [],
        "comprehension": {"required": required, "evidence_ref": "pending:PenniLogic/docs#66" if required else None},
        "owner": "content",
    }


def glossary():
    terms = [term(slug, slug, True) for slug in COMPREHENSION]
    terms.append(term("debt", "debt"))
    terms[-1]["forbidden_aliases"] = ["loan burden"]
    terms[-1]["contract_field_names"] = ["debt_id"]
    return {"schema_version": 1, "glossary_version": "0.1.0", "source_issue": "PenniLogic/docs#84",
            "status": "provisional", "terms": terms}


SLOT_KEYS = {
    "source": "debt.delete.source", "status": "debt.delete.status", "consequence": "debt.delete.consequence",
    "safe_remainder": "debt.delete.remainder", "next_action": "debt.delete.next",
}
# Each non-taxonomy pattern fills its slots with distinct keys of its own category (review round 1 F-04).
PATTERN_KEYS = {
    "destructive": SLOT_KEYS,
    "success": {slot: f"debt.saved.{slot}" for slot in content.SLOTS},
    "recovery": {slot: f"debt.restored.{slot}" for slot in content.SLOTS},
}


def voice():
    patterns = []
    for identifier, state in content.PATTERN_STATES.items():
        slots = {slot: (None if state else PATTERN_KEYS[identifier][slot]) for slot in content.SLOTS}
        patterns.append({"id": identifier, "taxonomy_state": state, "slots": slots})
    return {
        "schema_version": 1, "voice_version": "0.1.0", "source_issue": "PenniLogic/docs#84",
        "reading_level": {"target": "Synthetic target", "status": "provisional",
                          "evidence_ref": "pending:PenniLogic/docs#66"},
        "max_sentence_words": 12,
        "taxonomy_copy_rules": ["no_blame", "one_action"],
        "principles": [{"id": "voice.calm", "rule": "Calm and plain."}],
        "banned_patterns": [
            {"id": "banned.careless", "category": "shame", "phrase": "careless"},
            {"id": "banned.guaranteed", "category": "guarantee", "phrase": "guaranteed"},
            {"id": "banned.amazing", "category": "hype", "phrase": "amazing"},
            {"id": "banned.should_invest", "category": "advice", "phrase": "you should invest"},
        ],
        "conventions": [{"id": "convention.minor_units", "rule": "Amounts are integer minor units."}],
        "patterns": patterns,
    }


def key(name, text, category="label", **fields):
    entry = {
        "key": name, "category": category, "copy": text, "status": "provisional", "term_refs": [],
        "regulated_ref": None, "range": {"min": 1, "typical": 20, "max": 60}, "owner": "content",
        "platforms": list(CLIENTS), "neutral_safe_exit": False,
    }
    entry.update(fields)
    return entry


def catalogue():
    keys = [
        key("debt.delete.source", "From your debts list", "destructive"),
        key("debt.delete.status", "This debt is removed", "destructive", term_refs=["term.debt"]),
        key("debt.delete.consequence", "It no longer counts in totals", "destructive"),
        key("debt.delete.remainder", "Your other records stay as they are", "destructive"),
        key("debt.delete.next", "Review {item}", "destructive"),
        key("debt.saved.source", "From your debts list", "success"),
        key("debt.saved.status", "This debt is saved", "success"),
        key("debt.saved.consequence", "Totals now include it", "success"),
        key("debt.saved.safe_remainder", "Nothing else was changed", "success"),
        key("debt.saved.next_action", "Done", "success"),
        key("debt.restored.source", "From your last saved copy", "recovery"),
        key("debt.restored.status", "Your list is back", "recovery"),
        key("debt.restored.consequence", "Totals match the saved copy", "recovery"),
        key("debt.restored.safe_remainder", "Other records stay as they are", "recovery"),
        key("debt.restored.next_action", "Review {item}", "recovery"),
        key("state.empty.headline", None, "empty"),
        key("common.safe_exit.notification", "You have an update", "notification", neutral_safe_exit=True),
        key("common.safe_exit.denial", "This is not available here", "denial", neutral_safe_exit=True),
    ]
    for number, category in enumerate(CATEGORIES, start=1):
        keys.append(key(f"reg.{category}.text", None, "disclosure", regulated_ref=f"RC-{number:03d}"))
    return {"schema_version": 1, "catalogue_version": "0.1.0", "source_issue": "PenniLogic/docs#84",
            "placeholders": [{"id": "period_label", "description": "Synthetic.", "source": "surface_registration"}],
            "keys": keys}


def record(number, category):
    return {
        "id": f"RC-{number:03d}", "category": category, "key": f"reg.{category}.text", "version": "0.1.0",
        "status": "draft", "copy": "Synthetic draft text for review.", "fail_closed_key": "common.safe_exit.denial",
        "owner": "content", "approval": None, "history": [], "rollback_version": None,
    }


def regulated():
    return {"schema_version": 1, "regulated_version": "0.1.0", "source_issue": "PenniLogic/docs#84",
            "approver_role": "legal",
            "records": [record(number, category) for number, category in enumerate(CATEGORIES, start=1)]}


def documents():
    return {"glossary": glossary(), "voice": voice(), "message-keys": catalogue(), "regulated-copy": regulated()}


def schemas():
    return {name: content.support.load_json(ROOT / "product" / "content" / f"{name}.schema.json")
            for name in content.DOCUMENTS}


class FakeSources:
    """In-memory base documents and their base-commit schemas (default: the committed schemas); None means the base
    predates them, an exception means Git failed."""

    def __init__(self, base=None, error=None, base_schemas=None):
        self.base, self.error, self.base_schemas = base or {}, error, base_schemas

    def base_file(self, path):
        if self.error is not None:
            raise self.error
        for name, document in self.base.items():
            if path == content.document_path(name):
                return (json.dumps(document, indent=2) + "\n").encode("utf-8")
            if path == content.schema_path(name):
                return (json.dumps((self.base_schemas or schemas())[name], indent=2) + "\n").encode("utf-8")
        return None


def approval(start=NOW - timedelta(days=10), end=NOW + timedelta(days=10)):
    def stamp(moment):
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"role": "legal", "decision_ref": "synthetic decision", "effective_at": stamp(start),
            "expires_at": stamp(end)}


class Harness(unittest.TestCase):
    schemas = None

    @classmethod
    def setUpClass(cls):
        cls.schemas = schemas()

    def run_check(self, docs=None, now=NOW, owner=None, sources=None, taxonomy_data=None, gates_data=None):
        return content.check(
            documents() if docs is None else docs, self.schemas, taxonomy() if taxonomy_data is None else taxonomy_data,
            gates() if gates_data is None else gates_data, now, FakeSources() if sources is None else sources, owner,
        )

    def assertControlPasses(self, **options):
        model = self.run_check(**options)
        self.assertIsInstance(model, content.Model)
        return model

    def assertRefused(self, mutate, rule, subject=None, **options):
        """The unmutated control passes, then exactly one mutation fails with the exact rule and subject."""
        self.assertControlPasses(**options)
        docs = documents()
        mutate(docs)
        with self.assertRaises(content.Refused) as caught:
            self.run_check(docs, **options)
        self.assertIn(rule, content.STRUCTURE_RULES)
        self.assertEqual(caught.exception.rule, rule)
        self.assertEqual(caught.exception.subject, subject)
        return caught.exception


def terms_of(docs):
    return {term["id"]: term for term in docs["glossary"]["terms"]}


def keys_of(docs):
    return {entry["key"]: entry for entry in docs["message-keys"]["keys"]}


def records_of(docs):
    return {item["id"]: item for item in docs["regulated-copy"]["records"]}


class ControlTests(Harness):
    def test_synthetic_content_set_passes_structure(self):
        model = self.assertControlPasses()
        self.assertEqual(len(model.terms), 8)
        self.assertEqual(len(model.keys), 27)

    def test_synthetic_content_set_reports_exact_readiness_gaps(self):
        gaps = content.readiness(self.assertControlPasses())
        self.assertEqual(tuple(gaps), content.READINESS_RULES)
        self.assertEqual(gaps["readiness.comprehension_evidence"], sorted(f"term.{slug}" for slug in COMPREHENSION))
        self.assertEqual(len(gaps["readiness.term_unapproved"]), 8)
        self.assertEqual(len(gaps["readiness.key_unapproved"]), 27)
        self.assertEqual(gaps["readiness.regulated_unapproved"], [f"RC-{n:03d}" for n in range(1, 10)])
        self.assertEqual(gaps["readiness.reading_level_provisional"], ["voice.reading_level"])
        self.assertEqual(gaps["readiness.approver_unassigned"], ["approver_role"])
        self.assertEqual(gaps["readiness.nav_labels_held"], ["PenniLogic/docs#74"])
        self.assertEqual(gaps["readiness.pattern_slot_unstated"], sorted(
            f"pattern.{identifier}.{slot}" for identifier in ("empty", "loading", "error", "stale", "denied")
            for slot in content.SLOTS))

    def test_rule_identifiers_are_unique_and_each_is_raised_somewhere(self):
        rules = content.STRUCTURE_RULES + content.READINESS_RULES
        self.assertEqual(len(rules), len(set(rules)))
        source = (ROOT / "scripts" / "check_content.py").read_text(encoding="utf-8")
        for rule in rules:
            # Declared once in the tuple; at least one more use raises or records it.
            self.assertGreaterEqual(source.count(f'"{rule}"'), 2, rule)


class GlossaryTests(Harness):
    def test_term_id_grammar(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][7].update(id="term.Debt"), "term.id_grammar")

    def test_duplicate_term_id(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][7].update(id="term.payoff"), "term.duplicate_id",
                           "term.payoff")

    def test_duplicate_preferred_label_ignores_case(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][7].update(preferred_label="Payoff"),
                           "term.duplicate_label", "term.payoff term.debt")

    def test_alias_equal_to_own_label(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][7]["forbidden_aliases"].append("Debt"),
                           "term.alias_is_label", "term.debt")

    def test_alias_collides_with_another_preferred_label(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][7]["forbidden_aliases"].append("pending"),
                           "term.alias_collision", "term.debt term.pending")

    def test_alias_restating_a_taxonomy_forbidden_term_is_a_fork(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][7]["forbidden_aliases"].append("Oops"),
                           "taxonomy.forked_forbidden_term", "term.debt")

    def test_label_with_taxonomy_forbidden_term(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][7].update(preferred_label="wrong debt"),
                           "term.forbidden_term", "term.debt")

    def test_definition_with_taxonomy_forbidden_term(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][7].update(definition="Owed because of a loan."),
                           "term.forbidden_term", "term.debt")

    def test_definition_with_banned_voice_phrase(self):
        self.assertRefused(lambda d: terms_of(d)["term.debt"].update(definition="Owed money, repaid as guaranteed."),
                           "term.banned_pattern", "term.debt")

    def test_label_with_banned_voice_phrase(self):
        self.assertRefused(lambda d: terms_of(d)["term.debt"].update(preferred_label="amazing debt"),
                           "term.banned_pattern", "term.debt")

    def test_definition_with_another_terms_forbidden_alias(self):
        self.assertRefused(lambda d: terms_of(d)["term.payoff"].update(definition="When the loan burden ends."),
                           "term.forbidden_alias", "term.payoff")

    def test_contract_field_grammar(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][7].update(contract_field_names=["debtId"]),
                           "term.contract_field_grammar", "term.debt")

    def test_contract_field_claimed_by_two_terms(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][0].update(contract_field_names=["debt_id"]),
                           "term.contract_field_conflict", "term.payoff term.debt")

    def test_unknown_owner_role(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][7].update(owner="copywriter"), "owner.unknown_role",
                           "term.debt")

    def test_comprehension_term_missing(self):
        self.assertRefused(lambda d: d["glossary"]["terms"].pop(6), "term.comprehension_term_missing", "term.revoked")

    def test_comprehension_term_not_flagged(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][0]["comprehension"].update(required=False),
                           "term.comprehension_not_required", "term.payoff")

    def test_comprehension_evidence_other_than_the_held_reference_is_refused(self):
        self.assertRefused(
            lambda d: d["glossary"]["terms"][0]["comprehension"].update(evidence_ref="study complete"),
            "held.comprehension_evidence", "term.payoff")

    def test_approved_term_is_held(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][7].update(status="approved"), "held.term_approval",
                           "term.debt")

    def test_unknown_surface_is_a_schema_failure(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][7]["surfaces"].append("ios"), "schema.invalid")


def pattern(docs, identifier):
    return next(item for item in docs["voice"]["patterns"] if item["id"] == identifier)


class VoiceTests(Harness):
    def test_voice_id_grammar(self):
        self.assertRefused(lambda d: d["voice"]["principles"][0].update(id="calm"), "voice.id_grammar")

    def test_duplicate_voice_id(self):
        self.assertRefused(lambda d: d["voice"]["banned_patterns"][1].update(id="banned.careless"),
                           "voice.duplicate_id", "banned.careless")

    def test_sentence_limit_boundaries(self):
        for value, passes in ((7, False), (8, True), (40, True), (41, False)):
            docs = documents()
            docs["voice"]["max_sentence_words"] = value
            if passes:
                self.run_check(docs)
            else:
                with self.assertRaises(content.Refused) as caught:
                    self.run_check(docs)
                self.assertEqual(caught.exception.rule, "voice.sentence_limit_range")

    def test_confirmed_reading_level_is_held(self):
        self.assertRefused(lambda d: d["voice"]["reading_level"].update(status="confirmed"), "held.reading_level")

    def test_reading_level_evidence_other_than_the_held_reference_is_refused(self):
        self.assertRefused(lambda d: d["voice"]["reading_level"].update(evidence_ref="grade study"),
                           "held.reading_level")

    def test_unknown_taxonomy_copy_rule(self):
        self.assertRefused(lambda d: d["voice"]["taxonomy_copy_rules"].append("be_nice"),
                           "taxonomy.unknown_copy_rule")

    def test_taxonomy_copy_rule_not_imported(self):
        self.assertRefused(lambda d: d["voice"]["taxonomy_copy_rules"].remove("one_action"),
                           "taxonomy.copy_rule_missing")

    def test_banned_phrase_restating_a_taxonomy_term_is_a_fork(self):
        self.assertRefused(lambda d: d["voice"]["banned_patterns"][2].update(phrase="oops"),
                           "taxonomy.forked_forbidden_term", "banned.amazing")

    def test_banned_phrase_inside_a_taxonomy_term_is_a_fork(self):
        docs_taxonomy = taxonomy()
        docs_taxonomy["forbidden_terms"].append("totally amazing")
        self.assertControlPasses()
        with self.assertRaises(content.Refused) as caught:
            self.run_check(taxonomy_data=docs_taxonomy)
        self.assertEqual((caught.exception.rule, caught.exception.subject),
                         ("taxonomy.forked_forbidden_term", "banned.amazing"))

    def test_duplicate_banned_phrase(self):
        self.assertRefused(lambda d: d["voice"]["banned_patterns"][2].update(phrase="Careless"),
                           "voice.duplicate_pattern", "banned.amazing")

    def test_banned_category_missing(self):
        self.assertRefused(lambda d: d["voice"]["banned_patterns"][3].update(category="hype"),
                           "voice.banned_category_missing")

    def test_voice_rule_with_taxonomy_forbidden_term(self):
        self.assertRefused(lambda d: d["voice"]["principles"][0].update(rule="Never say oops."),
                           "voice.forbidden_term", "voice.calm")


class PatternTests(Harness):
    def test_duplicate_pattern(self):
        self.assertRefused(lambda d: d["voice"]["patterns"].append(copy.deepcopy(d["voice"]["patterns"][0])),
                           "pattern.duplicate", "empty")

    def test_missing_pattern(self):
        self.assertRefused(lambda d: d["voice"]["patterns"].pop(), "pattern.missing")

    def test_denied_pattern_must_reuse_the_taxonomy_state(self):
        self.assertRefused(lambda d: pattern(d, "denied").update(taxonomy_state="error"), "pattern.state_mismatch",
                           "denied")

    def test_pattern_state_absent_from_the_taxonomy(self):
        reduced = taxonomy()
        reduced["states"] = [state for state in reduced["states"] if state["id"] != "stale"]
        self.assertControlPasses()
        with self.assertRaises(content.Refused) as caught:
            self.run_check(taxonomy_data=reduced)
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("pattern.state_mismatch", "stale"))

    def test_taxonomy_pattern_may_not_restate_state_copy(self):
        self.assertRefused(lambda d: pattern(d, "stale")["slots"].update(status="debt.delete.status"),
                           "pattern.state_copy_forked", "stale")

    def test_non_taxonomy_pattern_fills_every_slot(self):
        self.assertRefused(lambda d: pattern(d, "success")["slots"].update(safe_remainder=None),
                           "pattern.slot_missing", "success")

    def test_pattern_slot_references_an_existing_key(self):
        self.assertRefused(lambda d: pattern(d, "recovery")["slots"].update(next_action="debt.delete.later"),
                           "pattern.unknown_key", "recovery")

    def test_pattern_slot_references_a_key_with_copy(self):
        self.assertRefused(lambda d: pattern(d, "recovery")["slots"].update(next_action="state.empty.headline"),
                           "pattern.unknown_key", "recovery")

    # Review round 1 F-04: criterion 2 slots are mapped, counted when unstated, and never filled by one key.
    def test_taxonomy_slot_maps_its_own_state_copy_and_leaves_the_gap_count(self):
        docs = documents()
        pattern(docs, "empty")["slots"].update(status="state.empty.headline")
        gaps = content.readiness(self.run_check(docs))
        self.assertNotIn("pattern.empty.status", gaps["readiness.pattern_slot_unstated"])
        self.assertEqual(len(gaps["readiness.pattern_slot_unstated"]), 24)

    def test_taxonomy_slot_may_not_name_another_states_copy(self):
        self.assertRefused(lambda d: pattern(d, "loading")["slots"].update(status="state.empty.headline"),
                           "pattern.state_copy_forked", "loading")

    def test_taxonomy_slot_names_an_existing_state_key(self):
        self.assertRefused(lambda d: pattern(d, "empty")["slots"].update(status="state.empty.body"),
                           "pattern.unknown_key", "empty")

    def test_non_taxonomy_slot_key_has_the_patterns_category(self):
        self.assertRefused(lambda d: pattern(d, "destructive")["slots"].update(status="debt.saved.status"),
                           "pattern.slot_category", "destructive")

    def test_non_taxonomy_pattern_uses_five_distinct_keys(self):
        self.assertRefused(lambda d: pattern(d, "success")["slots"].update(safe_remainder="debt.saved.consequence"),
                           "pattern.slot_reused", "success")


def add_key(docs, entry):
    docs["message-keys"]["keys"].append(entry)


class MessageKeyTests(Harness):
    def test_key_grammar(self):
        self.assertRefused(lambda d: add_key(d, key("debt", "Debt")), "key.grammar")

    def test_key_grammar_rejects_upper_case(self):
        self.assertRefused(lambda d: add_key(d, key("debt.Title", "Debt")), "key.grammar")

    def test_duplicate_key(self):
        self.assertRefused(lambda d: add_key(d, key("debt.delete.next", "Review")), "key.duplicate",
                           "debt.delete.next")

    def test_key_both_leaf_and_node(self):
        self.assertRefused(lambda d: add_key(d, key("debt.delete", "Delete")), "key.prefix_conflict",
                           "debt.delete debt.delete.consequence")

    def test_sibling_with_shared_text_prefix_is_not_a_conflict(self):
        docs = documents()
        add_key(docs, key("debt.delete_all", "Delete all"))
        self.run_check(docs)

    def test_foreign_namespace_root(self):
        self.assertRefused(lambda d: add_key(d, key("term.debt.label", "Debt")), "key.foreign_root",
                           "term.debt.label")

    def test_nav_root_is_held_for_docs74(self):
        self.assertRefused(lambda d: add_key(d, key("nav.home", "Home")), "held.nav_key", "nav.home")

    def test_state_key_must_derive_from_the_taxonomy(self):
        self.assertRefused(lambda d: add_key(d, key("state.empty.footer", None, "empty")),
                           "key.state_not_in_taxonomy", "state.empty.footer")

    def test_state_key_derived_from_a_variant_and_a_cause(self):
        docs = documents()
        add_key(docs, key("state.permission_denied.device.body", None, "denial"))
        add_key(docs, key("state.permission_denied.device.action", None, "action"))
        self.run_check(docs)

    def test_state_key_may_not_restate_taxonomy_copy(self):
        self.assertRefused(lambda d: keys_of(d)["state.empty.headline"].update(copy="Nothing here yet"),
                           "key.state_copy_forked", "state.empty.headline")

    def test_disclosure_copy_outside_reg_is_refused(self):
        # Review round 1 F-01: an AI disclosure or advice boundary as an ordinary key would be usable unapproved.
        self.assertRefused(lambda d: add_key(d, key("common.disclosure.ai", "AI insight from your data", "disclosure")),
                           "key.disclosure_outside_reg", "common.disclosure.ai")

    def test_regulated_text_restated_inside_an_ordinary_key_is_refused(self):
        self.assertRefused(lambda d: add_key(d, key("debt.delete.help", "Read this. Synthetic draft text for review.")),
                           "key.regulated_copy_restated", "debt.delete.help")

    def test_regulated_text_restated_with_other_case_and_spacing_is_refused(self):
        self.assertRefused(lambda d: add_key(d, key("debt.delete.help", "SYNTHETIC draft  text for review.")),
                           "key.regulated_copy_restated", "debt.delete.help")

    def test_reg_key_without_record(self):
        self.assertRefused(lambda d: keys_of(d)["reg.refund.text"].update(regulated_ref=None),
                           "key.regulated_root_without_record", "reg.refund.text")

    def test_reg_key_may_not_carry_copy(self):
        self.assertRefused(lambda d: keys_of(d)["reg.refund.text"].update(copy="Refund text"),
                           "key.regulated_copy_forked", "reg.refund.text")

    def test_regulated_reference_outside_the_reg_root(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"].update(regulated_ref="RC-001"),
                           "key.regulated_outside_root", "debt.delete.next")

    def test_common_key_serves_every_client(self):
        self.assertRefused(lambda d: keys_of(d)["common.safe_exit.denial"].update(platforms=["web"]),
                           "key.common_not_shared", "common.safe_exit.denial")

    def test_ordinary_key_needs_copy(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"].update(copy=None), "key.copy_missing",
                           "debt.delete.next")

    def test_range_order_boundaries(self):
        for bounds, passes in (((1, 1, 60), True), ((0, 5, 60), False), ((6, 5, 60), False),
                               ((1, 61, 60), False), ((1, 5, 2000), True), ((1, 5, 2001), False)):
            docs = documents()
            keys_of(docs)["debt.delete.next"]["range"] = dict(zip(("min", "typical", "max"), bounds))
            if passes:
                self.run_check(docs)
            else:
                with self.assertRaises(content.Refused) as caught:
                    self.run_check(docs)
                self.assertEqual((caught.exception.rule, caught.exception.subject),
                                 ("key.range_order", "debt.delete.next"))

    def test_copy_longer_than_max_range(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"]["range"].update(max=12, typical=12),
                           "key.copy_out_of_range", "debt.delete.next")

    def test_copy_at_exact_min_and_max_range_passes(self):
        docs = documents()
        keys_of(docs)["debt.delete.next"]["range"].update(min=13, typical=13, max=13)  # len("Review {item}") == 13
        self.run_check(docs)

    def test_copy_shorter_than_min_range(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"]["range"].update(min=14, typical=14),
                           "key.copy_out_of_range", "debt.delete.next")

    def test_unknown_term_reference(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"]["term_refs"].append("term.loan"),
                           "key.unknown_term", "debt.delete.next term.loan")

    def test_unknown_term_reference_outside_the_grammar_is_not_echoed(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"]["term_refs"].append("Loan Burden"),
                           "key.unknown_term", "debt.delete.next")

    def test_term_reference_without_its_preferred_label(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"]["term_refs"].append("term.payoff"),
                           "key.term_label_missing", "debt.delete.next term.payoff")

    def test_copy_with_taxonomy_forbidden_term(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"].update(copy="Review {item} because"),
                           "key.forbidden_term", "debt.delete.next")

    def test_copy_with_exclamation_mark(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"].update(copy="Review {item}!"),
                           "key.forbidden_term", "debt.delete.next")

    def test_key_reaching_a_client_where_its_term_is_not_used(self):
        self.assertRefused(lambda d: terms_of(d)["term.debt"].update(surfaces=["android", "contracts", "support"]),
                           "key.term_surface_missing", "debt.delete.status term.debt")

    def test_copy_with_forbidden_glossary_alias(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"].update(copy="Review loan burden"),
                           "key.forbidden_alias", "debt.delete.next")

    def test_copy_with_banned_guarantee(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"].update(copy="Payoff guaranteed"),
                           "key.banned_pattern", "debt.delete.next")

    def test_copy_with_banned_shame(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"].update(copy="A careless entry"),
                           "key.banned_pattern", "debt.delete.next")

    def test_sentence_word_limit_boundary(self):
        docs = documents()
        keys_of(docs)["debt.delete.remainder"].update(copy="One two three four five six seven eight nine ten {item} x")
        self.run_check(docs)
        self.assertRefused(
            lambda d: keys_of(d)["debt.delete.remainder"].update(
                copy="One two three four five six seven eight nine ten {item} x y"),
            "key.sentence_too_long", "debt.delete.remainder")

    def test_unknown_placeholder(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"].update(copy="Review {what}"),
                           "key.placeholder_unknown", "debt.delete.next")

    def test_catalogue_placeholder_is_usable(self):
        docs = documents()
        keys_of(docs)["debt.delete.next"]["copy"] = "Review {period_label}"
        self.run_check(docs)

    def test_safe_exit_copy_never_carries_a_placeholder(self):
        self.assertRefused(lambda d: keys_of(d)["common.safe_exit.denial"].update(copy="Not here: {item}"),
                           "key.safe_exit_placeholder", "common.safe_exit.denial")

    def test_neutral_safe_exit_needed_for_notifications(self):
        self.assertRefused(lambda d: keys_of(d)["common.safe_exit.notification"].update(neutral_safe_exit=False),
                           "key.neutral_safe_exit_missing")

    def test_approved_key_is_held(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"].update(status="approved"), "held.key_approval",
                           "debt.delete.next")

    def test_key_owner_role(self):
        self.assertRefused(lambda d: keys_of(d)["debt.delete.next"].update(owner="intern"), "owner.unknown_role",
                           "debt.delete.next")


class BannedVariantTests(Harness):
    """Review round 1 F-05: banned phrases match across case, hyphens and dashes, spacing and contractions."""

    def assertVariantRefused(self, phrase, text):
        docs = documents()
        docs["voice"]["banned_patterns"].append({"id": "banned.variant", "category": "shame", "phrase": phrase})
        self.run_check(docs)  # control: the phrase is configured and no copy uses it
        keys_of(docs)["debt.delete.consequence"].update(copy=text)
        with self.assertRaises(content.Refused) as caught:
            self.run_check(docs)
        self.assertEqual((caught.exception.rule, caught.exception.subject),
                         ("key.banned_pattern", "debt.delete.consequence"))

    def test_hyphenated_copy_matches_a_spaced_phrase(self):
        self.assertVariantRefused("debt free by", "You will be debt-free by June")

    def test_spaced_copy_matches_a_hyphenated_phrase(self):
        self.assertVariantRefused("risk-free", "This method is risk free")

    def test_en_dash_reads_as_a_hyphen(self):
        self.assertVariantRefused("life-changing", "A life\u2013changing result")

    def test_doubled_whitespace_is_collapsed(self):
        self.assertVariantRefused("bad with money", "You are bad  with money")

    def test_contraction_is_expanded(self):
        self.assertVariantRefused("you should have", "You should've paid on time")

    def test_typographic_contraction_is_expanded(self):
        self.assertVariantRefused("you should have", "You should\u2019ve paid on time")

    def test_spelling_variants_of_one_phrase_are_duplicates(self):
        self.assertRefused(lambda d: d["voice"]["banned_patterns"].append(
            {"id": "banned.variant", "category": "advice", "phrase": "You-should  invest"}),
            "voice.duplicate_pattern", "banned.variant")


class PlaceholderTests(Harness):
    def placeholders(self, docs):
        return docs["message-keys"]["placeholders"]

    def test_placeholder_grammar(self):
        self.assertRefused(lambda d: self.placeholders(d)[0].update(id="Period"), "placeholder.grammar")

    def test_duplicate_placeholder(self):
        self.assertRefused(lambda d: self.placeholders(d).append(copy.deepcopy(self.placeholders(d)[0])),
                           "placeholder.duplicate")

    def test_placeholder_shadowing_the_taxonomy(self):
        self.assertRefused(lambda d: self.placeholders(d)[0].update(id="item"), "placeholder.shadows_taxonomy")

    def test_placeholders_that_would_echo_content_credentials_or_identity(self):
        for identifier in ("payee_name", "otp", "operator_id", "raw_text", "account_ref", "member_alias"):
            with self.subTest(identifier=identifier):
                self.assertRefused(lambda d: self.placeholders(d)[0].update(id=identifier), "placeholder.prohibited")


    # Review round 1 F-06: parts match anywhere in the name, and identity-bearing names are on the list.
    def test_joined_up_and_identity_bearing_placeholder_names_are_prohibited(self):
        for identifier in ("username", "accountnumber", "cardnumber", "otpcode", "merchant", "payee", "sender",
                           "recipient", "counterparty", "upi_id", "vpa", "pan", "aadhaar", "ifsc", "iban", "passwd"):
            with self.subTest(identifier=identifier):
                self.assertRefused(lambda d: self.placeholders(d)[0].update(id=identifier), "placeholder.prohibited")

    def test_notification_never_echoes_a_data_placeholder(self):
        docs = documents()
        self.placeholders(docs).append({"id": "due_day", "description": "Synthetic.", "source": "service_response"})
        add_key(docs, key("debt.reminder.due", "Due on {due_day}", "label"))
        self.run_check(docs)  # control: a label may render the data placeholder
        keys_of(docs)["debt.reminder.due"].update(category="notification")
        with self.assertRaises(content.Refused) as caught:
            self.run_check(docs)
        self.assertEqual((caught.exception.rule, caught.exception.subject),
                         ("key.notification_data_placeholder", "debt.reminder.due"))

    def test_notification_may_use_a_surface_placeholder(self):
        docs = documents()
        add_key(docs, key("debt.reminder.period", "Your {period_label} summary is ready", "notification"))
        self.run_check(docs)


class ContentGuardTests(Harness):
    def mutate_copy(self, text):
        return lambda d: keys_of(d)["debt.delete.next"].update(copy=text)

    def test_url_shape(self):
        self.assertRefused(self.mutate_copy("Visit https://x"), "content.url_shape", "debt.delete.next")

    def test_domain_shape(self):
        self.assertRefused(self.mutate_copy("Visit pennilogic.com"), "content.url_shape", "debt.delete.next")

    def test_email_shape(self):
        self.assertRefused(self.mutate_copy("Write to a@b.c"), "content.email_shape", "debt.delete.next")

    def test_amount_shape(self):
        self.assertRefused(self.mutate_copy("Pay INR 50"), "content.number_shape", "debt.delete.next")

    def test_long_digit_run(self):
        self.assertRefused(self.mutate_copy("Call 98 76 5"), "content.number_shape", "debt.delete.next")

    def test_written_currency_and_indian_magnitudes_next_to_a_number(self):
        # Review round 2 SS-09 (round 1 F-16): written amounts and lower-case codes are amounts too.
        for text in ("Pay 50 rupees", "Pay 1 rupee", "Up to 2 lakh", "Up to 2 lakhs", "Up to 3 lac", "About 4 crore",
                     "Only 50 paise", "Pay inr 50", "Pay Rs. 50", "Pay rs 50", "Pay 50 rs", "Pay Rupees 50",
                     "Pay 50 inr"):
            with self.subTest(text=text):
                self.assertRefused(self.mutate_copy(text), "content.number_shape", "debt.delete.next")

    def test_currency_words_without_a_number_pass(self):
        docs = documents()
        keys_of(docs)["debt.delete.next"]["copy"] = "Review rupee {item}"
        self.run_check(docs)

    def test_singular_verb_after_the_plural_item_placeholder(self):
        # Review round 2 SS-09 (round 1 F-17): the taxonomy's {item} is the surface's plural noun.
        for text in ("{item} is back", "{item} was saved", "{item} has changed", "{item} isn't ready",
                     "{item}  Is back"):
            with self.subTest(text=text):
                self.assertRefused(self.mutate_copy(text), "key.item_agreement", "debt.delete.next")

    def test_plural_verb_after_the_item_placeholder_passes(self):
        docs = documents()
        keys_of(docs)["debt.delete.next"]["copy"] = "{item} are back"
        self.run_check(docs)

    def test_short_number_passes(self):
        docs = documents()
        keys_of(docs)["debt.delete.next"]["copy"] = "Review 2 {item}"
        self.run_check(docs)

    def test_secret_shape_built_at_runtime(self):
        planted = "".join(("Ab", "9" * 12, "Cd", "7" * 12))
        self.assertRefused(self.mutate_copy(planted), "content.secret_shape", "debt.delete.next")

    def test_padded_text(self):
        self.assertRefused(self.mutate_copy("Review {item} "), "content.blank_or_padded", "debt.delete.next")

    def test_homoglyph_letter_cannot_hide_a_forbidden_term(self):
        # Greek omicron in "oops": the ASCII lints would not see the taxonomy's forbidden term.
        self.assertRefused(self.mutate_copy("οops, review {item}"), "content.non_ascii_character",
                           "debt.delete.next")

    def test_fullwidth_letters_are_refused(self):
        self.assertRefused(self.mutate_copy("Review ｉｔｅｍ"), "content.non_ascii_character",
                           "debt.delete.next")

    def test_combining_mark_is_refused(self):
        self.assertRefused(self.mutate_copy("Reviéw {item}"), "content.non_ascii_character",
                           "debt.delete.next")

    def test_native_script_digits_cannot_hide_a_number(self):
        self.assertRefused(lambda d: terms_of(d)["term.debt"].update(definition="Owed १२३४५."),
                           "content.non_ascii_character", "term.debt")

    def test_lookalike_symbols_are_refused(self):
        # Symbol and punctuation lookalikes (Unicode S*/P*) that NFKC maps to ASCII would slip past the ASCII lints:
        # the forbidden "!", the banned "guarantee", the forbidden "oops", and the email, URL and amount shapes.
        lookalikes = {
            "fullwidth_exclamation": "Done\uff01", "double_exclamation": "Done \u203c",
            "small_exclamation": "Done\ufe57", "circled_letter_banned": "We \u24d6uaranteed it",
            "circled_letter_forbidden": "\u24deops, review {item}", "fullwidth_at": "Write to a\uff20b.c",
            "fullwidth_full_stop": "Visit pennilogic\uff0ecom", "fullwidth_dollar": "Pay \uff045",
            "rupee_sign": "Pay \u20a850", "indian_rupee_sign": "Pay \u20b950",
        }
        for case, text in lookalikes.items():
            with self.subTest(case=case):
                self.assertRefused(self.mutate_copy(text), "content.non_ascii_character", "debt.delete.next")

    def test_ascii_forms_of_the_lookalikes_meet_their_own_lints(self):
        # The controls: each lookalike's ASCII form is refused by the lint the lookalike would have bypassed.
        ascii_forms = {
            "Done!": "key.forbidden_term", "We guaranteed it": "key.banned_pattern",
            "oops, review {item}": "key.forbidden_term", "Write to a@b.c": "content.email_shape",
            "Visit pennilogic.com": "content.url_shape", "Pay $5": "content.number_shape",
        }
        for text, rule in ascii_forms.items():
            with self.subTest(text=text):
                self.assertRefused(self.mutate_copy(text), rule, "debt.delete.next")

    def test_allowed_typographic_punctuation_is_exactly_the_allow_list(self):
        self.assertEqual(content.TYPOGRAPHIC_PUNCTUATION, "\u2018\u2019\u201c\u201d\u2013\u2014\u2026")
        docs = documents()
        keys_of(docs)["debt.delete.next"]["copy"] = "\u201cReview\u201d \u2018{item}\u2019 \u2014 now\u2026"
        self.run_check(docs)

    def test_typographic_punctuation_passes(self):
        docs = documents()
        keys_of(docs)["debt.delete.next"]["copy"] = "Review {item} – it’s yours"
        self.run_check(docs)

    def test_stray_brace_is_an_unknown_placeholder(self):
        self.assertRefused(self.mutate_copy("Review {item"), "key.placeholder_unknown", "debt.delete.next")

    def test_doubled_braces_are_an_unknown_placeholder(self):
        self.assertRefused(self.mutate_copy("Review {{item}}"), "key.placeholder_unknown", "debt.delete.next")

    def test_stray_brace_in_regulated_copy(self):
        self.assertRefused(lambda d: records_of(d)["RC-001"].update(copy="Synthetic draft text } for review."),
                           "regulated.placeholder_unknown", "RC-001")

    def test_unprintable_text(self):
        self.assertRefused(self.mutate_copy("Review\u200b{item}"), "content.unprintable_character",
                           "debt.delete.next")

    def test_overlong_text(self):
        self.assertRefused(lambda d: d["glossary"]["terms"][7].update(definition="Owed. " * 101),
                           "content.blank_or_padded", "term.debt")
        self.assertRefused(lambda d: d["glossary"]["terms"][7].update(definition="Owed." + " owed" * 120),
                           "content.too_long", "term.debt")

    def test_object_keys_are_scanned(self):
        # Every schema object is closed, so the guard's key scan is defence in depth; prove it directly.
        content.guard_content({"id": "voice.calm", "rule": "Plain."})
        with self.assertRaises(content.Refused) as caught:
            content.guard_content({"id": "voice.calm", "https://x": "Plain."})
        self.assertEqual(str(caught.exception), "content.url_shape voice.calm")

    def test_refusal_never_echoes_copy_text(self):
        docs = documents()
        keys_of(docs)["debt.delete.next"]["copy"] = "Write to someone@mail.example"
        with self.assertRaises(content.Refused) as caught:
            self.run_check(docs)
        self.assertNotIn("example", str(caught.exception))
        self.assertEqual(str(caught.exception), "content.email_shape debt.delete.next")

    def test_unprintable_subject_is_dropped(self):
        error = content.Refused("key.grammar", "Debt Title")
        self.assertIsNone(error.subject)
        self.assertEqual(str(error), "key.grammar")


def approve(item, status="approved", **window):
    item["status"] = status
    item["approval"] = approval(**window)


def first(docs):
    return docs["regulated-copy"]["records"][0]


class RegulatedRecordTests(Harness):
    def test_id_grammar(self):
        self.assertRefused(lambda d: first(d).update(id="RC-0001"), "regulated.id_grammar")

    def test_id_zero_is_out_of_range(self):
        self.assertRefused(lambda d: first(d).update(id="RC-000"), "regulated.id_grammar")

    def test_duplicate_id(self):
        self.assertRefused(lambda d: d["regulated-copy"]["records"][1].update(id="RC-001"), "regulated.duplicate_id",
                           "RC-001")

    def test_approver_must_be_the_qualified_legal_owner(self):
        self.assertRefused(lambda d: d["regulated-copy"].update(approver_role="content"),
                           "regulated.approver_role_unqualified")

    def test_approver_role_must_exist_in_design_gates(self):
        self.assertControlPasses()
        with self.assertRaises(content.Refused) as caught:
            self.run_check(gates_data={"roles": [{"id": "content"}]})
        self.assertEqual(caught.exception.rule, "roles.unreadable")

    def test_every_category_has_a_record(self):
        self.assertRefused(lambda d: d["regulated-copy"]["records"][7].update(category="consent"),
                           "regulated.category_missing")

    def test_record_key_must_point_back(self):
        self.assertRefused(lambda d: first(d).update(key="reg.refund.text"), "regulated.key_mismatch", "RC-001")

    def test_record_key_must_exist(self):
        self.assertRefused(lambda d: first(d).update(key="reg.consent.other"), "regulated.key_mismatch", "RC-001")

    def test_fail_closed_key_must_exist(self):
        self.assertRefused(lambda d: first(d).update(fail_closed_key="common.safe_exit.other"),
                           "regulated.fail_closed_key_unknown", "RC-001")

    def test_fail_closed_key_must_be_a_neutral_safe_exit(self):
        self.assertRefused(lambda d: first(d).update(fail_closed_key="debt.delete.next"),
                           "regulated.fail_closed_key_unsafe", "RC-001")

    def test_fail_closed_key_may_not_be_regulated(self):
        self.assertRefused(lambda d: first(d).update(fail_closed_key="reg.refund.text"),
                           "regulated.fail_closed_key_unsafe", "RC-001")

    def test_copy_lint(self):
        cases = (
            ("Oops, consent text.", "regulated.forbidden_term"),
            ("Consent covers your loan burden.", "regulated.forbidden_alias"),
            ("Results are guaranteed.", "regulated.banned_pattern"),
            ("One two three four five six seven eight nine ten eleven twelve thirteen.", "regulated.sentence_too_long"),
            ("Consent for {what}.", "regulated.placeholder_unknown"),
        )
        for text, rule in cases:
            with self.subTest(rule=rule):
                self.assertRefused(lambda d: first(d).update(copy=text), rule, "RC-001")

    def test_record_copy_carries_the_labels_of_its_key_terms(self):
        self.assertRefused(lambda d: keys_of(d)["reg.consent.text"]["term_refs"].append("term.debt"),
                           "regulated.term_label_missing", "RC-001")

    def test_record_owner_role(self):
        self.assertRefused(lambda d: first(d).update(owner="legal_bot"), "owner.unknown_role", "RC-001")

    def test_draft_with_an_approval(self):
        self.assertRefused(lambda d: first(d).update(approval=approval()), "regulated.approval_unexpected", "RC-001")

    def test_approved_without_an_approval(self):
        self.assertRefused(lambda d: first(d).update(status="approved"), "regulated.approval_missing", "RC-001")


class RegulatedBindingTests(Harness):
    """Review round 1 F-09 and F-12: fallback coverage, one-to-one reg. binding, ranges of record text."""

    def test_fail_closed_key_must_cover_the_regulated_keys_platforms(self):
        docs = documents()
        add_key(docs, key("safe_exit.android.denial", "Not available here", "denial", platforms=["android"],
                          neutral_safe_exit=True))
        self.run_check(docs)  # control: the narrower fallback exists but is not used
        first(docs).update(fail_closed_key="safe_exit.android.denial")
        with self.assertRaises(content.Refused) as caught:
            self.run_check(docs)
        self.assertEqual((caught.exception.rule, caught.exception.subject),
                         ("regulated.fail_closed_platform_missing", "RC-001"))

    def test_second_reg_key_on_a_bound_record_is_refused(self):
        self.assertRefused(
            lambda d: add_key(d, key("reg.consent.second_surface", None, "disclosure", regulated_ref="RC-001")),
            "key.regulated_unbound", "reg.consent.second_surface")

    def test_record_copy_must_fit_its_keys_range(self):
        self.assertRefused(lambda d: first(d).update(copy="Synthetic draft text for review. " * 2 + "Read it."),
                           "key.copy_out_of_range", "reg.consent.text")

    def test_rollback_pinned_copy_must_fit_its_keys_range(self):
        def mutate(d):
            first(d).update(version="2.0.0", rollback_version="1.0.0",
                            history=[prior("1.0.0", "approved", approval(), text=("Earlier text. " * 6).strip())])
        docs = documents()
        first(docs).update(version="2.0.0", rollback_version="1.0.0",
                           history=[prior("1.0.0", "approved", approval())])
        self.run_check(docs, owner=OWNER)  # control
        self.assertRefused(mutate, "key.copy_out_of_range", "reg.consent.text", owner=OWNER)

    def test_state_key_range_must_fit_the_taxonomy_string(self):
        self.assertRefused(
            lambda d: keys_of(d)["state.empty.headline"].update(range={"min": 1, "typical": 4, "max": 5}),
            "key.copy_out_of_range", "state.empty.headline")


class NormalisedWordingTests(Harness):
    """Review round 2 SS-02: labels, aliases and restatements compare the normalised wording banned_in uses."""

    def test_duplicate_label_spelled_with_a_dash_or_extra_space(self):
        for label in ("pay-off", "Pay  Off", "PAY\u2013OFF"):
            with self.subTest(label=label):
                self.assertRefused(lambda d: terms_of(d)["term.debt"].update(preferred_label=label),
                                   "term.duplicate_label", "term.payoff term.debt")

    def test_alias_collision_spelled_with_a_dash_or_extra_space(self):
        for alias in ("pay-off", "Pay  off", "re-voked"):
            with self.subTest(alias=alias):
                other = "term.payoff" if "pay" in alias.casefold() else "term.revoked"
                self.assertRefused(lambda d: terms_of(d)["term.debt"]["forbidden_aliases"].append(alias),
                                   "term.alias_collision", f"term.debt {other}")

    def test_alias_equal_to_own_label_spelled_with_a_dash(self):
        self.assertRefused(lambda d: terms_of(d)["term.debt"]["forbidden_aliases"].append("de-bt"),
                           "term.alias_is_label", "term.debt")

    def test_key_copy_with_a_variant_of_a_forbidden_alias(self):
        for text in ("Review loan-burden", "Review loan  burden", "Review loan\u2013burden", "Review loan burdens",
                     "Review LOAN BURDEN"):
            with self.subTest(text=text):
                self.assertRefused(lambda d: keys_of(d)["debt.delete.next"].update(copy=text),
                                   "key.forbidden_alias", "debt.delete.next")

    def test_definition_with_a_variant_of_another_terms_alias(self):
        self.assertRefused(lambda d: terms_of(d)["term.payoff"].update(definition="Ends the loan-burdens."),
                           "term.forbidden_alias", "term.payoff")

    def test_regulated_copy_with_a_variant_of_a_forbidden_alias(self):
        self.assertRefused(lambda d: first(d).update(copy="Consent covers your loan-burden."),
                           "regulated.forbidden_alias", "RC-001")

    def test_taxonomy_string_restated_with_terminal_punctuation(self):
        for text in ("Synthetic.", "Synthetic!", "Synthetic\u2026", "Synthetic...", "SYNTHETIC ?"):
            with self.subTest(text=text):
                self.assertRefused(lambda d: add_key(d, key("states.empty.headline", text, "empty")),
                                   "key.taxonomy_copy_restated", "states.empty.headline")

    def test_word_that_merely_contains_an_alias_passes(self):
        docs = documents()
        keys_of(docs)["debt.delete.next"]["copy"] = "Review loan burdensome {item}"
        self.run_check(docs)


class TaxonomyRestatementTests(Harness):
    """Review round 1 F-15: a taxonomy string restated under a look-alike root forks same_wording."""

    def test_taxonomy_string_under_another_root_is_refused(self):
        self.assertRefused(lambda d: add_key(d, key("states.empty.headline", "SYNTHETIC", "empty")),
                           "key.taxonomy_copy_restated", "states.empty.headline")

    def test_generic_action_label_may_repeat_a_taxonomy_label(self):
        labelled = taxonomy()
        labelled["states"][1]["recovery_action"]["label"] = "Cancel"
        docs = documents()
        add_key(docs, key("common.action.cancel", "Cancel", "action"))
        self.run_check(docs, taxonomy_data=labelled)


class ApprovalTests(Harness):
    def test_published_loader_never_assigns_the_qualified_owner(self):
        # Without an injected assignment (the published state: legal is unassigned) no approval is possible.
        self.assertRefused(lambda d: approve(first(d)), "regulated.approver_unassigned", "RC-001")

    def test_assignment_of_another_role_is_not_the_qualified_owner(self):
        self.assertRefused(lambda d: approve(first(d)), "regulated.approver_unassigned", "RC-001",
                           owner={"role": "content"})

    def test_approved_inside_its_window_passes_with_an_assigned_owner(self):
        docs = documents()
        approve(first(docs))
        model = self.run_check(docs, owner=OWNER)
        gaps = content.readiness(model)
        self.assertNotIn("RC-001", gaps["readiness.regulated_unapproved"])
        self.assertEqual(gaps["readiness.approver_unassigned"], [])

    def test_approver_role_mismatch(self):
        def mutate(d):
            approve(first(d))
            first(d)["approval"]["role"] = "content"
        self.assertRefused(mutate, "regulated.approver_role_mismatch", "RC-001", owner=OWNER)

    def test_approval_needs_a_decision_reference(self):
        def mutate(d):
            approve(first(d))
            first(d)["approval"]["decision_ref"] = None
        self.assertRefused(mutate, "regulated.approval_evidence_missing", "RC-001", owner=OWNER)

    def test_invalid_instants(self):
        for value in ("2026-13-01T00:00:00Z", "yesterday at noon UTC"):
            with self.subTest(value=value):
                def mutate(d):
                    approve(first(d))
                    first(d)["approval"]["effective_at"] = value
                self.assertRefused(mutate, "time.invalid", owner=OWNER)

    def test_empty_window(self):
        self.assertRefused(lambda d: approve(first(d), start=NOW, end=NOW), "regulated.approval_window_invalid",
                           "RC-001", owner=OWNER)

    def test_lifetime_boundary(self):
        docs = documents()
        approve(first(docs), start=NOW - timedelta(days=1), end=NOW + timedelta(days=365))
        self.run_check(docs, owner=OWNER)
        self.assertRefused(
            lambda d: approve(first(d), start=NOW - timedelta(days=1), end=NOW + timedelta(days=365, seconds=1)),
            "regulated.approval_lifetime", "RC-001", owner=OWNER)

    def test_effective_at_now_is_usable(self):
        docs = documents()
        approve(first(docs), start=NOW)
        self.run_check(docs, owner=OWNER)

    def test_not_yet_effective(self):
        self.assertRefused(lambda d: approve(first(d), start=NOW + timedelta(seconds=1)),
                           "regulated.approval_not_yet_effective", "RC-001", owner=OWNER)

    def test_now_equal_to_expires_at_is_expired(self):
        self.assertRefused(lambda d: approve(first(d), end=NOW), "regulated.approval_expired", "RC-001",
                           owner=OWNER)

    def test_one_second_before_expiry_is_usable(self):
        docs = documents()
        approve(first(docs), end=NOW + timedelta(seconds=1))
        self.run_check(docs, owner=OWNER)

    def test_expired_status_needs_a_passed_expiry(self):
        docs = documents()
        approve(first(docs), status="expired", end=NOW)
        self.run_check(docs, owner=OWNER)
        self.assertRefused(lambda d: approve(first(d), status="expired", end=NOW + timedelta(seconds=1)),
                           "regulated.expired_status_mismatch", "RC-001", owner=OWNER)

    def test_untrusted_clocks(self):
        for now in (NOW.replace(tzinfo=None), NOW.astimezone(timezone(timedelta(hours=5, minutes=30))), "2026-10-13"):
            with self.subTest(now=now):
                with self.assertRaises(content.Refused) as caught:
                    self.run_check(now=now)
                self.assertEqual(caught.exception.rule, "time.untrusted_clock")


def prior(version, status, window, text="Synthetic earlier text for review.", bound="reg.consent.text"):
    return {"version": version, "key": bound, "status": status, "copy": text, "approval": window}


class HistoryAndRollbackTests(Harness):
    def with_history(self, docs, *entries, rollback=None):
        record = first(docs)
        record["version"] = "2.0.0"
        record["history"] = [prior(version, status, window) for version, status, window in entries]
        record["rollback_version"] = rollback

    def test_history_must_increase_below_the_current_version(self):
        docs = documents()
        self.with_history(docs, ("1.0.0", "draft", None), ("1.1.0", "withdrawn", None))
        self.run_check(docs)
        self.assertRefused(lambda d: self.with_history(d, ("1.1.0", "draft", None), ("1.0.0", "draft", None)),
                           "regulated.history_order", "RC-001")
        self.assertRefused(lambda d: self.with_history(d, ("2.0.0", "draft", None)), "regulated.history_order",
                           "RC-001")

    def test_history_approval_obeys_the_approver_rules(self):
        self.assertRefused(lambda d: self.with_history(d, ("1.0.0", "approved", approval())),
                           "regulated.approver_unassigned", "RC-001")

    def test_rollback_pins_a_prior_approved_version_inside_its_window(self):
        docs = documents()
        self.with_history(docs, ("1.0.0", "approved", approval()), rollback="1.0.0")
        self.run_check(docs, owner=OWNER)

    def test_rollback_to_an_unknown_version(self):
        self.assertRefused(lambda d: self.with_history(d, ("1.0.0", "draft", None), rollback="1.5.0"),
                           "regulated.rollback_target_unapproved", "RC-001", owner=OWNER)

    def test_rollback_to_an_unapproved_version(self):
        self.assertRefused(lambda d: self.with_history(d, ("1.0.0", "draft", None), rollback="1.0.0"),
                           "regulated.rollback_target_unapproved", "RC-001", owner=OWNER)

    def test_rollback_to_an_expired_approval(self):
        self.assertRefused(
            lambda d: self.with_history(d, ("1.0.0", "approved", approval(end=NOW)), rollback="1.0.0"),
            "regulated.rollback_target_unapproved", "RC-001", owner=OWNER)

    def test_version_grammar(self):
        self.assertRefused(lambda d: first(d).update(version="1.0.0-rc"), "version.grammar")

    # Review round 1 F-03: the pinned prior version carries its own text, so rollback never needs local text.
    def test_rollback_pin_renders_the_prior_versions_own_text(self):
        docs = documents()
        self.with_history(docs, ("1.0.0", "approved", approval()), rollback="1.0.0")
        view = "\n".join(content.render_regulated(self.run_check(docs, owner=OWNER).documents["regulated-copy"]))
        self.assertIn("  - 1.0.0 (approved - rollback pin): Synthetic earlier text for review.", view)

    def test_history_entry_without_its_copy_is_a_schema_failure(self):
        def mutate(d):
            self.with_history(d, ("1.0.0", "draft", None))
            del first(d)["history"][0]["copy"]
        self.assertRefused(mutate, "schema.invalid")

    def test_history_entry_bound_to_another_key(self):
        self.assertRefused(lambda d: self.with_history(d, ("1.0.0", "draft", None)) or
                           first(d)["history"][0].update(key="reg.refund.text"),
                           "regulated.history_key_mismatch", "RC-001")

    def test_history_copy_is_linted_like_current_copy(self):
        self.assertRefused(lambda d: self.with_history(d, ("1.0.0", "draft", None)) or
                           first(d)["history"][0].update(copy="Results are guaranteed."),
                           "regulated.banned_pattern", "RC-001")

    def test_rollback_pin_beside_a_usable_current_approval_is_refused(self):
        def mutate(d):
            self.with_history(d, ("1.0.0", "approved", approval()), rollback="1.0.0")
            approve(first(d))
        self.assertRefused(mutate, "regulated.rollback_with_usable_approval", "RC-001", owner=OWNER)

    # Review round 1 F-08: nobody can receive a record for review while the qualified owner is unassigned.
    def test_in_review_needs_an_assigned_approver(self):
        docs = documents()
        first(docs).update(status="in_review")
        self.run_check(docs, owner=OWNER)
        self.assertRefused(lambda d: first(d).update(status="in_review"), "regulated.review_without_approver",
                           "RC-001")

    def test_history_in_review_needs_an_assigned_approver(self):
        self.assertRefused(lambda d: self.with_history(d, ("1.0.0", "in_review", None)),
                           "regulated.review_without_approver", "RC-001")


class BaseVersioningTests(Harness):
    def check_against(self, base, mutate):
        """The control passes against the base; the one mutation of the candidate then fails."""
        self.run_check(sources=FakeSources(base))
        docs = documents()
        mutate(docs)
        with self.assertRaises(content.Refused) as caught:
            self.run_check(docs, sources=FakeSources(base))
        return caught.exception.rule, caught.exception.subject

    def test_base_that_predates_the_content_passes(self):
        self.run_check(sources=FakeSources({}))

    def test_unchanged_base_passes(self):
        self.run_check(sources=FakeSources(documents()))

    def test_git_failure_fails_closed(self):
        with self.assertRaises(content.Refused) as caught:
            self.run_check(sources=FakeSources(error=LookupError("git unavailable")))
        self.assertEqual(caught.exception.rule, "base.unavailable")

    def test_invalid_base_fails_closed(self):
        base = documents()
        del base["glossary"]["terms"]
        with self.assertRaises(content.Refused) as caught:
            self.run_check(sources=FakeSources(base))
        self.assertEqual(caught.exception.rule, "base.invalid")

    # Review round 1 F-10: the base is validated against the schemas of its own commit.
    def test_tightened_candidate_schema_still_compares_against_the_base(self):
        tightened = schemas()
        definition = tightened["glossary"]["definitions"]["term"]
        definition["required"].append("plural_label")
        definition["properties"]["plural_label"] = {"type": "string", "minLength": 1}
        docs = documents()
        docs["glossary"]["glossary_version"] = "1.0.0"
        for item in docs["glossary"]["terms"]:
            item["plural_label"] = item["preferred_label"] + "s"
        model = content.check(docs, tightened, taxonomy(), gates(), NOW, FakeSources(documents()))
        self.assertEqual(model.base_documents, content.DOCUMENTS)

    def test_base_document_without_its_schema_fails_closed(self):
        class Schemaless(FakeSources):
            def base_file(self, path):
                return None if path.endswith(".schema.json") else super().base_file(path)
        self.run_check(sources=FakeSources(documents()))  # control
        with self.assertRaises(content.Refused) as caught:
            self.run_check(sources=Schemaless(documents()))
        self.assertEqual(caught.exception.rule, "base.invalid")

    def test_base_missing_a_compared_field_fails_closed(self):
        loose = schemas()
        loose["glossary"]["required"].remove("glossary_version")
        base = documents()
        del base["glossary"]["glossary_version"]
        self.run_check(sources=FakeSources(documents(), base_schemas=loose))  # control
        with self.assertRaises(content.Refused) as caught:
            self.run_check(sources=FakeSources(base, base_schemas=loose))
        self.assertEqual(caught.exception.rule, "base.invalid")

    def test_undecodable_base_fails_closed(self):
        class Broken(FakeSources):
            def base_file(self, path):
                return b"\xff\xfe" if path.endswith("voice.json") else None
        with self.assertRaises(content.Refused) as caught:
            self.run_check(sources=Broken())
        self.assertEqual(caught.exception.rule, "base.invalid")

    def test_version_regression(self):
        base = documents()
        base["voice"]["voice_version"] = "0.2.0"
        with self.assertRaises(content.Refused) as caught:
            self.run_check(sources=FakeSources(base))
        self.assertEqual(caught.exception.rule, "version.regressed")

    def test_removing_a_term_needs_a_major_bump(self):
        base = documents()
        base["glossary"]["terms"].append(term("loan", "loan"))
        docs = documents()
        docs["glossary"]["glossary_version"] = "1.0.0"
        self.run_check(docs, sources=FakeSources(base))  # control: the removal ships with a major bump
        docs["glossary"]["glossary_version"] = "0.2.0"
        with self.assertRaises(content.Refused) as caught:
            self.run_check(docs, sources=FakeSources(base))
        self.assertEqual((caught.exception.rule, caught.exception.subject),
                         ("glossary.term_removed_without_major", "term.loan"))

    def test_removing_a_key_needs_a_major_bump(self):
        base = documents()
        base["message-keys"]["keys"].append(key("debt.edit.title", "Edit"))
        docs = documents()
        docs["message-keys"]["catalogue_version"] = "1.0.0"
        self.run_check(docs, sources=FakeSources(base))  # control: the removal ships with a major bump
        docs["message-keys"]["catalogue_version"] = "0.9.0"
        with self.assertRaises(content.Refused) as caught:
            self.run_check(docs, sources=FakeSources(base))
        self.assertEqual((caught.exception.rule, caught.exception.subject),
                         ("catalogue.key_removed_without_major", "debt.edit.title"))

    # Review round 1 F-11: additions and consumer-visible changes need at least a minor bump.
    def test_adding_a_term_needs_a_minor_bump(self):
        def add(d):
            d["glossary"]["terms"].append(term("loan", "loan"))
        docs = documents()
        add(docs)
        docs["glossary"]["glossary_version"] = "0.2.0"
        self.run_check(docs, sources=FakeSources(documents()))  # control: the addition ships with a minor bump
        self.assertEqual(self.check_against(documents(), add), ("glossary.changed_without_minor", "term.loan"))

    def test_relabelling_a_term_needs_a_minor_bump(self):
        def relabel(d):
            terms_of(d)["term.debt"].update(definition="Synthetic revised definition of debt.")
        docs = documents()
        relabel(docs)
        docs["glossary"]["glossary_version"] = "0.1.1"
        with self.assertRaises(content.Refused) as caught:  # a patch bump is not enough
            self.run_check(docs, sources=FakeSources(documents()))
        self.assertEqual(caught.exception.rule, "glossary.changed_without_minor")
        docs["glossary"]["glossary_version"] = "0.2.0"
        self.run_check(docs, sources=FakeSources(documents()))  # control
        self.assertEqual(self.check_against(documents(), relabel), ("glossary.changed_without_minor", "term.debt"))

    def test_adding_a_key_needs_a_minor_bump(self):
        self.assertEqual(self.check_against(documents(), lambda d: add_key(d, key("debt.edit.title", "Edit"))),
                         ("catalogue.changed_without_minor", "debt.edit.title"))

    def test_changing_key_copy_needs_a_minor_bump(self):
        def change(d):
            keys_of(d)["debt.delete.status"].update(copy="This debt is gone")
        docs = documents()
        change(docs)
        docs["message-keys"]["catalogue_version"] = "0.2.0"
        self.run_check(docs, sources=FakeSources(documents()))  # control
        self.assertEqual(self.check_against(documents(), change),
                         ("catalogue.changed_without_minor", "debt.delete.status"))

    def test_regulated_records_are_never_removed(self):
        base = documents()
        base["regulated-copy"]["records"].append(record(10, "consent") | {"key": "reg.consent.text"})
        docs = documents()
        docs["regulated-copy"]["regulated_version"] = "1.0.0"
        with self.assertRaises(content.Refused) as caught:
            self.run_check(docs, sources=FakeSources(base))
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("regulated.record_removed", "RC-010"))

    def test_regulated_copy_never_changes_without_a_version(self):
        base = documents()
        self.assertEqual(self.check_against(base, lambda d: first(d).update(copy="Synthetic revised text.")),
                         ("regulated.changed_without_version", "RC-001"))
        docs = documents()
        first(docs).update(copy="Synthetic revised text.", version="0.2.0",
                           history=[prior("0.1.0", "draft", None, text="Synthetic draft text for review.")])
        self.run_check(docs, sources=FakeSources(base))

    def test_new_version_keeps_the_superseded_text_in_history(self):
        # Review round 1 F-03: the base's current text moves into history; dropping it is refused.
        base = documents()
        self.assertEqual(
            self.check_against(base, lambda d: first(d).update(copy="Synthetic revised text.", version="0.2.0")),
            ("regulated.prior_version_not_kept", "RC-001"))

    def test_superseded_draft_cannot_gain_an_approval_in_history(self):
        base = documents()
        self.run_check(sources=FakeSources(base), owner=OWNER)
        docs = documents()
        first(docs).update(copy="Synthetic revised text.", version="0.2.0",
                           history=[prior("0.1.0", "approved", approval(), text="Synthetic draft text for review.")])
        with self.assertRaises(content.Refused) as caught:
            self.run_check(docs, sources=FakeSources(base), owner=OWNER)
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("regulated.history_rewritten", "RC-001"))

    # Review round 1 F-07: approval data and history are append-only against the base.
    def test_history_entries_are_byte_identical_to_the_base(self):
        base = documents()
        first(base).update(version="2.0.0", history=[prior("1.0.0", "withdrawn", None)])
        docs = documents()
        first(docs).update(version="2.0.0", history=[prior("1.0.0", "withdrawn", None)])
        self.run_check(docs, sources=FakeSources(base), owner=OWNER)  # control: unchanged history passes
        first(docs).update(history=[prior("1.0.0", "approved", approval())], rollback_version="1.0.0")
        with self.assertRaises(content.Refused) as caught:
            self.run_check(docs, sources=FakeSources(base), owner=OWNER)
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("regulated.history_rewritten", "RC-001"))

    def test_an_approval_window_cannot_be_redated_without_a_new_version(self):
        base = documents()
        approve(first(base), start=NOW - timedelta(days=285), end=NOW)
        docs = documents()
        approve(first(docs), start=NOW - timedelta(days=285), end=NOW, status="expired")
        self.run_check(docs, sources=FakeSources(base), owner=OWNER)  # control: the same approval, now expired
        approve(first(docs), start=NOW - timedelta(days=1), end=NOW + timedelta(days=364))
        with self.assertRaises(content.Refused) as caught:
            self.run_check(docs, sources=FakeSources(base), owner=OWNER)
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("regulated.approval_rewritten", "RC-001"))

    def test_withdrawn_copy_cannot_return_without_a_new_version(self):
        base = documents()
        first(base).update(status="withdrawn")
        docs = documents()
        first(docs).update(status="withdrawn")
        self.run_check(docs, sources=FakeSources(base))  # control
        first(docs).update(status="draft")
        with self.assertRaises(content.Refused) as caught:
            self.run_check(docs, sources=FakeSources(base))
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("regulated.status_reverted", "RC-001"))

    def test_regulated_record_version_never_regresses(self):
        base = documents()
        first(base)["version"] = "0.2.0"
        with self.assertRaises(content.Refused) as caught:
            self.run_check(sources=FakeSources(base))
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("version.regressed", "RC-001"))


class TaxonomyImportTests(unittest.TestCase):
    def test_published_taxonomy_is_imported_by_reference(self):
        published = content.support.load_json(ROOT / content.TAXONOMY)
        facts = content.taxonomy_facts(published)
        self.assertIs(facts["forbidden_terms"].__class__, list)
        self.assertEqual(facts["forbidden_terms"], published["forbidden_terms"])
        self.assertEqual(facts["copy_rules"], {rule["id"] for rule in published["copy_rules"]})
        self.assertEqual(facts["states"], {state["id"] for state in published["states"]})
        self.assertIn("state.permission_denied.device.action", facts["state_keys"])
        self.assertIn("state.error.validation.action", facts["state_keys"])
        self.assertIn("state.quota_exceeded.with_reset.body", facts["state_keys"])

    def test_published_design_gates_roles_include_the_legal_owner(self):
        roles = content.role_ids(content.support.load_json(ROOT / content.GATES))
        self.assertIn("legal", roles)
        self.assertIn("content", roles)

    def test_malformed_taxonomy_fails_closed(self):
        for mutate in (lambda t: t.pop("forbidden_terms"), lambda t: t.update(forbidden_terms=[]),
                       lambda t: t["states"][0].update(id="Empty State"), lambda t: t.update(copy_rules=None)):
            broken = taxonomy()
            mutate(broken)
            with self.assertRaises(content.Refused) as caught:
                content.taxonomy_facts(broken)
            self.assertEqual(caught.exception.rule, "taxonomy.unreadable")

    def test_taxonomy_deriving_a_key_that_is_also_a_node_fails_closed(self):
        content.taxonomy_facts(taxonomy())  # control
        broken = taxonomy()
        broken["states"][0]["copy"]["variants"] = {"action": {}}  # state.empty.action.headline under state.empty.action
        with self.assertRaises(content.Refused) as caught:
            content.taxonomy_facts(broken)
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("taxonomy.unreadable", None))

    def test_published_taxonomy_derives_prefix_free_state_keys(self):
        keys = sorted(content.taxonomy_facts(content.support.load_json(ROOT / content.TAXONOMY))["state_keys"])
        self.assertFalse([pair for pair in zip(keys, keys[1:]) if pair[1].startswith(pair[0] + ".")])
        self.assertEqual(len(keys), 43)  # 8 states x 3, 7 variants x 2, 5 cause or variant actions


def git_environment():
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="synthetic",
               GIT_AUTHOR_EMAIL="synthetic@localhost", GIT_COMMITTER_NAME="synthetic",
               GIT_COMMITTER_EMAIL="synthetic@localhost")
    return env


class RepositoryFixture:
    """A throwaway Git repository outside the checked repository with synthetic content at origin/main."""

    def __init__(self, directory):
        self.root = Path(directory)
        self.git = content.trusted_git(ROOT)

    def write(self, docs, taxonomy_data=None):
        for name, document in docs.items():
            self.put(content.document_path(name), document)
        for name in content.DOCUMENTS:
            source = ROOT / content.CONTENT / f"{name}.schema.json"
            self.put(f"{content.CONTENT}/{name}.schema.json", content.support.load_json(source))
        self.put(content.TAXONOMY, taxonomy() if taxonomy_data is None else taxonomy_data)
        self.put(content.GATES, gates())

    def put(self, relative, document):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")

    def run(self, *args):
        result = subprocess.run([self.git, "-c", "init.templateDir=", "-c", "commit.gpgsign=false", *args],
                                cwd=self.root, env=git_environment(), capture_output=True, timeout=30)
        if result.returncode != 0:
            raise AssertionError(result.stderr.decode("utf-8", "replace"))
        return result.stdout.decode("ascii").strip()

    def commit_as_base(self):
        self.run("init", "-q", "-b", "main")
        self.run("add", "-A")
        self.run("commit", "-q", "-m", "synthetic base")
        self.run("update-ref", "refs/remotes/origin/main", "HEAD")


class CommandLineTests(unittest.TestCase):
    """main() end to end against a throwaway repository: default mode, --structure, --now, --base, git hardening."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repository = RepositoryFixture(self.directory.name)
        self.repository.write(documents())
        self.repository.commit_as_base()

    def main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(content, "ROOT", self.repository.root), redirect_stdout(out), redirect_stderr(err):
            code = content.main(list(argv), now=NOW)
        return code, out.getvalue(), err.getvalue()

    def test_default_mode_reports_not_green_with_exact_gap_counts(self):
        code, out, err = self.main()
        self.assertEqual((code, err), (1, ""))
        lines = out.splitlines()
        self.assertEqual(lines[0], content.NOT_GREEN)
        self.assertTrue(lines[1].startswith("Content glossary 0.1.0 structure valid: 8 terms (7 need comprehension"))
        self.assertEqual(lines[2:], [
            "readiness.comprehension_evidence: 7", "readiness.reading_level_provisional: 1",
            "readiness.term_unapproved: 8", "readiness.key_unapproved: 27", "readiness.regulated_unapproved: 9",
            "readiness.approver_unassigned: 1", "readiness.nav_labels_held: 1", "readiness.pattern_slot_unstated: 25",
        ])

    def test_structure_mode_passes_without_readiness(self):
        code, out, err = self.main("--structure")
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(out.rstrip().endswith("0 approved; readiness not evaluated."))
        self.assertIn("27 keys (1 state., 0 nav., 9 reg., 2 common.)", out)

    def test_invalid_now_is_refused(self):
        self.assertEqual(self.main("--structure", "--now", "tomorrow"),
                         (1, "", "Content check refused: time.invalid\n"))

    def test_now_option_is_used(self):
        self.assertEqual(self.main("--structure", "--now", "2026-10-13T12:00:00Z")[0], 0)

    def test_removed_key_against_the_committed_base(self):
        docs = documents()
        docs["message-keys"]["keys"] = [entry for entry in docs["message-keys"]["keys"]
                                        if entry["key"] != "state.empty.headline"]
        self.repository.write(docs)
        self.assertEqual(self.main("--structure"),
                         (1, "", "Content check refused: catalogue.key_removed_without_major state.empty.headline\n"))

    def test_explicit_base_revision(self):
        self.assertEqual(self.main("--structure", "--base", "main")[0], 0)

    def test_unsafe_or_unknown_base_revision_fails_closed(self):
        for revision in ("--output=x", "no-such-branch"):
            with self.subTest(revision=revision):
                self.assertEqual(self.main("--structure", f"--base={revision}"),
                                 (1, "", "Content check refused: base.unavailable\n"))

    def test_missing_base_ref_fails_closed(self):
        self.repository.run("update-ref", "-d", "refs/remotes/origin/main")
        self.assertEqual(self.main("--structure"), (1, "", "Content check refused: base.unavailable\n"))

    def test_missing_document_is_unreadable(self):
        (self.repository.root / content.document_path("voice")).unlink()
        self.assertEqual(self.main(), (1, "", "Content check refused: input.unreadable_or_invalid\n"))

    def test_duplicate_json_key_is_unreadable(self):
        target = self.repository.root / content.document_path("glossary")
        text = target.read_text(encoding="utf-8")
        text = text.replace('"schema_version": 1,', '"schema_version": 1, "schema_version": 1,', 1)
        target.write_text(text, encoding="utf-8", newline="\n")
        self.assertEqual(self.main(), (1, "", "Content check refused: input.unreadable_or_invalid\n"))

    def test_hostile_bytes_fail_closed_without_echo(self):
        self.assertEqual(self.main()[0], 1)  # control: NOT GREEN, not refused
        self.assertEqual(self.main()[2], "")
        target = self.repository.root / content.document_path("voice")
        original = target.read_bytes()
        cases = {
            "invalid UTF-8": original.replace(b'"voice_version"', b'"voice_\xff_version"', 1),
            "byte order mark": b"\xef\xbb\xbf" + original,
            "deep nesting": b'{"schema_version": ' + b"[" * 100000 + b"]" * 100000 + b"}\n",
        }
        for label, raw in cases.items():
            with self.subTest(case=label):
                target.write_bytes(raw)
                self.assertEqual(self.main(), (1, "", "Content check refused: input.unreadable_or_invalid\n"))
        target.write_bytes(original)

    def test_git_inside_the_checked_repository_is_never_used(self):
        planted = self.repository.root / "bin"
        planted.mkdir()
        fake = planted / "git"
        fake.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake.chmod(0o755)
        path = os.pathsep.join(("bin", str(planted), os.environ.get("PATH", "")))
        with mock.patch.dict(os.environ, {"PATH": path}):
            chosen = content.trusted_git(self.repository.root)
        self.assertNotIn(str(self.repository.root.resolve()), str(Path(chosen).resolve()))
        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join(("bin", str(planted)))}):
            with self.assertRaises(LookupError):
                content.trusted_git(self.repository.root)


class SchemaTests(unittest.TestCase):
    def schema_paths(self):
        return [ROOT / content.CONTENT / f"{name}.schema.json" for name in content.DOCUMENTS]

    def test_schemas_use_only_the_shared_draft07_subset(self):
        allowed = content.support.SUPPORTED | content.support.ANNOTATIONS

        def walk(node):
            if isinstance(node, dict):
                self.assertLessEqual(set(node), allowed, set(node) - allowed)
                for keyword, value in node.items():
                    if keyword in ("properties", "definitions"):
                        for child in value.values():
                            walk(child)
                    elif keyword in ("items", "additionalProperties") and isinstance(value, dict):
                        walk(value)
        for path in self.schema_paths():
            with self.subTest(schema=path.name):
                walk(content.support.load_json(path))

    def test_schemas_are_canonical_json(self):
        for path in self.schema_paths():
            with self.subTest(schema=path.name):
                raw = path.read_bytes()
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
                self.assertNotIn(b"\r", raw)
                expected = json.dumps(content.support.load_json(path), indent=2, ensure_ascii=True) + "\n"
                self.assertEqual(raw.decode("utf-8"), expected)

    def test_unsupported_schema_keyword_is_refused(self):
        broken = schemas()
        broken["glossary"]["definitions"]["term"]["properties"]["id"]["maxLength"] = 40
        content.check(documents(), schemas(), taxonomy(), gates(), NOW, FakeSources())  # control
        with self.assertRaises(content.Refused) as caught:
            content.check(documents(), broken, taxonomy(), gates(), NOW, FakeSources())
        self.assertEqual(caught.exception.rule, "schema.invalid")

    def test_grammars_are_anchored_by_fullmatch(self):
        self.assertIsNone(content.KEY.fullmatch("debt.title\n"))
        self.assertIsNone(content.TERM.fullmatch("term.debt.extra"))
        self.assertIsNone(content.REGULATED.fullmatch("RC-0011"))


def published():
    """The committed content documents checked against the committed taxonomy and design-gates roles."""
    docs, published_schemas = content.load_documents(ROOT)
    model = content.check(
        docs, published_schemas, content.support.load_json(ROOT / content.TAXONOMY),
        content.support.load_json(ROOT / content.GATES), NOW, FakeSources(),
    )
    return docs, model


class PublishedContentTests(unittest.TestCase):
    """The published documents: structure passes, every judgment stays proposed and the gaps are exactly these."""

    @classmethod
    def setUpClass(cls):
        cls.docs, cls.model = published()

    def test_published_content_passes_structure(self):
        self.assertEqual(content.structure_line(self.model), (
            "Content glossary 0.1.0 structure valid: 30 terms (7 need comprehension evidence); voice 0.1.0: 18 "
            "banned patterns, 8 content patterns, taxonomy copy rules imported by reference; message keys 0.1.0: "
            "81 keys (43 state., 0 nav., 11 reg., 12 common.); regulated copy 0.1.0: 11 records, 0 approved"
        ))

    def test_published_readiness_gaps_are_exact(self):
        gaps = content.readiness(self.model)
        self.assertEqual(gaps["readiness.comprehension_evidence"], sorted(f"term.{slug}" for slug in COMPREHENSION))
        self.assertEqual(gaps["readiness.reading_level_provisional"], ["voice.reading_level"])
        self.assertEqual(len(gaps["readiness.term_unapproved"]), 30)
        self.assertEqual(gaps["readiness.term_unapproved"], sorted(terms_of(self.docs)))
        self.assertEqual(len(gaps["readiness.key_unapproved"]), 81)
        self.assertEqual(gaps["readiness.key_unapproved"], sorted(keys_of(self.docs)))
        self.assertEqual(gaps["readiness.regulated_unapproved"], [f"RC-{n:03d}" for n in range(1, 12)])
        self.assertEqual(gaps["readiness.approver_unassigned"], ["approver_role"])
        self.assertEqual(gaps["readiness.nav_labels_held"], ["PenniLogic/docs#74"])
        self.assertEqual(gaps["readiness.pattern_slot_unstated"], sorted(
            [f"pattern.{identifier}.{slot}" for identifier in ("empty", "loading", "error")
             for slot in ("source", "consequence", "safe_remainder")]
            + ["pattern.stale.consequence", "pattern.stale.safe_remainder", "pattern.denied.source",
               "pattern.denied.consequence"]))

    def test_published_pattern_copy_agrees_with_the_plural_item(self):
        # Review round 2 SS-09 (round 1 F-17): {item} is the surface's plural noun.
        keys = keys_of(self.docs)
        self.assertEqual([keys[key]["copy"] for key in (
            "pattern.recovery.status", "pattern.success.status", "pattern.destructive.consequence")],
            ["{item} are back", "{item} are saved", "This can't be undone and their history goes with them"])

    def test_every_published_judgment_is_proposed_and_nothing_is_approved(self):
        self.assertEqual(self.docs["glossary"]["status"], "provisional")
        self.assertEqual({term["status"] for term in self.docs["glossary"]["terms"]}, {"provisional"})
        self.assertEqual({entry["status"] for entry in self.docs["message-keys"]["keys"]}, {"provisional"})
        reading = self.docs["voice"]["reading_level"]
        self.assertEqual((reading["status"], reading["evidence_ref"]), ("provisional", "pending:PenniLogic/docs#66"))
        for record in self.docs["regulated-copy"]["records"]:
            with self.subTest(record=record["id"]):
                self.assertEqual((record["status"], record["approval"], record["history"], record["rollback_version"]),
                                 ("draft", None, [], None))
        for term in self.docs["glossary"]["terms"]:
            with self.subTest(term=term["id"]):
                expected = "pending:PenniLogic/docs#66" if term["comprehension"]["required"] else None
                self.assertEqual(term["comprehension"]["evidence_ref"], expected)
                self.assertEqual(term["contract_field_names"], [])  # contracts owns field names; none invented

    def test_published_banned_phrases_catch_inflected_and_respelled_forms(self):
        # Review round 1 F-05: the reviewer's bypasses, each refused by the published voice; the control passes.
        phrases = [pattern["phrase"] for pattern in self.docs["voice"]["banned_patterns"]]
        self.assertIsNone(content.banned_in("Your payoff date is a projection", phrases))
        for text in ("We guarantee your payoff date", "Our plan guarantees lower interest", "Guaranteeing a date",
                     "You will be debt-free by June", "This method is risk free", "You are bad  with money",
                     "A life changing result", "You should've paid on time"):
            with self.subTest(text=text):
                self.assertIsNotNone(content.banned_in(text, phrases))

    def test_published_state_keys_are_exactly_the_taxonomy_derived_set(self):
        facts = content.taxonomy_facts(content.support.load_json(ROOT / content.TAXONOMY))
        state = {key: entry for key, entry in keys_of(self.docs).items() if key.startswith("state.")}
        self.assertEqual(set(state), facts["state_keys"])
        self.assertEqual({entry["copy"] for entry in state.values()}, {None})

    def test_no_nav_key_is_published_while_docs74_holds_the_labels(self):
        self.assertEqual([key for key in keys_of(self.docs) if key.startswith("nav.")], [])

    def test_each_regulated_key_binds_its_record_and_falls_back_to_neutral_copy(self):
        keys = keys_of(self.docs)
        records = self.docs["regulated-copy"]["records"]
        self.assertEqual({record["category"] for record in records}, set(CATEGORIES))
        # AI disclosure and advice/projection boundaries are regulated (product/08 s12): no disclosure key outside reg.
        self.assertEqual([entry["key"] for entry in keys.values()
                          if entry["category"] == "disclosure" and not entry["key"].startswith("reg.")], [])
        for record in records:
            with self.subTest(record=record["id"]):
                self.assertEqual(keys[record["key"]]["regulated_ref"], record["id"])
                fallback = keys[record["fail_closed_key"]]
                self.assertTrue(fallback["neutral_safe_exit"])
                self.assertNotIn("{", fallback["copy"])

    def test_published_documents_are_canonical_json(self):
        for name in content.DOCUMENTS:
            with self.subTest(document=name):
                raw = (ROOT / content.document_path(name)).read_bytes()
                self.assertNotIn(b"\r", raw)
                expected = json.dumps(content.support.load_json(ROOT / content.document_path(name)), indent=2,
                                      ensure_ascii=True) + "\n"
                self.assertEqual(raw.decode("utf-8"), expected)

    def test_published_views_match_the_documents_byte_for_byte(self):
        views = content.render_views(self.model)
        self.assertEqual(sorted(views), [f"product/content/{name}.md" for name in sorted(content.DOCUMENTS)])
        for relative, text in views.items():
            with self.subTest(view=relative):
                self.assertEqual((ROOT / relative).read_bytes(), text.encode("utf-8"))
        content.check_views(ROOT, views)

def git_output(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


class PublishedGitPathTests(unittest.TestCase):
    """Review round 1 F-02: the published documents through the real loader, GitSources and main(), so CI enforces
    the additive-versioning and base rules (unittest discover is the only content gate CI runs)."""

    def test_published_content_passes_against_the_real_merge_base_at_the_real_clock(self):
        model = content.load_and_check(ROOT, datetime.now(timezone.utc))
        merge_base = git_output("merge-base", "HEAD", content.BASE_REF)
        present = tuple(name for name in content.DOCUMENTS
                        if git_output("ls-tree", "--name-only", merge_base, "--", content.document_path(name)))
        self.assertEqual(model.base_documents, present)  # which comparisons ran: none before the first merge

    def test_published_structure_mode_exits_zero_through_main(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = content.main(["--structure"])
        self.assertEqual((code, err.getvalue()), (0, ""))
        self.assertTrue(out.getvalue().endswith("; readiness not evaluated.\n"))


class ViewTests(unittest.TestCase):
    """--write-views and --check-views against a throwaway repository; rendering is inert and deterministic."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repository = RepositoryFixture(self.directory.name)
        self.repository.write(documents())
        self.repository.commit_as_base()
        self.views = self.repository.root / content.CONTENT

    def main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(content, "ROOT", self.repository.root), redirect_stdout(out), redirect_stderr(err):
            code = content.main(list(argv), now=NOW)
        return code, out.getvalue(), err.getvalue()

    def test_written_views_then_match(self):
        self.assertEqual(self.main("--check-views"), (1, "", "Content check refused: views.missing\n"))
        self.assertEqual(self.main("--write-views"), (0, "Content views written: 4\n", ""))
        self.assertEqual(self.main("--check-views"), (0, "Content views match: 4\n", ""))
        written = (self.views / "glossary.md").read_bytes()
        self.assertTrue(written.endswith(b"\n") and b"\r" not in written)

    def test_one_changed_byte_is_drift(self):
        self.main("--write-views")
        self.assertEqual(self.main("--check-views")[0], 0)  # control
        target = self.views / "voice.md"
        target.write_bytes(target.read_bytes().replace(b"Voice and tone", b"Voice and Tone", 1))
        self.assertEqual(self.main("--check-views"), (1, "", "Content check refused: views.drift\n"))

    def test_a_symlinked_view_is_never_read_or_written(self):
        self.main("--write-views")
        self.assertEqual(self.main("--check-views")[0], 0)  # control
        outside = Path(self.directory.name) / "outside.md"
        outside.write_bytes((self.views / "glossary.md").read_bytes())
        (self.views / "glossary.md").unlink()
        try:
            (self.views / "glossary.md").symlink_to(outside)
        except OSError:
            self.skipTest("symbolic links are not available to this user")
        self.assertEqual(self.main("--check-views"), (1, "", "Content check refused: views.unsafe_path\n"))
        self.assertEqual(self.main("--write-views"), (1, "", "Content check refused: views.unsafe_path\n"))
        self.assertEqual(outside.read_bytes(), (self.views / "glossary.md").read_bytes())

    def test_views_are_not_written_when_structure_fails(self):
        docs = documents()
        docs["glossary"]["terms"].append(copy.deepcopy(docs["glossary"]["terms"][0]))
        self.repository.write(docs)
        self.assertEqual(self.main("--write-views"),
                         (1, "", "Content check refused: term.duplicate_id term.payoff\n"))
        self.assertFalse((self.views / "glossary.md").exists())

    def test_write_replaces_the_entry_and_never_writes_through_a_hard_link(self):
        self.main("--write-views")
        view = self.views / "voice.md"
        other = Path(self.directory.name) / "linked.md"
        try:
            os.link(view, other)
        except OSError:
            self.skipTest("hard links are not available here")
        view.write_bytes(b"stale\n")  # both names now read "stale"
        self.assertEqual(self.main("--write-views")[0], 0)
        self.assertEqual(other.read_bytes(), b"stale\n")
        self.assertEqual(self.main("--check-views")[0], 0)
        self.assertEqual(sorted(path.name for path in self.views.glob(".view-*")), [])

    def test_modes_are_mutually_exclusive(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            content.main(["--structure", "--check-views"], now=NOW)

    def test_free_text_is_rendered_inert(self):
        self.assertEqual(content.cell("a|b*c<d>e`f_g[h]i\\j#k&l~m"),
                         "a\\|b\\*c\\<d\\>e\\`f\\_g\\[h\\]i\\\\j\\#k\\&l\\~m")
        docs = documents()
        terms_of(docs)["term.debt"]["definition"] = "Owed money | <b>bold</b> and [link](x)."
        lines = content.render_glossary(docs["glossary"])
        row = next(line for line in lines if line.startswith("| `term.debt`"))
        self.assertEqual(len(re.findall(r"(?<!\\)\|", row)), 9)  # eight columns, no injected cell
        self.assertNotIn("<b>", row)

    def test_rendering_is_deterministic(self):
        model = content.check(documents(), schemas(), taxonomy(), gates(), NOW, FakeSources())
        first, second = content.render_views(model), content.render_views(model)
        self.assertEqual(first, second)
        self.assertTrue(all(text.endswith("\n") and "\r" not in text for text in first.values()))

    def test_an_approval_window_is_rendered_from_the_record(self):
        docs = documents()
        first = docs["regulated-copy"]["records"][0]
        first.update(status="approved", approval=approval())
        model = content.check(docs, schemas(), taxonomy(), gates(), NOW, FakeSources(), OWNER)
        text = content.render_views(model)["product/content/regulated-copy.md"]
        self.assertIn("| RC-001 | consent | `reg.consent.text` | 0.1.0 | approved | 2026-10-03T12:00:00Z to "
                      "2026-10-23T12:00:00Z |", text)

if __name__ == "__main__":
    unittest.main()
