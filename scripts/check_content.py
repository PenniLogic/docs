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
regulated-copy, pattern or issue grammar; copy text is never echoed. Every JSON input goes through one strict loader
that refuses nesting deeper than MAX_JSON_DEPTH before parsing and integers longer than MAX_INTEGER_DIGITS before
conversion, so whether an input parses never depends on the interpreter's recursion, stack or integer-conversion
limits, and the first fault reported never depends on hash-seeded set order. Readiness gaps (comprehension evidence
held by PenniLogic/docs#66, the provisional reading level, unapproved terms, keys and regulated copy, the unassigned
approver and the docs#74 hold on `nav.` labels) are counted, never filled in, and keep the default mode NOT GREEN.
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
# Generic action labels a non-state key may share with a taxonomy action label (compared case-folded).
GENERIC_LABELS = ("cancel", "close", "continue", "done", "refresh", "retry", "try again")
# A placeholder whose name contains one of these parts anywhere (underscores ignored, so "username" and
# "account_number" both match) would echo raw content, credentials or hidden identity. Substring matching fails
# closed: an innocent name that happens to contain a part is refused too and must be renamed.
PROHIBITED_PLACEHOLDER_PARTS = (
    "password", "passwd", "passcode", "otp", "pin", "token", "secret", "credential", "key", "account", "card",
    "email", "phone", "mobile", "address", "contact", "name", "operator", "agent", "raw", "message", "body",
    "content", "note", "resource", "user", "member", "person", "people", "amount", "balance", "merchant", "payee",
    "payer", "sender", "recipient", "counterparty", "upi", "vpa", "pan", "aadhaar", "aadhar", "ifsc", "iban",
    # Raw SMS or transaction text, and the identity of a lender or institution (review round 2 SS-06).
    "sms", "text", "narration", "memo", "remark", "snippet", "description", "subject", "who", "lender", "bank",
    "institution",
)
# Placeholder sources that carry user data; notifications never echo them (voice.discreet_by_default).
DATA_PLACEHOLDER_SOURCES = ("client_cache", "service_response")
# Deepest array/object nesting accepted in any JSON this validator reads: the content documents and their schemas,
# the taxonomy, the design-gates roles and the base-commit blobs. The deepest of them published today nests 8 levels
# (glossary.schema.json; the content documents nest 4 and no JSON file in the repository nests more than 9), so 64
# leaves ample room while the recursion that follows an input's nesting after the scan (the C parser, the content
# guard, nested comparisons) stays far inside any interpreter's recursion and stack limits. Deeper input is refused
# before parsing (input.unreadable_or_invalid; base.invalid for a base blob): whether the parser itself overflows
# first depends on the build's C stack (PenniLogic/docs#84 native CI failure 1).
MAX_JSON_DEPTH = 64
# Longest decimal numeral converted to an integer (JSON integers and version components). Every 64-bit value fits,
# and the interpreter's configurable integer-conversion limit (PYTHONINTMAXSTRDIGITS, -X int_max_str_digits) can never
# be set below 640 digits, so int() within this bound never depends on it; a longer numeral is refused everywhere.
MAX_INTEGER_DIGITS = 20
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
    "content.non_ascii_character", "content.url_shape", "content.email_shape", "content.number_shape",
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
    "pattern.slot_missing", "pattern.unknown_key", "pattern.slot_category", "pattern.slot_reused",
    "placeholder.grammar", "placeholder.duplicate", "placeholder.shadows_taxonomy", "placeholder.prohibited",
    "key.term_surface_missing", "key.grammar", "key.duplicate", "key.prefix_conflict", "key.foreign_root",
    "key.state_not_in_taxonomy", "key.state_missing",
    "key.state_copy_forked", "held.nav_key", "key.regulated_outside_root", "key.regulated_root_without_record",
    "key.regulated_copy_forked", "key.disclosure_outside_reg", "key.regulated_copy_restated", "key.common_not_shared",
    "key.copy_missing", "key.range_order",
    "key.copy_out_of_range", "key.unknown_term", "key.term_label_missing", "key.forbidden_term",
    "key.forbidden_alias", "key.banned_pattern", "key.sentence_too_long", "key.placeholder_unknown",
    "key.safe_exit_placeholder", "key.notification_data_placeholder", "key.item_agreement", "key.several_actions",
    "key.code_like", "regulated.code_like", "key.neutral_safe_exit_missing",
    "held.key_approval",
    "regulated.id_grammar", "regulated.duplicate_id", "regulated.approver_role_unqualified",
    "regulated.category_missing", "regulated.key_mismatch", "regulated.fail_closed_key_unknown",
    "regulated.fail_closed_key_unsafe", "regulated.forbidden_term", "regulated.forbidden_alias",
    "regulated.banned_pattern", "regulated.sentence_too_long", "regulated.placeholder_unknown",
    "regulated.term_label_missing", "regulated.fail_closed_platform_missing", "key.regulated_unbound",
    "key.taxonomy_copy_restated",
    "regulated.approval_missing", "regulated.approval_unexpected", "regulated.approver_role_mismatch",
    "regulated.approver_unassigned", "regulated.approval_evidence_missing", "time.invalid", "time.untrusted_clock",
    "regulated.approval_window_invalid", "regulated.approval_lifetime", "regulated.approval_not_yet_effective",
    "regulated.approval_expired", "regulated.expired_status_mismatch", "regulated.history_order",
    "regulated.rollback_target_unapproved", "regulated.review_without_approver", "regulated.history_key_mismatch",
    "regulated.rollback_with_usable_approval",
    "base.unavailable", "base.invalid", "version.regressed", "regulated.history_rewritten", "regulated.status_reverted",
    "regulated.approval_rewritten", "regulated.prior_version_not_kept", "glossary.term_removed_without_major",
    "glossary.changed_without_minor", "catalogue.changed_without_minor", "voice.changed_without_minor",
    "catalogue.key_removed_without_major", "regulated.record_removed", "regulated.changed_without_version",
    "views.unsafe_path", "views.missing", "views.drift",
)
READINESS_RULES = (
    "readiness.comprehension_evidence", "readiness.reading_level_provisional", "readiness.term_unapproved",
    "readiness.key_unapproved", "readiness.regulated_unapproved", "readiness.approver_unassigned",
    "readiness.nav_labels_held", "readiness.pattern_slot_unstated",
)
# nav. keys carry docs#74 navigation labels; until docs#74 publishes them every nav. key is refused (held.nav_key).
NAV_SOURCE = "PenniLogic/docs#74"
# The client-state taxonomy owner: slots its state copy does not state are routed there, never filled in here.
STATE_SOURCE = "PenniLogic/docs#1"


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
    # Bounded before int(), so the interpreter's integer-conversion limit never decides the outcome.
    require(match is not None and all(len(part) <= MAX_INTEGER_DIGITS for part in match.groups()),
            "version.grammar")
    return tuple(int(part) for part in match.groups())


CONTENT_SHAPES = (
    ("content.url_shape", re.compile(r"[a-z][a-z0-9+.-]*://|\bwww\.|\b[a-z0-9-]+\.(com|net|org|io|in|app|dev)\b",
                                     re.IGNORECASE)),
    ("content.email_shape", re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")),
    ("content.number_shape", re.compile(
        r"[0-9](?:[^A-Za-z0-9\n]{0,2}[0-9]){4,}|[$£€₹¥]\s?[0-9]|[0-9]\s?[$£€₹¥]"
        # Currency codes, written currency and Indian magnitudes next to a number, in any letter case.
        r"|(?i:\b(?:INR|USD|EUR|GBP|Rs|rupees?|lakhs?|lacs?|crores?|paise)\.?\s?[0-9]"
        r"|[0-9]\s?(?:INR|USD|EUR|GBP|Rs|rupees?|lakhs?|lacs?|crores?|paise)\b)"
    )),
)
# Curly quotes and apostrophes, en and em dashes, and the ellipsis: the only non-ASCII characters in content text.
TYPOGRAPHIC_PUNCTUATION = "\u2018\u2019\u201c\u201d\u2013\u2014\u2026"
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
    # Source copy is English: any other non-ASCII character (a homoglyph letter, a combining mark, a native-script
    # digit, a circled letter, fullwidth or variant punctuation, a currency sign) could slip past the ASCII lints, so
    # only ASCII and the explicit typographic punctuation allow-list are accepted (none of those has an NFKC form
    # that a lint matches).
    require(all(character.isascii() or character in TYPOGRAPHIC_PUNCTUATION for character in text),
            "content.non_ascii_character", *subject)
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
        states, texts = set(), {}
        for state in taxonomy["states"]:
            identifier = state["id"]
            states.add(identifier)
            action = state["recovery_action"]
            texts[f"state.{identifier}.headline"] = state["copy"].get("headline")
            texts[f"state.{identifier}.body"] = state["copy"].get("body")
            texts[f"state.{identifier}.action"] = action.get("label")
            for variant, copy in state["copy"].get("variants", {}).items():
                for field in ("headline", "body"):
                    texts[f"state.{identifier}.{variant}.{field}"] = copy.get(field)
            for field in ("label_by_cause", "label_by_variant"):
                # A variant or cause label sits beside that variant's copy, so no derived key is also a node.
                texts.update((f"state.{identifier}.{name}.action", label)
                             for name, label in action.get(field, {}).items())
        keys = set(texts)
        # The same strings check_client_states.canonical_strings yields: copy, variants and action labels.
        canonical = {wording(text) for text in texts.values() if isinstance(text, str)}
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
        "state_keys": keys, "state_texts": {key: text for key, text in texts.items() if isinstance(text, str)},
        "canonical": canonical,
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
    forbidden = {compact(term) for term in facts["forbidden_terms"]}
    for term in terms:
        identifier, label = term["id"], compact(term["preferred_label"])
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
            folded = compact(alias)
            require(folded not in forbidden, "taxonomy.forked_forbidden_term", term["id"])
            require(folded != compact(term["preferred_label"]), "term.alias_is_label", term["id"])
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
        require(normalised(phrase) not in phrases, "voice.duplicate_pattern", pattern["id"])
        phrases.add(normalised(phrase))
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
    aliases = alias_forms(glossary)
    for term in glossary["terms"]:
        for text in (term["preferred_label"], term["definition"]):
            require(banned_in(text, banned) is None, "term.banned_pattern", term["id"])
            require(banned_in(text, aliases) is None, "term.forbidden_alias", term["id"])


DASHES = re.compile("[-\u2010\u2011\u2012\u2013\u2014\u2015\u2212]")
CONTRACTIONS = (
    ("won't", "will not"), ("can't", "cannot"), ("shan't", "shall not"), ("n't", " not"), ("'ve", " have"),
    ("'re", " are"), ("'ll", " will"), ("'d", " would"), ("'m", " am"),
)


def normalised(text):
    """Text as the banned-phrase lint compares it: case-folded, typographic apostrophes straightened, contractions
    expanded, hyphens and dashes read as spaces and whitespace collapsed ("Debt-free", "debt  free" and "debt free"
    are one phrase; "should've" is "should have")."""
    folded = text.casefold().replace("\u2019", "'").replace("\u2018", "'")
    for short, full in CONTRACTIONS:
        folded = folded.replace(short, full)
    return " ".join(DASHES.sub(" ", folded).split())


def compact(text):
    """normalised() without spaces: the form labels and aliases are compared in, so "pay-off", "pay  off" and
    "payoff" are one label (fails closed: two labels that differ only in spacing are refused as duplicates)."""
    return normalised(text).replace(" ", "")


def wording(text):
    """normalised() without terminal punctuation: whole strings are restatements whatever their final mark."""
    return normalised(text).rstrip(".!?\u2026 ")


def alias_forms(glossary):
    """Every forbidden alias with its plural forms ("txn", "txns", "txnes"), matched like banned phrases."""
    return [alias + suffix for term in glossary["terms"] for alias in term["forbidden_aliases"]
            for suffix in ("", "s", "es")]


def banned_in(text, phrases):
    """The first banned voice phrase in text: both sides normalised, then matched word-bounded like the taxonomy's
    forbidden terms. Inflected forms are separate phrases in voice.json (guarantee, guarantees, guaranteed ...)."""
    return support.forbidden_term(normalised(text), [normalised(phrase) for phrase in phrases])


def check_placeholders(catalogue, facts):
    """Catalogue placeholders add to the taxonomy's; none may shadow one or carry content, credentials or identity."""
    identifiers = [item["id"] for item in catalogue["placeholders"]]
    own = _unique(identifiers, SNAKE, "placeholder.grammar", "placeholder.duplicate")
    # Document order, never the set's: with two different faults, set order (and so the rule reported) would follow
    # the per-process hash seed.
    for identifier in identifiers:
        require(identifier not in facts["placeholders"], "placeholder.shadows_taxonomy")
        joined = identifier.replace("_", "")
        require(not any(part in joined for part in PROHIBITED_PLACEHOLDER_PARTS), "placeholder.prohibited")
    return own | facts["placeholders"]


def check_copy(text, subject, context, rules):
    """Shared copy lint for keys and regulated records: taxonomy terms, glossary aliases, banned voice patterns,
    sentence length and placeholders. `rules` maps each lint to the caller's static rule identifier."""
    require(forbidden_in(text, context["forbidden_terms"]) is None, rules["forbidden_term"], subject)
    require(banned_in(text, context["aliases"]) is None, rules["forbidden_alias"], subject)
    require(banned_in(text, context["banned"]) is None, rules["banned_pattern"], subject)
    # no_internal_detail (imported): an HTTP-style status or a SCREAMING_SNAKE token is an internal code.
    require(support.CODE_LIKE.search(text) is None, rules["code_like"], subject)
    require(all(count <= context["max_words"] for count in words_per_sentence(text)), rules["sentence"], subject)
    names = PLACEHOLDER.findall(text)
    require(all(name in context["placeholders"] for name in names), rules["placeholder"], subject)
    # Braces only ever delimit a placeholder: a stray, nested or doubled brace is an unknown placeholder.
    require(not set("{}") & set(PLACEHOLDER.sub("", text)), rules["placeholder"], subject)
    return names


ITEM_SINGULAR = re.compile(r"\{item\}\s+(?:is|was|has|does)(?:n't|n\u2019t)?\b", re.IGNORECASE)
KEY_COPY_RULES = {
    "forbidden_term": "key.forbidden_term", "forbidden_alias": "key.forbidden_alias",
    "banned_pattern": "key.banned_pattern", "sentence": "key.sentence_too_long",
    "placeholder": "key.placeholder_unknown", "code_like": "key.code_like",
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
        # The taxonomy string this key renders must fit the key's declared range, like any other copy.
        text = facts["state_texts"].get(key)
        bounds = entry["range"]
        require(text is None or bounds["min"] <= len(text) <= bounds["max"], "key.copy_out_of_range", key)
    elif entry["copy"] is not None:
        # same_wording: a taxonomy string restated under another root would fork it; generic labels may repeat.
        folded = wording(entry["copy"])
        require(folded not in facts["canonical"] or folded in GENERIC_LABELS, "key.taxonomy_copy_restated", key)
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
            # The taxonomy's {item} is the surface's plural noun ("{item} are back", never "{item} is back").
            require(ITEM_SINGULAR.search(copy) is None, "key.item_agreement", key)
            # one_action (imported): an action label offers exactly one action.
            require(entry["category"] != "action" or support.SEVERAL_ACTIONS.search(copy) is None,
                    "key.several_actions", key)
            require(not (entry["neutral_safe_exit"] and names), "key.safe_exit_placeholder", key)
            require(entry["category"] != "notification" or not set(names) & context["data_placeholders"],
                    "key.notification_data_placeholder", key)
        require(entry["status"] == "provisional", "held.key_approval", key)
        index[key] = entry
    for category in SAFE_EXIT_CATEGORIES:
        require(any(entry["category"] == category and entry["neutral_safe_exit"] and entry["copy"] is not None
                    for entry in entries), "key.neutral_safe_exit_missing")
    # Both directions: every key the taxonomy derives is catalogued, so a client never renders an unkeyed state.
    missing = sorted(facts["state_keys"] - set(index))
    require(not missing, "key.state_missing", *missing[:1])
    return index


def check_patterns(voice, keys):
    """The eight scope patterns (criterion 2: source, status, consequence, safe remainder, next action).

    A taxonomy pattern maps each slot to one of its own state's derived keys (headline, body or action) or leaves it
    null: the taxonomy does not state that slot, which readiness counts as a gap for the taxonomy owner. The other
    patterns fill every slot with a key of the pattern's own category that carries copy. No key fills two slots.
    """
    seen = set()
    for pattern in voice["patterns"]:
        identifier = pattern["id"]
        require(identifier not in seen, "pattern.duplicate", identifier)
        seen.add(identifier)
        state = PATTERN_STATES[identifier]
        require(pattern["taxonomy_state"] == state, "pattern.state_mismatch", identifier)
        values = [pattern["slots"][slot] for slot in SLOTS]
        for value in values:
            if state is not None:
                own = {f"state.{state}.{field}" for field in ("headline", "body", "action")}
                require(value is None or value in own, "pattern.state_copy_forked", identifier)
                require(value is None or value in keys, "pattern.unknown_key", identifier)
                continue
            require(value is not None, "pattern.slot_missing", identifier)
            require(value in keys, "pattern.unknown_key", identifier)
            require(keys[value]["copy"] is not None, "pattern.unknown_key", identifier)
            require(keys[value]["category"] == identifier, "pattern.slot_category", identifier)
        next_action = pattern["slots"]["next_action"]
        if state is None:
            # one_action (imported): a pattern's next action offers exactly one action.
            require(support.SEVERAL_ACTIONS.search(keys[next_action]["copy"]) is None, "key.several_actions",
                    next_action)
        # Every stated slot names a distinct key: one string in two slots would hide a criterion-2 gap.
        stated = [value for value in values if value is not None]
        require(len(set(stated)) == len(stated), "pattern.slot_reused", identifier)
    require(seen == set(PATTERN_STATES), "pattern.missing")


REGULATED_COPY_RULES = {
    "forbidden_term": "regulated.forbidden_term", "forbidden_alias": "regulated.forbidden_alias",
    "banned_pattern": "regulated.banned_pattern", "sentence": "regulated.sentence_too_long",
    "placeholder": "regulated.placeholder_unknown", "code_like": "regulated.code_like",
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
    """An approval exists for approved or expired copy, may stay on withdrawn copy that was approved (the audit
    trail is kept), and comes from the assigned qualified owner.

    Returns the (effective, expires) window, or None when the item carries no approval.
    """
    approval = item["approval"]
    if item["status"] == "withdrawn" and approval is None:
        return None
    if item["status"] not in ("approved", "expired", "withdrawn"):
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
        # Every client that can render the regulated key must also have its fail-closed copy.
        require(set(key["platforms"]) <= set(fallback["platforms"]), "regulated.fail_closed_platform_missing",
                identifier)
        check_copy(record["copy"], identifier, context, REGULATED_COPY_RULES)
        # The record's text is what the reg. key renders, so it must fit that key's declared range.
        bounds = key["range"]
        require(bounds["min"] <= len(record["copy"]) <= bounds["max"], "key.copy_out_of_range", record["key"])
        for reference in key["term_refs"]:
            label = terms[reference]["preferred_label"].casefold()
            require(forbidden_in(record["copy"], [label]) is not None, "regulated.term_label_missing", identifier)
        current = version(record["version"])
        # While the qualified owner is unassigned nobody can receive a record for review (content-governance step 2).
        require(owner is not None or record["status"] != "in_review", "regulated.review_without_approver", identifier)
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
            require(owner is not None or prior["status"] != "in_review", "regulated.review_without_approver",
                    identifier)
            # Each prior version keeps its own text and key binding, so a rollback never needs local or cached text.
            require(prior["key"] == record["key"], "regulated.history_key_mismatch", identifier)
            check_copy(prior["copy"], identifier, context, REGULATED_COPY_RULES)
            windows[prior["version"]] = (prior["status"], check_approval(prior, approver_role, owner, identifier))
        target = record["rollback_version"]
        if target is not None:
            # Exactly one copy is in force: a usable approval of the current version excludes a rollback pin.
            require(record["status"] != "approved", "regulated.rollback_with_usable_approval", identifier)
            # Rollback pins the prior approved version, still inside its window; never local or unapproved text.
            status, prior_window = windows.get(target, (None, None))
            require(status == "approved" and usable(prior_window, now), "regulated.rollback_target_unapproved",
                    identifier)
            pinned = next(prior for prior in record["history"] if prior["version"] == target)
            require(bounds["min"] <= len(pinned["copy"]) <= bounds["max"], "key.copy_out_of_range", record["key"])
    for category in REGULATED_CATEGORIES:
        require(any(record["category"] == category for record in regulated["records"]), "regulated.category_missing")
    # One-to-one: every reg. key is the key of exactly one record (records already claim distinct keys).
    for name in keys:
        require(not name.startswith("reg.") or name in bound, "key.regulated_unbound", name)
    # Regulated text is usable only through its record: no ordinary key may restate it, even inside longer copy.
    # Every complete sentence of every current and prior (history) version is compared as a word sequence, so
    # terminal punctuation, commas, dash and apostrophe variants, contractions, case and spacing do not bypass it.
    sentences = {sentence for record in regulated["records"]
                 for text in [record["copy"]] + [prior["copy"] for prior in record["history"]]
                 for sentence in regulated_sentences(text)}
    for name, entry in keys.items():
        if entry["copy"] is not None:
            spoken = f" {word_sequence(entry['copy'])} "
            require(not any(f" {sentence} " in spoken for sentence in sentences), "key.regulated_copy_restated",
                    name)


SENTENCE_END = re.compile(r"[.!?\u2026]+(?:\s+|$)")
WORD = re.compile(r"[^\W_]+")


def word_sequence(text):
    """normalised() reduced to its words: punctuation, dashes and spacing drop out and "cannot" reads as
    "can not", so "This can\u2019t be undone," and "this can not be undone" are one sequence."""
    return " ".join("can not" if word == "cannot" else word for word in WORD.findall(normalised(text)))


def regulated_sentences(text):
    """The word sequence of each complete sentence of regulated text (split at terminal punctuation)."""
    return [words for part in SENTENCE_END.split(text) if (words := word_sequence(part))]


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


QUOTE, BACKSLASH, OPENERS, CLOSERS = ord('"'), ord("\\"), b"[{", b"]}"


def nesting_depth(raw, limit=MAX_JSON_DEPTH):
    """The deepest array/object nesting of JSON bytes, from one iterative pass that skips string contents (escapes
    included) and stops at limit + 1. UTF-8 multi-byte sequences never contain these ASCII bytes, so the scan needs
    no decoding. Exact (up to limit + 1) for well-formed JSON; for malformed JSON never below the depth a parser
    reaches before rejecting it, since the parser reads the same valid prefix."""
    depth = deepest = 0
    in_string = escaped = False
    for byte in raw:
        if in_string:
            if escaped:
                escaped = False
            elif byte == BACKSLASH:
                escaped = True
            elif byte == QUOTE:
                in_string = False
        elif byte == QUOTE:
            in_string = True
        elif byte in OPENERS:
            depth += 1
            if depth > deepest:
                deepest = depth
                if deepest > limit:
                    break
        elif byte in CLOSERS:
            depth -= 1
    return deepest


def loads(raw):
    """Strict JSON from bytes, like check_client_states.load_json (UTF-8, no duplicate keys), with two bounds checked
    before the interpreter could decide the outcome: nesting deeper than MAX_JSON_DEPTH is refused before parsing
    starts, and an integer longer than MAX_INTEGER_DIGITS before it is converted."""
    require(nesting_depth(raw) <= MAX_JSON_DEPTH, "input.unreadable_or_invalid")

    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    def integer(numeral):
        require(len(numeral.lstrip("-")) <= MAX_INTEGER_DIGITS, "input.unreadable_or_invalid")
        return int(numeral)

    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_int=integer)


def read_json(path):
    """A JSON input file through the bounded loader above, never the sibling's unbounded load_json."""
    return loads(Path(path).read_bytes())


def document_path(name):
    return f"{CONTENT}/{name}.json"


def schema_path(name):
    return f"{CONTENT}/{name}.schema.json"


def read_base(sources):
    """Each content document at the base, checked against the schema of that same base commit (a candidate schema
    may legitimately tighten), or None where the base predates it. A base document without its schema fails closed."""
    base = {}
    for name in DOCUMENTS:
        try:
            raw = sources.base_file(document_path(name))
            raw_schema = None if raw is None else sources.base_file(schema_path(name))
        except LookupError:
            raise Refused("base.unavailable") from None
        if raw is None:
            base[name] = None
            continue
        try:
            require(raw_schema is not None, "base.invalid")
            base[name] = loads(raw)
            shape(base[name], loads(raw_schema))
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise Refused("base.invalid") from None
    return base


# Status moves a record may make without a new version: never back to approved or into review once expired/withdrawn.
STATUS_SUCCESSORS = {
    "draft": {"draft", "in_review", "approved", "withdrawn"},
    "in_review": {"draft", "in_review", "approved", "withdrawn"},
    "approved": {"approved", "expired", "withdrawn"},
    "expired": {"expired", "withdrawn"},
    "withdrawn": {"withdrawn"},
}


def check_record_history(before, after):
    """History is append-only against the base: earlier entries stay byte-identical, the superseded version is kept
    with its own text, key and approval, and an approval or terminal status never changes without a new version."""
    identifier = after["id"]
    kept = after["history"][:len(before["history"])]
    require(kept == before["history"], "regulated.history_rewritten", identifier)
    if after["version"] == before["version"]:
        require(after["status"] in STATUS_SUCCESSORS[before["status"]], "regulated.status_reverted", identifier)
        # An approval on record is never re-dated or dropped (withdrawn copy keeps it); none is invented on withdrawal.
        if before["approval"] is not None or after["status"] == "withdrawn":
            require(after["approval"] == before["approval"], "regulated.approval_rewritten", identifier)
        return
    entry = next((prior for prior in after["history"] if prior["version"] == before["version"]), None)
    require(entry is not None and entry["copy"] == before["copy"] and entry["key"] == before["key"],
            "regulated.prior_version_not_kept", identifier)
    allowed = {before["status"], "withdrawn"} | ({"expired"} if before["status"] == "approved" else set())
    require(entry["status"] in allowed, "regulated.history_rewritten", identifier)
    # The superseded version keeps exactly the approval it had: never dropped, re-dated or invented.
    require(entry["approval"] == before["approval"], "regulated.approval_rewritten", identifier)


# What consumers read from a term or key: changing any of these, or adding an item, needs at least a minor bump.
VERSIONED_FIELDS = {
    "glossary": ("preferred_label", "definition", "surfaces", "forbidden_aliases", "contract_field_names"),
    "message-keys": ("category", "copy", "range", "platforms", "term_refs", "neutral_safe_exit", "regulated_ref"),
}
# What a record version identifies: its text, the key that renders it, the key shown when it cannot render and its
# category. None of these changes while the version stays the same.
RECORD_VERSIONED_FIELDS = ("copy", "key", "fail_closed_key", "category")
CHANGE_RULES = {"glossary": "glossary.changed_without_minor", "message-keys": "catalogue.changed_without_minor"}


def check_base(documents, base):
    """Additive versioning against the base: versions never regress; adding or changing a term or key needs at least
    a minor bump and removing one a major bump; regulated records are never removed (withdraw instead) and their
    copy, key binding, fail-closed key and category never change without a new version."""
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
            # Voice: any change to what consumers read (patterns, banned list, sentence limit, rules) needs a minor.
            unchanged = all(documents[name][field] == before[field] for field in documents[name]
                            if field != version_field) and set(before) == set(documents[name])
            require(unchanged or new[:2] > old[:2], "voice.changed_without_minor")
            continue
        current = {item[identity]: item for item in documents[name][items]}
        for item in before[items]:
            subject = item[identity]
            if subject in current:
                continue
            require(name != "regulated-copy" and new[0] > old[0], removal_rule, subject)
        if name in VERSIONED_FIELDS:
            previous = {item[identity]: item for item in before[items]}
            for subject, item in current.items():
                changed = subject not in previous or any(
                    item[field] != previous[subject][field] for field in VERSIONED_FIELDS[name])
                require(not changed or new[:2] > old[:2], CHANGE_RULES[name], subject)
        if name == "regulated-copy":
            for item in before[items]:
                after = current[item["id"]]
                require(version(after["version"]) >= version(item["version"]), "version.regressed", item["id"])
                require(all(after[field] == item[field] for field in RECORD_VERSIONED_FIELDS)
                        or after["version"] != item["version"], "regulated.changed_without_version", item["id"])
                check_record_history(item, after)


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
        "aliases": alias_forms(glossary),
        "placeholders": check_placeholders(catalogue, facts),
        "data_placeholders": {item["id"] for item in catalogue["placeholders"]
                              if item["source"] in DATA_PLACEHOLDER_SOURCES},
    }
    identifiers = regulated_ids(regulated)
    keys = check_keys(catalogue, facts, terms, context, roles, identifiers)
    check_patterns(voice, keys)
    check_regulated(regulated, keys, terms, context, roles, now, owner)
    base = read_base(sources)
    try:
        check_base(documents, base)
    except (KeyError, TypeError, AttributeError):
        # A base shaped by an older schema may lack a field the comparison reads: fail closed, never skip.
        raise Refused("base.invalid") from None
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
    gaps["readiness.pattern_slot_unstated"] = [
        f"pattern.{pattern['id']}.{slot}" for pattern in documents["voice"]["patterns"] for slot in SLOTS
        if pattern["slots"][slot] is None
    ]
    return {rule: sorted(subjects) for rule, subjects in gaps.items()}


def structure_line(model):
    documents = model.documents
    glossary, catalogue = documents["glossary"], documents["message-keys"]
    regulated, voice = documents["regulated-copy"], documents["voice"]
    roots = {f"{root}.": sum(key.split(".", 1)[0] == root for key in model.keys) for root in RESERVED_ROOTS}
    # Every key is counted once: keys outside the reserved roots (such as pattern. slot keys) are "other".
    roots["other"] = len(model.keys) - sum(roots.values())
    return (
        f"Content glossary {glossary['glossary_version']} structure valid: {len(glossary['terms'])} terms "
        f"({sum(term['comprehension']['required'] for term in glossary['terms'])} need comprehension evidence); "
        f"voice {voice['voice_version']}: {len(voice['banned_patterns'])} banned patterns, "
        f"{len(voice['patterns'])} content patterns, taxonomy copy rules imported by reference; message keys "
        f"{catalogue['catalogue_version']}: {len(model.keys)} keys (" +
        ", ".join(f"{count} {root}" for root, count in roots.items()) +
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
              "Each pattern must state source, status, consequence, safe remainder and next action. Taxonomy "
              "patterns map a slot to their state's own copy; a slot the taxonomy does not state is a readiness gap "
              "for its owner and stays unfilled here. The others name one distinct key of the pattern's category per "
              "slot. Whether the copy meets the criterion is held for human review.", ""]
    rows = []
    for pattern in voice["patterns"]:
        state = pattern["taxonomy_state"]
        slots = [code(pattern["slots"][slot]) if pattern["slots"][slot] else f"not stated (held: {STATE_SOURCE})"
                 for slot in SLOTS]
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
    lines += ["", "## Copy by version", "",
              "Current copy first, then every prior version with its own text; a rollback pin shows the pinned text.",
              ""]
    for record in regulated["records"]:
        lines += [f"- {record['id']} {record['version']} ({record['status']}): {cell(record['copy'])}"]
        for prior in record["history"]:
            pinned = " - rollback pin" if prior["version"] == record["rollback_version"] else ""
            lines += [f"  - {prior['version']} ({prior['status']}{pinned}): {cell(prior['copy'])}"]
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
    documents = {name: read_json(root / document_path(name)) for name in DOCUMENTS}
    schemas = {name: read_json(root / schema_path(name)) for name in DOCUMENTS}
    return documents, schemas


def load_and_check(root, now, base=None):
    root = Path(root)
    documents, schemas = load_documents(root)
    return check(
        documents, schemas, read_json(root / TAXONOMY), read_json(root / GATES), now, GitSources(root, base),
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
