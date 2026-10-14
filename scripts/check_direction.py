"""Offline T-UXR-07 checks of the concept directions, synthetic probes and the pending D2 direction record.

PenniLogic/docs#76 publishes seven candidate visual and interaction directions DIR-01..DIR-07 as
product/direction/candidates.json, four static synthetic probes PRB-01..PRB-04 as product/direction/probes.json and
one SemVer-versioned direction record as product/direction/direction-record.json, all validated against
product/direction/direction.schema.json (a self-contained draft-07 subset; definitions candidate_set, probe_set and
direction_record).

Candidates span distinct material and graphic traditions and cite product truth by {commit, path, sha256}: a
Markdown or JSON document (never a schema, script or spike) under a product-truth root (product/, adr/, research/,
governance/, architecture/; never product/direction/) at a commit reachable from the accepted base ACCEPTED_BASE,
whose blob digest is checked in the local Git object store, so it needs a full-depth clone (a shallow clone is
refused as grounding.shallow_history). The check proves the cited bytes exist on accepted main;
it does not prove that the cited text supports the candidate.
Each candidate may carry non-binding, candidate-scoped illustrative sRGB values; they exist only to compute WCAG 2.x
contrast feasibility (relative luminance) per text and UI pair, and every claimed pass/fail must equal the computed
result; every value must be used by a pair. The no-raw-token rule applies to every other string: the record and the
probes and all candidate prose expose semantic roles and platform consequences, never a raw color, dimension, font
or token contract (docs#55). The raw-value, gamification, shame and trust-theater checks are lexical tripwires over
ASCII text (non-ASCII is refused); qualified Design and Accessibility review remains the control for those categories.

The record stays `pending` with `participant_count: null` (never 0) and `decision: null`. The validator refuses
AI-preference, internal-vote, synthetic-participant and mood-board "evidence", self-approval and platform-lead
approval, any final token contract and any non-pending status: no D2 gate record is resolvable offline, so no session
can record the decision_coordinator's D2 choice here. Representative-user evidence from the ticket's own
order-balanced direction study (docs#76 test 1; docs#53's frozen protocol covers debt versus expense cards only, and
participant contact waits for docs#65's pre-contact and consent conditions), validated personas (docs#66),
qualified Accessibility, Content and platform reviews and the D2 decision are counted as readiness gaps, never filled
in, and keep the default mode NOT GREEN. `--render` prints the generated markdown view
product/direction/README.md; a unittest pins the committed file to it. Every issue reference in the record must
resolve in the offline snapshot planning/issue-inventory.json; the record must name non-empty unresolved risks (each
open, with an owning issue), implementation consequences and consumers including docs#55, and, while pending, hold
docs#53, docs#65, infra#22 and D2's prerequisite D1 (docs#66, docs#67, docs#74, docs#75).

Structure failures raise `Refused` with a static rule identifier plus, at most, identifiers that match a DIR/PRB
grammar, a semantic role, a gate role or a `PenniLogic/<repo>#N` reference; input text is never echoed. Everything
runs offline: no network, remote action, approval, appointment or study is made or implied.
"""

import argparse
import functools
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = "product/direction/candidates.json"
PROBES = "product/direction/probes.json"
RECORD = "product/direction/direction-record.json"
SCHEMA = "product/direction/direction.schema.json"
# The committed offline issue snapshot that check_test_strategy.py also resolves owners against.
INVENTORY = "planning/issue-inventory.json"
GREEN = "GREEN: readiness complete"
NOT_GREEN = "NOT GREEN: readiness incomplete"


def _sibling(name, filename):
    """Load an accepted sibling checker read-only by path, as check_design_gates.py does."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


support = _sibling("direction_schema_support", "check_client_states.py")
gates = _sibling("direction_design_gates", "check_design_gates.py")

CANDIDATE_IDS = tuple(f"DIR-{number:02d}" for number in range(1, 8))
PROBE_TOPICS = {
    "PRB-01": "debt_progress", "PRB-02": "transaction_clarification",
    "PRB-03": "household_privacy", "PRB-04": "operator_urgency",
}
CANDIDATE_ID = re.compile(r"DIR-0[1-7]")
PROBE_ID = re.compile(r"PRB-0[1-4]")
ISSUE_REF = re.compile(r"(?:pending:)?PenniLogic/(docs|android|web|admin|api|contracts|infra)#[1-9][0-9]*")
SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
COMMIT = re.compile(r"[0-9a-f]{40}")
SEMANTIC_ROLES = (
    "surface", "surface_raised", "text_primary", "text_secondary", "control_boundary", "focus_indicator",
    "emphasis", "progress", "uncertainty", "provenance", "warning", "control",
)
# WCAG 2.x minimum contrast ratios: 1.4.3 (text, large text) and 1.4.11 (non-text UI components and focus).
CONTRAST_MINIMUM = {"text": 4.5, "large_text": 3.0, "ui": 3.0}
# Every candidate is assessed on the same pairs on its base surface, so failing counts compare across candidates:
# body and secondary text, the control boundary (the ticket's "control" legibility subject), the focus indicator, and
# the legibility subjects progress and uncertainty (non-text marks), provenance and warning (text).
REQUIRED_PAIRS = (
    ("text", "text_primary", "surface"), ("text", "text_secondary", "surface"),
    ("ui", "control_boundary", "surface"), ("ui", "focus_indicator", "surface"),
    ("ui", "progress", "surface"), ("ui", "uncertainty", "surface"),
    ("text", "provenance", "surface"), ("text", "warning", "surface"),
)
# Roles that review the record (D2 verifier and the ticket's Content and platform feasibility reviews).
REQUIRED_REVIEWS = ("accessibility", "content", "android_design", "web_design", "admin_design")
PLATFORM_ROLES = ("android_design", "web_design", "admin_design")
APPROVER_ROLE = "decision_coordinator"
# While pending, the record keeps the coordinator appendix's retained gates (docs#53 debt-study input, docs#66
# personas, infra#22 CI conformance), the docs#65 pre-contact and consent conditions (research/operations/README.md:
# no participant contact before them) and D2's prerequisite D1 (docs#66, docs#67, docs#74, docs#75; design-gates D2
# requires D1).
REQUIRED_HELD_GATES = tuple(f"pending:PenniLogic/{name}" for name in (
    "docs#53", "docs#65", "docs#66", "docs#67", "docs#74", "docs#75", "infra#22"))
# T-DSY-01 consumes the approved direction's semantic roles as its token contract.
REQUIRED_CONSUMERS = ("PenniLogic/docs#55",)
INVENTORY_REF = re.compile(r"PenniLogic/[A-Za-z0-9._-]+#[1-9][0-9]*")
TEXT_LIMIT = 600
SCRUBBED_GIT_VARIABLES = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR", "GIT_NAMESPACE",
)

# Content shapes refused in every string of every document (rule, pattern), checked in this order.
CONTENT_SHAPES = (
    ("content.markup", re.compile(r"<\s*/?\s*[A-Za-z!?]")),
    ("content.url_shape", re.compile(r"(?i)\b(?:https?|ftp|file|data|javascript|mailto):|\bwww\.|//[A-Za-z0-9]")),
    ("content.email_shape", re.compile(r"[^\s@]+@[^\s@]+\.[A-Za-z]{2,}")),
    ("content.account_shape", re.compile(r"[0-9](?:[ .-]?[0-9]){8,}")),
    ("content.gamification", re.compile(
        r"(?i)\b(?:streaks?|leaderboards?|confetti|badges?|troph(?:y|ies)|level(?:ed|s)? up|high scores?|"
        r"achievements? unlocked|earn(?:ed)? points|xp|coins?|reward points|(?:bronze|silver|gold|platinum|vip) tiers?|"
        r"(?:unlock|earn|win|collect|claim)(?:s|ed|ing)?(?:\s+\w+){0,3}?\s+(?:rewards?|prizes?|tiers?|levels?))\b")),
    ("content.shame_language", re.compile(
        r"(?i)\b(?:you failed|lazy|irresponsible|bad with money|careless|shameful|embarrassing)\b")),
    ("content.trust_theater", re.compile(
        r"(?i)\b(?:padlocks?|shields?|lock icons?|locks?|bank[- ]grade|military[- ]grade|100% (?:secure|safe)|"
        r"fully secure|compliance badges?|certified(?: secure)?|guaranteed safe|compliant|encrypt(?:ion|ed)|"
        r"seals?)\b")),
)
TOKEN = re.compile(r"[A-Za-z0-9+/=_-]{32,}")
HEX_RUN = re.compile(r"[0-9a-fA-F]{32,}")
# The no-raw-token rule (HC-m9): applies to every string of the direction record and the probes; only candidates
# may carry candidate-scoped illustrative values. Issue references are removed first, so `docs#126` is not a color
# while `tone#F7F3E8` is; a repository name followed by a decimal number (`web#123`) is read as an issue reference.
RAW_TOKEN = re.compile(
    r"(?i)#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\s*\(|"
    r"\b[0-9]+(?:\.[0-9]+)?\s*(?:px|dp|sp|pt|rem|em)\b|\bfont-(?:family|weight|size)\b|"
    r"\b(?:colou?r|spacing|radius|elevation|typography|font|motion|shadow|palette|theme|button|tokens?|sys)\.[a-z]|"
    r"(?<![A-Za-z0-9])--[a-z][a-z0-9-]*|"
    # ASCII spellings without the CSS syntax: 0xAARRGGBB, `rgb 31 42 68`, `48-dp`, `16 pixels`.
    r"\b0x[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|oklab|oklch)\s+[0-9]|"
    r"\b[0-9]+(?:\.[0-9]+)?\s*-\s*(?:px|dp|sp|pt|rem|em)\b|\b[0-9]+(?:\.[0-9]+)?\s*-?\s*(?:pixels?|dips?)\b"
)
TEXT_ISSUE_REF = re.compile(
    r"(?:pending:)?(?:PenniLogic/)?\b(?:docs|android|web|admin|api|contracts|infra)#[1-9][0-9]*\b")
# Probe text may not reference asset files: probes are static text descriptions without external assets.
ASSET = re.compile(r"(?i)\.(?:png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|otf|js|mjs|css|html?|mp4|webm|lottie)\b")
# Grounding pins are the only exempt strings, and only with their exact grammar.
EXEMPT = {"commit": COMMIT, "sha256": re.compile(r"sha256:[0-9a-f]{64}")}
# The accepted main commit this source branched from. Every grounding pin must be reachable from it, so a pin can
# never cite unmerged or candidate-local bytes; citing a newer accepted commit means updating this reviewed constant.
ACCEPTED_BASE = "1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4"
# Product truth is published under these roots; this source's own directory is never its own grounding.
PRODUCT_TRUTH_ROOTS = ("product/", "adr/", "research/", "governance/", "architecture/")
SELF_ROOT = "product/direction/"
# Product truth is a document: Markdown or a JSON data file. Checkers, generators, spike code and schemas under the
# roots (for example research/operations/*.py, research/spikes/** or *.schema.json) describe tooling, not the product.
PRODUCT_TRUTH_DOCUMENT = re.compile(r"[^/]+\.(?:md|json)")
# Candidate keys whose values are raw by design: illustrative sRGB values and grounding pins.
CANDIDATE_RAW_KEYS = ("srgb", "commit", "path", "sha256")
CATEGORY_DEFAULT = re.compile(r"(?:^|_)(?:fintech|neobank|dashboard|banking_app|glassmorphism)(?:_|$)")

STRUCTURE_RULES = (
    "input.unreadable_or_invalid", "schema.invalid",
    "content.too_long", "content.blank_or_padded", "content.unprintable_character", "content.invisible_character",
    "content.mixed_script",
    "content.secret_shape",
    "content.markup", "content.url_shape", "content.email_shape", "content.account_shape", "content.gamification",
    "content.shame_language", "content.trust_theater", "content.non_ascii",
    "candidate.count", "candidate.id_sequence", "candidate.incomplete", "candidate.name_duplicate",
    "candidate.material_not_distinct", "candidate.graphic_not_distinct", "candidate.category_default",
    "candidate.binding_values", "candidate.raw_value", "held.persona_validation",
    "grounding.missing", "grounding.path_not_canonical", "grounding.self_reference", "grounding.not_product_truth",
    "grounding.not_accepted", "grounding.unavailable", "grounding.shallow_history", "grounding.digest_mismatch",
    "contrast.duplicate_role", "contrast.unknown_role", "contrast.duplicate_pair", "contrast.required_pair_missing",
    "contrast.result_mismatch", "contrast.unused_role",
    "probe.count", "probe.topic_mismatch", "probe.markup", "probe.external_asset", "probe.raw_value", "probe.not_synthetic",
    "probe.unsafe_access_depiction", "probe.candidate_coverage",
    "record.version_grammar", "record.raw_token", "record.candidate_mismatch", "record.unknown_role",
    "record.semantic_roles_incomplete", "record.final_token_contract", "record.participant_count_zero",
    "record.participant_count_pending", "record.pending_with_decision", "record.decision_missing",
    "evidence.ai", "evidence.internal_vote", "evidence.synthetic", "evidence.mood_board", "evidence.missing",
    "held.study_evidence", "record.duplicate_entry", "record.incomplete", "record.dangling_reference",
    "record.consumer_missing", "record.held_gate_missing", "record.supersedes_unresolvable", "held.risk_disposition",
    "review.missing_role", "review.duplicate_role", "review.self_review", "held.review_record",
    "decision.invalid", "decision.unknown_candidate", "decision.rejected_mismatch", "decision.self_approval",
    "decision.platform_self_approval", "decision.wrong_approver", "held.d2_decision",
)
READINESS_RULES = (
    "readiness.user_evidence_missing", "readiness.persona_unvalidated", "readiness.review_pending",
    "readiness.contrast_failing", "readiness.decision_pending", "readiness.held_gate",
)
PAIR_SUBJECT = re.compile(r"(?:%s):(?:%s)" % ("|".join(SEMANTIC_ROLES), "|".join(SEMANTIC_ROLES)))


def printable(value):
    """Only grammar-validated identifiers may appear in output; everything else is input text."""
    return isinstance(value, str) and (
        CANDIDATE_ID.fullmatch(value) is not None or PROBE_ID.fullmatch(value) is not None
        or ISSUE_REF.fullmatch(value) is not None or value in SEMANTIC_ROLES or value in gates.ROLES
        or PAIR_SUBJECT.fullmatch(value) is not None or value == "D2"
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


def loads(raw):
    """Strict JSON from bytes: UTF-8 and no duplicate keys, like check_client_states.load_json."""
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value
    def finite_only(name):
        raise ValueError("non-finite JSON number")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=finite_only)


def shape(value, schema, definition):
    """Validate with the shared subset validator; its messages echo input, so only the rule survives."""
    try:
        support.validate_schema(value, schema["definitions"][definition], schema)
    except (ValueError, KeyError, TypeError, RecursionError, re.error):
        raise Refused("schema.invalid") from None


def subject_of(value):
    """The nearest printable record identifier of a JSON object, if any."""
    if isinstance(value, dict):
        for key in ("id", "candidate", "role"):
            if printable(value.get(key)):
                return (value[key],)
    return None


def _secret_token(text):
    for candidate in (text, re.sub(r"[-/_]", "", text)):
        if HEX_RUN.search(candidate):
            return True
        for match in TOKEN.finditer(candidate):
            if all(any(test(c) for c in match.group()) for test in (str.isdigit, str.islower, str.isupper)):
                return True
    return False


def fold(text):
    """The NFKC compatibility form with every non-ASCII decimal digit as its ASCII digit.

    Shape and lexicon scans run on the text, on this form and on its Latin skeleton (see forms), so fullwidth
    letters, ligatures, mathematical alphanumerics or Devanagari digits do not carry a refused word, raw value or
    account-like number past them; invisible marks are refused outright. Residual: look-alikes outside the
    CONFUSABLE subset are not mapped, but scan_text refuses any character still non-ASCII after this fold
    (content.non_ascii), so they cannot reach published data while it is ASCII-only.
    """
    if text.isascii():
        return text
    text = unicodedata.normalize("NFKC", text)
    return "".join(str(unicodedata.decimal(c)) if c.isdecimal() and not c.isascii() else c for c in text)


HOMOGLYPH_SCRIPTS = {"CYRILLIC", "GREEK"}
# Unicode Default_Ignorable_Code_Point (DerivedCoreProperties): invisible marks that render as nothing, so a refused
# word can hide behind them. Some are category Mn or Lo and pass str.isprintable(), hence an explicit list.
DEFAULT_IGNORABLE = re.compile(
    "[\u00ad\u034f\u061c\u115f\u1160\u17b4\u17b5\u180b-\u180f\u200b-\u200f\u202a-\u202e\u2060-\u206f"
    "\u3164\ufe00-\ufe0f\ufeff\uffa0\ufff0-\ufff8\U0001bca0-\U0001bca3\U0001d173-\U0001d17a"
    "\U000e0000-\U000e0fff]")
# Cyrillic and Greek letters that render like Latin ones (a subset of Unicode confusables), mapped to the Latin letter
# they imitate, so a whole word spelled in look-alikes is scanned as the Latin word it shows.
CONFUSABLE = str.maketrans(dict(zip(
    "\u0430\u0435\u043e\u0440\u0441\u0443\u0445\u0455\u0456\u0458\u04bb\u04cf\u0501\u051b\u051d"
    "\u0410\u0412\u0415\u041a\u041c\u041d\u041e\u0420\u0421\u0422\u0425\u0405\u0406\u0408\u04ae"
    "\u03b1\u03bf\u03c1\u03b9\u03ba\u03bd\u03c5\u03c4\u03c7"
    "\u0391\u0392\u0395\u0396\u0397\u0399\u039a\u039c\u039d\u039f\u03a1\u03a4\u03a5\u03a7",
    "aeopcyxsijhldqw" "ABEKMHOPCTXSIJY" "aopikvutx" "ABEZHIKMNOPTYX", strict=True)))


def skeleton(text):
    """The text with Cyrillic and Greek look-alike letters replaced by the Latin letters they imitate."""
    return text if text.isascii() else text.translate(CONFUSABLE)


def forms(text):
    """The distinct forms every shape and lexicon scan runs on: as written, folded, and its Latin skeleton."""
    if text.isascii():
        return (text,)
    folded = fold(text)
    return tuple(dict.fromkeys((text, folded, skeleton(folded))))


def mixed_script(text):
    """True when one word mixes Latin letters with Cyrillic or Greek ones (a homoglyph-spelled word)."""
    if text.isascii():
        return False
    for word in re.findall(r"\w+", text):
        scripts = {unicodedata.name(c, "").split(" ")[0] for c in word if c.isalpha()}
        if "LATIN" in scripts and scripts & HOMOGLYPH_SCRIPTS:
            return True
    return False


@functools.lru_cache(maxsize=8192)
def content_rule(text):
    """The first content rule the text violates, or None; depends on the text alone, so repeated strings (roles,
    kinds, results) are scanned once per process."""
    try:
        _scan(text)
    except Refused as refused:
        return refused.rule
    return None


def scan_text(text, subject):
    rule = content_rule(text)
    if rule is not None:
        raise Refused(rule, *subject)


def _scan(text):
    require(len(text) <= TEXT_LIMIT, "content.too_long")
    require(text.strip() == text and text != "", "content.blank_or_padded")
    require(text.isprintable(), "content.unprintable_character")
    require(DEFAULT_IGNORABLE.search(text) is None, "content.invisible_character")
    require(not mixed_script(text), "content.mixed_script")
    variants = forms(text)
    require(not any(_secret_token(form) for form in variants), "content.secret_shape")
    for rule, pattern in CONTENT_SHAPES:
        require(not any(pattern.search(form) for form in variants), rule)
    # The published data is ASCII. Until a declared localization field needs other scripts, any character left
    # non-ASCII after folding (accented or small-capital Latin, IPA, other scripts, combining marks) is refused, so a
    # look-alike outside the CONFUSABLE subset or a foreign letter glued to a word cannot slip past the lexicons.
    require(fold(text).isascii(), "content.non_ascii")


def strings(document):
    """Yield (text, subject, key) for every string value and key, depth first, in document order."""
    def walk(value, subject, key):
        if isinstance(value, dict):
            subject = subject_of(value) or subject
            for name, item in value.items():
                yield name, subject, None
                yield from walk(item, subject, name)
        elif isinstance(value, list):
            for item in value:
                yield from walk(item, subject, key)
        elif isinstance(value, str):
            yield value, subject, key
    yield from walk(document, (), None)


def guard_content(document):
    """Scan every string (and key) of a document; only grounding pins with their exact grammar are exempt."""
    for text, subject, key in strings(document):
        grammar = EXEMPT.get(key)
        if grammar is None or grammar.fullmatch(text) is None:
            scan_text(text, subject)


def raw_value(text):
    """True when any form of the text, with issue references removed, shows a raw color, dimension, font or token."""
    return any(RAW_TOKEN.search(TEXT_ISSUE_REF.sub(" ", form)) for form in forms(text))


def guard_record_tokens(record):
    """The no-raw-token rule: the direction record exposes semantic roles only (HC-m9)."""
    for text, subject, _ in strings(record):
        require(not raw_value(text), "record.raw_token", *subject)


def trusted_git(root):
    """Absolute path of git from absolute PATH entries outside the checked repository (as H06 resolves it).

    A bare "git" lets the operating system search relative PATH entries and, on Windows, the current directory
    first, so a candidate-local executable could forge the grounding blobs.
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
    """Pinned blobs from the local Git object store; never fetches, writes or pushes."""

    def __init__(self, root, base=None):
        self.root, self.executable, self.base = Path(root), None, base

    def accepted(self, commit):
        """True when the pinned commit is the accepted base or one of its ancestors (reachable from accepted main)."""
        if not (isinstance(commit, str) and COMMIT.fullmatch(commit)):
            raise LookupError("unpinned source")
        result = self._git("merge-base", "--is-ancestor", commit, self.base or ACCEPTED_BASE)
        if result.returncode not in (0, 1):
            raise LookupError("ancestry unavailable")
        return result.returncode == 0

    def shallow(self):
        """True when this checkout's history is truncated (a shallow clone), so older pins may be absent."""
        result = self._git("rev-parse", "--is-shallow-repository")
        return result.returncode == 0 and result.stdout.strip() == b"true"

    def _git(self, *args):
        self.executable = self.executable or trusted_git(self.root)
        env = {key: value for key, value in os.environ.items() if key not in SCRUBBED_GIT_VARIABLES}
        # Objects exactly as stored: no lazy fetch, and no replace refs or grafts that could substitute blobs.
        env.update(GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1", GIT_GRAFT_FILE=os.devnull)
        try:
            return subprocess.run(
                [self.executable, "--no-pager", *args], cwd=self.root, capture_output=True, timeout=30, env=env,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise LookupError("git unavailable") from None

    def blob(self, commit, path):
        if not (isinstance(commit, str) and COMMIT.fullmatch(commit) and isinstance(path, str)):
            raise LookupError("unpinned source")
        kind = self._git("cat-file", "-t", commit)
        if kind.returncode != 0 or kind.stdout.strip() != b"commit":
            raise LookupError("commit unavailable")
        result = self._git("cat-file", "blob", f"{commit}:{path}")
        if result.returncode != 0:
            raise LookupError("blob unavailable")
        return result.stdout


def sha256(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def relative_luminance(srgb):
    """WCAG 2.x relative luminance of an `#RRGGBB` sRGB value (0.04045 threshold as in IEC 61966-2-1)."""
    channels = []
    for index in (1, 3, 5):
        value = int(srgb[index:index + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first, second):
    """WCAG contrast ratio (L1 + 0.05) / (L2 + 0.05), lighter over darker; 1.0 to 21.0."""
    lighter, darker = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def contrast_passes(kind, foreground, background):
    return contrast_ratio(foreground, background) >= CONTRAST_MINIMUM[kind]


def check_contrast(candidate):
    """Every pair's claimed pass/fail equals the computed result; returns the failing pairs as subjects."""
    identifier = candidate["id"]
    values = {}
    for value in candidate["illustrative_values"]["values"]:
        require(value["role"] not in values, "contrast.duplicate_role", identifier, value["role"])
        values[value["role"]] = value["srgb"]
    seen, failing = set(), []
    for pair in candidate["contrast_pairs"]:
        key = (pair["kind"], pair["foreground"], pair["background"])
        subject = f"{pair['foreground']}:{pair['background']}"
        for role in key[1:]:
            require(role in values, "contrast.unknown_role", identifier, role)
        require(key not in seen, "contrast.duplicate_pair", identifier, subject)
        seen.add(key)
        computed = "pass" if contrast_passes(key[0], values[key[1]], values[key[2]]) else "fail"
        require(pair["result"] == computed, "contrast.result_mismatch", identifier, subject)
        if computed == "fail":
            failing.append(f"{identifier} {subject}")
    for required in REQUIRED_PAIRS:
        require(required in seen, "contrast.required_pair_missing", identifier, f"{required[1]}:{required[2]}")
    used = {role for key in seen for role in key[1:]}
    for role in values:
        # A value no pair uses is never computed, so it could carry an unchecked raw color into the candidate.
        require(role in used, "contrast.unused_role", identifier, role)
    return failing


def history_truncated(sources):
    """True only when the source port positively reports a shallow history; any doubt keeps the original rule."""
    try:
        return getattr(sources, "shallow", lambda: False)() is True
    except LookupError:
        return False


def check_grounding(candidate, sources, verified):
    """Each candidate cites product truth by {commit, path, sha256}: a canonical path under a product-truth root
    (never this source's own directory) at a commit reachable from the accepted base, whose blob digest matches."""
    identifier = candidate["id"]
    require(candidate["grounding"], "grounding.missing", identifier)
    for pin in candidate["grounding"]:
        # A pin names one canonical tree path: no `.` or `..` segment that git might resolve differently.
        require(not {".", ".."} & set(pin["path"].split("/")), "grounding.path_not_canonical", identifier)
        require(not pin["path"].startswith(SELF_ROOT), "grounding.self_reference", identifier)
        name = pin["path"].rsplit("/", 1)[-1]
        require(pin["path"].startswith(PRODUCT_TRUTH_ROOTS) and PRODUCT_TRUTH_DOCUMENT.fullmatch(name) is not None
                and not name.endswith(".schema.json") and not pin["path"].startswith("research/spikes/"),
                "grounding.not_product_truth", identifier)
        key = (pin["commit"], pin["path"])
        if key not in verified:
            accepted = None
            try:
                accepted = sources.accepted(pin["commit"])
                if accepted:
                    verified[key] = sha256(sources.blob(*key))
            except LookupError:
                pass
            if key not in verified:
                # A shallow clone cannot prove ancestry or hold older blobs: name the truncated history, not the pin.
                require(not history_truncated(sources), "grounding.shallow_history", identifier)
                require(accepted is not False, "grounding.not_accepted", identifier)
                raise Refused("grounding.unavailable", identifier)
        require(verified[key] == pin["sha256"], "grounding.digest_mismatch", identifier)


def check_candidates(document, sources):
    """Seven complete, distinct, grounded, non-default candidates; returns (failing pairs, unvalidated IDs)."""
    candidates = document["candidates"]
    require(len(candidates) == len(CANDIDATE_IDS), "candidate.count")
    require(tuple(item["id"] for item in candidates) == CANDIDATE_IDS, "candidate.id_sequence")
    names, materials, graphics, failing, unvalidated, verified = set(), set(), set(), [], [], {}
    for candidate in candidates:
        identifier = candidate["id"]
        require(all(candidate[key] for key in ("risks", "accessibility_notes", "persona_assumptions")),
                "candidate.incomplete", identifier)
        name = fold(candidate["name"]).casefold()
        require(name not in names, "candidate.name_duplicate", identifier)
        require(candidate["material_tradition"] not in materials, "candidate.material_not_distinct", identifier)
        require(candidate["graphic_tradition"] not in graphics, "candidate.graphic_not_distinct", identifier)
        names.add(name)
        materials.add(candidate["material_tradition"])
        graphics.add(candidate["graphic_tradition"])
        slugs = (candidate["material_tradition"], candidate["graphic_tradition"], re.sub(r"[^a-z0-9]+", "_", name))
        require(not candidate["category_default"] and not any(CATEGORY_DEFAULT.search(slug) for slug in slugs),
                "candidate.category_default", identifier)
        require(candidate["illustrative_values"]["binding"] is False, "candidate.binding_values", identifier)
        # docs#66 has no validated personas, so no assumption may claim validation.
        require(not any(item["validated"] for item in candidate["persona_assumptions"]),
                "held.persona_validation", identifier)
        # Only illustrative_values carries raw sRGB (computed for contrast) and grounding carries pins; candidate
        # prose is described in semantic terms like the record and the probes.
        require(not any(raw_value(text) for text, _, key in strings(candidate) if key not in CANDIDATE_RAW_KEYS),
                "candidate.raw_value", identifier)
        unvalidated.append(identifier)
        check_grounding(candidate, sources, verified)
        failing.extend(check_contrast(candidate))
    return failing, unvalidated


# Sharing and admin access are never ordinary browsing: each sensitive probe shows its explicit, bounded basis.
REQUIRED_DEPICTION = {"household_privacy": "explicit_revocable_grant", "operator_urgency": "audited_elevation"}


def check_probes(document):
    """Four static, offline, synthetic text probes, one per topic, each rendered for every candidate."""
    probes = document["probes"]
    require(len(probes) == len(PROBE_TOPICS), "probe.count")
    for expected, probe in zip(PROBE_TOPICS, probes):
        identifier = probe["id"]
        require(identifier == expected and probe["topic"] == PROBE_TOPICS[expected], "probe.topic_mismatch",
                *((identifier,) if printable(identifier) else ()))
        require(probe["format"] == "text", "probe.markup", identifier)
        require(probe["data_origin"] == "synthetic", "probe.not_synthetic", identifier)
        texts = [probe["scenario"], *(item["description"] for item in probe["renderings"])]
        require(not any(ASSET.search(form) for text in texts for form in forms(text)), "probe.external_asset",
                identifier)
        # Only candidates may carry candidate-scoped illustrative values; a probe is described in semantic terms.
        require(not any(raw_value(text) for text, _, _ in strings(probe)), "probe.raw_value", identifier)
        depiction = probe["access_depiction"]
        require(depiction != "ordinary_browsing" and depiction == REQUIRED_DEPICTION.get(probe["topic"], depiction),
                "probe.unsafe_access_depiction", identifier)
        require(tuple(item["candidate"] for item in probe["renderings"]) == CANDIDATE_IDS,
                "probe.candidate_coverage", identifier)


REFUSED_EVIDENCE = {
    "ai_preference": "evidence.ai", "internal_vote": "evidence.internal_vote",
    "synthetic_participant": "evidence.synthetic", "mood_board_preference": "evidence.mood_board",
}
# The ticket's legibility subjects: debt progress, provenance, uncertainty and control.
LEGIBILITY_ROLES = ("progress", "provenance", "uncertainty", "control")


def check_evidence(record):
    require(record["evidence"], "evidence.missing")
    for item in record["evidence"]:
        if item["kind"] in REFUSED_EVIDENCE:
            raise Refused(REFUSED_EVIDENCE[item["kind"]])
        require(item["data_origin"] != "synthetic_fixture", "evidence.synthetic")
        # No accepted representative-user direction study exists to resolve offline (none is planned yet).
        require(item["state"] == "pending" and item["study_ref"].startswith("pending:"), "held.study_evidence")
    count = record["participant_count"]
    require(count is None or count >= 1, "record.participant_count_zero")
    require(count is None or record["status"] != "pending", "record.participant_count_pending")


def check_reviews(record):
    author = record["prepared_by"]["ref"]
    seen = set()
    for review in record["reviews"]:
        role = review["role"]
        require(role in gates.ROLES, "record.unknown_role")
        require(role not in seen, "review.duplicate_role", role)
        seen.add(role)
        require(review["reviewer_ref"] != author, "review.self_review", role)
        # Reviews are recorded by qualified reviewers in their own records, never by this source.
        require(review["state"] == "pending" and review["reviewer_ref"] is None, "held.review_record", role)
    for role in REQUIRED_REVIEWS:
        require(role in seen, "review.missing_role", role)


def check_decision(record, schema):
    """A decision exists only outside `pending`; even a well-formed one is held: D2 is not resolvable here."""
    decision = record["decision"]
    if record["status"] == "pending":
        require(decision is None, "record.pending_with_decision")
        return
    require(decision is not None, "record.decision_missing")
    try:
        support.validate_schema(decision, schema["definitions"]["decision"], schema)
    except (ValueError, KeyError, TypeError, RecursionError, re.error):
        raise Refused("decision.invalid") from None
    require(decision["selected"] in CANDIDATE_IDS, "decision.unknown_candidate")
    others = sorted(set(CANDIDATE_IDS) - {decision["selected"]})
    require(sorted(decision["rejected"]) == others and len(set(decision["rejected"])) == len(others),
            "decision.rejected_mismatch", decision["selected"])
    author, role = record["prepared_by"], decision["approver_role"]
    responsible = {"systems", "content"}  # design-gates visual_direction responsible roles prepare, never approve
    require(role != author["role"] and role not in responsible and decision["approver_ref"] != author["ref"],
            "decision.self_approval")
    require(role not in PLATFORM_ROLES, "decision.platform_self_approval", role)
    require(role == APPROVER_ROLE, "decision.wrong_approver")
    raise Refused("held.d2_decision", "D2")


def issue_index(inventory):
    """The set of issue references in the offline inventory snapshot; a malformed snapshot is unreadable input."""
    issues = inventory.get("issues") if isinstance(inventory, dict) else None
    if not isinstance(issues, list) or not issues:
        raise ValueError("inventory has no issues")
    references = set()
    for issue in issues:
        reference = issue.get("reference") if isinstance(issue, dict) else None
        if not isinstance(reference, str) or INVENTORY_REF.fullmatch(reference) is None:
            raise ValueError("inventory reference malformed")
        references.add(reference)
    return frozenset(references)


def record_references(record):
    """Every issue reference the record makes, in document order."""
    yield record["source_issue"]
    yield record["prepared_by"]["ref"]
    yield from (item["study_ref"] for item in record["evidence"])
    yield from (item["owner_ref"] for item in record["unresolved_risks"])
    yield record["token_contract"]["owner_issue"]
    yield from record["consumers"]
    yield from record["held_gates"]


def check_links(record, issues):
    """Completeness (AC4) and resolution: every reference names an issue in the offline inventory snapshot."""
    require(all(record[key] for key in ("unresolved_risks", "implementation_consequences", "consumers")),
            "record.incomplete")
    for reference in record_references(record):
        bare = reference[len("pending:"):] if reference.startswith("pending:") else reference
        require(bare in issues, "record.dangling_reference", reference)
    for reference in REQUIRED_CONSUMERS:
        require(reference in record["consumers"], "record.consumer_missing", reference)
    if record["status"] == "pending":
        for reference in REQUIRED_HELD_GATES:
            require(reference in record["held_gates"], "record.held_gate_missing", reference)
    # No prior D2 direction record exists or is resolvable offline, so this record can supersede nothing.
    require(record["supersession"]["supersedes"] is None, "record.supersedes_unresolvable")
    # Mitigating or accepting a risk needs evidence or the D2 decision, neither of which exists here.
    require(all(item["state"] == "open" for item in record["unresolved_risks"]), "held.risk_disposition")


def check_record(record, schema, issues):
    require(SEMVER.fullmatch(record["version"]) is not None, "record.version_grammar")
    require(record["candidates_considered"] == list(CANDIDATE_IDS), "record.candidate_mismatch")
    require(record["prepared_by"]["role"] in gates.ROLES, "record.unknown_role")
    roles = [entry["role"] for entry in record["semantic_roles"]]
    require(len(roles) == len(set(roles)) and set(LEGIBILITY_ROLES) <= set(roles),
            "record.semantic_roles_incomplete")
    contract = record["token_contract"]
    require(contract["state"] != "final" and contract["reference"] is None, "record.final_token_contract")
    check_evidence(record)
    # Duplicates would inflate the readiness gap counts; checked after the evidence kinds so those refuse first.
    for entries in ([item["study_ref"] for item in record["evidence"]], record["consumers"], record["held_gates"]):
        require(len(entries) == len(set(entries)), "record.duplicate_entry")
    check_links(record, issues)
    check_reviews(record)
    check_decision(record, schema)


class Model:
    """The checked documents plus what readiness needs."""

    def __init__(self, candidates, probes, record, failing, unvalidated):
        self.candidates, self.probes, self.record = candidates, probes, record
        self.failing, self.unvalidated = failing, unvalidated


def check(candidates, probes, record, schema, sources, issues):
    """Run every structure rule in a fixed order; raise Refused at the first violation, else return the model."""
    shape(candidates, schema, "candidate_set")
    shape(probes, schema, "probe_set")
    shape(record, schema, "direction_record")
    for document in (candidates, probes, record):
        guard_content(document)
    guard_record_tokens(record)
    failing, unvalidated = check_candidates(candidates, sources)
    check_probes(probes)
    check_record(record, schema, issues)
    return Model(candidates, probes, record, failing, unvalidated)


def readiness(model):
    """Every visible gap by static rule, in published order; never filled in or waived."""
    record = model.record
    gaps = {rule: [] for rule in READINESS_RULES}
    gaps["readiness.user_evidence_missing"] = [
        item["study_ref"] for item in record["evidence"] if item["state"] != "accepted"
    ]
    gaps["readiness.persona_unvalidated"] = list(model.unvalidated)
    gaps["readiness.review_pending"] = [item["role"] for item in record["reviews"] if item["state"] == "pending"]
    gaps["readiness.contrast_failing"] = list(model.failing)
    gaps["readiness.decision_pending"] = ["D2"] if record["status"] == "pending" else []
    gaps["readiness.held_gate"] = list(record["held_gates"])
    return gaps


def structure_line(model):
    pairs = sum(len(item["contrast_pairs"]) for item in model.candidates["candidates"])
    return (
        f"Direction structure valid: {len(model.candidates['candidates'])} candidates, "
        f"{len(model.probes['probes'])} probes, {pairs} contrast pairs ({len(model.failing)} failing), "
        f"record {model.record['version']} {model.record['status']}"
    )


MARKDOWN = "product/direction/README.md"
RENDER_COMMAND = "python scripts/check_direction.py --render > product/direction/README.md"


def cell(text):
    """A markdown table cell: backslashes and pipes escaped; checked content has no newlines or markup."""
    return str(text).replace("\\", "\\\\").replace("|", "\\|")


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(cell(item) for item in row) + " |" for row in rows]
    return lines


def ratio_text(foreground, background):
    """The ratio truncated (never rounded up) to two decimals, so a displayed value never overstates contrast."""
    return f"{int(contrast_ratio(foreground, background) * 100) / 100:.2f}"


def render_candidate(candidate):
    values = {item["role"]: item["srgb"] for item in candidate["illustrative_values"]["values"]}
    lines = [
        f"### {candidate['id']} {candidate['name']}", "",
        f"Material tradition `{candidate['material_tradition']}`; graphic tradition "
        f"`{candidate['graphic_tradition']}`.", "",
    ]
    for label, key in (("Rationale", "rationale"), ("Intended feel", "intended_feel"),
                       ("Form language", "form_language"), ("Signature interaction", "signature_interaction"),
                       ("Content behavior", "content_behavior")):
        lines += [f"- **{label}:** {candidate[key]}"]
    for label, key in (("Risks", "risks"), ("Accessibility notes", "accessibility_notes")):
        lines += ["", f"{label}:", ""] + [f"- {item}" for item in candidate[key]]
    lines += ["", "Persona assumptions (unvalidated until docs#66):", ""]
    lines += [f"- {item['text']}" for item in candidate["persona_assumptions"]]
    lines += ["", "Contrast feasibility (illustrative, non-binding values; WCAG 2.x relative luminance):", ""]
    lines += table(("Kind", "Foreground", "Background", "Ratio", "Minimum", "Result"), [
        (pair["kind"], f"{pair['foreground']} `{values[pair['foreground']]}`",
         f"{pair['background']} `{values[pair['background']]}`",
         ratio_text(values[pair["foreground"]], values[pair["background"]]),
         f"{CONTRAST_MINIMUM[pair['kind']]:.1f}", pair["result"])
        for pair in candidate["contrast_pairs"]
    ])
    lines += ["", "Feasibility:", ""]
    lines += table(("Criterion", "Assessment"), [(key, text) for key, text in candidate["feasibility"].items()])
    lines += ["", "Grounding (pins on accepted main; bytes verified by digest, relevance not machine-checked):", ""]
    lines += [f"- `{pin['path']}` at `{pin['commit']}` (`{pin['sha256']}`)" for pin in candidate["grounding"]]
    return lines + [""]


def render_probe(probe):
    lines = [
        f"### {probe['id']} {probe['topic']}", "",
        f"Format `{probe['format']}`; data origin `{probe['data_origin']}`; access depiction "
        f"`{probe['access_depiction']}`.", "", probe["scenario"], "",
    ]
    lines += table(("Candidate", "Rendering"), [(item["candidate"], item["description"])
                                                for item in probe["renderings"]])
    return lines + [""]


def render_record(record):
    count, decision = record["participant_count"], record["decision"]
    lines = [
        f"## Direction record ({record['status']})", "",
        f"Version `{record['version']}`, gate `{record['gate']}`, status `{record['status']}`, prepared by role "
        f"`{record['prepared_by']['role']}` ({record['prepared_by']['ref']}). Participant count: "
        + ("not recorded (null; no study has run)" if count is None else str(count)) + ". Decision: "
        + ("none (null)" if decision is None else f"`{decision['selected']}`") + ". Token contract: "
        f"`{record['token_contract']['state']}` ({record['token_contract']['owner_issue']}).", "",
        "Evidence:", "",
    ]
    lines += table(("Kind", "Reference", "Origin", "State"), [
        (item["kind"], item["study_ref"], item["data_origin"], item["state"]) for item in record["evidence"]])
    lines += ["", "Reviews:", ""]
    lines += table(("Role", "State", "Reviewer"), [
        (item["role"], item["state"], item["reviewer_ref"] or "none recorded") for item in record["reviews"]])
    lines += ["", "Semantic roles:", ""]
    lines += table(("Role", "Meaning"), [(item["role"], item["meaning"]) for item in record["semantic_roles"]])
    lines += ["", "Platform consequences:", ""]
    lines += table(("Platform", "Consequence"), list(record["platform_consequences"].items()))
    lines += ["", "Unresolved risks:", ""]
    lines += table(("Risk", "Disposition", "Owner"), [
        (item["text"], item["state"], item["owner_ref"]) for item in record["unresolved_risks"]])
    for label, key in (("Implementation consequences", "implementation_consequences"),
                       ("Consumers", "consumers"), ("Held gates", "held_gates")):
        lines += ["", f"{label}:", ""] + [f"- {item}" for item in record[key]]
    lines += ["", "Supersedes: none (no prior D2 direction record exists).", "",
              f"Supersession: {record['supersession']['requires']}", ""]
    return lines


def render_markdown(model):
    """The generated markdown view of the published data; a unittest pins product/direction/README.md to it."""
    gaps = readiness(model)
    lines = [
        "# Concept directions and pending D2 direction record (T-UXR-07)", "",
        "> **Status: proposal; D2 decision pending.** Generated from `candidates.json`, `probes.json` and",
        "> `direction-record.json` by `" + RENDER_COMMAND + "`; do not edit by hand.",
        "> Source issue PenniLogic/docs#76. Nothing here is user evidence, a review, an approval or a",
        "> selected direction: candidates and probes are authored proposals with synthetic figures, persona",
        "> assumptions are unvalidated, illustrative values are non-binding and are not a token contract.",
        "> The raw-value, gamification, shame and trust-theater checks are lexical tripwires over ASCII text;",
        "> qualified Design and Accessibility review remains the control for those categories.", "",
        "## Readiness", "",
        f"`python scripts/check_direction.py` reports **{NOT_GREEN if any(gaps.values()) else GREEN}**.",
        structure_line(model) + ".", "",
    ]
    lines += table(("Readiness rule", "Open gaps"), [(rule, len(gaps[rule])) for rule in READINESS_RULES])
    lines += ["", "## Candidates", "",
              f"Every candidate is assessed on the same {len(REQUIRED_PAIRS)} contrast pairs on its base surface, "
              "so the failing counts below are comparable.", ""]
    lines += table(("ID", "Name", "Material", "Graphic", "Failing contrast pairs"), [
        (item["id"], item["name"], item["material_tradition"], item["graphic_tradition"],
         sum(pair["result"] == "fail" for pair in item["contrast_pairs"]))
        for item in model.candidates["candidates"]
    ])
    lines += [""]
    for candidate in model.candidates["candidates"]:
        lines += render_candidate(candidate)
    lines += ["## Probes (static, synthetic, text only)", ""]
    for probe in model.probes["probes"]:
        lines += render_probe(probe)
    lines += render_record(model.record)
    return "\n".join(lines).rstrip("\n") + "\n"


def emit(text):
    """Write UTF-8 with LF line endings on every platform, so the regenerated view stays byte-identical."""
    stream = getattr(sys.stdout, "buffer", None)
    if stream is None:
        sys.stdout.write(text)
        return
    sys.stdout.flush()
    stream.write(text.encode("utf-8"))
    stream.flush()


MAX_INPUT_BYTES = 1 << 20


def read_input(root, relative):
    """Bytes of one input file: no symlink anywhere below the root, regular file, at most MAX_INPUT_BYTES."""
    current = Path(root)
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("symlinked input")
    descriptor = os.open(current, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0))
    with os.fdopen(descriptor, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("not a regular file")
        raw = handle.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input too large")
    return raw


def load_and_check(root, sources=None):
    root = Path(root)

    def read(relative):
        return loads(read_input(root, relative))

    issues = issue_index(read(INVENTORY))
    return check(read(CANDIDATES), read(PROBES), read(RECORD), read(SCHEMA), sources or GitSources(root), issues)


def main(argv=None, root=None, sources=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--structure", action="store_true", help="Check structure only; readiness is not evaluated.")
    mode.add_argument("--render", action="store_true", help=f"Print the generated {MARKDOWN} to standard output.")
    args = parser.parse_args(argv)
    try:
        model = load_and_check(ROOT if root is None else root, sources)
        if args.structure:
            print(structure_line(model) + "; readiness not evaluated.")
            return 0
        if args.render:
            emit(render_markdown(model))
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
        print(f"Direction check refused: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, LookupError, TypeError, AttributeError, RecursionError, re.error):
        # Fail closed without a traceback, whose message could echo input content.
        print("Direction check refused: input.unreadable_or_invalid", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
