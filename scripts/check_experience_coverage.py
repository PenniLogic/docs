"""Offline T-UXR-06 checks of the experience-coverage registry, its client-issue partition and D20 summary.

PenniLogic/docs#75 publishes the screen, flow, component and test traceability registry as
product/experience-coverage.json, the disposition of every Android, web and admin issue of the
committed inventory as product/experience-coverage-partition.json (both validated against
product/experience-coverage.schema.json, a self-contained draft-07 subset) and the generated D20
summary as product/experience-coverage.md. The registry cites the frozen planning import
planning/source/evidence/experience-coverage.json by commit, path and sha256 and never edits it.

Structure failures raise `Refused` with a static rule identifier plus, at most, identifiers that match
the registry ID or `PenniLogic/<repo>#N` grammar; input text is never echoed. Readiness gaps (D6
dependencies and handoffs, docs#74 route IDs, verified independent QA, owner confirmation of DesignOps
proposals, imported persona and ticket contradictions, security states, unresolved and post-snapshot
issues) are counted, never filled in, and keep the default mode NOT GREEN. Everything runs offline
against local files and the local Git object store: no network, remote action, approval, appointment,
gate closure or independent Design QA is made or implied.
"""

import argparse
from collections import defaultdict
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "product/experience-coverage.json"
PARTITION = "product/experience-coverage-partition.json"
SCHEMA = "product/experience-coverage.schema.json"
SUMMARY = "product/experience-coverage.md"
TAXONOMY = "product/client-state-taxonomy.json"
# planning/** is an unchanged historical contract, so the imported bytes are pinned here.
IMPORT_PATH = "planning/source/evidence/experience-coverage.json"
IMPORT_SHA256 = "sha256:2f7b27c1f6683d4c256a938ccfb0fc06614f83fe57996a4d7aeaf0b7cae0bf3a"
# The full remote-tracking ref: a local branch named origin/main must not shadow it.
BASE_REF = "refs/remotes/origin/main"
# The registry author (DesignOps, PenniLogic/docs#75) is never a flow's independent QA owner.
AUTHOR_ISSUE, AUTHOR_PLAN_ID = "PenniLogic/docs#75", "T-UXR-06"
GREEN = "GREEN: readiness complete"
NOT_GREEN = "NOT GREEN: readiness incomplete"


def _sibling(name, filename):
    """Load an accepted sibling checker read-only by path, as check_design_gates.py does."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


support = _sibling("experience_schema_support", "check_client_states.py")
gates = _sibling("experience_design_gates", "check_design_gates.py")
strategy = _sibling("experience_test_strategy", "check_test_strategy.py")
INVENTORY = strategy.INVENTORY

COLLECTIONS = (
    ("personas", "persona"), ("journeys", "journey"), ("user_stories", "user_story"), ("flows", "flow"),
    ("screens", "screen"), ("components", "component"), ("diagrams", "diagram"),
)
KIND_ORDER = {kind: index for index, (_, kind) in enumerate(COLLECTIONS)}
GRAMMAR = {
    "persona": re.compile(r"P([0-9]{2})"),
    "journey": re.compile(r"J([0-9]{2})"),
    "user_story": re.compile(r"US-(AND|WEB|ADM)-([0-9]{2})"),
    "flow": re.compile(r"F-(AND|WEB|ADM)-([0-9]{2})"),
    "screen": re.compile(r"S-(AND|WEB|ADM)-([0-9]{3})"),
    "component": re.compile(r"C-[A-Z0-9]+(?:-[A-Z0-9]+)*"),
    "diagram": re.compile(r"D([0-9]{2})"),
}
DIGITS = {"persona": 2, "journey": 2, "user_story": 2, "flow": 2, "screen": 3, "diagram": 2}
INFIX = {"AND": "android", "WEB": "web", "ADM": "admin"}
PLATFORMS = ("android", "web", "admin")
CLIENT_REPOSITORIES = tuple(f"PenniLogic/{platform}" for platform in PLATFORMS)
# Component IDs with this prefix belong to test fixtures only and are refused in published data.
SYNTHETIC_PREFIX = "C-SYN-"
ISSUE_REF = re.compile(
    r"PenniLogic/(" + "|".join(re.escape(name.split("/")[1]) for name in strategy.REPOSITORY_IDS) + r")#([1-9][0-9]*)"
)
HANDOFF = re.compile(r"HND-(AND|WEB|ADM)-([0-9]{3})@(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
COMMIT = re.compile(r"[0-9a-f]{40}")
REVISION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,199}")
_SEGMENT = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_ELEMENT = rf"(?:{_SEGMENT}|:[a-z][a-z0-9]*(?:-[a-z0-9]+)*)"
# route_hint is the imported provisional hint, not a docs#74 route: Android deep links or web/admin paths.
ROUTE_HINTS = {
    "android": re.compile(rf"(?:android|android-widget)://{_SEGMENT}(?:/{_ELEMENT})*"),
    "path": re.compile(rf"/{_ELEMENT}(?:/{_ELEMENT})*(?:/\*)?"),
}
ROUTE_HINT_LIMIT = 120
FREE_TEXT = frozenset({
    "description", "name", "jobs", "as_a", "i_want", "so_that", "artifact_path", "security_reason",
    "retired_reason", "rationale",
})
GRAMMAR_CHECKED = frozenset({"route_hint"})
FREE_TEXT_LIMIT = 400
CONTENT_SHAPES = (
    # Printable ASCII only: control characters and look-alike digits, at signs or currency signs cannot slip past
    # the ASCII shape patterns below.
    ("content.unprintable_character", re.compile(r"[^\x20-\x7e]")),
    ("content.secret_shape", re.compile(
        r"\bgh[pousr]_[A-Za-z0-9]{8,}|\bgithub_pat_|-----BEGIN|\bAKIA[0-9A-Z]{16}\b|\bxox[abposr]-"
        r"|\bsk-[A-Za-z0-9_-]{20,}|[0-9a-fA-F]{32,}"
    )),
    ("content.url_shape", re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://|\bwww\.", re.IGNORECASE)),
    ("content.email_shape", re.compile(r"[^\s@]+@[^\s@]+\.[A-Za-z]{2,}")),
    ("content.amount_shape", re.compile(
        r"\$\s*[0-9]|\b(?:INR|USD|EUR|GBP|Rs\.?)\s*[0-9]"
        r"|[0-9]\s*(?:INR|USD|EUR|GBP|rupees?|lakhs?|crores?)\b",
        re.IGNORECASE,
    )),
)
PHONE = re.compile(r"\+?[0-9][0-9 ().-]{6,}[0-9]")
TOKEN = re.compile(r"[A-Za-z0-9+=_]{32,}")
SCRUBBED_GIT_VARIABLES = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR", "GIT_NAMESPACE",
)

STRUCTURE_RULES = (
    "input.unreadable_or_invalid", "schema.invalid", "schema.free_text_unlisted",
    "content.too_long", "content.unprintable_character", "content.secret_shape", "content.url_shape",
    "content.email_shape", "content.phone_shape", "content.amount_shape",
    "import.mismatch", "import.unavailable", "import.digest_mismatch", "import.invalid",
    "ledger.base_unavailable", "ledger.base_invalid", "inventory.invalid", "taxonomy.unreadable",
    "id.duplicate", "id.platform_infix_mismatch", "id.synthetic_reserved", "id.out_of_range",
    "range.invalid", "range.overlap", "range.unknown_role",
    "ledger.duplicate", "ledger.kind_or_platform_mismatch", "ledger.retired_reason", "ledger.missing_record",
    "ledger.retired_in_use", "ledger.dropped_record", "ledger.entry_removed", "ledger.reordered",
    "ledger.entry_changed", "ledger.import_discontinuity",
    "reference.dangling", "ticket.empty", "ticket.issue_missing", "ticket.dangling", "ticket.plan_id_mismatch",
    "ticket.renounced", "ownership.design_missing", "ownership.implementation_missing", "ownership.qa_missing",
    "graph.journey_without_persona", "graph.flow_without_screens", "graph.flow_without_journey",
    "graph.orphan_screen", "graph.link_mismatch",
    "platform.shared_mixed", "platform.story_flow", "platform.story_persona", "platform.flow_screen",
    "platform.screen_component", "platform.implementation_repository", "route.hint_grammar", "platform.route_hint",
    "state.unknown_screen_state", "state.unknown_component_state", "taxonomy.map_mismatch", "component.unused",
    "screen.critical_mismatch", "security.reason_mismatch", "security.state_not_on_screen",
    "d6.dependency_mismatch", "handoff.platform_mismatch",
    "qa.independence_evidence", "qa.evidence_unavailable", "qa.evidence_digest_mismatch",
    "flow.critical_without_persona", "ownership.qa_not_independent", "diagram.d20_artifact",
    "partition.duplicate_issue", "partition.unknown_issue", "partition.plan_id_mismatch",
    "partition.rationale_missing", "partition.rationale_on_frontend", "partition.unclassified_issue",
    "partition.unmapped_implementation_ticket", "partition.frontend_without_mapping",
    "partition.post_snapshot_invalid", "release_gate.bypass", "summary.drift",
)
READINESS_RULES = (
    "readiness.d6_missing", "readiness.route_missing", "readiness.qa_unverified",
    "readiness.persona_outside_journey", "readiness.screen_ticket_outside_flows",
    "readiness.security_states_missing", "readiness.proposal_unconfirmed", "readiness.ticket_unresolved",
    "readiness.post_snapshot_issue",
)


def classify(identifier):
    """Return (kind, platform, number) for a registry ID or None; platform and number may be None."""
    if not isinstance(identifier, str):
        return None
    for kind, grammar in GRAMMAR.items():
        match = grammar.fullmatch(identifier)
        if match:
            groups = match.groups()
            platform = INFIX[groups[0]] if len(groups) == 2 else None
            return kind, platform, int(groups[-1]) if groups else None
    return None


def printable(value):
    """Only registry IDs and public issue references may appear in output; everything else is input text."""
    return isinstance(value, str) and (classify(value) is not None or ISSUE_REF.fullmatch(value) is not None)


class Refused(ValueError):
    """A static rule identifier plus at most grammar-validated identifiers; never echoes input text."""

    def __init__(self, rule, *subjects):
        self.rule = rule
        self.subject = " ".join(subjects) if subjects and all(printable(item) for item in subjects) else None
        super().__init__(rule if self.subject is None else f"{rule} {self.subject}")


def require(condition, rule, *subjects):
    if not condition:
        raise Refused(rule, *subjects)


def natural_key(subject):
    """Sort subjects by kind, platform and number (or repository and issue number), not by raw text."""
    key = []
    for token in subject.split(" "):
        info, issue = classify(token), ISSUE_REF.fullmatch(token)
        if info is not None:
            kind, platform, number = info
            key.append((0, KIND_ORDER[kind], -1 if platform is None else PLATFORMS.index(platform),
                        -1 if number is None else number, token))
        elif issue is not None:
            key.append((1, strategy.REPOSITORY_ORDER[f"PenniLogic/{issue.group(1)}"], int(issue.group(2)), 0, token))
        else:
            key.append((2, 0, 0, 0, token))
    return key


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


def registry_checksum(registry):
    """The T-DQA-12 `registry_checksum`: sha256 over canonical JSON (sorted keys, compact, ASCII)."""
    return gates.digest(registry)


def _schema_subject(error, value):
    match = re.match(
        r"\$\.(personas|journeys|user_stories|flows|screens|components|diagrams|id_ledger|entries)\[([0-9]+)\]",
        str(error),
    ) if isinstance(error, ValueError) else None
    if match is None or not isinstance(value, dict) or not isinstance(value.get(match.group(1)), list):
        return ()
    items, index = value[match.group(1)], int(match.group(2))
    item = items[index] if index < len(items) else None
    candidate = item.get("issue" if match.group(1) == "entries" else "id") if isinstance(item, dict) else None
    return (candidate,) if printable(candidate) else ()


def shape(value, schema, definition=None):
    """Validate with the shared subset validator; its messages echo input, so only a rule and record ID survive."""
    try:
        selected = schema if definition is None else schema["definitions"][definition]
        support.validate_schema(value, selected, schema)
    except (ValueError, KeyError, TypeError, RecursionError) as error:
        raise Refused("schema.invalid", *_schema_subject(error, value)) from None


def unconstrained_text(schema):
    """Property names whose schema leaves a string (or list of strings) without pattern, enum or const."""
    definitions = schema.get("definitions", {})

    def resolve(node):
        for _ in range(32):
            if not (isinstance(node, dict) and "$ref" in node):
                break
            node = definitions.get(str(node["$ref"]).rsplit("/", 1)[-1], {})
        return node if isinstance(node, dict) else {}

    def free(node):
        node = resolve(node)
        types = node.get("type", [])
        types = types if isinstance(types, list) else [types]
        if "string" in types and not {"pattern", "enum", "const"} & node.keys():
            return True
        return "array" in types and free(node.get("items", {}))

    found = set()

    def walk(node):
        if not isinstance(node, dict):
            return
        for name, child in node.get("properties", {}).items():
            if free(child):
                found.add(name)
            walk(child)
        extra = node.get("additionalProperties")
        if isinstance(extra, dict):
            if free(extra):
                found.add("*")
            walk(extra)
        walk(node.get("items"))

    walk(schema)
    for definition in definitions.values():
        walk(definition)
    return found


def _scan(text, subject):
    require(len(text) <= FREE_TEXT_LIMIT, "content.too_long", *subject)
    for rule, pattern in CONTENT_SHAPES:
        require(pattern.search(text) is None, rule, *subject)
    for match in PHONE.finditer(text):
        require(sum(character.isdigit() for character in match.group()) < 9, "content.phone_shape", *subject)
    for match in TOKEN.finditer(text):
        token = match.group()
        mixed = all(any(test(c) for c in token) for test in (str.isdigit, str.islower, str.isupper))
        require(not mixed, "content.secret_shape", *subject)


def guard_content(value, subject=()):
    """Scan every allowlisted free-text value; the schema leaves no other string unconstrained."""
    if isinstance(value, dict):
        for key in ("id", "issue"):
            if printable(value.get(key)):
                subject = (value[key],)
                break
        for key, item in value.items():
            if key in FREE_TEXT:
                for text in item if isinstance(item, list) else [item]:
                    if isinstance(text, str):
                        _scan(text, subject)
            elif key == "plan_id" and isinstance(item, str):
                _scan(item, subject)  # unresolved plan IDs reach the summary without an inventory match
            elif key not in GRAMMAR_CHECKED:
                guard_content(item, subject)
    elif isinstance(value, list):
        for item in value:
            guard_content(item, subject)


def trusted_git(root):
    """Absolute path of git from absolute PATH entries outside the checked repository.

    A bare "git" lets the operating system search relative PATH entries and, on Windows, the current
    directory first, so a candidate-local executable could forge the ledger base or the import.
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
    """Pinned blobs and the ledger base from the local Git object store; never fetches, writes or pushes."""

    def __init__(self, root, base=None):
        self.root, self.base, self.executable = Path(root), base, None

    def _git(self, *args):
        self.executable = self.executable or trusted_git(self.root)
        env = {key: value for key, value in os.environ.items() if key not in SCRUBBED_GIT_VARIABLES}
        env["GIT_NO_LAZY_FETCH"] = "1"
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

    def base_registry(self):
        """The registry bytes at the ledger base, or None when the base predates the registry."""
        if self.base is None:
            commit = self._commit("merge-base", "HEAD", BASE_REF)
        elif isinstance(self.base, str) and REVISION.fullmatch(self.base):
            commit = self._commit("rev-parse", "--verify", "--quiet", f"{self.base}^{{commit}}")
        else:
            raise LookupError("unsafe revision")
        if self._git("cat-file", "-e", f"{commit}:{REGISTRY}").returncode != 0:
            return None
        return self.blob(commit, REGISTRY)


def read_import(registry, sources, pin):
    """Read the frozen import at its pinned commit and return its IDs by kind (continuity input)."""
    reference = registry["imported_from"]
    require((reference["path"], reference["sha256"]) == tuple(pin), "import.mismatch")
    try:
        blob = sources.blob(reference["commit"], reference["path"])
    except LookupError:
        raise Refused("import.unavailable") from None
    require(isinstance(blob, bytes) and gates.digest(blob) == reference["sha256"], "import.digest_mismatch")
    try:
        imported = loads(blob)
    except (ValueError, RecursionError):
        raise Refused("import.invalid") from None
    identities = []
    for collection, kind in COLLECTIONS:
        records = imported.get(collection) if isinstance(imported, dict) else None
        require(isinstance(records, list), "import.invalid")
        for record in records:
            identifier = record.get("id") if isinstance(record, dict) else None
            info = classify(identifier)
            require(info is not None and info[0] == kind, "import.invalid")
            identities.append(identifier)
    return identities


def _ledger_entry_consistent(entry):
    info = classify(entry["id"])
    return info is not None and (info[0], info[1]) == (entry["kind"], entry["platform"])


def read_base(sources, schema):
    """The base registry's ledger, or None when the base predates the registry (import continuity applies)."""
    try:
        blob = sources.base_registry()
    except LookupError:
        raise Refused("ledger.base_unavailable") from None
    if blob is None:
        return None
    try:
        base = loads(blob)
    except (ValueError, RecursionError):
        raise Refused("ledger.base_invalid") from None
    ledger = base.get("id_ledger") if isinstance(base, dict) else None
    require(isinstance(ledger, list), "ledger.base_invalid")
    seen = set()
    for entry in ledger:
        try:
            shape(entry, schema, "ledger_entry")
        except Refused:
            raise Refused("ledger.base_invalid") from None
        require(entry["id"] not in seen and _ledger_entry_consistent(entry), "ledger.base_invalid")
        seen.add(entry["id"])
    return ledger


def inventory_index(inventory):
    """Reuse check_test_strategy.validate_inventory; its messages echo input, so only the rule survives."""
    try:
        return strategy.validate_inventory(inventory)
    except (ValueError, KeyError, TypeError, AttributeError):
        raise Refused("inventory.invalid") from None


def taxonomy_states(taxonomy):
    """Map taxonomy identifiers (snake case) to their hyphenated state names."""
    try:
        states = {state["id"]: state["name"] for state in taxonomy["states"]}
        valid = len(states) == len(taxonomy["states"]) and all(
            isinstance(key, str) and isinstance(value, str) for key, value in states.items()
        )
    except (KeyError, TypeError):
        raise Refused("taxonomy.unreadable") from None
    require(valid and bool(states), "taxonomy.unreadable")
    return states


def ticket_key(ticket):
    return ticket["issue"] if ticket["issue"] is not None else f"plan:{ticket['plan_id']}"


def is_registry_author(ticket):
    return ticket["issue"] == AUTHOR_ISSUE or ticket["plan_id"] == AUTHOR_PLAN_ID


def expand_platforms(platforms, owner):
    """`shared` means all three client platforms and is never mixed with explicit platforms."""
    if "shared" in platforms:
        require(platforms == ["shared"], "platform.shared_mixed", owner)
        return set(PLATFORMS)
    return set(platforms)


def lacks_d6(screen):
    return screen["d6_dependency"] is None or screen["handoff_ref"] is None


class Model:
    """Indexes over a structurally checked registry, partition and inventory snapshot."""

    def __init__(self, registry, partition, index):
        self.registry, self.partition, self.index = registry, partition, index
        self.records = {}
        self.by_kind = {kind: {} for _, kind in COLLECTIONS}
        self.unresolved = []
        self.stories_by_flow = defaultdict(list)
        self.ledger_base = None

    @property
    def flows(self):
        return self.by_kind["flow"]

    @property
    def screens(self):
        return self.by_kind["screen"]

    def implementation_issues(self, screen):
        """Issues implementing a screen directly or through any flow that contains it."""
        tickets = list(screen["implementation_tickets"])
        for flow_id in screen["flow_ids"]:
            tickets += self.flows[flow_id]["implementation_tickets"]
        return sorted({ticket["issue"] for ticket in tickets if ticket["issue"] is not None}, key=natural_key)

    def frontend_issues(self):
        issues = set()
        for record in [*self.flows.values(), *self.screens.values()]:
            issues.update(ticket["issue"] for ticket in record["implementation_tickets"] if ticket["issue"] is not None)
        return issues


def check_identifiers(model, synthetic_ok):
    registry = model.registry
    for collection, kind in COLLECTIONS:
        for record in registry[collection]:
            identifier = record["id"]
            require(identifier not in model.records, "id.duplicate", identifier)
            platform = classify(identifier)[1]
            require(platform is None or record["platform"] == platform, "id.platform_infix_mismatch", identifier)
            require(synthetic_ok or not identifier.startswith(SYNTHETIC_PREFIX), "id.synthetic_reserved", identifier)
            model.records[identifier] = kind
            model.by_kind[kind][identifier] = record
    ranges = defaultdict(list)
    for item in registry["id_ranges"]:
        kind, platform, first, last = item["kind"], item["platform"], item["first"], item["last"]
        require(item["owner_role"] in gates.ROLES, "range.unknown_role")
        require((platform is not None) == (kind in ("user_story", "flow", "screen")), "range.invalid")
        if kind == "component":
            require(first is None and last is None, "range.invalid")
        else:
            require(isinstance(first, int) and isinstance(last, int) and 1 <= first <= last < 10 ** DIGITS[kind],
                    "range.invalid")
        for other in ranges[(kind, platform)]:
            require(kind != "component" and (last < other["first"] or first > other["last"]), "range.overlap")
        ranges[(kind, platform)].append(item)
    for identifier, kind in model.records.items():
        _, platform, number = classify(identifier)
        require(any(kind == "component" or item["first"] <= number <= item["last"]
                    for item in ranges.get((kind, platform), [])), "id.out_of_range", identifier)


def check_ledger(model, imported, base):
    ledger = model.registry["id_ledger"]
    entries = {}
    for entry in ledger:
        identifier = entry["id"]
        require(identifier not in entries, "ledger.duplicate", identifier)
        require(_ledger_entry_consistent(entry), "ledger.kind_or_platform_mismatch", identifier)
        require((entry["status"] == "retired") == (entry["retired_reason"] is not None), "ledger.retired_reason",
                identifier)
        entries[identifier] = entry
    for identifier in model.records:
        require(identifier in entries, "ledger.missing_record", identifier)
        require(entries[identifier]["status"] == "active", "ledger.retired_in_use", identifier)
    for identifier, entry in entries.items():
        require(entry["status"] != "active" or identifier in model.records, "ledger.dropped_record", identifier)
    if base is not None:
        for entry in base:
            require(entry["id"] in entries, "ledger.entry_removed", entry["id"])
        require([entry["id"] for entry in ledger[:len(base)]] == [entry["id"] for entry in base], "ledger.reordered")
        for entry in base:
            require(entry["status"] != "retired" or entries[entry["id"]] == entry, "ledger.entry_changed", entry["id"])
    for identifier in imported:
        require(identifier in entries, "ledger.import_discontinuity", identifier)
    model.ledger_base = "base registry" if base is not None else "frozen import"


REFERENCES = (
    ("journeys", "persona_ids", "persona"), ("journeys", "flow_ids", "flow"),
    ("user_stories", "persona_ids", "persona"), ("user_stories", "journey_ids", "journey"),
    ("user_stories", "flow_id", "flow"), ("flows", "journey_ids", "journey"), ("flows", "screen_ids", "screen"),
    ("screens", "flow_ids", "flow"), ("screens", "component_ids", "component"),
)
TICKETS = (
    ("personas", "owner_ticket"), ("journeys", "owner_ticket"), ("user_stories", "owner_ticket"),
    ("flows", "design_ticket"), ("flows", "implementation_tickets"), ("flows", "qa_ticket"),
    ("screens", "design_ticket"), ("screens", "implementation_tickets"), ("screens", "qa_ticket"),
    ("components", "design_ticket"), ("diagrams", "owner_ticket"),
)


def check_references(model):
    for collection, field, kind in REFERENCES:
        for record in model.registry[collection]:
            values = record[field] if isinstance(record[field], list) else [record[field]]
            for value in values:
                require(model.records.get(value) == kind, "reference.dangling", record["id"], value)


def check_tickets(model):
    by_plan = {issue["plan_id"] for issue in model.index.values() if issue.get("plan_id")}
    for collection, field in TICKETS:
        for record in model.registry[collection]:
            value = record[field]
            for ticket in value if isinstance(value, list) else [value]:
                if ticket is None:
                    continue
                plan_id, issue = ticket["plan_id"], ticket["issue"]
                require(plan_id is not None or issue is not None, "ticket.empty", record["id"])
                if issue is None:
                    require(plan_id not in by_plan, "ticket.issue_missing", record["id"])
                    model.unresolved.append(record["id"])
                    continue
                found = model.index.get(issue)
                require(found is not None, "ticket.dangling", record["id"], issue)
                require(found.get("plan_id") == plan_id, "ticket.plan_id_mismatch", record["id"], issue)
                require(not (found["state"] == "closed" and found.get("state_reason") in strategy.UNOWNED_REASONS),
                        "ticket.renounced", record["id"], issue)


def check_ownership(model):
    for record in [*model.flows.values(), *model.screens.values()]:
        require(record["design_ticket"] is not None, "ownership.design_missing", record["id"])
        require(bool(record["implementation_tickets"]), "ownership.implementation_missing", record["id"])
        require(record["qa_ticket"] is not None, "ownership.qa_missing", record["id"])
    for component in model.by_kind["component"].values():
        require(component["design_ticket"] is not None, "ownership.design_missing", component["id"])


def check_graph(model):
    journeys, flows, screens = model.by_kind["journey"], model.flows, model.screens
    for journey in journeys.values():
        require(bool(journey["persona_ids"]), "graph.journey_without_persona", journey["id"])
    for flow in flows.values():
        require(bool(flow["screen_ids"]), "graph.flow_without_screens", flow["id"])
    listed_flows = {flow_id for journey in journeys.values() for flow_id in journey["flow_ids"]}
    for flow in flows.values():
        require(flow["id"] in listed_flows, "graph.flow_without_journey", flow["id"])
    listed_screens = {screen_id for flow in flows.values() for screen_id in flow["screen_ids"]}
    for screen in screens.values():
        require(screen["id"] in listed_screens, "graph.orphan_screen", screen["id"])
    for journey in journeys.values():
        for flow_id in journey["flow_ids"]:
            require(journey["id"] in flows[flow_id]["journey_ids"], "graph.link_mismatch", journey["id"], flow_id)
    for flow in flows.values():
        for journey_id in flow["journey_ids"]:
            require(flow["id"] in journeys[journey_id]["flow_ids"], "graph.link_mismatch", flow["id"], journey_id)
        for screen_id in flow["screen_ids"]:
            require(flow["id"] in screens[screen_id]["flow_ids"], "graph.link_mismatch", flow["id"], screen_id)
    for screen in screens.values():
        for flow_id in screen["flow_ids"]:
            require(screen["id"] in flows[flow_id]["screen_ids"], "graph.link_mismatch", screen["id"], flow_id)
    for story in model.by_kind["user_story"].values():
        model.stories_by_flow[story["flow_id"]].append(story)


def check_platforms(model):
    personas = {key: expand_platforms(item["platforms"], key) for key, item in model.by_kind["persona"].items()}
    components = {key: expand_platforms(item["platforms"], key) for key, item in model.by_kind["component"].items()}
    for story in model.by_kind["user_story"].values():
        require(story["platform"] == model.flows[story["flow_id"]]["platform"], "platform.story_flow", story["id"])
        for persona_id in story["persona_ids"]:
            require(story["platform"] in personas[persona_id], "platform.story_persona", story["id"], persona_id)
    for flow in model.flows.values():
        for screen_id in flow["screen_ids"]:
            require(model.screens[screen_id]["platform"] == flow["platform"], "platform.flow_screen", flow["id"],
                    screen_id)
    for screen in model.screens.values():
        for component_id in screen["component_ids"]:
            require(screen["platform"] in components[component_id], "platform.screen_component", screen["id"],
                    component_id)
    for record in [*model.flows.values(), *model.screens.values()]:
        for ticket in record["implementation_tickets"]:
            if ticket["issue"] is not None:
                require(model.index[ticket["issue"]]["repository"] == f"PenniLogic/{record['platform']}",
                        "platform.implementation_repository", record["id"], ticket["issue"])
    for screen in model.screens.values():
        hint = screen["route_hint"]
        require(len(hint) <= ROUTE_HINT_LIMIT, "route.hint_grammar", screen["id"])
        family = next((name for name, grammar in ROUTE_HINTS.items() if grammar.fullmatch(hint)), None)
        require(family is not None, "route.hint_grammar", screen["id"])
        require((family == "android") == (screen["platform"] == "android"), "platform.route_hint", screen["id"])


def check_states(model, taxonomy):
    required, component_states = set(model.registry["required_states"]), set(model.registry["component_states"])
    for screen in model.screens.values():
        require(set(screen["states"]) <= required, "state.unknown_screen_state", screen["id"])
    for component in model.by_kind["component"].values():
        require(set(component["required_states"]) <= component_states, "state.unknown_component_state",
                component["id"])
    mapping = model.registry["taxonomy_state_map"]
    pairs = {item["taxonomy_state"]: item["state"] for item in mapping}
    require(len(pairs) == len(mapping) == len({item["state"] for item in mapping}) and pairs == taxonomy
            and set(pairs.values()) <= required, "taxonomy.map_mismatch")
    used = {component_id for screen in model.screens.values() for component_id in screen["component_ids"]}
    for component in model.by_kind["component"].values():
        require(component["id"] in used or component["foundational"], "component.unused", component["id"])


def check_screens(model):
    for screen in model.screens.values():
        identifier, states = screen["id"], set(screen["states"])
        derived = any(model.flows[flow_id]["critical"] for flow_id in screen["flow_ids"])
        require(screen["critical"] == derived, "screen.critical_mismatch", identifier)
        require(screen["security_critical"] == (screen["security_reason"] is not None), "security.reason_mismatch",
                identifier)
        require(set(screen["privacy_states"]) <= states and set(screen["authorization_states"]) <= states,
                "security.state_not_on_screen", identifier)
        dependency = screen["d6_dependency"]
        if dependency is not None:
            require(dependency["gate_id"] == "D6" and dependency["artifact_id"] == identifier, "d6.dependency_mismatch",
                    identifier)
        if screen["handoff_ref"] is not None:
            match = HANDOFF.fullmatch(screen["handoff_ref"])
            require(match is not None and INFIX[match.group(1)] == screen["platform"], "handoff.platform_mismatch",
                    identifier)


def check_flows(model, sources):
    for flow in model.flows.values():
        identifier, independence = flow["id"], flow["qa_independence"]
        require((independence["status"] == "verified") == (independence["evidence"] is not None),
                "qa.independence_evidence", identifier)
        if independence["evidence"] is not None:
            evidence = independence["evidence"]
            try:
                blob = sources.blob(evidence["commit"], evidence["path"])
            except LookupError:
                raise Refused("qa.evidence_unavailable", identifier) from None
            require(isinstance(blob, bytes) and gates.digest(blob) == evidence["sha256"], "qa.evidence_digest_mismatch",
                    identifier)
        if flow["critical"]:
            require(bool(model.stories_by_flow[identifier]), "flow.critical_without_persona", identifier)
            qa, design = flow["qa_ticket"], flow["design_ticket"]
            implementation = {ticket_key(ticket) for ticket in flow["implementation_tickets"]}
            require(ticket_key(qa) != ticket_key(design) and ticket_key(qa) not in implementation
                    and not is_registry_author(qa), "ownership.qa_not_independent", identifier)


def check_diagrams(model):
    diagram = model.by_kind["diagram"].get("D20")
    require(diagram is not None and diagram["type"] == "coverage-matrix" and diagram["artifact_path"] == SUMMARY,
            "diagram.d20_artifact", "D20")


def check_partition(model):
    index, entries = model.index, {}
    for entry in model.partition["entries"]:
        issue = entry["issue"]
        require(issue not in entries, "partition.duplicate_issue", issue)
        found = index.get(issue)
        require(found is not None and found["repository"] in CLIENT_REPOSITORIES, "partition.unknown_issue", issue)
        require(found.get("plan_id") == entry["plan_id"], "partition.plan_id_mismatch", issue)
        if entry["disposition"] == "non_frontend":
            require(entry["rationale_class"] is not None and entry["rationale"] is not None,
                    "partition.rationale_missing", issue)
        else:
            require(entry["rationale_class"] is None and entry["rationale"] is None, "partition.rationale_on_frontend",
                    issue)
        entries[issue] = entry
    clients = sorted((key for key, item in index.items() if item["repository"] in CLIENT_REPOSITORIES), key=natural_key)
    for issue in clients:
        require(issue in entries, "partition.unclassified_issue", issue)
    frontend = model.frontend_issues()
    for issue in sorted(frontend, key=natural_key):
        require(entries[issue]["disposition"] == "frontend", "partition.unmapped_implementation_ticket", issue)
    for issue, entry in entries.items():
        require(entry["disposition"] != "frontend" or issue in frontend, "partition.frontend_without_mapping", issue)
    highest = defaultdict(int)
    for item in index.values():
        highest[item["repository"]] = max(highest[item["repository"]], item["number"])
    for issue in model.partition["post_snapshot_issues"]:
        repository, number = issue.split("#")
        require(issue not in index and int(number) > highest[repository], "partition.post_snapshot_invalid", issue)


def check_release_gate(model):
    """A client implementation issue closed as delivered while any of its screens lacks D6 bypassed the gate."""
    for screen in model.screens.values():
        if lacks_d6(screen):
            for issue in model.implementation_issues(screen):
                found = model.index[issue]
                require(not (found["state"] == "closed" and found.get("state_reason") not in strategy.UNOWNED_REASONS),
                        "release_gate.bypass", issue, screen["id"])


def check(registry, partition, schema, inventory, taxonomy, sources, import_pin=None, synthetic_ok=False):
    """Run every structure rule in a fixed order; raise Refused at the first violation, else return the model."""
    shape(registry, schema)
    shape(partition, schema, "partition")
    require(unconstrained_text(schema) <= FREE_TEXT | GRAMMAR_CHECKED, "schema.free_text_unlisted")
    guard_content(registry)
    guard_content(partition)
    imported = read_import(registry, sources, import_pin or (IMPORT_PATH, IMPORT_SHA256))
    base = read_base(sources, schema)
    model = Model(registry, partition, inventory_index(inventory))
    states = taxonomy_states(taxonomy)
    check_identifiers(model, synthetic_ok)
    check_ledger(model, imported, base)
    check_references(model)
    check_tickets(model)
    check_ownership(model)
    check_graph(model)
    check_platforms(model)
    check_states(model, states)
    check_screens(model)
    check_flows(model, sources)
    check_diagrams(model)
    check_partition(model)
    check_release_gate(model)
    return model


def readiness(model):
    """Every visible gap by static rule: sorted, de-duplicated subjects; never filled in or waived."""
    gaps = {rule: set() for rule in READINESS_RULES}
    flows, journeys = model.flows, model.by_kind["journey"]
    for screen in model.screens.values():
        identifier = screen["id"]
        if lacks_d6(screen):
            gaps["readiness.d6_missing"].add(identifier)
        if screen["route_id"] is None:
            gaps["readiness.route_missing"].add(identifier)
        if screen["security_critical"] and not (screen["privacy_states"] and screen["authorization_states"]):
            gaps["readiness.security_states_missing"].add(identifier)
        if screen["proposal"] is not None:
            gaps["readiness.proposal_unconfirmed"].add(identifier)
        owned = {
            ticket_key(ticket) for flow_id in screen["flow_ids"] for ticket in flows[flow_id]["implementation_tickets"]
        }
        for ticket in screen["implementation_tickets"]:
            if ticket_key(ticket) not in owned:
                extra = (ticket["issue"],) if ticket["issue"] is not None else ()
                gaps["readiness.screen_ticket_outside_flows"].add(" ".join((identifier, *extra)))
    for flow in flows.values():
        if flow["critical"] and flow["qa_independence"]["status"] != "verified":
            gaps["readiness.qa_unverified"].add(flow["id"])
    for story in model.by_kind["user_story"].values():
        for journey_id in story["journey_ids"]:
            if not set(story["persona_ids"]) <= set(journeys[journey_id]["persona_ids"]):
                gaps["readiness.persona_outside_journey"].add(f"{story['id']} {journey_id}")
    for component in model.by_kind["component"].values():
        if component["proposal"] is not None:
            gaps["readiness.proposal_unconfirmed"].add(component["id"])
    for entry in model.partition["entries"]:
        if entry["proposed_by"] is not None:
            gaps["readiness.proposal_unconfirmed"].add(entry["issue"])
    gaps["readiness.ticket_unresolved"].update(model.unresolved)
    gaps["readiness.post_snapshot_issue"].update(model.partition["post_snapshot_issues"])
    return {rule: sorted(subjects, key=natural_key) for rule, subjects in gaps.items()}


def structure_line(model):
    registry, flows = model.registry, model.flows
    frontend = sum(entry["disposition"] == "frontend" for entry in model.partition["entries"])
    return (
        f"Experience coverage {registry['registry_version']} structure valid: {len(registry['personas'])} personas, "
        f"{len(registry['journeys'])} journeys, {len(registry['user_stories'])} user stories, {len(flows)} flows "
        f"({sum(flow['critical'] for flow in flows.values())} critical), {len(model.screens)} screens, "
        f"{len(registry['components'])} components, {len(registry['diagrams'])} diagrams, "
        f"{len(registry['id_ledger'])} ledger IDs checked against the {model.ledger_base}; "
        f"{len(model.partition['entries'])} client issues partitioned ({frontend} frontend, "
        f"{len(model.partition['entries']) - frontend} non-frontend); registry checksum "
        f"{registry_checksum(registry)}"
    )


def basis_points(count, total):
    return count * 10000 // total if total else 0


def _table(header, alignment, rows):
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(alignment) + " |"]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return lines


def _coverage(screens):
    with_d6 = sum(not lacks_d6(screen) for screen in screens)
    with_route = sum(screen["route_id"] is not None for screen in screens)
    total = len(screens)
    return [total, with_d6, basis_points(with_d6, total), with_route, basis_points(with_route, total)]


def _owner_rows(groups):
    def order(item):
        issue, plan_id = item[0]
        return (0, natural_key(issue)) if issue is not None else (1, [(2, 0, 0, 0, plan_id or "")])
    rows = []
    for (issue, plan_id), screens in sorted(groups.items(), key=order):
        owner = f"`{issue}`" if issue is not None else "unresolved"
        rows.append([owner, f"`{plan_id}`" if plan_id else "none", *_coverage(screens)])
    return rows


def render_summary(model, gaps):
    """Deterministic D20 markdown: IDs, rule names and integers only; no titles, names or timestamps."""
    registry, partition = model.registry, model.partition
    screens = list(model.screens.values())
    complete = not any(gaps.values())
    coverage = ["Screens", "With D6 and handoff", "D6 bp", "With route ID", "Route bp"]
    aligned = ["---:"] * len(coverage)
    lines = [
        GREEN if complete else NOT_GREEN,
        "",
        "# Experience coverage summary (D20)",
        "",
        f"Generated from `{REGISTRY}` and `{PARTITION}` by",
        "`python scripts/check_experience_coverage.py --write-summary`. Never edit this file by hand: the default",
        "mode, `--check-summary` and `scripts/tests/test_experience_coverage.py` compare it byte for byte.",
        "Counts are integers and coverage is in basis points (10000 = 100 percent, rounded down). A present D6",
        "dependency, handoff reference or route ID is a recorded reference, not a gate closure or an approval.",
        "",
    ]
    ledger = registry["id_ledger"]
    reference = registry["imported_from"]
    lines += _table(["Registry", "Value"], ["---", "---"], [
        ["Registry version", f"`{registry['registry_version']}`"],
        ["Schema version", f"`{registry['schema_version']}`"],
        ["Registry checksum", f"`{registry_checksum(registry)}`"],
        ["Imported from", f"`{reference['path']}` at `{reference['commit']}`"],
        ["Ledger", f"{sum(e['status'] == 'active' for e in ledger)} active, "
                   f"{sum(e['status'] == 'retired' for e in ledger)} retired"],
    ])
    lines += ["", "## Readiness gaps", ""]
    lines += _table(["Rule", "Gaps"], ["---", "---:"], [[f"`{rule}`", len(gaps[rule])] for rule in READINESS_RULES])
    lines += ["", "## Records", ""]
    rows = []
    for collection, kind in COLLECTIONS:
        entries = [entry for entry in ledger if entry["kind"] == kind]
        rows.append([kind, len(registry[collection]), sum(e["status"] == "active" for e in entries),
                     sum(e["status"] == "retired" for e in entries)])
    lines += _table(["Kind", "Records", "Ledger active", "Ledger retired"], ["---", "---:", "---:", "---:"], rows)
    lines += ["", "## Client-issue partition", ""]
    rows = []
    for repository in CLIENT_REPOSITORIES:
        entries = [entry for entry in partition["entries"] if entry["issue"].split("#")[0] == repository]
        frontend = sum(entry["disposition"] == "frontend" for entry in entries)
        rows.append([f"`{repository}`", len(entries), frontend, len(entries) - frontend,
                     sum(entry["proposed_by"] is not None for entry in entries),
                     sum(issue.split("#")[0] == repository for issue in partition["post_snapshot_issues"])])
    lines += _table(["Repository", "Issues", "Frontend", "Non-frontend", "Awaiting owner confirmation",
                     "Post-snapshot disclosed"], ["---", "---:", "---:", "---:", "---:", "---:"], rows)
    lines += ["", "## Screens by platform", ""]
    lines += _table(["Platform", *coverage], ["---", *aligned], [
        [platform, *_coverage([s for s in screens if s["platform"] == platform])] for platform in PLATFORMS
    ])
    lines += ["", "## Screens by criticality", ""]
    lines += _table(["Criticality", *coverage], ["---", *aligned], [
        [label, *_coverage([s for s in screens if s["critical"] == value])]
        for label, value in (("critical", True), ("standard", False))
    ])
    lines += ["", "## Screens by state", ""]
    lines += _table(["State", *coverage], ["---", *aligned], [
        [f"`{state}`", *_coverage([s for s in screens if state in s["states"]])]
        for state in registry["required_states"]
    ])
    for title, fields in (
        ("design owner", ("design_ticket",)), ("implementation owner", ("implementation_tickets",)),
        ("QA owner", ("qa_ticket",)),
    ):
        groups = defaultdict(list)
        for screen in screens:
            for field in fields:
                value = screen[field]
                for ticket in value if isinstance(value, list) else [value]:
                    groups[(ticket["issue"], ticket["plan_id"])].append(screen)
        lines += ["", f"## Screens by {title}", ""]
        lines += _table([title[0].upper() + title[1:], "Plan ID", *coverage], ["---", "---", *aligned],
                        _owner_rows(groups))
    lines += ["", "## Critical flows by platform", ""]
    rows = []
    for platform in PLATFORMS:
        flows = [flow for flow in model.flows.values() if flow["platform"] == platform]
        critical = [flow for flow in flows if flow["critical"]]
        verified = sum(flow["qa_independence"]["status"] == "verified" for flow in critical)
        rows.append([platform, len(flows), len(critical), verified, basis_points(verified, len(critical))])
    lines += _table(["Platform", "Flows", "Critical", "QA independence verified", "Verified bp"],
                    ["---", "---:", "---:", "---:", "---:"], rows)
    lines += ["", "## Gap identifiers", ""]
    listed = [f"- `{rule}` ({len(gaps[rule])}): " + ", ".join(gaps[rule]) for rule in READINESS_RULES if gaps[rule]]
    lines += listed or ["None."]
    return "\n".join(lines) + "\n"


def load_and_check(root, base=None):
    root = Path(root)
    return check(
        support.load_json(root / REGISTRY), support.load_json(root / PARTITION), support.load_json(root / SCHEMA),
        support.load_json(root / INVENTORY), support.load_json(root / TAXONOMY), GitSources(root, base),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--structure", action="store_true", help="Check structure only; readiness is not evaluated.")
    modes.add_argument("--write-summary", action="store_true", help=f"Regenerate {SUMMARY} from the checked registry.")
    modes.add_argument("--check-summary", action="store_true", help=f"Fail unless {SUMMARY} matches byte for byte.")
    parser.add_argument("--base", help=f"Git revision whose committed registry the ledger must extend "
                                       f"(default: the merge base of HEAD and {BASE_REF}).")
    args = parser.parse_args(argv)
    try:
        model = load_and_check(ROOT, args.base)
        if args.structure:
            print(structure_line(model) + "; readiness not evaluated.")
            return 0
        gaps = readiness(model)
        summary = render_summary(model, gaps)
        status = NOT_GREEN if any(gaps.values()) else GREEN
        if args.write_summary:
            target = ROOT / SUMMARY
            if target.is_symlink():
                raise OSError("refusing to write the summary through a symlink")
            target.write_text(summary, encoding="utf-8", newline="\n")
            print(f"Experience coverage summary written to {SUMMARY} ({status}).")
            return 0
        try:
            current = (ROOT / SUMMARY).read_bytes()
        except OSError:
            current = None
        require(current == summary.encode("utf-8"), "summary.drift")
        if args.check_summary:
            print(f"Experience coverage summary {SUMMARY} matches the registry ({status}).")
            return 0
        print(status)
        print(structure_line(model))
        if status == GREEN:
            return 0
        for rule in READINESS_RULES:
            print(f"{rule}: {len(gaps[rule])}")
        return 1
    except Refused as error:
        print(f"Experience coverage check refused: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, RecursionError):
        # Fail closed without a traceback, whose message could echo input content.
        print("Experience coverage check refused: input.unreadable_or_invalid", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
