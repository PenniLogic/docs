"""Offline T-UXR-08 checks of the UX outcome, research cadence and design-debt catalogue and its summary.

PenniLogic/docs#77 publishes governance/ux-outcomes.json, validated against governance/ux-outcomes.schema.json
(the shared draft-07 subset) and by the rules below, and the generated summary governance/ux-outcomes.md. Journey
identifiers come from the experience-coverage registry pinned by commit, path and sha256 (the frozen planning import
at docs 1722fc79 until PenniLogic/docs#75 integrates), read from the local Git object store only. Every `pending:`
reference must name an issue of the committed inventory snapshot (planning/issue-inventory.json) other than this one.

The catalogue defines outcomes; it collects nothing. Collection stays disabled, every event is an allowlisted,
non-financial shape (bucketed or enumerated values whose every name and value segment comes from a reviewed
vocabulary; no free text, money, raw content, prompt, identity, household, location or demographic detail; E33-F04),
opt-out is honoured in every event and denominator, and cohort minimums, retention, aggregation and access are
references to PenniLogic/infra#27 (T-PLT-03), never numbers. Baselines are null and `unmeasured`, thresholds are
`unset` and a crossed kill threshold opens a reviewed product decision, never an automatic action. The only numbers
in the catalogue are the two privacy-budget caps; free text names none (a digit outside an identifier or a cardinal
number word is refused). Design debt uses `DEBT-NNN` identifiers; the D8 check is the function `d8_blocking_debt`,
which never edits governance/design-gates.json.

Structure failures raise `Refused` with a static rule identifier plus, at most, identifiers that match a catalogue or
journey grammar; input text is never echoed. Held inputs (approvals, research operations, payload allowlist review,
retention values, measurements, benchmark runs) are readiness gaps that keep the default mode NOT GREEN. Nothing here
contacts a network, records an approval or implies that research, consent or collection happened.
"""

import argparse
from datetime import date, datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DATA = "governance/ux-outcomes.json"
SCHEMA = "governance/ux-outcomes.schema.json"
SUMMARY = "governance/ux-outcomes.md"
INVENTORY = "planning/issue-inventory.json"
SOURCE_ISSUE = "PenniLogic/docs#77"
# The imported registry on docs main (final plan section 7, TS-M8); re-pinning after docs#75 is a one-field change.
REGISTRY_PIN = {
    "commit": "1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4",
    "path": "planning/source/evidence/experience-coverage.json",
    "sha256": "sha256:2f7b27c1f6683d4c256a938ccfb0fc06614f83fe57996a4d7aeaf0b7cae0bf3a",
}
# The full remote-tracking ref: a local branch named origin/main must not shadow it.
BASE_REF = "refs/remotes/origin/main"
PLATFORM_REF = "pending:PenniLogic/infra#27"  # T-PLT-03: cohort minimum, retention, aggregation and access
# Review round 1 (spec-and-safety.-r1-F1): each held privacy and research gate names the issue that owns it in the
# accepted threat model and plan; the choice stays labelled for coordinator confirmation in the summary.
# E33-F04 references the E07 allowlist rule E07-F01 (owner android#7); api#82 validates ingestion against it.
PAYLOAD_ALLOWLIST_REFS = ("pending:PenniLogic/android#7", "pending:PenniLogic/api#82")
# The E33 data class of these definitions: analytics purpose in the consent ledger and purpose registry (O-1).
CONSENT_REF = "pending:PenniLogic/api#24"
OPT_OUT_ENFORCEMENT_REF = "pending:PenniLogic/api#63"  # E07-F03: opt-out recorded and enforced server-side
# Outcome interpretation stays unvalidated until research operations (T-UXR-02) and persona, jobs and mental-model
# evidence (T-UXR-03) exist: the ticket's retained acceptance gates.
OUTCOME_VALIDATION_REFS = ("pending:PenniLogic/docs#65", "pending:PenniLogic/docs#66")
# E38 moderated usability per platform (T-DQA-04/05/06); a journey's platforms come from its pinned registry flows.
MODERATED_OWNERS = {"android": "pending:PenniLogic/docs#129", "web": "pending:PenniLogic/docs#130",
                    "admin": "pending:PenniLogic/docs#131"}
GREEN = "GREEN: readiness complete"
NOT_GREEN = "NOT GREEN: readiness incomplete"


def _sibling(name, filename):
    """Load an accepted sibling checker read-only by path, as check_design_gates.py does."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


support = _sibling("ux_outcomes_schema_support", "check_client_states.py")
gates = _sibling("ux_outcomes_design_gates", "check_design_gates.py")
strategy = _sibling("ux_outcomes_test_strategy", "check_test_strategy.py")
ROLES = frozenset(gates.ROLES)

GRAMMAR = {
    "journey": re.compile(r"J[0-9]{2}"),
    "metric": re.compile(r"M-(J[0-9]{2})-[0-9]{2}"),
    "guardrail": re.compile(r"G-(J[0-9]{2})-[0-9]{2}"),
    "threshold": re.compile(r"TH-[0-9]{3}"),
    "event": re.compile(r"EV-[0-9]{3}"),
    "trigger": re.compile(r"RT-[0-9]{3}"),
    "benchmark": re.compile(r"BM-(J[0-9]{2})"),
    "debt": re.compile(r"DEBT-[0-9]{3}"),
}
PENDING = re.compile(r"pending:PenniLogic/([a-z][a-z0-9.-]*)#([1-9][0-9]*)")
COMMIT = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
CATALOGUE_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
SNAKE = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")
# A journey code as an event enum value (j01); the only digits an event value may carry.
JOURNEY_VALUE = re.compile(r"j[0-9]{2}")
ISSUE = re.compile(r"PenniLogic/[a-z][a-z0-9.-]*#[1-9][0-9]*")
PLAN_IDENTIFIER = re.compile(r"T-[A-Z]{2,5}-[0-9]{2}")
NAME_LIMIT = 48
TEXT_LIMIT = 400
SCRUBBED_GIT_VARIABLES = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR", "GIT_NAMESPACE",
)


def classify(identifier):
    """The catalogue kind of a grammar-valid identifier, or None."""
    if not isinstance(identifier, str):
        return None
    for kind, grammar in GRAMMAR.items():
        if grammar.fullmatch(identifier):
            return kind
    return None


def printable(value):
    """Only catalogue and journey identifiers may appear in output; everything else is input text."""
    return classify(value) is not None


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
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique)


def digest(value):
    """sha256 over bytes, or over canonical JSON (sorted keys, compact, ASCII), as check_design_gates.digest."""
    return gates.digest(value)


def shape(value, schema, definition=None):
    """Validate with the shared subset validator; its messages echo input, so only the rule survives."""
    try:
        selected = schema if definition is None else schema["definitions"][definition]
        support.validate_schema(value, selected, schema)
    except (ValueError, KeyError, TypeError, RecursionError, re.error):
        raise Refused("schema.invalid") from None


_CURRENCIES = "INR|USD|EUR|GBP|AED|SGD|AUD|CAD|JPY|CNY|CHF|SAR|QAR|KWD|BHD|OMR|NZD|HKD|ZAR"
CONTENT_SHAPES = (
    # Printable ASCII only, so look-alike digits, at signs or currency signs cannot slip past the shapes below.
    ("content.unprintable_character", re.compile(r"[^\x20-\x7e]")),
    ("content.secret_shape", re.compile(
        r"\bgh[pousr]_[A-Za-z0-9]{8,}|\bgithub_pat_|-----BEGIN|\bAKIA[0-9A-Z]{16}\b|\bxox[abposr]-"
        r"|\bsk-[A-Za-z0-9_-]{20,}"
    )),
    ("content.url_shape", re.compile(
        r"[A-Za-z][A-Za-z0-9+.-]*://|\bwww\.|\b(?:mailto|javascript|vbscript|tel|sms|file|intent|ftp):"
        r"|\bdata:[a-z]+/|\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:com|org|net|io|co|dev|app|ai|gov|edu|info|biz|me|us"
        r"|uk|in|xyz)\b",
        re.IGNORECASE,
    )),
    # Any at sign: email addresses, UPI handles and user@host forms alike.
    ("content.email_shape", re.compile(r"@")),
    # Currency codes and signs, and Indian shorthand (1,50,000/-, 1.5L, 2 Cr, 3 lk).
    ("content.amount_shape", re.compile(
        r"\$\s*[0-9]|\b(?:" + _CURRENCIES + r"|Rs\.?)\s*[0-9]|[0-9]\s*(?:" + _CURRENCIES + r")\b"
        r"|[0-9]\s*(?:k|lakhs?|lacs?|lk|crores?|cr|rupees?|paise|dollars?|euros?|pounds?|cents?|bucks?|dirhams?)\b"
        r"|[0-9]\s*(?:/-|(?-i:L)\b)",
        re.IGNORECASE,
    )),
    ("content.personal_id_shape", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b|\b[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\b")),
    # Nine or more digits, whatever short non-alphanumeric separators sit between them.
    ("content.phone_shape", re.compile(r"[0-9](?:[^A-Za-z0-9]{0,3}[0-9]){8,}")),
)
TOKEN = re.compile(r"[A-Za-z0-9+=_]{32,}")
HEX_RUN = re.compile(r"[0-9a-fA-F]{32,}")
# Only these strings skip the scan, and only when they match their exact grammar at exactly this path.
EXEMPT_PATHS = {
    ("registry_ref", "commit"): COMMIT, ("registry_ref", "sha256"): DIGEST,
    ("benchmarks", "*", "task_script_sha256"): DIGEST,
}
# The two privacy-budget caps are the only numbers; baselines, targets, thresholds and cohorts carry none.
NUMBER_PATHS = frozenset({("privacy", "privacy_budget", "max_fields_per_event"),
                          ("privacy", "privacy_budget", "max_values_per_field")})
# Review round 1 (spec-and-safety.-r1-F5): free text names no number either. A string that is wholly a grammar-valid
# value is exempt; elsewhere identifiers are taken out and any remaining digit, or a cardinal number word, is refused,
# so no cohort size, retention period, sample size or threshold can be invented in prose (final plan 8.3).
STRUCTURED = (PENDING, SEMVER, CATALOGUE_DATE, JOURNEY_VALUE, ISSUE, PLAN_IDENTIFIER)
EMBEDDED_IDENTIFIER = re.compile(
    r"(?<![A-Za-z0-9])(?:[MG]-J[0-9]{2}-[0-9]{2}|(?:TH|EV|RT|DEBT)-[0-9]{3}|BM-J[0-9]{2}|[Jj][0-9]{2})(?![A-Za-z0-9])"
    r"|PenniLogic/[a-z][a-z0-9.-]*#[1-9][0-9]*"
)
NUMBER_WORD = re.compile(
    r"\b(?:zero|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen"
    r"|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundreds?|thousands?"
    r"|lakhs?|crores?|millions?|billions?|dozens?|percent|half)\b",
    re.IGNORECASE,
)
# Event names, field names and values are snake-case tokens whose digits check_event polices (event.number_token).
EVENT_TOKEN_PATHS = frozenset({("events", "*", "name"), ("events", "*", "fields", "*", "name"),
                               ("events", "*", "fields", "*", "values", "*")})


def _secret_token(text):
    for candidate in (text, re.sub(r"[-/_]", "", text)):
        if HEX_RUN.search(candidate):
            return True
        for match in TOKEN.finditer(candidate):
            if all(any(test(c) for c in match.group()) for test in (str.isdigit, str.islower, str.isupper)):
                return True
    return False


def _scan(text, subject):
    require(len(text) <= TEXT_LIMIT, "content.too_long", *subject)
    require(text.strip() == text and text != "", "content.blank_or_padded", *subject)
    for rule, pattern in CONTENT_SHAPES:
        require(pattern.search(text) is None, rule, *subject)
    require(not _secret_token(text), "content.secret_shape", *subject)


def guard_numbers(document):
    """No number in any string (spec-and-safety.-r1-F5). It runs after the structure rules, so a malformed identifier,
    version or reference still reports its own rule; EXEMPT_PATHS digests and event tokens are skipped."""
    def walk(value, subject, path):
        if isinstance(value, dict):
            if printable(value.get("id")):
                subject = (value["id"],)
            for key, item in value.items():
                walk(item, subject, (*path, key))
        elif isinstance(value, list):
            for item in value:
                walk(item, subject, (*path, "*"))
        elif isinstance(value, str) and path not in EXEMPT_PATHS and path not in EVENT_TOKEN_PATHS:
            if classify(value) is not None or any(grammar.fullmatch(value) for grammar in STRUCTURED):
                return
            require(re.search(r"[0-9]", EMBEDDED_IDENTIFIER.sub(" ", value)) is None, "content.number_in_text",
                    *subject)
            require(NUMBER_WORD.search(value) is None, "content.number_word", *subject)

    walk(document, (), ())


def guard_content(document):
    """Scan every string value and key; only EXEMPT_PATHS values with their grammar and NUMBER_PATHS are exempt."""
    def walk(value, subject, path):
        if isinstance(value, dict):
            if printable(value.get("id")):
                subject = (value["id"],)
            for key, item in value.items():
                _scan(key, subject)
                walk(item, subject, (*path, key))
        elif isinstance(value, list):
            for item in value:
                walk(item, subject, (*path, "*"))
        elif isinstance(value, str):
            grammar = EXEMPT_PATHS.get(path)
            if grammar is None or not grammar.fullmatch(value):
                _scan(value, subject)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            require(path in NUMBER_PATHS, "content.unexpected_number", *subject)

    walk(document, (), ())


def trusted_git(root):
    """Absolute path of git from absolute PATH entries outside the checked repository (H06 hardening).

    A bare "git" lets the operating system search relative PATH entries and, on Windows, the current directory
    first, so a candidate-local executable could forge the pinned registry or the benchmark base.
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
    """Pinned blobs and the benchmark base from the local Git object store; never fetches, writes or pushes."""

    def __init__(self, root, base=None):
        self.root, self.base, self.executable, self.commit = Path(root), base, None, None

    def _git(self, *args):
        self.executable = self.executable or trusted_git(self.root)
        env = {key: value for key, value in os.environ.items() if key not in SCRUBBED_GIT_VARIABLES}
        # Objects exactly as stored: no lazy fetch, replace refs or grafts that could substitute pinned bytes.
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

    def base_commit(self):
        if self.commit is None:
            if self.base is None:
                args = ("merge-base", "HEAD", BASE_REF)
            elif isinstance(self.base, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,199}", self.base):
                args = ("rev-parse", "--verify", "--quiet", f"{self.base}^{{commit}}")
            else:
                raise LookupError("unsafe revision")
            result = self._git(*args)
            commit = result.stdout.decode("ascii", "replace").strip()
            if result.returncode != 0 or not COMMIT.fullmatch(commit):
                raise LookupError("no such commit")
            self.commit = commit
        return self.commit

    def base_file(self, path):
        """Bytes of path at the base, or None only when the base commit's tree has no such entry."""
        commit = self.base_commit()
        listed = self._git("ls-tree", "-z", "--name-only", commit, "--", path)
        if listed.returncode != 0:
            raise LookupError("base tree unavailable")
        if not listed.stdout:
            return None
        if listed.stdout != path.encode("ascii") + b"\0":
            raise LookupError("unexpected base tree entry")
        return self.blob(commit, path)


def read_registry(document, sources, pin):
    """({journey ID: critical}, {journey ID: platforms}) from the pinned registry, read at the pinned commit and
    digest-checked; a journey's platforms are those of the flows it names."""
    require(document["registry_ref"] == pin, "registry.ref_mismatch")
    try:
        blob = sources.blob(pin["commit"], pin["path"])
    except LookupError:
        raise Refused("registry.unavailable") from None
    require(isinstance(blob, bytes) and digest(blob) == pin["sha256"], "registry.digest_mismatch")
    try:
        registry = loads(blob)
    except (ValueError, RecursionError):
        raise Refused("registry.invalid") from None
    journeys = registry.get("journeys") if isinstance(registry, dict) else None
    flows = registry.get("flows") if isinstance(registry, dict) else None
    require(isinstance(journeys, list) and isinstance(flows, list), "registry.invalid")
    platform_of = {}
    for flow in flows:
        identifier = flow.get("id") if isinstance(flow, dict) else None
        require(isinstance(identifier, str) and identifier not in platform_of
                and isinstance(flow.get("platform"), str), "registry.invalid")
        platform_of[identifier] = flow["platform"]
    pinned, platforms = {}, {}
    for record in journeys:
        identifier = record.get("id") if isinstance(record, dict) else None
        require(classify(identifier) == "journey" and identifier not in pinned, "registry.invalid")
        require(isinstance(record.get("critical"), bool), "registry.invalid")
        flow_ids = record.get("flow_ids")
        require(isinstance(flow_ids, list) and all(isinstance(flow, str) and flow in platform_of for flow in flow_ids),
                "registry.invalid")
        pinned[identifier] = record["critical"]
        platforms[identifier] = frozenset(platform_of[flow] for flow in flow_ids)
    return pinned, platforms


def read_base(sources):
    """{(benchmark ID, version): script digest} of the committed catalogue at the base (merge base with
    origin/main), or None when the base predates the catalogue. Only the benchmark keys are read, so a later schema
    change elsewhere in the catalogue cannot make an older base unreadable."""
    try:
        blob = sources.base_file(DATA)
    except LookupError:
        raise Refused("base.unavailable") from None
    if blob is None:
        return None
    try:
        base = loads(blob)
    except (ValueError, RecursionError):
        raise Refused("base.invalid") from None
    benchmarks = base.get("benchmarks") if isinstance(base, dict) else None
    require(isinstance(benchmarks, list), "base.invalid")
    versions = {}
    for item in benchmarks:
        key = (item.get("id"), item.get("version")) if isinstance(item, dict) else (None, None)
        value = item.get("task_script_sha256") if isinstance(item, dict) else None
        require(classify(key[0]) == "benchmark" and isinstance(key[1], str) and SEMVER.fullmatch(key[1])
                and isinstance(value, str) and DIGEST.fullmatch(value) and key not in versions, "base.invalid")
        versions[key] = value
    return versions


def read_inventory(root):
    """The issue references of the committed inventory snapshot, validated by check_test_strategy (offline)."""
    try:
        return frozenset(strategy.validate_inventory(support.load_json(local_path(root, INVENTORY))))
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
        raise Refused("inventory.invalid") from None


def check_references(document, inventory):
    """Review round 1 (spec-and-safety.-r1-F9): every `pending:` reference names an issue in the inventory, and never
    this ticket, so each held gate has an owner that can close it."""
    for reference in pending_references(document):
        issue = reference[len("pending:"):]
        require(issue != SOURCE_ISSUE, "reference.self")
        require(issue in inventory, "reference.unknown_issue")


COLLECTIONS = (
    ("events", "event"), ("metrics", "metric"), ("guardrails", "guardrail"), ("thresholds", "threshold"),
    ("research_triggers", "trigger"), ("benchmarks", "benchmark"), ("design_debt", "debt"),
)
APPROVAL_ROLES = frozenset({"privacy", "product_owner", "research", "decision_coordinator"})
ENABLE_REQUIRES = frozenset({"consent", "payload_allowlist", "cohort_minimum"})
OPERATIONS_REF = "pending:PenniLogic/docs#65"  # T-UXR-02 research operations, consent and panel
CADENCES = frozenset({"per_release", "monthly", "quarterly", "post_beta"})
REQUIRED_STUDIES = frozenset({"moderated_usability", "unmoderated_benchmark", "diary_follow_up",
                              "panel_health_review"})
REQUIRED_PANEL_HEALTH = frozenset({"attrition", "coverage", "recency"})
GUARDRAIL_CLASSES = frozenset({"permission_coercion", "harmful_sharing", "support_demand", "accessibility",
                               "dark_pattern"})
# A primary outcome is a user outcome; time, error and abandonment are diagnostics, never the primary.
OUTCOME_KINDS = frozenset({"task_success", "comprehension", "correction", "recovery", "trust",
                           "sustained_progress"})
# Review round 1 (spec-and-safety.-r1-F7): the ticket scope names per-journey task success, time, error, correction,
# abandonment, comprehension and recovery measures; every critical journey carries each kind (proposed, unvalidated).
MEASURE_KINDS = frozenset({"task_success", "time_on_task", "error", "correction", "abandonment", "comprehension",
                           "recovery"})
# Allowlisted payload shapes: coarsened, enumerated values only; no free text, number or identifier kind exists.
FIELD_KINDS = frozenset({"boolean", "enum", "count_bucket", "duration_bucket"})
BUDGET_CAPS = {"max_fields_per_event": (1, 8), "max_values_per_field": (2, 12)}
VALUE_LIMIT = 32
# Planted-field rejection (E33-F04; ticket criterion 3): a name, field or value segment naming one of these
# categories is refused with the category's rule. Matching is per underscore segment (and its plural), also by
# substring for the unambiguous words in SUBSTRINGS, so a joined name such as `txnamount` is caught, and on every
# look-alike reading of the token (am0unt, arnount). Whatever no category names still has to pass EVENT_VOCABULARY.
SENSITIVE = (
    ("event.money_field", ("amount", "balance", "money", "currency", "price", "cost", "fee", "salary", "income",
                           "payment", "debt", "loan", "emi", "interest", "spend", "spent", "merchant", "payee",
                           "counterparty", "account", "iban", "upi", "card", "wallet", "networth",
                           "amt", "acct", "accno", "ifsc", "vpa",
                           # Review round 1: currency codes, units and Indian shorthand as segments, and the money,
                           # payer and lender words that passed (credit_limit, txn_kind, payer, lender, employer).
                           *_CURRENCIES.lower().split("|"), "rs", "rupee", "paise", "paisa", "lakh", "lac", "lk",
                           "crore", "cr", "k", "dollar", "euro", "pound", "cent", "buck", "dirham",
                           "bank", "credit", "debit", "overdraft", "saving", "savings", "investment", "invest",
                           "bill", "rent", "txn", "transaction", "transfer", "deposit", "withdrawal", "refund",
                           "cashback", "tax", "mortgage", "pension", "payer", "payroll", "wage", "recipient",
                           "lender", "borrower", "creditor", "debtor", "employer", "budget", "allowance", "invoice",
                           "receipt", "fund", "asset", "liability")),
    ("event.content_field", ("text", "message", "body", "content", "note", "memo", "description", "comment",
                             "query", "search", "transcript", "sms", "raw", "narration", "subject", "freeform")),
    ("event.prompt_field", ("prompt", "completion", "response", "reply", "chat", "utterance", "conversation")),
    ("event.identity_field", ("name", "email", "phone", "mobile", "address", "user", "uid", "id", "ids", "uuid",
                              "device", "ip", "identifier", "token", "pan", "aadhaar", "dob", "birth",
                              "contact", "handle", "imei", "msisdn", "ssn", "passport", "gstin",
                              "otp", "pin", "password", "passcode", "secret", "credential")),
    ("event.household_field", ("household", "member", "relationship", "partner", "spouse", "child", "children",
                               "parent", "family", "invitee", "grantee", "guardian", "dependant", "dependent",
                               "wife", "husband", "kid", "son", "daughter", "sibling", "brother", "sister", "mother",
                               "father", "grandparent", "relative", "marital", "married", "widow", "divorce")),
    ("event.location_field", ("location", "lat", "lon", "latitude", "longitude", "gps", "geo", "geohash",
                              "coordinate", "pincode", "postcode", "zipcode", "zip", "city", "town", "village",
                              "district", "locality", "region", "country")),
    ("event.demographic_field", ("gender", "sex", "age", "religion", "caste", "tribe", "ethnicity", "race",
                                 "nationality", "disability", "health", "medical", "pregnancy", "pregnant",
                                 "orientation")),
)
SUBSTRINGS = frozenset({"amount", "balance", "merchant", "salary", "counterparty", "transcript", "message", "prompt",
                        "email", "aadhaar", "household", "relationship", "spouse", "password", "passcode", "passport",
                        "msisdn", "credential", "loan", "overdraft", "savings", "investment", "creditor", "employer",
                        "family", "husband", "pincode", "postcode", "zipcode", "religion", "disability"})
# Look-alike readings: digits read as the letters they imitate (1 as l or i) and rn, vv read as m, w.
LOOK_ALIKE = tuple(str.maketrans("0123456789", "o" + one + "zeasgtbg") for one in "li")
# Review round 1 (spec-and-safety.-r1-F2): the positive allowlist. Every underscore segment of an event name, field
# name and value must be one of these reviewed, neutral words; anything else (a merchant, bank, place, number or a
# joined abbreviation such as txnamt) is refused with `event.vocabulary`. Adding a word is a reviewed code change
# and still needs the payload review held on every event.
EVENT_VOCABULARY = frozenset("""
    abandoned accepted access answer answered article assistant assisted assistive cancel change check class
    completed comprehension confirmation confirmed conflict connectivity consequence core corrected correction
    day declined deferred discarded downgrade edit elapsed entry error escalated escalation explanation few
    figure finished first form goal granted help immediate journey kind later long longer medium met milestone
    minute minutes mode month more not offer on once only opened or outcome partly paused permission plan
    reached recovery request restored result reversed revoked route same saved scope self service session set
    share shared short shown source stage start started step subscription support task three times twice
    unavailable uncertainty under understood upgrade validation view week within
""".split())


# Review round 1 (spec-and-safety.-r1-F3): an event whose words name an incentive must carry that incentive tag, so
# the perverse-incentive rule cannot be bypassed by leaving the tag null. Short words match a whole segment only.
INCENTIVE_WORDS = {
    "permission_grant": ("permission", "grant", "consent"),
    "ai_use": ("assistant", "ai", "llm", "chatbot", "copilot"),
    "subscription": ("subscri", "upgrade", "premium", "paywall", "renew"),
    "sharing": ("share", "sharing", "invit", "referr"),
}


def incentive_classes(tokens):
    """The incentive classes whose words appear in any of the snake-case tokens."""
    found = set()
    for token in tokens:
        segments, compact = token.split("_"), token.replace("_", "")
        for klass, words in INCENTIVE_WORDS.items():
            if any(word in segments if len(word) <= 3 else word in compact for word in words):
                found.add(klass)
    return found


def look_alikes(token):
    """The token and its look-alike readings, so am0unt, ba1ance, arnount and h0usehold read as the words they
    imitate."""
    readings = {token, *(token.translate(table) for table in LOOK_ALIKE)}
    return sorted(readings | {reading.replace("rn", "m").replace("vv", "w") for reading in readings})


def sensitive_rule(token):
    """The category rule a snake-case token, or any look-alike reading of it, falls under, or None."""
    readings = look_alikes(token)
    for rule, words in SENSITIVE:
        for reading in readings:
            segments = reading.split("_")
            compact = reading.replace("_", "")
            for word in words:
                if any(segment in (word, word + "s", word + "es") for segment in segments):
                    return rule
                if word in SUBSTRINGS and word in compact:
                    return rule
    return None


def index(document):
    """{collection: {ID: record}}; every ID must match its collection's grammar and be unique."""
    indexed = {}
    for collection, kind in COLLECTIONS:
        records = {}
        for record in document[collection]:
            identifier = record["id"]
            require(classify(identifier) == kind, "id.grammar")
            require(identifier not in records, "id.duplicate", identifier)
            records[identifier] = record
        indexed[collection] = records
    return indexed


def journey_of(identifier):
    """The J infix of an M-, G- or BM- identifier."""
    for kind in ("metric", "guardrail", "benchmark"):
        match = GRAMMAR[kind].fullmatch(identifier)
        if match:
            return match.group(1)
    return None


def parse_date(value):
    """A calendar date in YYYY-MM-DD form, or None."""
    if not (isinstance(value, str) and CATALOGUE_DATE.fullmatch(value)):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def check_frame(document):
    """Catalogue status, collection, privacy references, budget and approvals."""
    require(isinstance(document["catalogue_version"], str) and SEMVER.fullmatch(document["catalogue_version"]),
            "catalogue.version")
    require(document["status"] == "proposed", "held.catalogue_status")
    collection = document["collection"]
    require(collection["enabled"] is False, "collection.enabled")
    require(set(collection["enable_requires"]) == ENABLE_REQUIRES, "collection.enable_conditions")
    privacy = document["privacy"]
    for key in ("cohort_minimum_ref", "retention_ref", "aggregation_ref", "access_ref"):
        require(privacy[key] == PLATFORM_REF, "privacy.platform_ref")
    require(privacy["opt_out"]["honoured"] is True, "privacy.opt_out")
    require(sorted(privacy["payload_allowlist_refs"]) == sorted(PAYLOAD_ALLOWLIST_REFS),
            "privacy.payload_allowlist_ref")
    require(privacy["consent_ref"] == CONSENT_REF, "privacy.consent_ref")
    require(privacy["opt_out"]["enforcement_ref"] == OPT_OUT_ENFORCEMENT_REF, "privacy.opt_out_enforcement_ref")
    require(sorted(document["outcome_validation_refs"]) == sorted(OUTCOME_VALIDATION_REFS), "validation.refs")
    require(privacy["session_recording"] == "prohibited", "privacy.session_recording")
    for key, (low, high) in BUDGET_CAPS.items():
        require(low <= privacy["privacy_budget"][key] <= high, "privacy.budget_bounds")
    roles = [item["role"] for item in document["approvals"]]
    require(len(roles) == len(set(roles)) and set(roles) == APPROVAL_ROLES, "approval.roles")
    for item in document["approvals"]:
        # No session here records an approval (HC-m13): every role stays pending with no decision reference.
        require(item["status"] == "pending", "held.approval_recorded")


def check_event(event, budget):
    """Allowlisted, non-financial, opt-out-honouring, disabled event shapes (E33-F04, ticket criterion 3)."""
    identifier = event["id"]
    require(SNAKE.fullmatch(event["name"]) is not None and len(event["name"]) <= NAME_LIMIT,
            "event.name_grammar", identifier)
    names_used, enumerated = [event["name"]], []
    require(len(event["fields"]) <= budget["max_fields_per_event"], "event.privacy_budget", identifier)
    names = set()
    for field in event["fields"]:
        require(SNAKE.fullmatch(field["name"]) is not None and len(field["name"]) <= NAME_LIMIT,
                "event.field_grammar", identifier)
        require(field["name"] not in names, "event.field_duplicate", identifier)
        names.add(field["name"])
        require(field["kind"] in FIELD_KINDS, "event.kind_not_allowlisted", identifier)
        values = field["values"]
        if field["kind"] == "boolean":
            require(values == [], "event.values_mismatch", identifier)
        else:
            require(len(values) >= 2, "event.values_mismatch", identifier)
            require(len(values) <= budget["max_values_per_field"], "event.privacy_budget", identifier)
        for value in values:
            require(SNAKE.fullmatch(value) is not None and len(value) <= VALUE_LIMIT, "event.value_grammar",
                    identifier)
        names_used.append(field["name"])
        enumerated += values
    # Category first (the most specific rule), then digits, then the reviewed vocabulary; all fail closed. Only an
    # enumerated value may be a journey code; a name never carries a digit.
    tokens = [(token, False) for token in names_used] + [(token, True) for token in enumerated]
    for token, _ in tokens:
        rule = sensitive_rule(token)
        require(rule is None, rule, identifier)
    for token, is_value in tokens:
        code = is_value and JOURNEY_VALUE.fullmatch(token) is not None
        require(code or not any(character.isdigit() for character in token), "event.number_token", identifier)
    for token, is_value in tokens:
        code = is_value and JOURNEY_VALUE.fullmatch(token) is not None
        require(code or set(token.split("_")) <= EVENT_VOCABULARY, "event.vocabulary", identifier)
    classes = incentive_classes(token for token, _ in tokens)
    if classes:
        require(event["incentive"] is not None, "incentive.untagged", identifier)
        require(event["incentive"] in classes, "incentive.tag_mismatch", identifier)
    require(event["opt_out_honoured"] is True, "event.opt_out_not_honoured", identifier)
    require(event["enabled"] is False, "collection.enabled", identifier)


# Units that describe a share of one counted population: the numerator narrows the same events as the denominator.
SHARE_UNITS = frozenset({"proportion", "duration_bucket_share"})


def field_values(event, name):
    """The values a filter may select on one event field (a boolean reads true or false), or None."""
    for field in event["fields"]:
        if field["name"] == name:
            return frozenset({"true", "false"}) if field["kind"] == "boolean" else frozenset(field["values"])
    return None


def selection(side, events, identifier):
    """{field: values} of one ratio side. Every filter names a field of every event on the side and selects known
    values that strictly narrow it (review round 1, spec-and-safety.-r1-F4)."""
    selected = {}
    for item in side["filters"]:
        name = item["field"]
        require(name not in selected, "ratio.filter_duplicate", identifier)
        for event_id in side["event_ids"]:
            known = field_values(events[event_id], name)
            require(known is not None, "ratio.filter_field_unknown", identifier)
            require(set(item["values"]) < known, "ratio.filter_values", identifier)
        selected[name] = frozenset(item["values"])
    return selected


def check_ratio(record, events):
    """An explicit numerator and an eligibility-defined denominator that excludes opted-out users, each a filtered
    event selection scoped to the record's journey. A same-event denominator is allowed only when the numerator
    strictly narrows it, so the ratio computes the share its statement names."""
    identifier = record["id"]
    numerator, denominator = record["numerator"]["event_ids"], record["denominator"]["event_ids"]
    require(numerator, "ratio.numerator_missing", identifier)
    require(denominator, "ratio.denominator_missing", identifier)
    for event_id in (*numerator, *denominator):
        require(event_id in events, "reference.dangling", identifier)
    chosen = {key: selection(record[key], events, identifier) for key in ("numerator", "denominator")}
    journey = record["journey_id"].lower()
    for key in ("numerator", "denominator"):
        for event_id in record[key]["event_ids"]:
            if field_values(events[event_id], "journey") is not None:
                require(chosen[key].get("journey") == {journey}, "ratio.journey_scope", identifier)
    same_events = set(numerator) == set(denominator)
    if same_events:
        require(chosen["numerator"] != chosen["denominator"], "ratio.denominator_same_as_numerator", identifier)
        require(all(name in chosen["numerator"] and chosen["numerator"][name] <= values
                    for name, values in chosen["denominator"].items()), "ratio.numerator_outside_denominator",
                identifier)
    if "unit" in record:
        require((record["unit"] in SHARE_UNITS) == same_events, "ratio.unit_mismatch", identifier)
    require(record["denominator"]["excludes_opted_out"] is True, "ratio.opt_out_not_excluded", identifier)


def check_measure(record, indexed):
    """Shared journey, status and threshold rules of a metric or guardrail."""
    identifier = record["id"]
    require(classify(record["journey_id"]) == "journey", "id.grammar", identifier)
    require(journey_of(identifier) == record["journey_id"], "id.journey_mismatch", identifier)
    # Outcome interpretation stays unvalidated until docs#65/docs#66 evidence exists (held acceptance gate).
    require(record["status"] == "unvalidated", "held.validation", identifier)
    require(record["threshold_id"] in indexed["thresholds"], "reference.dangling", identifier)
    check_ratio(record, indexed["events"])


def check_metric(metric, indexed):
    """Outcome metrics; an incentive event (permission grant, AI use, subscription, sharing) is never rewarded by a
    primary, and a secondary that rewards one carries benefit context and a guardrail (ticket criterion 2)."""
    identifier = metric["id"]
    check_measure(metric, indexed)
    if metric["role"] == "primary":
        require(metric["kind"] in OUTCOME_KINDS, "metric.primary_kind", identifier)
    for guardrail_id in metric["guardrail_ids"]:
        guardrail = indexed["guardrails"].get(guardrail_id)
        require(guardrail is not None, "reference.dangling", identifier)
        require(guardrail["journey_id"] == metric["journey_id"], "metric.guardrail_other_journey", identifier)
    # A ratio rewards an incentive event in its numerator when it should increase, and in its denominator when it
    # should decrease (review round 1, spec-and-safety.-r1-F3).
    rewarded = metric["numerator"] if metric["direction"] == "increase" else metric["denominator"]
    if any(indexed["events"][event_id]["incentive"] is not None for event_id in rewarded["event_ids"]):
        require(metric["role"] != "primary", "incentive.primary", identifier)
        require(metric["benefit_context"] is not None and metric["guardrail_ids"] != [],
                "incentive.without_safety_context", identifier)


def check_coverage(indexed, pinned):
    """Every pinned critical journey: one primary outcome, a trust or harm guardrail, one benchmark and a measure of
    each kind the ticket scope names."""
    for journey, critical in sorted(pinned.items()):
        if not critical:
            continue
        primaries = [m for m in indexed["metrics"].values() if m["journey_id"] == journey and m["role"] == "primary"]
        require(primaries, "coverage.primary_missing", journey)
        require(len(primaries) == 1, "coverage.primary_duplicate", journey)
        require(any(g["journey_id"] == journey for g in indexed["guardrails"].values()),
                "coverage.guardrail_missing", journey)
        require(f"BM-{journey}" in indexed["benchmarks"], "coverage.benchmark_missing", journey)
        kinds = {m["kind"] for m in indexed["metrics"].values() if m["journey_id"] == journey}
        require(kinds >= MEASURE_KINDS, "coverage.measure_kind_missing", journey)
    covered = {guardrail["class"] for guardrail in indexed["guardrails"].values()}
    require(covered >= GUARDRAIL_CLASSES, "coverage.guardrail_class_missing")
    used = {event_id for collection in ("metrics", "guardrails") for record in indexed[collection].values()
            for event_id in (*record["numerator"]["event_ids"], *record["denominator"]["event_ids"])}
    for identifier in indexed["events"]:
        require(identifier in used, "event.unused", identifier)


def check_thresholds(indexed):
    """A crossed threshold opens a reviewed product decision (ticket criterion 4); it never acts on its own."""
    measured = [*indexed["metrics"].values(), *indexed["guardrails"].values()]
    triggered = {trigger["source_id"] for trigger in indexed["research_triggers"].values()
                 if trigger["condition"] == "threshold_crossed"}
    for identifier, threshold in indexed["thresholds"].items():
        require(threshold["on_cross"] == "product_decision_review", "threshold.automatic_action", identifier)
        require(set(threshold["reviewers"]) <= ROLES, "threshold.unknown_role", identifier)
        require("product_owner" in threshold["reviewers"], "threshold.review_missing", identifier)
        require(threshold["minimum_sample_ref"] == PLATFORM_REF, "privacy.platform_ref", identifier)
        require(any(record["threshold_id"] == identifier for record in measured), "threshold.unused", identifier)
        require(identifier in triggered, "threshold.without_trigger", identifier)


def check_triggers(indexed):
    sources = {"threshold_crossed": indexed["thresholds"], "benchmark_regression": indexed["benchmarks"]}
    for identifier, trigger in indexed["research_triggers"].items():
        require(trigger["source_id"] in sources[trigger["condition"]], "trigger.source_mismatch", identifier)
        require(trigger["owner_role"] == "research", "trigger.owner_role", identifier)
        require(trigger["journey_ids"] != [], "trigger.journey_missing", identifier)
        for journey in trigger["journey_ids"]:
            require(classify(journey) == "journey", "id.grammar", identifier)


def check_calendar(calendar):
    """Continuous research cadence and panel health; no session is scheduled (docs#65 operations are held)."""
    require(calendar["operations_ref"] == OPERATIONS_REF, "calendar.operations_ref")
    studies = [item["study"] for item in calendar["cadences"]]
    require(len(studies) == len(set(studies)), "calendar.duplicate_study")
    require(set(studies) >= REQUIRED_STUDIES, "calendar.study_missing")
    require(set(calendar["panel_health"]) >= REQUIRED_PANEL_HEALTH, "calendar.panel_health_missing")
    for item in calendar["cadences"]:
        for journey in item["journey_ids"]:
            require(classify(journey) == "journey", "id.grammar")


def check_benchmarks(indexed, base, platforms):
    """Versioned, reproducible unmoderated benchmarks (ticket criterion 5): the task script digest is recorded,
    and a changed script at an already-published version is refused (the version must be bumped)."""
    for identifier, benchmark in indexed["benchmarks"].items():
        require(classify(benchmark["journey_id"]) == "journey", "id.grammar", identifier)
        require(journey_of(identifier) == benchmark["journey_id"], "id.journey_mismatch", identifier)
        require(SEMVER.fullmatch(benchmark["version"]) is not None, "benchmark.version_grammar", identifier)
        # Unmoderated benchmarks follow moderated defects closing on every platform the journey runs on (product/08).
        owners = [MODERATED_OWNERS.get(platform) for platform in sorted(platforms.get(benchmark["journey_id"], ()))]
        require(owners and None not in owners and benchmark["moderated_defects_refs"] == sorted(owners),
                "benchmark.moderated_owner", identifier)
        require(benchmark["task_steps"] != [], "benchmark.script_missing", identifier)
        recorded = digest(benchmark["task_steps"])
        require(benchmark["task_script_sha256"] == recorded, "benchmark.script_digest_mismatch", identifier)
        published = None if base is None else base.get((identifier, benchmark["version"]))
        require(published is None or published == recorded, "benchmark.version_not_bumped", identifier)


def check_longitudinal(plan, indexed):
    """The post-beta longitudinal plan names cohort, cadence, retention, stop criteria and decisions."""
    require(plan["cohort_minimum_ref"] == PLATFORM_REF, "longitudinal.cohort_ref")
    require(plan["retention_ref"] == PLATFORM_REF, "longitudinal.retention_ref")
    require(plan["cadence"] in CADENCES, "longitudinal.cadence")
    require(plan["stop_criteria"] != [], "longitudinal.stop_criteria_missing")
    require(plan["decisions_it_may_change"] != [], "longitudinal.decisions_missing")
    known = {*indexed["metrics"], *indexed["guardrails"], *indexed["thresholds"]}
    for identifier in plan["decisions_it_may_change"]:
        require(identifier in known, "reference.dangling")


def check_debt(indexed, schema, fixture):
    """Design-debt register records; a recorded CDO-equivalent exception is held in published data (HC-m13)."""
    for identifier, debt in indexed["design_debt"].items():
        require(debt["owner_role"] in ROLES, "debt.owner_role", identifier)
        require(parse_date(debt["due_date"]) is not None, "debt.due_date", identifier)
        require(debt["journey_ids"] != [], "debt.journey_missing", identifier)
        for journey in debt["journey_ids"]:
            require(classify(journey) == "journey", "id.grammar", identifier)
        exception = debt["exception"]
        if exception is None:
            continue
        require(fixture, "held.cdo_exception", identifier)
        shape(exception, schema, "exception")
        require(exception["recorded_by_role"] == "decision_coordinator", "debt.exception_role", identifier)
        recorded, expires = parse_date(exception["recorded_on"]), parse_date(exception["expires_on"])
        require(recorded is not None and expires is not None and recorded < expires, "debt.exception_dates",
                identifier)


def d8_blocking_debt(design_debt, today):
    """The D8 design-debt check (ticket criterion 6): sorted IDs of open critical or high debt without a current,
    dated decision_coordinator (CDO-equivalent) exception. `today` is injected; an exception is current from its
    recorded_on date up to, not including, its expires_on date. Never reads or edits governance/design-gates.json."""
    if not isinstance(today, date) or isinstance(today, datetime):
        raise TypeError("today must be a date")
    blocking = []
    for debt in design_debt:
        if debt["status"] != "open" or debt["severity"] not in ("critical", "high"):
            continue
        exception = debt["exception"]
        if isinstance(exception, dict) and exception.get("recorded_by_role") == "decision_coordinator":
            recorded, expires = parse_date(exception.get("recorded_on")), parse_date(exception.get("expires_on"))
            if recorded is not None and expires is not None and recorded <= today < expires:
                continue
        blocking.append(debt["id"])
    return sorted(blocking)


def check(document, schema, sources, pin=None, base=None, fixture=False, inventory=None):
    """Every structure rule, fail closed. `base` is {(BM ID, version): digest} of the base catalogue or None;
    `fixture` (tests only, never the CLI) admits a recorded debt exception so the D8 rules can be exercised;
    `inventory` holds the known issue references (default: this repository's committed snapshot)."""
    pin = REGISTRY_PIN if pin is None else pin
    inventory = read_inventory(ROOT) if inventory is None else inventory
    shape(document, schema)
    guard_content(document)
    check_frame(document)
    pinned, platforms = read_registry(document, sources, pin)
    indexed = index(document)
    budget = document["privacy"]["privacy_budget"]
    for event in indexed["events"].values():
        check_event(event, budget)
    for guardrail in indexed["guardrails"].values():
        check_measure(guardrail, indexed)
    for metric in indexed["metrics"].values():
        check_metric(metric, indexed)
    check_triggers(indexed)
    check_thresholds(indexed)
    check_calendar(document["research_calendar"])
    check_benchmarks(indexed, base, platforms)
    check_longitudinal(document["longitudinal_plan"], indexed)
    check_debt(indexed, schema, fixture)
    check_coverage(indexed, pinned)
    check_references(document, inventory)
    guard_numbers(document)
    return {"document": document, "indexed": indexed, "pinned": pinned, "platforms": platforms}


READINESS_RULES = (
    "readiness.approval_pending", "readiness.collection_disabled", "readiness.payload_review_pending",
    "readiness.pending_reference", "readiness.baseline_unmeasured", "readiness.threshold_unset",
    "readiness.measure_unvalidated", "readiness.benchmark_unrun", "readiness.longitudinal_unrun",
    "readiness.journey_outside_pin", "readiness.registry_import_pin", "readiness.d8_blocking_debt",
)


def pending_references(value):
    """Distinct `pending:PenniLogic/<repo>#N` references anywhere in the catalogue, sorted."""
    found = set()

    def walk(item):
        if isinstance(item, dict):
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
        elif isinstance(item, str) and PENDING.fullmatch(item):
            found.add(item)

    walk(value)
    return sorted(found, key=lambda ref: (PENDING.fullmatch(ref).group(1), int(PENDING.fullmatch(ref).group(2))))


def readiness(model, today):
    """Held inputs, counted and never filled in: each keeps the default mode NOT GREEN."""
    document, indexed, pinned = model["document"], model["indexed"], model["pinned"]
    measures = [*indexed["metrics"], *indexed["guardrails"]]
    referenced = {record["journey_id"] for collection in ("metrics", "guardrails", "benchmarks")
                  for record in indexed[collection].values()}
    referenced |= {journey for collection in ("research_triggers", "design_debt")
                   for record in indexed[collection].values() for journey in record["journey_ids"]}
    referenced |= {journey for item in document["research_calendar"]["cadences"] for journey in item["journey_ids"]}
    return {
        "readiness.approval_pending": sorted(item["role"] for item in document["approvals"]
                                             if item["status"] == "pending"),
        "readiness.collection_disabled": ["collection"] if document["collection"]["enabled"] is False else [],
        "readiness.payload_review_pending": sorted(identifier for identifier, event in indexed["events"].items()
                                                   if event["payload_review"] == "pending"),
        "readiness.pending_reference": pending_references(document),
        "readiness.baseline_unmeasured": sorted(
            [*measures, *indexed["benchmarks"]],
            key=lambda identifier: (journey_of(identifier), identifier)),
        "readiness.threshold_unset": sorted(identifier for identifier, threshold in indexed["thresholds"].items()
                                            if threshold["kill"]["value"] is None),
        "readiness.measure_unvalidated": sorted(measures, key=lambda identifier: (journey_of(identifier), identifier)),
        "readiness.benchmark_unrun": sorted(identifier for identifier, benchmark in indexed["benchmarks"].items()
                                            if benchmark["results"] is None),
        "readiness.longitudinal_unrun": ["longitudinal_plan"]
        if document["longitudinal_plan"]["status"] == "unrun" else [],
        "readiness.journey_outside_pin": sorted(journey for journey in referenced if journey not in pinned),
        "readiness.registry_import_pin": ["registry_ref"]
        if document["registry_ref"]["path"] == REGISTRY_PIN["path"] else [],
        "readiness.d8_blocking_debt": d8_blocking_debt(document["design_debt"], today),
    }


def cell(text):
    """Table-safe text: content-guarded ASCII with backslashes, ampersands, angle brackets, backticks, square
    brackets and pipes neutralised, so free text can open no HTML, code span, link or image."""
    text = text.replace("\\", "\\\\").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for character in "`[]|":
        text = text.replace(character, "\\" + character)
    return text


def sentence(text):
    """Table-safe free text closed with a full stop, so the generated prose that follows it stays separated."""
    escaped = cell(text)
    return escaped if escaped.endswith((".", "!", "?")) else escaped + "."


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def codes(values):
    return ", ".join(f"`{value}`" for value in values) if values else "none"


def ratio(record, key):
    part = record[key]
    detail = part["definition"] if key == "numerator" else part["eligibility"]
    where = "; ".join(f"`{item['field']}` is {' or '.join(f'`{value}`' for value in item['values'])}"
                      for item in part["filters"])
    return f"{codes(part['event_ids'])}{' where ' + where if where else ''}: {cell(detail)}"


def render_summary(model, gaps):
    """The generated governance/ux-outcomes.md: LF, deterministic, no timestamps or issue titles (TS-M4). The D8
    check depends on the date it runs, so it is reported by the validator and not written here."""
    document, indexed = model["document"], model["indexed"]
    privacy, collection = document["privacy"], document["collection"]
    registry = document["registry_ref"]
    budget = privacy["privacy_budget"]
    held = [rule for rule in READINESS_RULES if rule != "readiness.d8_blocking_debt"]
    status = NOT_GREEN if any(gaps[rule] for rule in held) else "readiness inputs complete (D8 debt check separate)"
    lines = [
        f"<!-- Generated by scripts/check_ux_outcomes.py --write-summary from {DATA}; do not edit by hand. -->",
        "", "# UX outcomes, research cadence and design-debt governance (T-UXR-08)", "",
        f"Catalogue `{document['catalogue_version']}`, status `{document['status']}`, source "
        f"`{document['source_issue']}`. Journeys are read from `{registry['path']}` at `{registry['commit']}` "
        f"(`{registry['sha256']}`). Every value below is a proposal awaiting the Privacy, Product, UX Research and "
        "CDO-equivalent approvals; no measurement, research session, approval or collection has happened.", "",
        f"Readiness: **{status}**.", "",
        *table(("Readiness rule", "Count"), [(f"`{rule}`", str(len(gaps[rule]))) for rule in held]), "",
        "## Privacy and collection", "",
        f"- Collection: {'enabled' if collection['enabled'] else 'disabled'}; enabling requires "
        f"{codes(sorted(collection['enable_requires']))}. Rollback: {sentence(collection['rollback'])}",
        f"- Payload allowlist (referenced, not restated; E33-F04 names the E07 allowlist rule E07-F01 and its "
        f"ingestion validation): {codes(sorted(privacy['payload_allowlist_refs']))}.",
        f"- Analytics consent (purpose entry in the consent ledger): `{privacy['consent_ref']}`. Opt-out honoured: "
        f"{sentence(privacy['opt_out']['rule'])} Server-side opt-out enforcement (E07-F03): "
        f"`{privacy['opt_out']['enforcement_ref']}`. Study-specific research consent stays with "
        f"`{document['research_calendar']['operations_ref']}`.",
        "- These owner choices follow the accepted threat-model records (E07, E33) and await coordinator "
        "confirmation.",
        f"- Cohort minimum, retention, aggregation and access: `{privacy['cohort_minimum_ref']}`, "
        f"`{privacy['retention_ref']}`, `{privacy['aggregation_ref']}`, `{privacy['access_ref']}`.",
        f"- Session recording of financial or operator-sensitive content: `{privacy['session_recording']}`.",
        f"- Privacy budget: at most {budget['max_fields_per_event']} fields per event and "
        f"{budget['max_values_per_field']} enumerated values per field; no free-text, number or identifier kind.",
        "- Planted-field rejection: event names, field names and values use only the reviewed vocabulary "
        "`EVENT_VOCABULARY` in `scripts/check_ux_outcomes.py`; money, currency, raw content, prompt, identity, "
        "household, location and demographic words, and their digit-for-letter and rn/vv look-alikes, are refused by "
        "category, and a digit appears only in a journey code. Residual risk: a reviewed word can still be misused in "
        "context, so the payload review held on every event remains the backstop.",
        "", "## Events", "",
        *table(("Event", "Name", "Fields", "Incentive", "Purpose"), [
            (f"`{identifier}`", f"`{event['name']}`",
             ", ".join(f"`{field['name']}` ({field['kind']})" for field in event["fields"]) or "none",
             event["incentive"] or "none", cell(event["purpose"]))
            for identifier, event in sorted(indexed["events"].items())]), "",
        "## Outcome metrics", "",
        "Every metric and guardrail stays `unvalidated` until research operations and persona, jobs and "
        f"mental-model evidence exist: {codes(sorted(document['outcome_validation_refs']))}.", "",
        *table(("Metric", "Journey", "Role", "Kind", "Statement", "Numerator", "Denominator", "Direction",
                "Threshold", "Guardrails", "Sample limitation"), [
            (f"`{identifier}`", f"`{metric['journey_id']}`", metric["role"], metric["kind"], cell(metric["statement"]),
             ratio(metric, "numerator"), ratio(metric, "denominator"), metric["direction"],
             f"`{metric['threshold_id']}`", codes(metric["guardrail_ids"]), cell(metric["sample_limitation"]))
            for identifier, metric in sorted(indexed["metrics"].items())]), "",
        "## Guardrails", "",
        *table(("Guardrail", "Journey", "Class", "Concern", "Signal", "Numerator", "Denominator", "Threshold"), [
            (f"`{identifier}`", f"`{guardrail['journey_id']}`", guardrail["class"], guardrail["concern"],
             cell(guardrail["signal"]), ratio(guardrail, "numerator"), ratio(guardrail, "denominator"),
             f"`{guardrail['threshold_id']}`")
            for identifier, guardrail in sorted(indexed["guardrails"].items())]), "",
        "Baselines are `unmeasured` and targets and thresholds `unset`: values arrive only through a reviewed, "
        "versioned catalogue change backed by research evidence.", "",
        "## Decision thresholds", "",
        *table(("Threshold", "Warn", "Kill", "Minimum sample", "On crossing", "Reviewers"), [
            (f"`{identifier}`", threshold["warn"]["source"], threshold["kill"]["source"],
             f"`{threshold['minimum_sample_ref']}`", threshold["on_cross"], codes(sorted(threshold["reviewers"])))
            for identifier, threshold in sorted(indexed["thresholds"].items())]), "",
        "## Research triggers", "",
        *table(("Trigger", "Journeys", "Condition", "Source", "Follow-up", "Owner", "Status"), [
            (f"`{identifier}`", codes(trigger["journey_ids"]), trigger["condition"], f"`{trigger['source_id']}`",
             trigger["follow_up"], trigger["owner_role"], trigger["status"])
            for identifier, trigger in sorted(indexed["research_triggers"].items())]), "",
    ]
    return "\n".join(lines + render_tail(model)) + "\n"


def render_tail(model):
    document, indexed = model["document"], model["indexed"]
    calendar, plan = document["research_calendar"], document["longitudinal_plan"]
    return [
        "## Research calendar and panel health", "",
        f"Operations, consent and panel: `{calendar['operations_ref']}`. No session is scheduled. Panel health "
        f"measures: {codes(sorted(calendar['panel_health']))}.", "",
        *table(("Study", "Cadence", "Journeys"), [
            (item["study"], item["cadence"], codes(item["journey_ids"]))
            for item in sorted(calendar["cadences"], key=lambda item: item["study"])]), "",
        "## Unmoderated benchmarks", "",
        "Each benchmark starts only after moderated-usability defects close on every platform its journey runs on "
        "(platforms from the pinned registry flows; E38 owners: Android "
        f"`{MODERATED_OWNERS['android']}`, web `{MODERATED_OWNERS['web']}`, admin `{MODERATED_OWNERS['admin']}`). "
        "These owner choices await coordinator confirmation.", "",
        *table(("Benchmark", "Journey", "Version", "Scenario", "Steps", "Script digest", "Success", "Entry"), [
            (f"`{identifier}`", f"`{benchmark['journey_id']}`", benchmark["version"], cell(benchmark["scenario"]),
             str(len(benchmark["task_steps"])), f"`{benchmark['task_script_sha256']}`",
             cell(benchmark["success_definition"]),
             f"{benchmark['entry_criteria']} ({codes(benchmark['moderated_defects_refs'])})")
            for identifier, benchmark in sorted(indexed["benchmarks"].items())]), "",
        "## Post-beta longitudinal plan", "",
        f"- Status: `{plan['status']}`. Cohort: {sentence(plan['cohort'])} Minimum: `{plan['cohort_minimum_ref']}`.",
        f"- Cadence: {plan['cadence']}. Retention: `{plan['retention_ref']}`. Privacy review: "
        f"`{plan['privacy_review_ref']}`.",
        *[f"- Stop criterion: {sentence(item)}" for item in plan["stop_criteria"]],
        f"- Decisions it may change: {codes(plan['decisions_it_may_change'])}.", "",
        "## Design-debt register", "",
        "Open critical or high debt blocks D8 unless the CDO-equivalent (`decision_coordinator`) records a dated, "
        "unexpired exception; `check_ux_outcomes.d8_blocking_debt` evaluates this on the date it runs.", "",
        *(table(("Debt", "Title", "Journeys", "Severity", "Owner", "Due", "Release impact", "Status", "Exception"), [
            (f"`{identifier}`", cell(debt["title"]), codes(debt["journey_ids"]), debt["severity"], debt["owner_role"],
             debt["due_date"], debt["release_impact"], debt["status"],
             "none" if debt["exception"] is None else
             f"{debt['exception']['recorded_by_role']} {debt['exception']['recorded_on']} to "
             f"{debt['exception']['expires_on']}")
            for identifier, debt in sorted(indexed["design_debt"].items())]) if indexed["design_debt"]
          else ["No design debt is recorded."]), "",
        "## Approvals", "",
        *table(("Role", "Status"), [(item["role"], item["status"])
                                    for item in sorted(document["approvals"], key=lambda item: item["role"])]),
    ]


def local_path(root, relative):
    """root/relative, refused (OSError) when any component below the root is a symlink, so a planted link cannot
    redirect a read or the summary write outside the repository."""
    path = Path(root)
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise OSError("refusing a symlinked path")
    return path


def load_and_check(root, base=None):
    root = Path(root)
    sources = GitSources(root, base)
    document, schema = support.load_json(local_path(root, DATA)), support.load_json(local_path(root, SCHEMA))
    return check(document, schema, sources, base=read_base(sources), inventory=read_inventory(root))


def today_utc():
    return datetime.now(timezone.utc).date()


def main(argv=None, root=None, loader=None, today=None):
    """CLI. `root`, `loader` and `today` are test seams; the command line always uses the repository and clock."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--structure", action="store_true", help="Check structure only; readiness is not evaluated.")
    modes.add_argument("--write-summary", action="store_true", help=f"Regenerate {SUMMARY} from the catalogue.")
    modes.add_argument("--check-summary", action="store_true", help=f"Fail unless {SUMMARY} matches byte for byte.")
    parser.add_argument("--base", help=f"Git revision whose committed benchmarks must not change without a version "
                                       f"bump (default: the merge base of HEAD and {BASE_REF}).")
    args = parser.parse_args(argv)
    root = ROOT if root is None else Path(root)
    try:
        model = (loader or load_and_check)(root, args.base)
        if args.structure:
            print(f"UX outcomes structure valid: {len(model['indexed']['metrics'])} metrics, "
                  f"{len(model['indexed']['guardrails'])} guardrails, {len(model['indexed']['events'])} events; "
                  "readiness not evaluated.")
            return 0
        gaps = readiness(model, today_utc() if today is None else today)
        summary = render_summary(model, gaps)
        status = NOT_GREEN if any(gaps.values()) else GREEN
        if args.write_summary:
            target = local_path(root, SUMMARY)
            target.write_text(summary, encoding="utf-8", newline="\n")
            print(f"UX outcomes summary written to {SUMMARY} ({status}).")
            return 0
        try:
            current = local_path(root, SUMMARY).read_bytes()
        except OSError:
            current = None
        require(current == summary.encode("utf-8"), "summary.drift")
        if args.check_summary:
            print(f"UX outcomes summary {SUMMARY} matches the catalogue ({status}).")
            return 0
        print(status)
        if status == GREEN:
            return 0
        for rule in READINESS_RULES:
            print(f"{rule}: {len(gaps[rule])}")
        return 1
    except Refused as error:
        print(f"UX outcomes check refused: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, RecursionError, LookupError,
            re.error):
        # Fail closed without a traceback, whose message could echo input content.
        print("UX outcomes check refused: input.unreadable_or_invalid", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
