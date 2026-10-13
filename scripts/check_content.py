"""Offline T-CNT-01 checks of the product glossary, voice rules, message-key catalogue and regulated-copy records.

PenniLogic/docs#84 publishes product/content/glossary.json, voice.json, message-keys.json and regulated-copy.json,
each validated against its own self-contained draft-07 subset schema in product/content/. The client-state taxonomy
(product/client-state-taxonomy.json, PenniLogic/docs#1) is imported read-only through the shared loader of
scripts/check_client_states.py: its forbidden terms and copy rules are applied by reference and never restated, and
`state.` message keys are derived from its state identifiers. Roles come read-only from governance/design-gates.json.

Grammars: terms `term.<slug>`; message keys `[a-z][a-z0-9_]*(\\.[a-z0-9_]+)+` with the reserved roots `state.`
(taxonomy-derived), `nav.` (docs#74 labels, held), `reg.` (regulated) and `common.`; regulated copy `RC-NNN`.
Regulated copy is approved only by the qualified legal/compliance owner (design-gates role `legal`), which is
unassigned: this validator is never given an assignment from the published data, so every approval is refused and
every record stays draft. Approval windows are evaluated with an injected clock; `now == expires_at` is expired.

Structure failures raise `Refused` with a static rule identifier plus, at most, identifiers that match a term, key,
regulated-copy, pattern or issue grammar; copy text is never echoed. Readiness gaps (comprehension evidence held by
PenniLogic/docs#66, the provisional reading level, unapproved terms, keys and regulated copy, the unassigned approver
and the docs#74 hold on `nav.` labels) are counted, never filled in, and keep the default mode NOT GREEN.
`--write-views` regenerates the Markdown views product/content/{glossary,voice,message-keys,regulated-copy}.md from
the checked documents and `--check-views` fails when they drift; free text is rendered with Markdown escaped.
Everything runs offline against local files and the local Git object store: no network, remote action, approval,
legal interpretation or comprehension result is made or implied.
"""

import argparse
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
CONTENT = "product/content"
DOCUMENTS = ("glossary", "voice", "message-keys", "regulated-copy")
TAXONOMY = "product/client-state-taxonomy.json"
GATES = "governance/design-gates.json"
# The full remote-tracking ref: a local branch named origin/main must not shadow it.
BASE_REF = "refs/remotes/origin/main"
GREEN = "GREEN: readiness complete"
NOT_GREEN = "NOT GREEN: readiness incomplete"
SOURCE_ISSUE = "PenniLogic/docs#84"


def _sibling(name, filename):
    """Load an accepted sibling checker read-only by path, as check_design_gates.py does."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


support = _sibling("content_schema_support", "check_client_states.py")

TERM = re.compile(r"term\.[a-z0-9_]+")
KEY = re.compile(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+)+")
REGULATED = re.compile(r"RC-([0-9]{3})")
SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
SNAKE = re.compile(r"[a-z][a-z0-9_]*")
INSTANT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
ISSUE_REF = re.compile(r"PenniLogic/(docs|contracts|infra|api|android|web|admin)#[1-9][0-9]*")
PLACEHOLDER = re.compile(r"\{([^{}]*)\}")

RESERVED_ROOTS = ("state", "nav", "reg", "common")
# Vocabularies are disjoint: a key root may not be another namespace's prefix.
FOREIGN_ROOTS = ("term", "voice", "banned", "convention")
CLIENTS = ("android", "web", "admin")
# Comprehension testing covers exactly these terms (acceptance criterion 5); evidence is held by docs#66.
COMPREHENSION_TERMS = (
    "term.payoff", "term.projected", "term.available", "term.pending", "term.reversed", "term.aggregate",
    "term.revoked",
)
COMPREHENSION_SOURCE = "pending:PenniLogic/docs#66"
READING_LEVEL_SOURCE = "pending:PenniLogic/docs#66"
BANNED_CATEGORIES = ("shame", "guarantee", "hype", "advice")
# The eight content patterns of the scope; five reuse a taxonomy state instead of restating its copy.
PATTERN_STATES = {
    "empty": "empty", "loading": "loading", "error": "error", "stale": "stale", "denied": "permission_denied",
    "destructive": None, "success": None, "recovery": None,
}
SLOTS = ("source", "status", "consequence", "safe_remainder", "next_action")
REGULATED_CATEGORIES = (
    "consent", "permission", "disclaimer", "plan_change", "refund", "deletion", "access", "incident", "ai_disclosure",
)
# The qualified legal/compliance owner: the design-gates `legal` role, explicitly unassigned there.
APPROVER_ROLE = "legal"
# Neutral safe-exit copy must exist for shared-device and coercive contexts (security and privacy section).
SAFE_EXIT_CATEGORIES = ("notification", "denial")
# A placeholder whose name carries one of these parts would echo raw content, credentials or hidden identity.
PROHIBITED_PLACEHOLDER_PARTS = (
    "password", "passcode", "otp", "pin", "token", "secret", "credential", "key", "account", "card", "email",
    "phone", "name", "operator", "agent", "raw", "message", "body", "content", "note", "resource", "user",
    "member", "amount", "balance",
)
# Numeric bounds are enforced here, not in the schemas (shared draft-07 subset).
SENTENCE_WORDS = (8, 40)
RANGE_LIMIT = 2000
TEXT_LIMIT = 600
APPROVAL_LIFETIME = timedelta(days=366)
SCRUBBED_GIT_VARIABLES = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR", "GIT_NAMESPACE",
)
COMMIT = re.compile(r"[0-9a-f]{40}")
REVISION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,199}")
VOICE_ID = {
    "principles": re.compile(r"voice\.[a-z0-9_]+"),
    "banned_patterns": re.compile(r"banned\.[a-z0-9_]+"),
    "conventions": re.compile(r"convention\.[a-z0-9_]+"),
}

STRUCTURE_RULES = (
    "input.unreadable_or_invalid", "schema.invalid", "taxonomy.unreadable", "roles.unreadable",
    "content.too_long", "content.blank_or_padded", "content.unprintable_character", "content.secret_shape",
    "content.non_ascii_word_character", "content.url_shape", "content.email_shape", "content.number_shape",
    "version.grammar", "owner.unknown_role",
    "term.id_grammar", "term.duplicate_id", "term.duplicate_label", "term.alias_is_label", "term.alias_collision",
    "term.forbidden_term", "term.banned_pattern", "term.forbidden_alias", "term.contract_field_grammar",
    "term.contract_field_conflict",
    "term.comprehension_term_missing", "term.comprehension_not_required", "held.comprehension_evidence",
    "held.term_approval",
    "voice.id_grammar", "voice.duplicate_id", "voice.sentence_limit_range", "held.reading_level",
    "taxonomy.unknown_copy_rule", "taxonomy.copy_rule_missing", "taxonomy.forked_forbidden_term",
    "voice.duplicate_pattern", "voice.banned_category_missing", "voice.forbidden_term",
    "pattern.duplicate", "pattern.missing", "pattern.state_mismatch", "pattern.state_copy_forked",
    "pattern.slot_missing", "pattern.unknown_key",
    "placeholder.grammar", "placeholder.duplicate", "placeholder.shadows_taxonomy", "placeholder.prohibited",
    "key.term_surface_missing", "key.grammar", "key.duplicate", "key.prefix_conflict", "key.foreign_root",
    "key.state_not_in_taxonomy",
    "key.state_copy_forked", "held.nav_key", "key.regulated_outside_root", "key.regulated_root_without_record",
    "key.regulated_copy_forked", "key.disclosure_outside_reg", "key.regulated_copy_restated", "key.common_not_shared",
    "key.copy_missing", "key.range_order",
    "key.copy_out_of_range", "key.unknown_term", "key.term_label_missing", "key.forbidden_term",
    "key.forbidden_alias", "key.banned_pattern", "key.sentence_too_long", "key.placeholder_unknown",
    "key.safe_exit_placeholder", "key.neutral_safe_exit_missing", "held.key_approval",
    "regulated.id_grammar", "regulated.duplicate_id", "regulated.approver_role_unqualified",
    "regulated.category_missing", "regulated.key_mismatch", "regulated.fail_closed_key_unknown",
    "regulated.fail_closed_key_unsafe", "regulated.forbidden_term", "regulated.forbidden_alias",
    "regulated.banned_pattern", "regulated.sentence_too_long", "regulated.placeholder_unknown",
    "regulated.term_label_missing",
    "regulated.approval_missing", "regulated.approval_unexpected", "regulated.approver_role_mismatch",
    "regulated.approver_unassigned", "regulated.approval_evidence_missing", "time.invalid", "time.untrusted_clock",
    "regulated.approval_window_invalid", "regulated.approval_lifetime", "regulated.approval_not_yet_effective",
    "regulated.approval_expired", "regulated.expired_status_mismatch", "regulated.history_order",
    "regulated.rollback_target_unapproved",
    "base.unavailable", "base.invalid", "version.regressed", "glossary.term_removed_without_major",
    "catalogue.key_removed_without_major", "regulated.record_removed", "regulated.changed_without_version",
    "views.unsafe_path", "views.missing", "views.drift",
)
READINESS_RULES = (
    "readiness.comprehension_evidence", "readiness.reading_level_provisional", "readiness.term_unapproved",
    "readiness.key_unapproved", "readiness.regulated_unapproved", "readiness.approver_unassigned",
    "readiness.nav_labels_held",
)
# nav. keys carry docs#74 navigation labels; until docs#74 publishes them every nav. key is refused (held.nav_key).
NAV_SOURCE = "PenniLogic/docs#74"


def printable(value):
    """Only grammar-validated identifiers may appear in output; everything else is input text."""
    return isinstance(value, str) and (
        any(grammar.fullmatch(value) for grammar in (TERM, KEY, REGULATED, ISSUE_REF))
        or value in PATTERN_STATES
    )


class Refused(ValueError):
    """A static rule identifier plus at most grammar-validated identifiers; never echoes input text."""

    def __init__(self, rule, *subjects):
        self.rule = rule
        self.subject = " ".join(subjects) if subjects and all(printable(item) for item in subjects) else None
        super().__init__(rule if self.subject is None else f"{rule} {self.subject}")


def require(condition, rule, *subjects):
    if not condition:
        raise Refused(rule, *subjects)


def shape(value, schema):
    """Validate with the shared subset validator; its messages echo input, so only the rule survives."""
    try:
        support.validate_schema(value, schema)
    except (ValueError, KeyError, TypeError, RecursionError, re.error):  # re.error: a malformed pattern
        raise Refused("schema.invalid") from None


def version(value):
    match = SEMVER.fullmatch(value) if isinstance(value, str) else None
    require(match is not None, "version.grammar")
    return tuple(int(part) for part in match.groups())


CONTENT_SHAPES = (
    ("content.url_shape", re.compile(r"[a-z][a-z0-9+.-]*://|\bwww\.|\b[a-z0-9-]+\.(com|net|org|io|in|app|dev)\b",
                                     re.IGNORECASE)),
    ("content.email_shape", re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")),
    ("content.number_shape", re.compile(
        r"[0-9](?:[^A-Za-z0-9\n]{0,2}[0-9]){4,}|[$£€₹¥]\s?[0-9]|[0-9]\s?[$£€₹¥]"
        r"|\b(?:INR|USD|EUR|GBP|Rs)\.?\s?[0-9]|[0-9]\s?(?:INR|USD|EUR|GBP)\b"
    )),
)
SECRET_RUN = re.compile(r"[A-Za-z0-9+/=_-]{24,}")
HEX_RUN = re.compile(r"[0-9a-fA-F]{24,}")


def _secret_shape(text):
    """A key-shaped run: long hex, or a long mixed run with digits and both letter cases (or digits and letters)."""
    if HEX_RUN.search(text):
        return True
    for match in SECRET_RUN.finditer(text):
        run = match.group()
        if any(c.isdigit() for c in run) and any(c.isalpha() for c in run):
            return True
    return False


def scan_text(text, subject):
    """Refuse free text that is blank, padded, unprintable, overlong or shaped like a secret, URL, email or number."""
    require(text != "" and text.strip() == text, "content.blank_or_padded", *subject)
    require(len(text) <= TEXT_LIMIT, "content.too_long", *subject)
    require(all(character.isprintable() for character in text), "content.unprintable_character", *subject)
    # Source copy is English: a non-ASCII letter, mark or digit (a homoglyph, a combining mark, a native-script digit)
    # would slip past the word-bounded ASCII lints, so only ASCII ones are accepted; symbols such as an apostrophe stay.
    require(all(character.isascii() or unicodedata.category(character)[0] not in "LMN" for character in text),
            "content.non_ascii_word_character", *subject)
    require(not _secret_shape(text), "content.secret_shape", *subject)
    for rule, pattern in CONTENT_SHAPES:
        require(pattern.search(text) is None, rule, *subject)


def guard_content(document):
    """Scan every key and string value of a document; instants and versions with their exact grammar are exempt."""
    def walk(value, subject):
        if isinstance(value, dict):
            for field in ("id", "key"):
                if printable(value.get(field)):
                    subject = (value[field],)
                    break
            for key, item in value.items():
                scan_text(key, subject)
                walk(item, subject)
        elif isinstance(value, list):
            for item in value:
                walk(item, subject)
        elif isinstance(value, str) and not (INSTANT.fullmatch(value) or SEMVER.fullmatch(value)):
            scan_text(value, subject)

    walk(document, ())


def taxonomy_facts(taxonomy):
    """Import (never fork) the taxonomy's forbidden terms, copy rules, placeholders and state identifiers."""
    try:
        forbidden = list(taxonomy["forbidden_terms"])
        copy_rules = {rule["id"] for rule in taxonomy["copy_rules"]}
        placeholders = {placeholder["id"] for placeholder in taxonomy["placeholders"]}
        states, keys = set(), set()
        for state in taxonomy["states"]:
            identifier = state["id"]
            states.add(identifier)
            keys.update(f"state.{identifier}.{field}" for field in ("headline", "body", "action"))
            for variant in state["copy"].get("variants", {}):
                keys.update(f"state.{identifier}.{variant}.{field}" for field in ("headline", "body"))
            action = state["recovery_action"]
            for field in ("label_by_cause", "label_by_variant"):
                # A variant or cause label sits beside that variant's copy, so no derived key is also a node.
                keys.update(f"state.{identifier}.{name}.action" for name in action.get(field, {}))
        ordered = sorted(keys)
        valid = (
            forbidden and all(isinstance(term, str) and term for term in forbidden) and copy_rules and states
            and all(isinstance(item, str) and SNAKE.fullmatch(item) for item in copy_rules | placeholders | states)
            and all(KEY.fullmatch(key) for key in keys)
            and not any(after.startswith(before + ".") for before, after in zip(ordered, ordered[1:]))
        )
    except (KeyError, TypeError, AttributeError):
        valid = False
    require(valid, "taxonomy.unreadable")
    return {
        "forbidden_terms": forbidden, "copy_rules": copy_rules, "placeholders": placeholders, "states": states,
        "state_keys": keys,
    }


def role_ids(gates):
    """Role identifiers of governance/design-gates.json, read-only; the approver role must be among them."""
    try:
        roles = {role["id"] for role in gates["roles"]}
        valid = bool(roles) and all(isinstance(role, str) and SNAKE.fullmatch(role) for role in roles)
    except (KeyError, TypeError):
        valid = False
    require(valid and APPROVER_ROLE in roles, "roles.unreadable")
    return roles


def forbidden_in(text, terms):
    """The shared taxonomy matcher (check_client_states.forbidden_term): word-bounded, case-insensitive."""
    return support.forbidden_term(text, terms)


def words_per_sentence(text):
    """Word counts of each sentence, with placeholders counted as one word."""
    sentences = [part for part in re.split(r"[.?!:;]+(?:\s|$)", PLACEHOLDER.sub("x", text)) if part.strip()]
    return [len(sentence.split()) for sentence in sentences]


def _unique(identifiers, grammar, grammar_rule, duplicate_rule):
    seen = set()
    for identifier in identifiers:
        require(isinstance(identifier, str) and grammar.fullmatch(identifier) is not None, grammar_rule)
        require(identifier not in seen, duplicate_rule, identifier)
        seen.add(identifier)
    return seen


def check_glossary(glossary, facts, roles):
    """One definition and preferred label per term; aliases never collide; comprehension evidence stays held."""
    version(glossary["glossary_version"])
    terms = glossary["terms"]
    _unique([term["id"] for term in terms], TERM, "term.id_grammar", "term.duplicate_id")
    index, labels, fields = {}, {}, {}
    forbidden = {term.casefold() for term in facts["forbidden_terms"]}
    for term in terms:
        identifier, label = term["id"], term["preferred_label"].casefold()
        require(term["owner"] in roles, "owner.unknown_role", identifier)
        require(label not in labels, "term.duplicate_label", labels.get(label, identifier), identifier)
        labels[label] = identifier
        for text in (term["preferred_label"], term["definition"]):
            require(forbidden_in(text, facts["forbidden_terms"]) is None, "term.forbidden_term", identifier)
        for field in term["contract_field_names"]:
            require(SNAKE.fullmatch(field) is not None, "term.contract_field_grammar", identifier)
            require(field not in fields, "term.contract_field_conflict", fields.get(field, identifier), identifier)
            fields[field] = identifier
        comprehension = term["comprehension"]
        require(comprehension["evidence_ref"] in (None, COMPREHENSION_SOURCE), "held.comprehension_evidence",
                identifier)
        require(term["status"] == "provisional", "held.term_approval", identifier)
        index[identifier] = term
    for term in terms:
        for alias in term["forbidden_aliases"]:
            folded = alias.casefold()
            require(folded not in forbidden, "taxonomy.forked_forbidden_term", term["id"])
            require(folded != term["preferred_label"].casefold(), "term.alias_is_label", term["id"])
            require(folded not in labels, "term.alias_collision", term["id"], labels.get(folded, term["id"]))
    for identifier in COMPREHENSION_TERMS:
        require(identifier in index, "term.comprehension_term_missing", identifier)
        require(index[identifier]["comprehension"]["required"] is True, "term.comprehension_not_required", identifier)
    return index


def check_voice(voice, facts):
    """Voice rules import the taxonomy copy rules by identifier and add only non-overlapping banned patterns."""
    version(voice["voice_version"])
    for field, grammar in VOICE_ID.items():
        _unique([item["id"] for item in voice[field]], grammar, "voice.id_grammar", "voice.duplicate_id")
    low, high = SENTENCE_WORDS
    require(low <= voice["max_sentence_words"] <= high, "voice.sentence_limit_range")
    reading = voice["reading_level"]
    require(reading["status"] == "provisional" and reading["evidence_ref"] in (None, READING_LEVEL_SOURCE),
            "held.reading_level")
    cited = set(voice["taxonomy_copy_rules"])
    require(cited <= facts["copy_rules"], "taxonomy.unknown_copy_rule")
    require(facts["copy_rules"] <= cited, "taxonomy.copy_rule_missing")
    phrases = set()
    for pattern in voice["banned_patterns"]:
        phrase = pattern["phrase"].casefold()
        require(phrase not in phrases, "voice.duplicate_pattern", pattern["id"])
        phrases.add(phrase)
        # Overlap with the imported list in either direction is a fork of the taxonomy's forbidden terms.
        require(forbidden_in(phrase, facts["forbidden_terms"]) is None
                and all(phrase not in term.casefold() for term in facts["forbidden_terms"]),
                "taxonomy.forked_forbidden_term", pattern["id"])
    for category in BANNED_CATEGORIES:
        require(any(pattern["category"] == category for pattern in voice["banned_patterns"]),
                "voice.banned_category_missing")
    for item in (*voice["principles"], *voice["conventions"]):
        require(forbidden_in(item["rule"], facts["forbidden_terms"]) is None, "voice.forbidden_term", item["id"])
    return [pattern["phrase"] for pattern in voice["banned_patterns"]]


def check_term_wording(glossary, banned):
    """Labels and definitions follow the voice too: no banned phrase and no term's forbidden alias."""
    aliases = [alias.casefold() for term in glossary["terms"] for alias in term["forbidden_aliases"]]
    for term in glossary["terms"]:
        for text in (term["preferred_label"], term["definition"]):
            require(banned_in(text, banned) is None, "term.banned_pattern", term["id"])
            require(forbidden_in(text, aliases) is None, "term.forbidden_alias", term["id"])


def banned_in(text, phrases):
    """The first banned voice phrase in text, matched like the taxonomy's forbidden terms."""
    return support.forbidden_term(text, [phrase.casefold() for phrase in phrases])


def check_placeholders(catalogue, facts):
    """Catalogue placeholders add to the taxonomy's; none may shadow one or carry content, credentials or identity."""
    own = _unique([item["id"] for item in catalogue["placeholders"]], SNAKE, "placeholder.grammar",
                  "placeholder.duplicate")
    for identifier in own:
        require(identifier not in facts["placeholders"], "placeholder.shadows_taxonomy")
        require(not set(identifier.split("_")) & set(PROHIBITED_PLACEHOLDER_PARTS), "placeholder.prohibited")
    return own | facts["placeholders"]


def check_copy(text, subject, context, rules):
    """Shared copy lint for keys and regulated records: taxonomy terms, glossary aliases, banned voice patterns,
    sentence length and placeholders. `rules` maps each lint to the caller's static rule identifier."""
    require(forbidden_in(text, context["forbidden_terms"]) is None, rules["forbidden_term"], subject)
    require(forbidden_in(text, context["aliases"]) is None, rules["forbidden_alias"], subject)
    require(banned_in(text, context["banned"]) is None, rules["banned_pattern"], subject)
    require(all(count <= context["max_words"] for count in words_per_sentence(text)), rules["sentence"], subject)
    names = PLACEHOLDER.findall(text)
    require(all(name in context["placeholders"] for name in names), rules["placeholder"], subject)
    # Braces only ever delimit a placeholder: a stray, nested or doubled brace is an unknown placeholder.
    require(not set("{}") & set(PLACEHOLDER.sub("", text)), rules["placeholder"], subject)
    return names


KEY_COPY_RULES = {
    "forbidden_term": "key.forbidden_term", "forbidden_alias": "key.forbidden_alias",
    "banned_pattern": "key.banned_pattern", "sentence": "key.sentence_too_long",
    "placeholder": "key.placeholder_unknown",
}


def check_key_roots(entry, facts, regulated_ids):
    """Reserved roots: state. is taxonomy-derived, nav. is held for docs#74, reg. binds an RC record, common. is
    shared by every client. Copy for state. and reg. keys lives in the taxonomy and the regulated record."""
    key, root = entry["key"], entry["key"].split(".", 1)[0]
    require(root not in FOREIGN_ROOTS, "key.foreign_root", key)
    require(root != "nav", "held.nav_key", key)
    if root == "state":
        require(key in facts["state_keys"], "key.state_not_in_taxonomy", key)
        require(entry["copy"] is None, "key.state_copy_forked", key)
    if root == "reg":
        require(entry["regulated_ref"] in regulated_ids, "key.regulated_root_without_record", key)
        require(entry["copy"] is None, "key.regulated_copy_forked", key)
    else:
        require(entry["regulated_ref"] is None, "key.regulated_outside_root", key)
        # Disclosure copy (AI disclosure, advice and projection boundaries) is regulated: it lives only under reg.
        require(entry["category"] != "disclosure", "key.disclosure_outside_reg", key)
    if root == "common":
        require(set(entry["platforms"]) == set(CLIENTS), "key.common_not_shared", key)
    if root not in ("state", "reg"):
        require(entry["copy"] is not None, "key.copy_missing", key)


def check_keys(catalogue, facts, terms, context, roles, regulated_ids):
    """Every key: grammar, unique leaf, reserved root, owner, range, term references, copy lint and safe exit."""
    version(catalogue["catalogue_version"])
    entries = catalogue["keys"]
    keys = sorted(_unique([entry["key"] for entry in entries], KEY, "key.grammar", "key.duplicate"))
    for before, after in zip(keys, keys[1:]):
        # Sorted order puts "a.b" directly before any "a.b.c", so adjacent pairs find every leaf/node clash.
        require(not after.startswith(before + "."), "key.prefix_conflict", before, after)
    index = {}
    for entry in entries:
        key, copy = entry["key"], entry["copy"]
        require(entry["owner"] in roles, "owner.unknown_role", key)
        check_key_roots(entry, facts, regulated_ids)
        bounds = entry["range"]
        require(1 <= bounds["min"] <= bounds["typical"] <= bounds["max"] <= RANGE_LIMIT, "key.range_order", key)
        for reference in entry["term_refs"]:
            require(reference in terms, "key.unknown_term", key, *((reference,) if printable(reference) else ()))
            # One term across platforms: a key may only reach clients where its terms are defined for use.
            require(set(entry["platforms"]) <= set(terms[reference]["surfaces"]), "key.term_surface_missing", key,
                    reference)
        if copy is not None:
            require(bounds["min"] <= len(copy) <= bounds["max"], "key.copy_out_of_range", key)
            for reference in entry["term_refs"]:
                label = terms[reference]["preferred_label"].casefold()
                require(forbidden_in(copy, [label]) is not None, "key.term_label_missing", key, reference)
            names = check_copy(copy, key, context, KEY_COPY_RULES)
            require(not (entry["neutral_safe_exit"] and names), "key.safe_exit_placeholder", key)
        require(entry["status"] == "provisional", "held.key_approval", key)
        index[key] = entry
    for category in SAFE_EXIT_CATEGORIES:
        require(any(entry["category"] == category and entry["neutral_safe_exit"] and entry["copy"] is not None
                    for entry in entries), "key.neutral_safe_exit_missing")
    return index


def check_patterns(voice, keys):
    """The eight scope patterns: taxonomy patterns reuse their state's copy; the others fill every slot with a key."""
    seen = set()
    for pattern in voice["patterns"]:
        identifier = pattern["id"]
        require(identifier not in seen, "pattern.duplicate", identifier)
        seen.add(identifier)
        state = PATTERN_STATES[identifier]
        require(pattern["taxonomy_state"] == state, "pattern.state_mismatch", identifier)
        for slot in SLOTS:
            value = pattern["slots"][slot]
            if state is not None:
                require(value is None, "pattern.state_copy_forked", identifier)
                continue
            require(value is not None, "pattern.slot_missing", identifier)
            require(value in keys, "pattern.unknown_key", identifier)
            require(keys[value]["copy"] is not None, "pattern.unknown_key", identifier)
    require(seen == set(PATTERN_STATES), "pattern.missing")


REGULATED_COPY_RULES = {
    "forbidden_term": "regulated.forbidden_term", "forbidden_alias": "regulated.forbidden_alias",
    "banned_pattern": "regulated.banned_pattern", "sentence": "regulated.sentence_too_long",
    "placeholder": "regulated.placeholder_unknown",
}


def instant(value):
    try:
        require(isinstance(value, str) and INSTANT.fullmatch(value) is not None, "time.invalid")
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise Refused("time.invalid") from None


def trusted_clock(now):
    require(isinstance(now, datetime) and now.tzinfo is not None and now.utcoffset() == timedelta(0),
            "time.untrusted_clock")
    return now


def check_approval(item, approver_role, owner, subject):
    """An approval exists exactly for approved or expired copy and comes from the assigned qualified owner.

    Returns the (effective, expires) window, or None when the item carries no approval.
    """
    approval = item["approval"]
    if item["status"] not in ("approved", "expired"):
        require(approval is None, "regulated.approval_unexpected", subject)
        return None
    require(approval is not None, "regulated.approval_missing", subject)
    require(approval["role"] == approver_role, "regulated.approver_role_mismatch", subject)
    # Only an injected, coordinator-verified assignment of the qualified owner makes an approval possible; the
    # published data never supplies one (the legal role is unassigned), so every approval is refused here.
    require(isinstance(owner, dict) and owner.get("role") == approver_role, "regulated.approver_unassigned", subject)
    require(approval["decision_ref"] is not None, "regulated.approval_evidence_missing", subject)
    effective, expires = instant(approval["effective_at"]), instant(approval["expires_at"])
    require(effective < expires, "regulated.approval_window_invalid", subject)
    require(expires - effective <= APPROVAL_LIFETIME, "regulated.approval_lifetime", subject)
    return effective, expires


def usable(window, now):
    """Approved copy is usable only inside its window: effective_at <= now < expires_at (equality is expired)."""
    return window is not None and window[0] <= now < window[1]


def check_regulated(regulated, keys, terms, context, roles, now, owner):
    """Regulated copy: qualified approver, key binding, fail-closed fallback, approval window, history, rollback."""
    version(regulated["regulated_version"])
    approver_role = regulated["approver_role"]
    require(approver_role == APPROVER_ROLE and approver_role in roles, "regulated.approver_role_unqualified")
    bound = set()
    for record in regulated["records"]:
        identifier = record["id"]
        require(record["owner"] in roles, "owner.unknown_role", identifier)
        key = keys.get(record["key"])
        require(key is not None and key["regulated_ref"] == identifier and record["key"] not in bound,
                "regulated.key_mismatch", identifier)
        bound.add(record["key"])
        fallback = keys.get(record["fail_closed_key"])
        require(fallback is not None, "regulated.fail_closed_key_unknown", identifier)
        require(fallback["regulated_ref"] is None and fallback["neutral_safe_exit"] and fallback["copy"] is not None,
                "regulated.fail_closed_key_unsafe", identifier)
        check_copy(record["copy"], identifier, context, REGULATED_COPY_RULES)
        for reference in key["term_refs"]:
            label = terms[reference]["preferred_label"].casefold()
            require(forbidden_in(record["copy"], [label]) is not None, "regulated.term_label_missing", identifier)
        current = version(record["version"])
        window = check_approval(record, approver_role, owner, identifier)
        if record["status"] == "approved":
            require(now >= window[0], "regulated.approval_not_yet_effective", identifier)
            require(now < window[1], "regulated.approval_expired", identifier)
        if record["status"] == "expired":
            require(now >= window[1], "regulated.expired_status_mismatch", identifier)
        previous, windows = None, {}
        for prior in record["history"]:
            number = version(prior["version"])
            require((previous is None or previous < number) and number < current, "regulated.history_order",
                    identifier)
            previous = number
            windows[prior["version"]] = (prior["status"], check_approval(prior, approver_role, owner, identifier))
        target = record["rollback_version"]
        if target is not None:
            # Rollback pins the prior approved version, still inside its window; never local or unapproved text.
            status, prior_window = windows.get(target, (None, None))
            require(status == "approved" and usable(prior_window, now), "regulated.rollback_target_unapproved",
                    identifier)
    for category in REGULATED_CATEGORIES:
        require(any(record["category"] == category for record in regulated["records"]), "regulated.category_missing")
    # Regulated text is usable only through its record: no ordinary key may restate it, even inside longer copy.
    texts = [" ".join(record["copy"].casefold().split()) for record in regulated["records"]]
    for name, entry in keys.items():
        if entry["copy"] is not None:
            folded = " ".join(entry["copy"].casefold().split())
            require(not any(text in folded for text in texts), "key.regulated_copy_restated", name)


def regulated_ids(regulated):
    identifiers = _unique([record["id"] for record in regulated["records"]], REGULATED, "regulated.id_grammar",
                          "regulated.duplicate_id")
    require(all(REGULATED.fullmatch(identifier).group(1) != "000" for identifier in identifiers),
            "regulated.id_grammar")
    return identifiers


def trusted_git(root):
    """Absolute path of git from absolute PATH entries outside the checked repository.

    A bare "git" lets the operating system search relative PATH entries and, on Windows, the current directory
    first, so a candidate-local executable could forge the base catalogue the additive-versioning rules compare.
    """
    root = Path(root).resolve()
    names = ("git.exe",) if os.name == "nt" else ("git",)
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry or not os.path.isabs(entry):
            continue
        directory = Path(entry).resolve()
        if directory == root or root in directory.parents:
            continue
        for name in names:
            candidate = directory / name
            target = candidate.resolve()
            if target.is_file() and os.access(target, os.X_OK) and root not in target.parents:
                return str(candidate)
    raise LookupError("git not found outside the repository")


class GitSources:
    """Content documents at the base commit from the local Git object store; never fetches, writes or pushes."""

    def __init__(self, root, base=None):
        self.root, self.base, self.executable, self.commit = Path(root), base, None, None

    def _git(self, *args):
        self.executable = self.executable or trusted_git(self.root)
        env = {key: value for key, value in os.environ.items() if key not in SCRUBBED_GIT_VARIABLES}
        # Objects exactly as stored: no lazy fetch, replace refs or grafts that could substitute base bytes.
        env.update(GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1", GIT_GRAFT_FILE=os.devnull)
        try:
            return subprocess.run(
                [self.executable, "--no-pager", *args], cwd=self.root, capture_output=True, timeout=30, env=env,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise LookupError("git unavailable") from None

    def _commit(self, *args):
        result = self._git(*args)
        commit = result.stdout.decode("ascii", "replace").strip()
        if result.returncode != 0 or not COMMIT.fullmatch(commit):
            raise LookupError("no such commit")
        return commit

    def base_commit(self):
        if self.commit is None:
            if self.base is None:
                self.commit = self._commit("merge-base", "HEAD", BASE_REF)
            elif isinstance(self.base, str) and REVISION.fullmatch(self.base):
                self.commit = self._commit("rev-parse", "--verify", "--quiet", f"{self.base}^{{commit}}")
            else:
                raise LookupError("unsafe revision")
        return self.commit

    def base_file(self, path):
        """Bytes of path at the base, or None only when the base commit's tree has no such entry.

        Presence is read from the tree: a listed blob missing from the local object store (a blobless clone, a
        pruned object) fails closed instead of passing as a base that predates the content documents.
        """
        commit = self.base_commit()
        listed = self._git("ls-tree", "-z", "--name-only", commit, "--", path)
        if listed.returncode != 0:
            raise LookupError("base tree unavailable")
        if not listed.stdout:
            return None
        if listed.stdout != path.encode("ascii") + b"\0":
            raise LookupError("unexpected base tree entry")
        result = self._git("cat-file", "blob", f"{commit}:{path}")
        if result.returncode != 0:
            raise LookupError("blob unavailable")
        return result.stdout


def loads(raw):
    """Strict JSON from bytes: UTF-8 and no duplicate keys, like check_client_states.load_json."""
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique)


def document_path(name):
    return f"{CONTENT}/{name}.json"


def read_base(sources, schemas):
    """Each content document at the base, schema-checked, or None where the base predates it."""
    base = {}
    for name in DOCUMENTS:
        try:
            raw = sources.base_file(document_path(name))
        except LookupError:
            raise Refused("base.unavailable") from None
        if raw is None:
            base[name] = None
            continue
        try:
            base[name] = loads(raw)
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise Refused("base.invalid") from None
        try:
            shape(base[name], schemas[name])
        except Refused:
            raise Refused("base.invalid") from None
    return base


def check_base(documents, base):
    """Additive versioning against the base: versions never regress; removing a term or key needs a major bump;
    regulated records are never removed (withdraw instead) and their copy never changes without a new version."""
    fields = {
        "glossary": ("glossary_version", "terms", "id", "glossary.term_removed_without_major"),
        "message-keys": ("catalogue_version", "keys", "key", "catalogue.key_removed_without_major"),
        "voice": ("voice_version", None, None, None),
        "regulated-copy": ("regulated_version", "records", "id", "regulated.record_removed"),
    }
    for name, (version_field, items, identity, removal_rule) in fields.items():
        before = base.get(name)
        if before is None:
            continue
        old, new = version(before[version_field]), version(documents[name][version_field])
        require(new >= old, "version.regressed")
        if items is None:
            continue
        current = {item[identity]: item for item in documents[name][items]}
        for item in before[items]:
            subject = item[identity]
            if subject in current:
                continue
            require(name != "regulated-copy" and new[0] > old[0], removal_rule, subject)
        if name == "regulated-copy":
            for item in before[items]:
                after = current[item["id"]]
                require(version(after["version"]) >= version(item["version"]), "version.regressed", item["id"])
                require(after["copy"] == item["copy"] or after["version"] != item["version"],
                        "regulated.changed_without_version", item["id"])


class Model:
    """The checked documents plus the indexes readiness and the structure line read.

    `base_documents` names the content documents found at the base commit (empty when the base predates them), so a
    caller can assert which additive-versioning comparisons actually ran.
    """

    def __init__(self, documents, terms, keys, owner, base_documents=()):
        self.documents, self.terms, self.keys, self.owner = documents, terms, keys, owner
        self.base_documents = tuple(base_documents)


def check(documents, schemas, taxonomy, gates, now, sources, owner=None):
    """Run every structure rule in a fixed order; raise Refused at the first violation, else return the model.

    `now` is the injected clock; `owner` is an injected assignment of the qualified legal/compliance owner, which the
    published loader never supplies.
    """
    now = trusted_clock(now)
    for name in DOCUMENTS:
        shape(documents[name], schemas[name])
    for name in DOCUMENTS:
        guard_content(documents[name])
    facts, roles = taxonomy_facts(taxonomy), role_ids(gates)
    glossary, voice = documents["glossary"], documents["voice"]
    catalogue, regulated = documents["message-keys"], documents["regulated-copy"]
    terms = check_glossary(glossary, facts, roles)
    banned = check_voice(voice, facts)
    check_term_wording(glossary, banned)
    for pattern in voice["patterns"]:
        state = pattern["taxonomy_state"]
        require(state is None or state in facts["states"], "pattern.state_mismatch", pattern["id"])
    context = {
        "forbidden_terms": facts["forbidden_terms"], "banned": banned, "max_words": voice["max_sentence_words"],
        "aliases": [alias.casefold() for term in glossary["terms"] for alias in term["forbidden_aliases"]],
        "placeholders": check_placeholders(catalogue, facts),
    }
    identifiers = regulated_ids(regulated)
    keys = check_keys(catalogue, facts, terms, context, roles, identifiers)
    check_patterns(voice, keys)
    check_regulated(regulated, keys, terms, context, roles, now, owner)
    base = read_base(sources, schemas)
    check_base(documents, base)
    return Model(documents, terms, keys, owner, (name for name in DOCUMENTS if base[name] is not None))


def readiness(model):
    """Every visible gap by static rule: sorted subjects; never filled in or waived."""
    documents = model.documents
    gaps = {rule: [] for rule in READINESS_RULES}
    for term in documents["glossary"]["terms"]:
        if term["comprehension"]["required"]:
            gaps["readiness.comprehension_evidence"].append(term["id"])
        if term["status"] != "approved":
            gaps["readiness.term_unapproved"].append(term["id"])
    if documents["voice"]["reading_level"]["status"] != "confirmed":
        gaps["readiness.reading_level_provisional"].append("voice.reading_level")
    gaps["readiness.key_unapproved"] = [key for key, entry in model.keys.items() if entry["status"] != "approved"]
    gaps["readiness.regulated_unapproved"] = [
        record["id"] for record in documents["regulated-copy"]["records"] if record["status"] != "approved"
    ]
    if model.owner is None:
        gaps["readiness.approver_unassigned"].append("approver_role")
    gaps["readiness.nav_labels_held"].append(NAV_SOURCE)
    return {rule: sorted(subjects) for rule, subjects in gaps.items()}


def structure_line(model):
    documents = model.documents
    glossary, catalogue = documents["glossary"], documents["message-keys"]
    regulated, voice = documents["regulated-copy"], documents["voice"]
    roots = {root: sum(key.split(".", 1)[0] == root for key in model.keys) for root in RESERVED_ROOTS}
    return (
        f"Content glossary {glossary['glossary_version']} structure valid: {len(glossary['terms'])} terms "
        f"({sum(term['comprehension']['required'] for term in glossary['terms'])} need comprehension evidence); "
        f"voice {voice['voice_version']}: {len(voice['banned_patterns'])} banned patterns, "
        f"{len(voice['patterns'])} content patterns, taxonomy copy rules imported by reference; message keys "
        f"{catalogue['catalogue_version']}: {len(model.keys)} keys (" +
        ", ".join(f"{count} {root}." for root, count in roots.items()) +
        f"); regulated copy {regulated['regulated_version']}: {len(regulated['records'])} records, "
        f"{sum(record['status'] == 'approved' for record in regulated['records'])} approved"
    )


MARKDOWN_SPECIAL = re.compile(r"([\\`*_\[\]<>|#&~])")


def cell(text):
    """Checked free text as inert Markdown: every character with Markdown meaning is backslash-escaped."""
    return MARKDOWN_SPECIAL.sub(r"\\\1", text)


def code(identifier):
    return f"`{identifier}`"


def listing(items, empty="none"):
    return ", ".join(items) if items else empty


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def banner(name, notice):
    return [
        f"<!-- Generated by `python scripts/check_content.py --write-views` from {CONTENT}/{name}.json; "
        "do not edit by hand. -->",
        "",
        f"> **Status: proposed.** Every value below is proposed by the implementing session of {SOURCE_ISSUE} and "
        f"awaits confirmation by its owner. {notice}",
        "",
    ]


def render_glossary(glossary):
    lines = [f"# Product glossary {glossary['glossary_version']}", ""]
    lines += banner("glossary", "Comprehension evidence for the flagged terms is held by "
                                f"{COMPREHENSION_SOURCE.split(':', 1)[1]}; no term is approved.")
    rows = []
    for term in glossary["terms"]:
        comprehension = term["comprehension"]
        rows.append([
            code(term["id"]), cell(term["preferred_label"]), cell(term["definition"]), listing(term["surfaces"]),
            listing([cell(alias) for alias in term["forbidden_aliases"]]),
            ("required, evidence " + (comprehension["evidence_ref"] or "missing")) if comprehension["required"]
            else "not required",
            term["status"], term["owner"],
        ])
    lines += table(["ID", "Preferred label", "Definition", "Surfaces", "Forbidden aliases", "Comprehension",
                    "Status", "Owner"], rows)
    return lines


def render_voice(voice):
    reading = voice["reading_level"]
    lines = [f"# Voice and tone {voice['voice_version']}", ""]
    lines += banner("voice", "The reading-level target is provisional until comprehension research confirms it.")
    lines += [
        "## Reading level and sentences", "",
        f"- Target ({reading['status']}, evidence {reading['evidence_ref'] or 'missing'}): {cell(reading['target'])}",
        f"- At most {voice['max_sentence_words']} words per sentence in message-key and regulated copy.", "",
        "## Copy rules imported from the client-state taxonomy", "",
        f"Applied by reference from {code(TAXONOMY)} (never restated here): "
        + listing([code(rule) for rule in voice["taxonomy_copy_rules"]]) + ". The taxonomy's forbidden terms "
        "apply to every term, key and regulated record.", "",
        "## Principles", "",
    ]
    lines += [f"- {code(item['id'])}: {cell(item['rule'])}" for item in voice["principles"]]
    lines += ["", "## Banned patterns", ""]
    lines += table(["ID", "Category", "Phrase"], [
        [code(item["id"]), item["category"], cell(item["phrase"])] for item in voice["banned_patterns"]
    ])
    lines += ["", "## Conventions", ""]
    lines += [f"- {code(item['id'])}: {cell(item['rule'])}" for item in voice["conventions"]]
    lines += ["", "## Content patterns", "",
              "Taxonomy patterns reuse their state's copy; the others name one message key per slot.", ""]
    rows = []
    for pattern in voice["patterns"]:
        state = pattern["taxonomy_state"]
        slots = ["taxonomy" if state else code(pattern["slots"][slot]) for slot in SLOTS]
        rows.append([pattern["id"], code(f"state.{state}") if state else "none", *slots])
    lines += table(["Pattern", "Taxonomy state", *SLOTS], rows)
    return lines


def render_keys(catalogue, regulated):
    statuses = {record["id"]: record["status"] for record in regulated["records"]}
    lines = [f"# Message keys {catalogue['catalogue_version']}", ""]
    lines += banner("message-keys", f"`nav.` keys are held for {NAV_SOURCE}; `state.` copy lives in the taxonomy "
                                    "and `reg.` copy in its regulated record.")
    lines += ["## Placeholders added to the taxonomy's", ""]
    lines += [f"- {code(item['id'])} ({item['source']}): {cell(item['description'])}"
              for item in catalogue["placeholders"]] or ["None."]
    lines += ["", "## Keys", ""]
    rows = []
    for entry in catalogue["keys"]:
        if entry["regulated_ref"] is not None:
            copy = f"{entry['regulated_ref']} ({statuses[entry['regulated_ref']]})"
        else:
            copy = "taxonomy" if entry["copy"] is None else cell(entry["copy"])
        bounds = entry["range"]
        rows.append([
            code(entry["key"]), entry["category"], copy, f"{bounds['min']}/{bounds['typical']}/{bounds['max']}",
            listing([code(reference) for reference in entry["term_refs"]]),
            "yes" if entry["neutral_safe_exit"] else "no", listing(entry["platforms"]), entry["status"],
            entry["owner"],
        ])
    lines += table(["Key", "Category", "Copy", "Range min/typical/max", "Terms", "Safe exit", "Platforms", "Status",
                    "Owner"], rows)
    return lines


def render_regulated(regulated):
    lines = [f"# Regulated copy {regulated['regulated_version']}", ""]
    records = regulated["records"]
    approved = sum(record["status"] == "approved" for record in records)
    lines += banner("regulated-copy", f"{approved} of {len(records)} records approved. Only approved copy inside its "
                                      "approval window may be shown; for any other record a consumer shows its "
                                      "fail-closed key. Draft copy is not legal text.")
    lines += [
        f"Approver role: {code(regulated['approver_role'])} (qualified legal/compliance owner; unassigned in "
        f"{code(GATES)}, so no record can be approved).", "",
    ]
    lines += table(["ID", "Category", "Key", "Version", "Status", "Approval", "Fail-closed key", "History",
                    "Rollback"], [
        [record["id"], record["category"], code(record["key"]), record["version"], record["status"],
         "none" if record["approval"] is None else f"{record['approval']['effective_at']} to "
                                                    f"{record['approval']['expires_at']}",
         code(record["fail_closed_key"]), listing([prior["version"] for prior in record["history"]]),
         record["rollback_version"] or "none"]
        for record in regulated["records"]
    ])
    lines += ["", "## Draft copy", ""]
    for record in regulated["records"]:
        lines += [f"- {record['id']} {record['version']} ({record['status']}): {cell(record['copy'])}"]
    return lines


def render_views(model):
    """Markdown views of the checked documents: deterministic, LF, final newline, no timestamps."""
    documents = model.documents
    views = {
        "glossary": render_glossary(documents["glossary"]),
        "voice": render_voice(documents["voice"]),
        "message-keys": render_keys(documents["message-keys"], documents["regulated-copy"]),
        "regulated-copy": render_regulated(documents["regulated-copy"]),
    }
    return {f"{CONTENT}/{name}.md": "\n".join(lines) + "\n" for name, lines in views.items()}


def view_target(root, relative):
    """A view path inside the content directory of root, never reached through a symbolic link."""
    root = Path(root)
    target, directory = root / relative, root / CONTENT
    require(not directory.is_symlink() and not target.is_symlink()
            and directory.resolve() == root.resolve() / CONTENT and target.parent == directory, "views.unsafe_path")
    return target


def check_views(root, views):
    for relative, text in views.items():
        target = view_target(root, relative)
        require(target.is_file(), "views.missing")
        require(target.read_bytes() == text.encode("utf-8"), "views.drift")


def write_views(root, views):
    """Write each view to a fresh file in the content directory and rename it over the view: the rename replaces
    the directory entry, so a hard link or a symbolic link planted after view_target never receives the bytes."""
    for relative, text in views.items():
        target = view_target(root, relative)
        handle, temporary = tempfile.mkstemp(dir=target.parent, prefix=".view-", suffix=".tmp")
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(text.encode("utf-8"))
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def load_documents(root):
    root = Path(root)
    documents = {name: support.load_json(root / document_path(name)) for name in DOCUMENTS}
    schemas = {name: support.load_json(root / f"{CONTENT}/{name}.schema.json") for name in DOCUMENTS}
    return documents, schemas


def load_and_check(root, now, base=None):
    root = Path(root)
    documents, schemas = load_documents(root)
    return check(
        documents, schemas, support.load_json(root / TAXONOMY), support.load_json(root / GATES), now,
        GitSources(root, base),
    )


def main(argv=None, now=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--structure", action="store_true", help="Check structure only; readiness is not evaluated.")
    modes.add_argument("--write-views", action="store_true",
                       help=f"Regenerate the Markdown views in {CONTENT}/ from the checked documents.")
    modes.add_argument("--check-views", action="store_true",
                       help=f"Fail unless the Markdown views in {CONTENT}/ match the checked documents byte for byte.")
    parser.add_argument("--base", help=f"Git revision whose committed content the additive-versioning rules extend "
                                       f"(default: the merge base of HEAD and {BASE_REF}).")
    parser.add_argument("--now", help="Evaluate approval windows at this UTC instant (YYYY-MM-DDTHH:MM:SSZ) instead "
                                      "of the system clock.")
    args = parser.parse_args(argv)
    try:
        if args.now is not None:
            now = instant(args.now)
        model = load_and_check(ROOT, datetime.now(timezone.utc) if now is None else now, args.base)
        if args.structure:
            print(structure_line(model) + "; readiness not evaluated.")
            return 0
        if args.write_views or args.check_views:
            views = render_views(model)
            (write_views if args.write_views else check_views)(ROOT, views)
            print(f"Content views {'written' if args.write_views else 'match'}: {len(views)}")
            return 0
        gaps = readiness(model)
        status = NOT_GREEN if any(gaps.values()) else GREEN
        print(status)
        print(structure_line(model))
        if status == GREEN:
            return 0
        for rule in READINESS_RULES:
            print(f"{rule}: {len(gaps[rule])}")
        return 1
    except Refused as error:
        print(f"Content check refused: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, RecursionError, re.error):
        # Fail closed without a traceback, whose message could echo input content.
        print(f"Content check refused: {Refused("input.unreadable_or_invalid")}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
