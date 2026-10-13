"""Offline T-UXR-04 checks of the journey and service blueprints, their gap register and generated summary.

PenniLogic/docs#67 publishes one service blueprint per registry journey (J01-J12) as
product/journey-blueprints.json and its journey gaps as product/journey-gaps.json, both validated against
product/journey-blueprints.schema.json (a self-contained draft-07 subset), plus the generated, never hand-edited
markdown rendering product/journey-blueprints.md. Journey, persona, flow, screen and diagram identifiers are read
from the experience-coverage registry pinned by `registry_ref` {commit, path, sha256} (TS-M8): until docs#75 is
integrated that is the imported planning registry at docs 1722fc79, read from the local Git object store and
digest-checked. The registry is never edited; its content gaps are recorded as GAP-Jnn-nn entries routed to
their owners.

Blueprint steps Jnn.C.nn and Jnn.T.nn are the customer and team lanes. Every step names its channel, system, data
classification and authorization; the checks below enforce registry joins, lane and channel agreement, reachable
step graphs, failure and recovery coverage, cross-channel handoff authority, rights/sharing/billing controls
(clock, audit, notification, reversal), the backstage boundary (no raw message egress, client-side money
arithmetic or unauthorized detail access), content-free telemetry and abuse paths per journey. Metric references
stay `pending:PenniLogic/docs#77` and event references `pending:<owner issue>`; no EV- or M- identifier is minted.
Persona basis stays provisional until docs#66 evidence exists.

Structure failures raise `Refused` with a static rule identifier plus, at most, identifiers matching a published
grammar; input text is never echoed. Readiness gaps (pending research, approvals, metrics and events, open gaps
without backlog items, held Figma artifacts, the unintegrated registry) are counted, never filled in, and keep the
default mode NOT GREEN. No network, remote action, approval, issue creation or review is made or implied.
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
DATA = "product/journey-blueprints.json"
GAPS = "product/journey-gaps.json"
SCHEMA = "product/journey-blueprints.schema.json"
SUMMARY = "product/journey-blueprints.md"
ADR_DIRECTORY = "adr"
# TS-M8: consumers pin the imported registry on main until docs#75 (draft PR #176) is integrated.
REGISTRY_PIN = {
    "commit": "1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4",
    "path": "planning/source/evidence/experience-coverage.json",
    "sha256": "sha256:2f7b27c1f6683d4c256a938ccfb0fc06614f83fe57996a4d7aeaf0b7cae0bf3a",
}
REGISTRY_ISSUE = "PenniLogic/docs#75"
RESEARCH_ISSUE = "PenniLogic/docs#66"
METRIC_PENDING = "pending:PenniLogic/docs#77"
OWNER_PLAN_ID = "T-UXR-04"
GREEN = "GREEN: readiness complete"
NOT_GREEN = "NOT GREEN: readiness incomplete"
SCRUBBED_GIT_VARIABLES = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR", "GIT_NAMESPACE",
)


def _sibling(name, filename):
    """Load an accepted sibling checker read-only by path, as check_design_gates.py does."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


support = _sibling("journey_schema_support", "check_client_states.py")
gates = _sibling("journey_design_gates", "check_design_gates.py")
strategy = _sibling("journey_test_strategy", "check_test_strategy.py")
INVENTORY = strategy.INVENTORY

# The blueprint-owned diagrams (docs#67 "Owns diagram"); renderings here are markdown text, Figma is held.
OWNED_DIAGRAMS = ("D01", "D03", "D04", "D05", "D21")
APPROVAL_ROLES = ("product", "architecture", "security", "operations", "ia")
BRANCH_KINDS = ("failure", "offline", "timeout", "revocation", "partial", "escalation", "rollback",
                "permission_denied")
SIGNALS = ("completion", "abandonment", "correction", "recovery", "escalation")
# Content-free event shape: identifiers and coded outcomes only, never text, amounts, merchants or contacts.
TELEMETRY_FIELDS = frozenset({"journey_id", "step_id", "signal", "outcome", "reason_code", "platform"})
LANE_CHANNELS = {"customer": frozenset({"android", "web", "notification"}), "team": frozenset({"admin", "service"})}
SURFACES = frozenset({"android", "web", "admin", "notification"})
PLATFORM_CHANNEL = {"AND": "android", "WEB": "web", "ADM": "admin"}
# docs#67 scope: rights, sharing and billing blueprints carry clock, audit, notification and reversal controls.
POLICY_CLASS = {"J06": "sharing", "J07": "sharing", "J09": "billing", "J10": "rights", "J11": "rights"}
BOUNDARY_RULES = (
    ("raw_message_egress", "boundary.raw_message_egress"),
    ("client_money_arithmetic", "boundary.client_money_arithmetic"),
    ("unauthorized_detail_access", "boundary.unauthorized_detail_access"),
)

GRAMMAR = {
    "blueprint": re.compile(r"BP-(J[0-9]{2})"),
    "step": re.compile(r"(J[0-9]{2})\.(C|T)\.([0-9]{2})"),
    "abuse": re.compile(r"AB-(J[0-9]{2})-([0-9]{2})"),
    "gap": re.compile(r"GAP-(J[0-9]{2})-([0-9]{2})"),
    "journey": re.compile(r"J[0-9]{2}"),
    "persona": re.compile(r"P[0-9]{2}"),
    "flow": re.compile(r"F-(AND|WEB|ADM)-[0-9]{2}"),
    "screen": re.compile(r"S-(AND|WEB|ADM)-[0-9]{3}"),
    "diagram": re.compile(r"D[0-9]{2}"),
    "adr": re.compile(r"ADR-[0-9]{3}"),
    "role": re.compile(r"product|architecture|security|operations|ia"),
}
ISSUE_REF = re.compile(
    r"PenniLogic/(" + "|".join(re.escape(name.split("/")[1]) for name in strategy.REPOSITORY_IDS)
    + r")#([1-9][0-9]{0,5})"
)
PENDING_REF = re.compile(r"pending:(" + ISSUE_REF.pattern + r")")
MINTED = re.compile(r"(?:EV|M|G|TH|RT|BM)-")
COMMIT = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
FILE_PATH = re.compile(r"[a-z0-9_.-]+(?:/[a-z0-9_.-]+)*")
TEXT_LIMIT = 400
_CURRENCIES = "INR|USD|EUR|GBP|AED|SGD|AUD|CAD|JPY|CNY|CHF|SAR|QAR|KWD|BHD|OMR|NZD|HKD|ZAR"
CONTENT_SHAPES = (
    # Printable ASCII only, so look-alike digits, at signs or currency signs cannot slip past the shapes below.
    ("content.unprintable_character", re.compile(r"[^\x20-\x7e]")),
    # The summary renders text into markdown tables and mermaid labels; these characters would break out.
    ("content.markup_character", re.compile(r"[|`<>\"\[\]{}\\]")),
    ("content.secret_shape", re.compile(
        r"\bgh[pousr]_[A-Za-z0-9]{8,}|\bgithub_pat_|-----BEGIN|\bAKIA[0-9A-Z]{16}\b|\bxox[abposr]-"
        r"|\bsk-[A-Za-z0-9_-]{20,}|[A-Za-z0-9+=_]{32,}"
    )),
    ("content.url_shape", re.compile(
        r"[A-Za-z][A-Za-z0-9+.-]*://|\bwww\.|\b(?:mailto|javascript|tel|sms|file|intent|ftp):"
        r"|\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:com|org|net|io|co|dev|app|ai|gov|edu|info|me|us|uk|in|xyz)\b",
        re.IGNORECASE,
    )),
    ("content.email_shape", re.compile(r"@")),
    ("content.amount_shape", re.compile(
        r"\$\s*[0-9]|\b(?:" + _CURRENCIES + r"|Rs\.?)\s*[0-9]|[0-9]\s*(?:" + _CURRENCIES + r")\b"
        r"|[0-9]\s*(?:k|lakhs?|lacs?|crores?|cr|rupees?|paise|dollars?|euros?|cents?)\b|[0-9]\s*/-",
        re.IGNORECASE,
    )),
    ("content.phone_shape", re.compile(r"[0-9](?:[^A-Za-z0-9]{0,3}[0-9]){8,}")),
)
# Exact-grammar values exempt from the text scan, at their own paths only.
EXEMPT_PATHS = {
    ("registry_ref", "commit"): COMMIT, ("registry_ref", "sha256"): DIGEST, ("registry_ref", "path"): FILE_PATH,
    ("approvals", "*", "source", "commit"): COMMIT, ("approvals", "*", "source", "sha256"): DIGEST,
    ("approvals", "*", "source", "path"): FILE_PATH,
    ("research_gate", "evidence", "*", "commit"): COMMIT, ("research_gate", "evidence", "*", "sha256"): DIGEST,
    ("research_gate", "evidence", "*", "path"): FILE_PATH,
}
NUMBER_PATHS = frozenset({("schema_version",)})

STRUCTURE_RULES = (
    "input.unreadable_or_invalid", "schema.invalid",
    "content.too_long", "content.blank_or_padded", "content.unprintable_character", "content.markup_character",
    "content.secret_shape", "content.url_shape", "content.email_shape", "content.amount_shape",
    "content.phone_shape", "content.unexpected_number",
    "registry.ref_mismatch", "registry.unavailable", "registry.digest_mismatch", "registry.invalid",
    "inventory.invalid", "id.duplicate",
    "blueprint.journey_mismatch", "blueprint.missing_journey", "blueprint.unknown_journey",
    "blueprint.name_mismatch", "blueprint.persona_mismatch", "blueprint.flow_mismatch",
    "blueprint.audience_mismatch", "blueprint.order",
    "persona.basis_ref", "approval.order", "approval.ia_before_backlog",
    "held.approval", "held.research_evidence", "held.status", "held.persona_basis", "held.backlog_item",
    "held.gap_status",
    "diagram.set_mismatch", "diagram.registry_mismatch",
    "map.supersedes_mismatch", "metric.minted", "metric.ref_not_pending",
    "step.journey_mismatch", "step.lane_mismatch", "step.channel_lane_mismatch", "step.flow_missing",
    "step.flow_on_service", "step.flow_outside_journey", "step.flow_channel_mismatch", "step.screen_missing",
    "step.screen_outside_flow", "step.dangling_next", "step.unreachable", "step.no_terminal",
    "step.service_without_branch", "branch.dangling_target",
    "coverage.flow_without_step", "coverage.critical_flow_unmapped", "coverage.branch_missing",
    "coverage.signal_missing", "coverage.not_applicable_kind", "coverage.not_applicable_contradiction",
    "handoff.missing", "handoff.unexpected",
    "policy.class_mismatch", "policy.controls_missing", "policy.controls_unexpected", "policy.ref_grammar",
    "policy.unknown_adr", "boundary.raw_message_egress", "boundary.client_money_arithmetic",
    "boundary.unauthorized_detail_access", "boundary.restricted_notification",
    "telemetry.content_field", "telemetry.identity_missing",
    "event.minted", "event.ref_grammar", "reference.unknown_issue",
    "moment.dangling_step", "abuse.missing", "abuse.journey_mismatch", "abuse.dangling_step",
    "gap.journey_mismatch", "gap.unknown_journey", "gap.dangling_step", "gap.category_owner",
    "summary.drift",
)
READINESS_RULES = (
    "readiness.registry_unintegrated", "readiness.research_pending", "readiness.persona_provisional",
    "readiness.approval_pending", "readiness.metric_pending", "readiness.event_pending",
    "readiness.gap_open", "readiness.gap_backlog_missing", "readiness.figma_held",
)


def classify(identifier):
    """Return the grammar kind of a published identifier, or None."""
    if not isinstance(identifier, str):
        return None
    for kind, grammar in GRAMMAR.items():
        if grammar.fullmatch(identifier):
            return kind
    return None


def printable(value):
    """Only published identifiers and public issue references may appear in output; everything else is input."""
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
    """Sort subjects by their digits and text, so J02 precedes J10 and S-AND-002 precedes S-AND-010.

    Only the captured ASCII digit runs (odd split positions) are numbers; str.isdigit() would also accept
    non-ASCII digits that int() rejects.
    """
    return [(int(part) if index % 2 else 0, part) for index, part in enumerate(re.split(r"([0-9]+)", subject))]


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


def _schema_subject(error, value):
    """The record ID of the first failing blueprint or gap, when it is a published identifier."""
    match = re.match(r"\$\.(blueprints|gaps)\[([0-9]+)\](?:\.steps\[([0-9]+)\])?", str(error))
    if match is None or not isinstance(value, dict) or not isinstance(value.get(match.group(1)), list):
        return ()
    items, index = value[match.group(1)], int(match.group(2))
    item = items[index] if index < len(items) else None
    candidate = item.get("id") if isinstance(item, dict) else None
    if match.group(3) is not None and isinstance(item, dict) and isinstance(item.get("steps"), list):
        steps, position = item["steps"], int(match.group(3))
        step = steps[position] if position < len(steps) else None
        candidate = step.get("id") if isinstance(step, dict) else None
    return (candidate,) if printable(candidate) else ()


def shape(value, schema, definition=None):
    """Validate with the shared subset validator; its messages echo input, so only a rule and record ID survive."""
    try:
        selected = schema if definition is None else schema["definitions"][definition]
        support.validate_schema(value, selected, schema)
    except (ValueError, KeyError, TypeError, RecursionError, re.error) as error:
        raise Refused("schema.invalid", *_schema_subject(error, value)) from None


def _scan(text, subject):
    require(len(text) <= TEXT_LIMIT, "content.too_long", *subject)
    require(text.strip() == text and text != "", "content.blank_or_padded", *subject)
    for rule, pattern in CONTENT_SHAPES:
        require(pattern.search(text) is None, rule, *subject)


def guard_content(document):
    """Scan every string value and key; only EXEMPT_PATHS values with their exact grammar and NUMBER_PATHS skip."""
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
    """Absolute path of git from absolute PATH entries outside the checked repository (H06's hardened resolution).

    A bare "git" lets the operating system search relative PATH entries and, on Windows, the current directory
    first, so a candidate-local executable could forge the pinned registry.
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

    def __init__(self, root):
        self.root, self.executable = Path(root), None

    def _git(self, *args):
        self.executable = self.executable or trusted_git(self.root)
        env = {key: value for key, value in os.environ.items() if key not in SCRUBBED_GIT_VARIABLES}
        # Objects exactly as stored: no lazy fetch, and no replace refs or grafts that could substitute the bytes.
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


def _records(registry, collection, kind):
    records = registry.get(collection) if isinstance(registry, dict) else None
    require(isinstance(records, list), "registry.invalid")
    indexed = {}
    for record in records:
        identifier = record.get("id") if isinstance(record, dict) else None
        require(classify(identifier) == kind and identifier not in indexed, "registry.invalid")
        indexed[identifier] = record
    return indexed


def _identifiers(record, key, kind):
    values = record.get(key)
    require(isinstance(values, list) and all(classify(value) == kind for value in values)
            and len(set(values)) == len(values), "registry.invalid")
    return values


def read_registry(document, sources, pin):
    """The pinned registry's journeys, flows, screens and diagrams, read at the pinned commit and digest-checked."""
    require(document["registry_ref"] == pin, "registry.ref_mismatch")
    try:
        blob = sources.blob(pin["commit"], pin["path"])
    except LookupError:
        raise Refused("registry.unavailable") from None
    require(isinstance(blob, bytes) and gates.digest(blob) == pin["sha256"], "registry.digest_mismatch")
    try:
        registry = loads(blob)
    except (ValueError, RecursionError):
        raise Refused("registry.invalid") from None
    personas = _records(registry, "personas", "persona")
    journeys = _records(registry, "journeys", "journey")
    flows = _records(registry, "flows", "flow")
    screens = _records(registry, "screens", "screen")
    diagrams = _records(registry, "diagrams", "diagram")
    for journey in journeys.values():
        require(isinstance(journey.get("name"), str) and journey["name"] != "", "registry.invalid")
        require(set(_identifiers(journey, "persona_ids", "persona")) <= set(personas), "registry.invalid")
        require(set(_identifiers(journey, "flow_ids", "flow")) <= set(flows), "registry.invalid")
    for flow in flows.values():
        require(set(_identifiers(flow, "screen_ids", "screen")) <= set(screens), "registry.invalid")
        require(set(_identifiers(flow, "journey_ids", "journey")) <= set(journeys), "registry.invalid")
        require(isinstance(flow.get("critical"), bool), "registry.invalid")
    for diagram in diagrams.values():
        require(isinstance(diagram.get("owner_ticket"), str), "registry.invalid")
    return {"journeys": journeys, "flows": flows, "screens": screens, "diagrams": diagrams}


def inventory_index(inventory):
    """Reuse check_test_strategy.validate_inventory; its messages echo input, so only the rule survives."""
    try:
        return strategy.validate_inventory(inventory)
    except (ValueError, KeyError, TypeError, AttributeError):
        raise Refused("inventory.invalid") from None


class Model:
    """The checked documents with their registry and inventory joins."""

    def __init__(self, document, gaps, registry, issues, adrs):
        self.document, self.gaps, self.registry, self.issues, self.adrs = document, gaps, registry, issues, adrs
        self.blueprints = {blueprint["journey_id"]: blueprint for blueprint in document["blueprints"]}
        self.steps = {step["id"]: step for blueprint in document["blueprints"] for step in blueprint["steps"]}


def check_identifiers(document, gaps):
    """Every blueprint, step, abuse path and gap ID is issued once."""
    seen = set()
    for blueprint in document["blueprints"]:
        for identifier in (blueprint["id"], *(step["id"] for step in blueprint["steps"]),
                           *(abuse["id"] for abuse in blueprint["abuse_paths"])):
            require(identifier not in seen, "id.duplicate", identifier)
            seen.add(identifier)
    for gap in gaps["gaps"]:
        require(gap["id"] not in seen, "id.duplicate", gap["id"])
        seen.add(gap["id"])


def check_header(model):
    document, registry = model.document, model.registry
    approvals = document["approvals"]
    require([approval["role"] for approval in approvals] == list(APPROVAL_ROLES), "approval.order")
    # docs#67 criterion 5: journey gaps create owned backlog items before IA approval.
    unfiled = [gap for gap in model.gaps["gaps"] if gap["status"] == "open" and gap["backlog_item"] is None]
    require(approvals[-1]["status"] == "pending" or not unfiled, "approval.ia_before_backlog", "ia")
    # HC-m13: approvals, research evidence and the validated status are held human inputs. No session here records
    # them and this checker cannot resolve or digest-check a decision or evidence record, so a well-formed source
    # pointer proves nothing: every resolved value is refused rather than trusted (held.*, as H05 and H07 do).
    for approval in approvals:
        require(approval["status"] == "pending" and approval["source"] is None, "held.approval", approval["role"])
    gate = document["research_gate"]
    require(gate["status"] == "pending" and not gate["evidence"], "held.research_evidence", RESEARCH_ISSUE)
    require(document["status"] == "provisional", "held.status")
    require([diagram["id"] for diagram in document["diagrams"]] == list(OWNED_DIAGRAMS), "diagram.set_mismatch")
    for identifier in OWNED_DIAGRAMS:
        record = registry["diagrams"].get(identifier)
        require(record is not None and record["owner_ticket"] == OWNER_PLAN_ID, "diagram.registry_mismatch",
                identifier)


def _flow_platform(flow_id):
    return PLATFORM_CHANNEL[flow_id.split("-")[1]]


def check_blueprint(model, blueprint):
    journey_id, identifier = blueprint["journey_id"], blueprint["id"]
    require(GRAMMAR["blueprint"].fullmatch(identifier).group(1) == journey_id, "blueprint.journey_mismatch",
            identifier)
    journey = model.registry["journeys"].get(journey_id)
    require(journey is not None, "blueprint.unknown_journey", identifier)
    require(blueprint["journey_name"] == journey["name"], "blueprint.name_mismatch", identifier)
    require(set(blueprint["persona_ids"]) == set(journey["persona_ids"]), "blueprint.persona_mismatch", identifier)
    require(set(blueprint["flow_ids"]) == set(journey["flow_ids"]), "blueprint.flow_mismatch", identifier)
    operator = all(_flow_platform(flow_id) == "admin" for flow_id in journey["flow_ids"])
    require(blueprint["audience"] == ("operator" if operator else "customer"), "blueprint.audience_mismatch",
            identifier)
    # Personas stay planning hypotheses until docs#66 evidence exists; a validated basis is a held input.
    require(blueprint["persona_basis"] == "provisional", "held.persona_basis", identifier)
    require(blueprint["persona_basis_ref"] == "pending:" + RESEARCH_ISSUE, "persona.basis_ref", identifier)
    require(blueprint["target_map"]["supersedes"] == f"{identifier}.current_map", "map.supersedes_mismatch",
            identifier)
    metric = blueprint["outcome"]["metric_ref"]
    # docs#77 owns M-/G-/TH-/EV- identifiers; until it publishes them, the reference stays pending.
    require(MINTED.match(metric) is None, "metric.minted", identifier)
    require(metric == METRIC_PENDING, "metric.ref_not_pending", identifier)
    require(blueprint["policy_class"] == POLICY_CLASS.get(journey_id), "policy.class_mismatch", identifier)


def check_blueprints(model):
    order = [blueprint["journey_id"] for blueprint in model.document["blueprints"]]
    for blueprint in model.document["blueprints"]:
        check_blueprint(model, blueprint)
    for journey_id in sorted(model.registry["journeys"], key=natural_key):
        require(journey_id in model.blueprints, "blueprint.missing_journey", journey_id)
    require(order == sorted(order, key=natural_key), "blueprint.order")


def check_reference(model, value, minted_rule, grammar_rule, subject, adr_ok=False):
    """A pending owner-issue reference (or, for policies, an accepted ADR); never a minted outcome ID."""
    if minted_rule is not None:
        require(MINTED.match(value) is None, minted_rule, subject)
    if adr_ok and GRAMMAR["adr"].fullmatch(value):
        require(value in model.adrs, "policy.unknown_adr", subject, value)
        return
    match = PENDING_REF.fullmatch(value)
    require(match is not None, grammar_rule, subject)
    require(match.group(1) in model.issues, "reference.unknown_issue", subject, match.group(1))


def check_step(model, blueprint, step):
    identifier, journey_id = step["id"], blueprint["journey_id"]
    journey_part, lane_letter, _ = GRAMMAR["step"].fullmatch(identifier).groups()
    require(journey_part == journey_id, "step.journey_mismatch", identifier)
    require(lane_letter == step["lane"][0].upper(), "step.lane_mismatch", identifier)
    channel = step["channel"]
    require(channel in LANE_CHANNELS[step["lane"]], "step.channel_lane_mismatch", identifier)
    flow_id = step["flow_id"]
    if channel in PLATFORM_CHANNEL.values():
        require(flow_id is not None, "step.flow_missing", identifier)
    if channel == "service":
        require(flow_id is None, "step.flow_on_service", identifier)
    flow_screens = set()
    if flow_id is not None:
        require(flow_id in blueprint["flow_ids"], "step.flow_outside_journey", identifier, flow_id)
        require(channel == "notification" or _flow_platform(flow_id) == channel, "step.flow_channel_mismatch",
                identifier, flow_id)
        flow_screens = set(model.registry["flows"][flow_id]["screen_ids"])
    if channel in PLATFORM_CHANNEL.values():
        require(step["screen_ids"], "step.screen_missing", identifier)
    for screen_id in step["screen_ids"]:
        require(screen_id in flow_screens, "step.screen_outside_flow", identifier, screen_id)
    own = {item["id"] for item in blueprint["steps"]}
    for target in step["next"]:
        require(target in own, "step.dangling_next", identifier)
    for branch in step["branches"]:
        require(branch["to"] is None or branch["to"] in own, "branch.dangling_target", identifier)
    # A backstage service step can fail; its failure and recovery path is part of the blueprint.
    require(channel != "service" or step["branches"], "step.service_without_branch", identifier)
    for field, rule in BOUNDARY_RULES:
        require(step["boundary"][field] is False, rule, identifier)
    require(not (channel == "notification" and step["data_class"] == "restricted"), "boundary.restricted_notification",
            identifier)
    telemetry = step["telemetry"]
    if telemetry is not None:
        require(set(telemetry["fields"]) <= TELEMETRY_FIELDS, "telemetry.content_field", identifier)
        require({"journey_id", "step_id"} <= set(telemetry["fields"]), "telemetry.identity_missing", identifier)
    for value in step["event_refs"]:
        check_reference(model, value, "event.minted", "event.ref_grammar", identifier)
    for value in step["policy_refs"]:
        check_reference(model, value, None, "policy.ref_grammar", identifier, adr_ok=True)
    require(step["controls"] is None or blueprint["policy_class"] is not None, "policy.controls_unexpected",
            identifier)


def _edges(blueprint):
    for step in blueprint["steps"]:
        for target in step["next"]:
            yield step["id"], target
        for branch in step["branches"]:
            if branch["to"] is not None:
                yield step["id"], branch["to"]


def check_graph(blueprint):
    """Reachability from the first step, at least one terminal step and cross-channel handoff authority."""
    steps = {step["id"]: step for step in blueprint["steps"]}
    successors = defaultdict(set)
    for source, target in _edges(blueprint):
        successors[source].add(target)
    reached, frontier = set(), [blueprint["steps"][0]["id"]]
    while frontier:
        current = frontier.pop()
        if current not in reached:
            reached.add(current)
            frontier.extend(successors[current])
    for identifier in steps:
        require(identifier in reached, "step.unreachable", identifier)
    require(any(not step["next"] for step in blueprint["steps"]), "step.no_terminal", blueprint["id"])
    crossing = {target for source, target in _edges(blueprint)
                if steps[source]["channel"] != steps[target]["channel"] and steps[target]["channel"] in SURFACES}
    for identifier, step in steps.items():
        # The receiving surface names the authoritative service and what it may safely show.
        require(identifier not in crossing or step["handoff"] is not None, "handoff.missing", identifier)
        require(identifier in crossing or step["handoff"] is None, "handoff.unexpected", identifier)


def check_coverage(model, blueprint):
    """Flow use, failure branches, signals, moments of truth, abuse paths and policy controls of one journey."""
    identifier, steps = blueprint["id"], blueprint["steps"]
    own = {step["id"] for step in steps}
    used = {step["flow_id"] for step in steps}
    for flow_id in blueprint["flow_ids"]:
        require(flow_id in used, "coverage.flow_without_step", identifier, flow_id)
    present = {
        "branch": {branch["kind"] for step in steps for branch in step["branches"]},
        "signal": {step["telemetry"]["signal"] for step in steps if step["telemetry"] is not None},
    }
    declared = {"branch": set(), "signal": set()}
    for entry in blueprint["not_applicable"]:
        scope, kind = entry["scope"], entry["kind"]
        require(kind in (BRANCH_KINDS if scope == "branch" else SIGNALS), "coverage.not_applicable_kind", identifier)
        require(kind not in present[scope] and kind not in declared[scope], "coverage.not_applicable_contradiction",
                identifier)
        declared[scope].add(kind)
    for scope, kinds, rule in (("branch", BRANCH_KINDS, "coverage.branch_missing"),
                               ("signal", SIGNALS, "coverage.signal_missing")):
        for kind in kinds:
            require(kind in present[scope] or kind in declared[scope], rule, identifier)
    for moment in blueprint["moments_of_truth"]:
        require(moment["step_id"] in own, "moment.dangling_step", identifier)
    # docs#67: household and operator journeys model uncooperative actors; every journey here carries one.
    require(blueprint["abuse_paths"], "abuse.missing", identifier)
    for abuse in blueprint["abuse_paths"]:
        require(GRAMMAR["abuse"].fullmatch(abuse["id"]).group(1) == blueprint["journey_id"], "abuse.journey_mismatch",
                abuse["id"])
        require(abuse["step_id"] in own, "abuse.dangling_step", abuse["id"])
    if blueprint["policy_class"] is not None:
        require(any(step["controls"] is not None for step in steps), "policy.controls_missing", identifier)


def check_registry_coverage(model):
    """Every critical registry flow belongs to a blueprinted journey (docs#67 criterion 1)."""
    mapped = {flow_id for blueprint in model.document["blueprints"] for flow_id in blueprint["flow_ids"]}
    for flow_id in sorted(model.registry["flows"], key=natural_key):
        if model.registry["flows"][flow_id]["critical"]:
            require(flow_id in mapped, "coverage.critical_flow_unmapped", flow_id)


GAP_OWNERS = {"registry_content": REGISTRY_ISSUE, "research": RESEARCH_ISSUE, "metric": "PenniLogic/docs#77"}


def check_gaps(model):
    """Gaps are routed to an inventory issue that owns them; registry, research and metric gaps to their owner."""
    for gap in model.gaps["gaps"]:
        identifier, journey_id = gap["id"], gap["journey_id"]
        require(GRAMMAR["gap"].fullmatch(identifier).group(1) == journey_id, "gap.journey_mismatch", identifier)
        require(journey_id in model.blueprints, "gap.unknown_journey", identifier)
        if gap["step_id"] is not None:
            own = {step["id"] for step in model.blueprints[journey_id]["steps"]}
            require(gap["step_id"] in own, "gap.dangling_step", identifier)
        require(gap["owner_issue"] in model.issues, "reference.unknown_issue", identifier, gap["owner_issue"])
        expected = GAP_OWNERS.get(gap["category"])
        require(expected is None or gap["owner_issue"] == expected, "gap.category_owner", identifier)
        # HC-m10: creating a backlog issue is an owner-approved mutation outside this change, and any inventory
        # issue (the gap's own owner, docs#67 itself, a closed issue) would otherwise clear criterion 5.
        require(gap["backlog_item"] is None, "held.backlog_item", identifier)
        require(gap["status"] == "open", "held.gap_status", identifier)


def check(document, gaps, schema, inventory, adrs, sources, pin=None):
    """Run every structure rule in a fixed order; raise Refused at the first violation, else return the model."""
    shape(document, schema)
    shape(gaps, schema, "gaps_document")
    guard_content(document)
    guard_content(gaps)
    registry = read_registry(document, sources, REGISTRY_PIN if pin is None else pin)
    model = Model(document, gaps, registry, inventory_index(inventory), frozenset(adrs))
    check_identifiers(document, gaps)
    check_header(model)
    check_blueprints(model)
    for blueprint in document["blueprints"]:
        for step in blueprint["steps"]:
            check_step(model, blueprint, step)
        check_graph(blueprint)
        check_coverage(model, blueprint)
    check_registry_coverage(model)
    check_gaps(model)
    return model


def readiness(model):
    """Every visible gap by static rule: sorted, de-duplicated subjects; never filled in or waived."""
    document, gaps = model.document, {rule: set() for rule in READINESS_RULES}
    if document["registry_ref"]["path"] == REGISTRY_PIN["path"]:
        gaps["readiness.registry_unintegrated"].add(REGISTRY_ISSUE)
    if document["research_gate"]["status"] != "complete":
        gaps["readiness.research_pending"].add(RESEARCH_ISSUE)
    for approval in document["approvals"]:
        if approval["status"] != "recorded":
            gaps["readiness.approval_pending"].add(approval["role"])
    for blueprint in document["blueprints"]:
        if blueprint["persona_basis"] != "validated":
            gaps["readiness.persona_provisional"].add(blueprint["journey_id"])
        if blueprint["outcome"]["metric_ref"].startswith("pending:"):
            gaps["readiness.metric_pending"].add(blueprint["journey_id"])
        for step in blueprint["steps"]:
            if any(value.startswith("pending:") for value in step["event_refs"]):
                gaps["readiness.event_pending"].add(step["id"])
    for gap in model.gaps["gaps"]:
        if gap["status"] == "open":
            gaps["readiness.gap_open"].add(gap["id"])
            # docs#67 criterion 5: gaps create owned backlog items before IA approval; none is created here.
            if gap["backlog_item"] is None:
                gaps["readiness.gap_backlog_missing"].add(gap["id"])
    for diagram in document["diagrams"]:
        if diagram["figma"] == "held":
            gaps["readiness.figma_held"].add(diagram["id"])
    return {rule: sorted(subjects, key=natural_key) for rule, subjects in gaps.items()}


def reopen_index(model):
    """Which blueprints a service, contract-event owner or policy change reopens (and only those)."""
    index = {"system": defaultdict(set), "event": defaultdict(set), "policy": defaultdict(set)}
    for blueprint in model.document["blueprints"]:
        for step in blueprint["steps"]:
            index["system"][step["system"]].add(blueprint["id"])
            if step["handoff"] is not None:
                index["system"][step["handoff"]["authoritative_service"]].add(blueprint["id"])
            for value in step["event_refs"]:
                index["event"][value].add(blueprint["id"])
            for value in step["policy_refs"]:
                index["policy"][value].add(blueprint["id"])
    return {kind: {key: sorted(values, key=natural_key) for key, values in sorted(entries.items())}
            for kind, entries in index.items()}


def structure_line(model):
    blueprints = model.document["blueprints"]
    steps = [step for blueprint in blueprints for step in blueprint["steps"]]
    return (
        f"Journey blueprints {model.document['blueprint_version']} structure valid: {len(blueprints)} blueprints, "
        f"{len(steps)} steps ({sum(step['lane'] == 'customer' for step in steps)} customer, "
        f"{sum(step['lane'] == 'team' for step in steps)} team), "
        f"{sum(len(step['branches']) for step in steps)} branches, "
        f"{sum(len(blueprint['abuse_paths']) for blueprint in blueprints)} abuse paths, "
        f"{len(model.gaps['gaps'])} gaps; registry {model.document['registry_ref']['commit']} checked"
    )


def _table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines + [""]


def _list(values):
    return ", ".join(values) if values else "none"


def _node(step_id):
    return step_id.replace(".", "_")


def _mermaid_steps(blueprint):
    """Text rendering of one blueprint: lanes as subgraphs, next edges solid, branch edges labelled by kind."""
    lines = ["```mermaid", "flowchart LR"]
    for lane in ("customer", "team"):
        members = [step for step in blueprint["steps"] if step["lane"] == lane]
        if members:
            lines.append(f"    subgraph {lane}[{lane} lane]")
            lines += [f'        {_node(step["id"])}["{step["id"]} {step["channel"]}: {step["action"]}"]'
                      for step in members]
            lines.append("    end")
    for step in blueprint["steps"]:
        lines += [f"    {_node(step['id'])} --> {_node(target)}" for target in step["next"]]
        lines += [f"    {_node(step['id'])} -. {branch['kind']} .-> {_node(branch['to'])}"
                  for branch in step["branches"] if branch["to"] is not None]
    return lines + ["```", ""]


def _ecosystem(model):
    """D01 text rendering: which channels reach which systems, derived from every blueprint step."""
    pairs = sorted({(step["channel"], step["system"]) for step in model.steps.values()})
    lines = ["```mermaid", "flowchart LR"]
    for channel in sorted({channel for channel, _ in pairs}):
        lines.append(f'    channel_{channel}["{channel} channel"]')
    for system in sorted({system for _, system in pairs}):
        lines.append(f'    system_{system.replace("-", "_")}["{system}"]')
    lines += [f"    channel_{channel} --> system_{system.replace('-', '_')}" for channel, system in pairs]
    return lines + ["```", ""]


def _blueprint_section(model, blueprint):
    identifier = blueprint["id"]
    lines = [f"### {identifier} {blueprint['journey_name']}", ""]
    lines += [f"- Journey {blueprint['journey_id']}, {blueprint['audience']} audience; personas "
              f"{_list(blueprint['persona_ids'])} ({blueprint['persona_basis']}, {blueprint['persona_basis_ref']}).",
              f"- Flows: {_list(blueprint['flow_ids'])}. Diagrams: {_list(blueprint['diagram_ids'])}. Policy class: "
              f"{blueprint['policy_class'] or 'none'}.",
              f"- Success: {blueprint['outcome']['success']}",
              f"- Failure recovery: {blueprint['outcome']['failure_recovery']}",
              f"- Metric: {blueprint['outcome']['metric_ref']}",
              f"- Current map ({blueprint['current_map']['basis']}): {blueprint['current_map']['summary']}",
              f"- Target map (supersedes {blueprint['target_map']['supersedes']}): {blueprint['target_map']['summary']}",
              ""]
    lines += ["Moments of truth:", ""]
    lines += [f"- {moment['step_id']}: {moment['statement']}" for moment in blueprint["moments_of_truth"]] + [""]
    lines += _mermaid_steps(blueprint)
    lines += _table(("Step", "Lane", "Channel", "System", "Actor", "Action", "Flow", "Screens", "Data",
                     "Authorization", "Events", "Policies", "Signal"), [
        (step["id"], step["lane"], step["channel"], step["system"], step["actor"], step["action"],
         step["flow_id"] or "none", _list(step["screen_ids"]), step["data_class"], step["authorization"],
         _list(step["event_refs"]), _list(step["policy_refs"]),
         step["telemetry"]["signal"] if step["telemetry"] else "none")
        for step in blueprint["steps"]])
    lines += _table(("Step", "Branch", "To", "Recovery", "Recovery owner"), [
        (step["id"], branch["kind"], branch["to"] or "terminal", branch["recovery"], branch["recovery_owner"])
        for step in blueprint["steps"] for branch in step["branches"]])
    handoffs = [(step["id"], step["handoff"]["authoritative_service"], step["handoff"]["may_show"])
                for step in blueprint["steps"] if step["handoff"] is not None]
    if handoffs:
        lines += _table(("Receiving step", "Authoritative service", "Receiving surface may show"), handoffs)
    controls = [(step["id"], step["controls"]["clock"], step["controls"]["audit"], step["controls"]["notification"],
                 step["controls"]["reversal"]) for step in blueprint["steps"] if step["controls"] is not None]
    if controls:
        lines += _table(("Step", "Clock", "Audit", "Notification", "Reversal"), controls)
    lines += _table(("Abuse path", "Step", "Actor", "Threat", "Safe failure"), [
        (abuse["id"], abuse["step_id"], abuse["actor"], abuse["threat"], abuse["safe_failure"])
        for abuse in blueprint["abuse_paths"]])
    if blueprint["not_applicable"]:
        lines += _table(("Not applicable", "Kind", "Reason"), [
            (entry["scope"], entry["kind"], entry["reason"]) for entry in blueprint["not_applicable"]])
    return lines


def render_summary(model, gaps):
    """The generated markdown rendering; deterministic, LF, no timestamps or issue titles."""
    document, pin = model.document, model.document["registry_ref"]
    status = NOT_GREEN if any(gaps.values()) else GREEN
    lines = [
        "# PenniLogic journey and service blueprints", "",
        f"<!-- Generated by scripts/check_journeys.py --write-summary from {DATA} and {GAPS}; do not edit. -->", "",
        f"Blueprint version {document['blueprint_version']} ({document['status']}) for {document['source_issue']} "
        f"({document['plan_id']}). Readiness: {status}.", "",
        f"Registry pin: commit {pin['commit']}, path {pin['path']}, {pin['sha256']}.", "",
        "Personas are planning hypotheses, not research evidence: every persona basis stays provisional until "
        f"{RESEARCH_ISSUE} evidence exists. Metric references stay pending on PenniLogic/docs#77 and event "
        "references pending on their owner issues. Diagrams here are markdown text renderings; their Figma "
        "artifacts are held. No approval, review, tabletop or backlog issue is recorded by this file.", "",
        "## Readiness gaps", "",
    ]
    lines += _table(("Rule", "Count", "Subjects"), [
        (rule, str(len(gaps[rule])), _list(gaps[rule])) for rule in READINESS_RULES])
    lines += ["## Approvals and research gate", ""]
    lines += _table(("Role", "Status"), [(item["role"], item["status"]) for item in document["approvals"]])
    lines += [f"Research gate {document['research_gate']['issue']}: {document['research_gate']['status']}, "
              f"{len(document['research_gate']['evidence'])} evidence records.", ""]
    lines += ["## Diagram renderings", ""]
    lines += _table(("Diagram", "Rendering", "Figma"), [
        (diagram["id"], diagram["rendering"], diagram["figma"]) for diagram in document["diagrams"]])
    lines += ["### D01 experience ecosystem (text rendering)", ""] + _ecosystem(model)
    lines += ["### D03 current and target journey map set (text rendering)", ""]
    lines += _table(("Blueprint", "Journey", "Audience", "Current map", "Target map", "Success", "Failure recovery"), [
        (blueprint["id"], blueprint["journey_id"], blueprint["audience"], blueprint["current_map"]["summary"],
         blueprint["target_map"]["summary"], blueprint["outcome"]["success"], blueprint["outcome"]["failure_recovery"])
        for blueprint in document["blueprints"]])
    lines += ["### D21 critical journey task flow and wireflow index (text rendering)", ""]
    rows = []
    for blueprint in document["blueprints"]:
        for flow_id in blueprint["flow_ids"]:
            steps = [step for step in blueprint["steps"] if step["flow_id"] == flow_id]
            screens = sorted({screen for step in steps for screen in step["screen_ids"]}, key=natural_key)
            rows.append((blueprint["journey_id"], flow_id, _list([step["id"] for step in steps]), _list(screens)))
    lines += _table(("Journey", "Flow", "Steps", "Screens"), rows)
    lines += ["D04 and D05 are the text renderings of the blueprints that list them below.", "",
              "## Blueprints", ""]
    for blueprint in document["blueprints"]:
        lines += _blueprint_section(model, blueprint)
    lines += ["## Reopen index", "",
              "A change to a system, an event owner or a policy reopens only the blueprints listed for it.", ""]
    index = reopen_index(model)
    lines += _table(("Kind", "Reference", "Blueprints"), [
        (kind, key, _list(values)) for kind in ("system", "event", "policy") for key, values in index[kind].items()])
    lines += ["## Journey gaps", ""]
    lines += _table(("Gap", "Journey", "Step", "Category", "Owner", "Backlog item", "Status", "Summary"), [
        (gap["id"], gap["journey_id"], gap["step_id"] or "none", gap["category"], gap["owner_issue"],
         gap["backlog_item"] or "none", gap["status"], gap["summary"]) for gap in model.gaps["gaps"]])
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def adr_identifiers(root):
    return frozenset(path.stem for path in (Path(root) / ADR_DIRECTORY).glob("ADR-[0-9][0-9][0-9].md"))


def repository_file(root, relative):
    """The file at a fixed relative path, refusing a symlink at any component below the root or any path that
    resolves outside it, so a planted link cannot redirect a read or the summary write (fail closed)."""
    root, current = Path(root), Path(root)
    for part in Path(relative).parts:
        current = current / part
        require(not current.is_symlink(), "input.unreadable_or_invalid")
    require(root.resolve() in current.resolve().parents, "input.unreadable_or_invalid")
    return current


def load_and_check(root):
    root = Path(root)
    data, gaps, schema, inventory = (support.load_json(repository_file(root, relative))
                                     for relative in (DATA, GAPS, SCHEMA, INVENTORY))
    return check(data, gaps, schema, inventory, adr_identifiers(root), GitSources(root))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--structure", action="store_true", help="Check structure only; readiness is not evaluated.")
    modes.add_argument("--write-summary", action="store_true", help=f"Regenerate {SUMMARY} from the checked data.")
    modes.add_argument("--check-summary", action="store_true", help=f"Fail unless {SUMMARY} matches byte for byte.")
    args = parser.parse_args(argv)
    try:
        model = load_and_check(ROOT)
        if args.structure:
            print(structure_line(model) + "; readiness not evaluated.")
            return 0
        gaps = readiness(model)
        summary = render_summary(model, gaps)
        status = NOT_GREEN if any(gaps.values()) else GREEN
        if args.write_summary:
            repository_file(ROOT, SUMMARY).write_text(summary, encoding="utf-8", newline="\n")
            print(f"Journey blueprint summary written to {SUMMARY} ({status}).")
            return 0
        try:
            current = repository_file(ROOT, SUMMARY).read_bytes()
        except OSError:
            current = None
        require(current == summary.encode("utf-8"), "summary.drift")
        if args.check_summary:
            print(f"Journey blueprint summary {SUMMARY} matches the data ({status}).")
            return 0
        print(status)
        print(structure_line(model))
        if status == GREEN:
            return 0
        for rule in READINESS_RULES:
            print(f"{rule}: {len(gaps[rule])}")
        return 1
    except Refused as error:
        print(f"Journey blueprint check refused: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, RecursionError, re.error):
        # Fail closed without a traceback, whose message could echo input content.
        print("Journey blueprint check refused: input.unreadable_or_invalid", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
