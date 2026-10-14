"""Offline T-UXR-05 checks of the provisional route topology, platform allocation and generated sitemaps.

PenniLogic/docs#74 publishes the Android, customer-web and admin route trees with their screen placements, deep-link
patterns, redirects, role access, research and decision status as product/navigation/routes.json and the D19
capability allocation as product/navigation/platform-allocation.json (each validated against its own
self-contained draft-07 subset schema), plus the generated provisional sitemaps product/navigation/sitemaps.md.
Both data files pin the experience-coverage registry they place by `registry_ref` {commit, path, sha256}, the
design-gates `source` shape; the pinned blob is read through a trusted absolute Git (no PATH or current-directory
lookup, no replace refs or grafts, no lazy fetch). Every structure rule runs against that pinned blob, so a later
registry change never breaks this check: screen, flow and journey IDs added to or retired from the working-tree
registry are readiness gaps, and moving the pin is this ticket's own change.

Structure failures raise `Refused` with a static rule identifier plus, at most, identifiers that match a known
grammar (route, screen, flow, journey, capability or role IDs, docs issue references) or the fixed platform
and decision vocabulary; input text is never echoed. Values that need a human or another ticket (IA, Security,
Accessibility and CDO decisions, tree-test and card-sort evidence, H04 `nav.` message keys, an accepted operator-role
vocabulary, docs#66/docs#67 persona and blueprint validation) are refused when filled in (`held.*`) and counted as
readiness gaps while empty, so the default mode stays NOT GREEN. Everything runs offline against local files and the
local Git object store: no network, remote action, approval, research or review is made or implied.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ROUTES = "product/navigation/routes.json"
ROUTES_SCHEMA = "product/navigation/routes.schema.json"
ALLOCATION = "product/navigation/platform-allocation.json"
ALLOCATION_SCHEMA = "product/navigation/platform-allocation.schema.json"
SITEMAPS = "product/navigation/sitemaps.md"
# The imported planning registry (unchanged on main) and the docs#75 canonical registry once it is integrated.
IMPORT_PATH = "planning/source/evidence/experience-coverage.json"
CANONICAL_PATH = "product/experience-coverage.json"
REGISTRY_PATHS = (IMPORT_PATH, CANONICAL_PATH)
REGISTRY_ISSUE = "PenniLogic/docs#75"
# The full remote-tracking ref: a local branch named origin/main must not shadow it.
BASE_REF = "refs/remotes/origin/main"
GREEN = "GREEN: readiness complete"
NOT_GREEN = "NOT GREEN: readiness incomplete"


def _sibling(name, filename):
    """Load an accepted sibling checker read-only by path, as check_design_gates.py does."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


support = _sibling("navigation_schema_support", "check_client_states.py")
gates = _sibling("navigation_design_gates", "check_design_gates.py")

PLATFORMS = ("android", "web", "admin")
INFIX = {"AND": "android", "WEB": "web", "ADM": "admin"}
DECISIONS = ("information_architecture", "security", "accessibility")
ROUTE_ID = re.compile(r"R-(AND|WEB|ADM)-([0-9]{3})")
SCREEN_ID = re.compile(r"S-(AND|WEB|ADM)-([0-9]{3})")
FLOW_ID = re.compile(r"F-(AND|WEB|ADM)-([0-9]{2})")
JOURNEY_ID = re.compile(r"J[0-9]{2}")
SYNTHETIC_ROLE = re.compile(r"ROLE-SYN-[0-9]{2}")
IDENTIFIER = re.compile(
    r"R-(?:AND|WEB|ADM)-[0-9]{3}|S-(?:AND|WEB|ADM)-[0-9]{3}|F-(?:AND|WEB|ADM)-[0-9]{2}|J[0-9]{2}"
    r"|CAP-[0-9]{3}|ROLE-(?:SYN-)?[0-9]{2}|PenniLogic/docs#[1-9][0-9]{0,5}"
)
VOCABULARY = frozenset(PLATFORMS + DECISIONS)
COMMIT = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
# Letters-only path segments: a pattern names a place, never an identifier, amount or token.
_SEGMENT = r"[a-z]+(?:-[a-z]+)*"
_ELEMENT = rf"(?:{_SEGMENT}|:{_SEGMENT})"
DEEP_LINKS = {
    "android": re.compile(rf"android://{_SEGMENT}(?:/{_ELEMENT})*"),
    "web": re.compile(rf"/{_ELEMENT}(?:/{_ELEMENT})*(?:/\*)?|/"),
    "admin": re.compile(rf"/{_ELEMENT}(?:/{_ELEMENT})*(?:/\*)?"),
}
# A launcher widget's surface (the registry's android-widget:// hints): an external widget entry's only grammar.
WIDGET_LINK = re.compile(rf"android-widget://{_SEGMENT}(?:/{_ELEMENT})*")
# Imported registry hints (H06 grammar): Android and widget deep links or web/admin paths.
ROUTE_HINT = re.compile(rf"(?:android|android-widget)://{_SEGMENT}(?:/{_ELEMENT})*|/{_ELEMENT}(?:/{_ELEMENT})*(?:/\*)?")
PATTERN_LIMIT = 120
# Accepted sources a provisional operator role may be derived from (ADR-020 and the product documents).
ROLE_SOURCES = ("adr/ADR-020.md", "product/01-product-spec.md", "product/08-experience-design-and-sdlc-plan.md")
SCRUBBED_GIT_VARIABLES = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR", "GIT_NAMESPACE",
)

STRUCTURE_RULES = (
    "input.unreadable_or_invalid", "schema.invalid",
    "content.too_long", "content.blank_or_padded", "content.unprintable_character", "content.secret_shape",
    "content.url_shape", "content.email_shape", "content.phone_shape", "content.amount_shape",
    "content.unexpected_number",
    "registry.path_unaccepted", "registry.ref_mismatch", "registry.unavailable", "registry.commit_unpublished",
    "registry.digest_mismatch", "registry.invalid", "registry.current_invalid",
    "id.duplicate", "id.platform_infix_mismatch", "id.out_of_range", "reference.dangling",
    "role.synthetic_reserved", "role.source_unaccepted", "held.role_accepted",
    "route.root_count", "route.parent_dangling", "route.parent_platform_mismatch", "route.audience_widened",
    "route.cycle", "route.entry_mismatch", "route.search_only", "route.empty_leaf", "route.retired_reused",
    "held.label_status", "held.message_key", "label.dynamic_content",
    "presentation.platform_mismatch", "presentation.narrow_hidden", "android.primary_count",
    "android.primary_adaptation", "android.unlisted_primary",
    "access.customer_route_roles", "admin.access_mismatch", "admin.role_unknown", "admin.unauthorized_not_absent",
    "admin.role_wider_than_parent", "admin.external_entry",
    "placement.unknown_screen", "placement.duplicate", "placement.orphan_screen", "placement.route_dangling",
    "placement.platform_mismatch", "placement.host_and_external", "placement.rationale_missing",
    "deep_link.grammar", "deep_link.duplicate_pattern", "deep_link.ambiguous_pattern", "deep_link.hint_unmapped",
    "deep_link.hint_misrouted", "deep_link.redirect_duplicate", "deep_link.redirect_dangling",
    "deep_link.redirect_shadowed",
    "base.unavailable", "base.invalid", "route.id_dropped", "route.retired_dropped", "deep_link.published_changed",
    "deep_link.redirect_removed",
    "research.platform_set", "held.research_evidence", "decision.set_mismatch", "held.approval",
    "allocation.flow_platform_mismatch", "allocation.status_flows_mismatch", "allocation.flow_unallocated",
    "allocation.rationale_missing", "allocation.approval_missing", "allocation.approval_without_divergence",
    "held.assumptions",
    "sitemaps.drift",
)
READINESS_RULES = (
    "readiness.tree_test_not_run", "readiness.card_sort_not_run", "readiness.decision_pending",
    "readiness.cdo_approval_pending", "readiness.assumption_provisional", "readiness.label_provisional",
    "readiness.role_provisional", "readiness.registry_not_canonical", "readiness.registry_id_added",
    "readiness.registry_id_retired",
)


def printable(value):
    """Only grammar-validated identifiers and the fixed vocabulary may appear in output; all else is input text."""
    return isinstance(value, str) and (IDENTIFIER.fullmatch(value) is not None or value in VOCABULARY)


class Refused(ValueError):
    """A static rule identifier plus at most grammar-validated identifiers; never echoes input text."""

    def __init__(self, rule, *subjects):
        self.rule = rule
        self.subject = " ".join(subjects) if subjects and all(printable(item) for item in subjects) else None
        super().__init__(rule if self.subject is None else f"{rule} {self.subject}")


def require(condition, rule, *subjects):
    if not condition:
        raise Refused(rule, *subjects)


_ORDER = {"AND": 0, "WEB": 1, "ADM": 2, "android": 0, "web": 1, "admin": 2}


def natural_key(subject):
    """Sort by kind, platform (Android, web, admin) and number, not by raw text."""
    return [(0, _ORDER[token]) if token in _ORDER else (1, int(token)) if token.isdigit() else (2, token)
            for token in re.findall(r"[A-Za-z_]+|[0-9]+", subject)]


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


# The record identifier the content guard and schema refusals may name, per collection.
RECORD_KEYS = {
    "routes": "id", "roles": "id", "capabilities": "id", "screen_placements": "screen_id",
    "redirects": "to_route_id", "research": "platform", "decisions": "decision",
}


def _schema_subject(error, value):
    match = re.match(r"\$\.(" + "|".join(RECORD_KEYS) + r")\[([0-9]+)\]", str(error))
    if match is None or not isinstance(value, dict) or not isinstance(value.get(match.group(1)), list):
        return ()
    items, index = value[match.group(1)], int(match.group(2))
    item = items[index] if index < len(items) else None
    candidate = item.get(RECORD_KEYS[match.group(1)]) if isinstance(item, dict) else None
    return (candidate,) if printable(candidate) else ()


def shape(value, schema, definition=None):
    """Validate with the shared subset validator; its messages echo input, so only a rule and record ID survive."""
    try:
        selected = schema if definition is None else schema["definitions"][definition]
        support.validate_schema(value, selected, schema)
    except (ValueError, KeyError, TypeError, RecursionError, re.error) as error:  # re.error: a malformed pattern
        raise Refused("schema.invalid", *_schema_subject(error, value)) from None


TEXT_LIMIT = 400
_CURRENCIES = "INR|USD|EUR|GBP|AED|SGD|AUD|CAD|JPY|CNY|CHF|SAR|QAR|KWD|BHD|OMR|NZD|HKD|ZAR"
CONTENT_SHAPES = (
    # Printable ASCII only: look-alike digits, at signs or currency signs cannot slip past the shapes below.
    ("content.unprintable_character", re.compile(r"[^\x20-\x7e]")),
    ("content.secret_shape", re.compile(
        r"\bgh[pousr]_[A-Za-z0-9]{8,}|\bgithub_pat_|-----BEGIN|\bAKIA[0-9A-Z]{16}\b|\bxox[abposr]-"
        r"|\bsk-[A-Za-z0-9_-]{20,}|[0-9a-fA-F]{32,}"
    )),
    ("content.url_shape", re.compile(
        r"[A-Za-z][A-Za-z0-9+.-]*://|\bwww\.|\b(?:mailto|javascript|tel|sms|file|intent|ftp):"
        r"|\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:com|org|net|io|co|dev|app|ai|gov|edu|info|biz|me|us|uk|in|xyz)\b",
        re.IGNORECASE,
    )),
    # Any at sign: email addresses, UPI handles and user@host forms alike.
    ("content.email_shape", re.compile(r"@")),
    # Nine or more digits, whatever short separators sit between them.
    ("content.phone_shape", re.compile(r"[0-9](?:[^A-Za-z0-9]{0,3}[0-9]){8,}")),
    ("content.amount_shape", re.compile(
        r"\$\s*[0-9]|\b(?:" + _CURRENCIES + r"|Rs\.?)\s*[0-9]|[0-9]\s*(?:" + _CURRENCIES + r")\b"
        r"|[0-9]\s*(?:k|lakhs?|lacs?|crores?|cr|rupees?|paise|dollars?|euros?|pounds?|cents?)\b|[0-9]\s*/-",
        re.IGNORECASE,
    )),
)
# Mixed-case alphanumeric runs of 32+ characters with a digit are key-shaped too.
TOKEN = re.compile(r"[A-Za-z0-9+=_]{32,}")
# Grammar-checked values exempt from the scan, located by path ("*" = any list index): the pin's commit and digest
# (hex runs), its path and a role's source (closed allowlists) and deep-link or widget patterns (letters-only).
_ANY_DEEP_LINK = re.compile("|".join(f"(?:{grammar.pattern})" for grammar in DEEP_LINKS.values()))
EXEMPT_PATHS = {
    ("registry_ref", "commit"): COMMIT.fullmatch, ("registry_ref", "sha256"): DIGEST.fullmatch,
    ("registry_ref", "path"): REGISTRY_PATHS.__contains__, ("roles", "*", "source"): ROLE_SOURCES.__contains__,
    ("routes", "*", "patterns", "*"): lambda value: len(value) <= PATTERN_LIMIT and _ANY_DEEP_LINK.fullmatch(value),
    ("redirects", "*", "from_pattern"): lambda value: len(value) <= PATTERN_LIMIT and _ANY_DEEP_LINK.fullmatch(value),
    ("screen_placements", "*", "external", "patterns", "*"):
        lambda value: len(value) <= PATTERN_LIMIT and (_ANY_DEEP_LINK.fullmatch(value) or WIDGET_LINK.fullmatch(value)),
}
NUMBER_PATHS = frozenset({("schema_version",)} | {
    ("research", "*", "tree_test", "metrics", name) for name in ("task_success", "first_click_correctness",
                                                                  "backtrack_rate")
})


def _scan(text, subject):
    require(len(text) <= TEXT_LIMIT, "content.too_long", *subject)
    require(text.strip() == text and text != "", "content.blank_or_padded", *subject)
    for rule, pattern in CONTENT_SHAPES:
        require(pattern.search(text) is None, rule, *subject)
    for candidate in (text, re.sub(r"[-/_]", "", text)):
        for match in TOKEN.finditer(candidate):
            run = match.group()
            require(not all(any(test(c) for c in run) for test in (str.isdigit, str.islower, str.isupper)),
                    "content.secret_shape", *subject)


def guard_content(document):
    """Scan every string value wherever the schema puts it; only EXEMPT_PATHS values that pass their own check and
    the NUMBER_PATHS numbers are exempt. Keys are fixed by the schema (no additional properties anywhere)."""
    def walk(value, subject, path):
        if isinstance(value, dict):
            for key in ("id", "screen_id", "to_route_id", "platform", "decision"):
                if printable(value.get(key)):
                    subject = (value[key],)
                    break
            for key, item in value.items():
                walk(item, subject, (*path, key))
        elif isinstance(value, list):
            for item in value:
                walk(item, subject, (*path, "*"))
        elif isinstance(value, str):
            exempt = EXEMPT_PATHS.get(path)
            if not (exempt is not None and exempt(value)):
                _scan(value, subject)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            require(path in NUMBER_PATHS, "content.unexpected_number", *subject)

    walk(document, (), ())


def trusted_git(root):
    """Absolute path of git from absolute PATH entries outside the checked repository.

    A bare "git" lets the operating system search relative PATH entries and, on Windows, the current directory
    first, so a candidate-local executable could forge the pinned registry or the compatibility base.
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
    """The pinned registry blob and the compatibility base from the local Git object store; never fetches or writes."""

    def __init__(self, root):
        self.root, self.executable, self.commit = Path(root), None, None

    def _git(self, *args):
        self.executable = self.executable or trusted_git(self.root)
        env = {key: value for key, value in os.environ.items() if key not in SCRUBBED_GIT_VARIABLES}
        # Objects exactly as stored: no lazy fetch, and no replace refs or grafts, which could substitute the pinned
        # registry bytes or move the merge base.
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

    def is_published(self, commit):
        """Whether the pinned commit is in the published history (an ancestor of the merge base of HEAD and
        origin/main), so a branch cannot pin registry bytes of its own; any other answer is a lookup failure."""
        result = self._git("merge-base", "--is-ancestor", commit, self.base_commit())
        if result.returncode not in (0, 1):
            raise LookupError("ancestry unavailable")
        return result.returncode == 0

    def base_commit(self):
        if self.commit is None:
            result = self._git("merge-base", "HEAD", BASE_REF)
            commit = result.stdout.decode("ascii", "replace").strip()
            if result.returncode != 0 or not COMMIT.fullmatch(commit):
                raise LookupError("no merge base")
            self.commit = commit
        return self.commit

    def base_routes(self):
        """routes.json bytes at the merge base of HEAD and origin/main, or None when that tree has no such entry.

        Presence is read from the tree: a listed blob missing from the local object store fails closed instead of
        passing as a base that predates the route map.
        """
        commit = self.base_commit()
        listed = self._git("ls-tree", "-z", "--name-only", commit, "--", ROUTES)
        if listed.returncode != 0:
            raise LookupError("base tree unavailable")
        if not listed.stdout:
            return None
        if listed.stdout != ROUTES.encode("ascii") + b"\0":
            raise LookupError("unexpected base tree entry")
        return self.blob(commit, ROUTES)


class Registry:
    """The identifiers this check needs from an experience-coverage registry: screens with their platform and imported
    route hint, flows with their platform and journeys (the docs#75 registry names the hint route_hint)."""

    def __init__(self, document, rule):
        require(isinstance(document, dict), rule)
        self.screens, self.flows = {}, {}
        for record in self._records(document, "screens", SCREEN_ID, rule):
            hint = record.get("route_hint") if "route_hint" in record else record.get("route")
            require(isinstance(hint, str) and len(hint) <= PATTERN_LIMIT and ROUTE_HINT.fullmatch(hint), rule)
            self.screens[record["id"]] = (INFIX[record["id"][2:5]], hint)
        for record in self._records(document, "flows", FLOW_ID, rule):
            self.flows[record["id"]] = INFIX[record["id"][2:5]]
        self.journeys = {record["id"] for record in self._records(document, "journeys", JOURNEY_ID, rule)}
        # Natural order, so the first offending screen or flow reported never depends on the registry's list order.
        self.screens = dict(sorted(self.screens.items(), key=lambda item: natural_key(item[0])))
        self.flows = dict(sorted(self.flows.items(), key=lambda item: natural_key(item[0])))

    @staticmethod
    def _records(document, collection, grammar, rule):
        records = document.get(collection)
        require(isinstance(records, list), rule)
        seen = set()
        for record in records:
            identifier = record.get("id") if isinstance(record, dict) else None
            require(isinstance(identifier, str) and grammar.fullmatch(identifier) and identifier not in seen, rule)
            if grammar in (SCREEN_ID, FLOW_ID):
                require(record.get("platform") == INFIX[identifier[2:5]], rule)
            seen.add(identifier)
            yield record


def parse_registry(raw, rule):
    try:
        document = loads(raw)
    except (ValueError, RecursionError):
        raise Refused(rule) from None
    return Registry(document, rule)


def read_registry(routes, allocation, sources):
    """The pinned registry: both files cite one accepted path at a published commit, with matching bytes."""
    reference = routes["registry_ref"]
    require(reference == allocation["registry_ref"], "registry.ref_mismatch")
    require(reference["path"] in REGISTRY_PATHS, "registry.path_unaccepted")
    try:
        blob = sources.blob(reference["commit"], reference["path"])
        published = sources.is_published(reference["commit"])
    except LookupError:
        raise Refused("registry.unavailable") from None
    require(published is True, "registry.commit_unpublished")
    require(isinstance(blob, bytes) and gates.digest(blob) == reference["sha256"], "registry.digest_mismatch")
    return parse_registry(blob, "registry.invalid")


def by_id(records, key="id"):
    """Index records by identifier in natural order; a repeated identifier is refused."""
    index = {}
    for record in records:
        require(record[key] not in index, "id.duplicate", record[key])
        index[record[key]] = record
    return dict(sorted(index.items(), key=lambda item: natural_key(item[0])))


class Model:
    """Schema-valid route map and allocation plus the pinned registry, indexed for the rules below."""

    def __init__(self, routes, allocation, registry):
        self.document, self.allocation, self.registry = routes, allocation, registry
        self.routes = by_id(routes["routes"])
        self.roles = by_id(routes["roles"])
        self.capabilities = by_id(allocation["capabilities"])
        self.children = {identifier: [] for identifier in self.routes}
        for route in self.routes.values():
            if route["parent_route_id"] in self.children:
                self.children[route["parent_route_id"]].append(route["id"])
        self.roots = {platform: [route["id"] for route in self.routes.values()
                                 if route["platform"] == platform and route["parent_route_id"] is None]
                      for platform in PLATFORMS}
        self.hosted = {identifier: [] for identifier in self.routes}
        self.placements = {}
        # Exact patterns and match shapes, each owned by a route or an external entry's screen; redirects by shape.
        self.patterns, self.shapes, self.redirects = {}, {}, {}
        self.base = None


def check_identifiers(model, synthetic_ok):
    for identifier, route in model.routes.items():
        match = ROUTE_ID.fullmatch(identifier)
        require(INFIX[match.group(1)] == route["platform"], "id.platform_infix_mismatch", identifier)
        require(int(match.group(2)) > 0, "id.out_of_range", identifier)
    for identifier in model.capabilities:
        require(int(identifier[4:]) > 0, "id.out_of_range", identifier)
    for identifier, role in model.roles.items():
        require(int(identifier[-2:]) > 0, "id.out_of_range", identifier)
        require(synthetic_ok or not SYNTHETIC_ROLE.fullmatch(identifier), "role.synthetic_reserved", identifier)
        require(role["source"] in ROLE_SOURCES, "role.source_unaccepted", identifier)
        # ADR-020 section 5 names the operator's role as a policy input but publishes no role list, so no role can be
        # accepted from a source this check can read; every role stays provisional.
        require(role["status"] == "provisional", "held.role_accepted", identifier)
    for identifier in sorted(model.document["retired_route_ids"], key=natural_key):
        require(identifier not in model.routes, "route.retired_reused", identifier)


def check_topology(model):
    """One root per platform; every other route has one same-platform parent and a navigation entry, never search,
    and never a wider audience than its parent."""
    for platform, roots in model.roots.items():
        require(len(roots) == 1, "route.root_count", platform)
    for identifier, route in model.routes.items():
        parent = route["parent_route_id"]
        if parent is not None:
            require(parent in model.routes, "route.parent_dangling", identifier)
            require(model.routes[parent]["platform"] == route["platform"], "route.parent_platform_mismatch",
                    identifier)
            # A signed-out child of a signed-in route would be reachable without the sign-in, and in the admin
            # console without the roles, that its parent requires.
            require(route["audience"] == "signed_in" or model.routes[parent]["audience"] == "signed_out",
                    "route.audience_widened", identifier)
        require((parent is None) == (route["entry_from_parent"] is None), "route.entry_mismatch", identifier)
        # Global search is not a navigation edge: a route entered only through it is unreachable in the tree.
        require(route["entry_from_parent"] != "global_search", "route.search_only", identifier)
    for identifier in model.routes:
        seen, current = set(), identifier
        while model.routes[current]["parent_route_id"] is not None:
            seen.add(current)
            current = model.routes[current]["parent_route_id"]
            require(current not in seen, "route.cycle", identifier)


# A navigation label is static text: template braces, markup, format or parameter markers would inject data.
DYNAMIC_LABEL = re.compile(r"[{}<>%$#\[\]]|:[A-Za-z_]")
SIDE_NAVIGATION = ("navigation_rail", "navigation_drawer")


def check_labels(model):
    """Labels stay provisional text with no message key: H04 (PenniLogic/docs#84) owns the `nav.` key root."""
    for identifier, route in model.routes.items():
        label = route["label"]
        require(label["status"] == "provisional", "held.label_status", identifier)
        require(label["message_key"] is None, "held.message_key", identifier)
        require(DYNAMIC_LABEL.search(label["text"]) is None, "label.dynamic_content", identifier)


def check_presentation(model):
    """Android compact/expanded and web/admin narrow/wide; 3-5 Android primary destinations (product/08 line 209)."""
    for identifier, route in model.routes.items():
        android = route["platform"] == "android"
        presentation = route["presentation"]
        for key in ("compact", "expanded", "narrow", "wide"):
            require((presentation[key] is not None) == (android == (key in ("compact", "expanded"))),
                    "presentation.platform_mismatch", identifier)
        # No route is hidden by a breakpoint: narrow web (and the admin console) stays a complete fallback.
        require(presentation["narrow"] != "hidden", "presentation.narrow_hidden", identifier)
        if not android:
            continue
        bar = (presentation["compact"] == "navigation_bar" or presentation["expanded"] in SIDE_NAVIGATION
               or route["entry_from_parent"] == "primary_navigation")
        if route["primary"]:
            require(presentation["compact"] == "navigation_bar" and presentation["expanded"] in SIDE_NAVIGATION
                    and route["entry_from_parent"] == "primary_navigation", "android.primary_adaptation", identifier)
        else:
            require(not bar, "android.unlisted_primary", identifier)
    primary = sum(route["primary"] for route in model.routes.values() if route["platform"] == "android")
    require(3 <= primary <= 5, "android.primary_count", "android")


def check_access(model):
    """Admin navigation is an authorization result: a destination outside the operator's roles is absent."""
    for identifier, route in model.routes.items():
        access = route["access"]
        if route["platform"] != "admin":
            require(access is None, "access.customer_route_roles", identifier)
            continue
        require((route["audience"] == "signed_in") == (access is not None), "admin.access_mismatch", identifier)
        if access is None:
            continue
        for role in access["roles"]:
            require(role in model.roles, "admin.role_unknown", identifier)
        # Not rendered, not addressable, no deep link for that role: never a disabled, greyed or hidden entry.
        require(access["unauthorized"] == "absent", "admin.unauthorized_not_absent", identifier)
        parent = model.routes[route["parent_route_id"]] if route["parent_route_id"] is not None else None
        if parent is not None and parent["access"] is not None:
            require(set(access["roles"]) <= set(parent["access"]["roles"]), "admin.role_wider_than_parent",
                    identifier)


def check_placements(model):
    """Each registry screen is placed exactly once: hosted by one same-platform route, or a documented external entry
    (deep link, notification, system handoff or widget) with a rationale; admin screens are always hosted. Every route
    hosts a screen or has children."""
    screens = model.registry.screens
    for item in sorted(model.document["screen_placements"], key=lambda item: natural_key(item["screen_id"])):
        identifier, host, external = item["screen_id"], item["host_route_id"], item["external"]
        require(identifier in screens, "placement.unknown_screen", identifier)
        require(identifier not in model.placements, "placement.duplicate", identifier)
        model.placements[identifier] = item
        require((host is None) != (external is None), "placement.host_and_external", identifier)
        if host is not None:
            require(host in model.routes, "placement.route_dangling", identifier)
            require(model.routes[host]["platform"] == screens[identifier][0], "placement.platform_mismatch",
                    identifier)
            model.hosted[host].append(identifier)
        else:
            require(external["rationale"] is not None, "placement.rationale_missing", identifier)
            # Outside every route an operator screen would carry no role: admin screens are always hosted, and an
            # operator deep link resolves to a role-bound route.
            require(screens[identifier][0] != "admin", "admin.external_entry", identifier)
    for identifier in screens:
        require(identifier in model.placements, "placement.orphan_screen", identifier)
    for identifier in model.routes:
        require(model.hosted[identifier] or model.children[identifier], "route.empty_leaf", identifier)


def match_shape(pattern):
    """What a pattern matches: every parameter segment matches any one segment, whatever its name."""
    return re.sub(rf":{_SEGMENT}", ":", pattern)


def _claim(model, platform, pattern, grammar, owner):
    """Record one pattern for its owner (a route, or the screen of an external entry): within its grammar, unique,
    and alone in its match shape on the platform."""
    require(grammar is not None and len(pattern) <= PATTERN_LIMIT and grammar.fullmatch(pattern), "deep_link.grammar",
            owner)
    require((platform, pattern) not in model.patterns, "deep_link.duplicate_pattern", owner)
    model.patterns[(platform, pattern)] = owner
    require(model.shapes.setdefault((platform, match_shape(pattern)), owner) == owner, "deep_link.ambiguous_pattern",
            owner)


def check_deep_links(model):
    """Every pattern resolves to exactly one route or external entry of its platform; imported route hints map to the
    hosting route, or to the external entry's own pattern; redirects lead from retired patterns to active routes.
    Static segments outrank parameters, which outrank a trailing wildcard, so only patterns with the same match shape
    are ambiguous, and hints, redirects and the published base are all compared by match shape."""
    for identifier, route in model.routes.items():
        for pattern in route["patterns"]:
            _claim(model, route["platform"], pattern, DEEP_LINKS[route["platform"]], identifier)
    # An invitation, notification or widget landing opened from outside the product has no route, but the links that
    # open it persist outside the app: they are claimed like route patterns, so nothing else captures them.
    for identifier, item in model.placements.items():
        if item["external"] is not None:
            platform, entry = model.registry.screens[identifier][0], item["external"]["entry"]
            grammar = (WIDGET_LINK if platform == "android" else None) if entry == "widget" else DEEP_LINKS[platform]
            for pattern in item["external"]["patterns"]:
                _claim(model, platform, pattern, grammar, identifier)
    for item in model.document["redirects"]:
        target, pattern = item["to_route_id"], item["from_pattern"]
        require(target in model.routes, "deep_link.redirect_dangling", target)
        platform = model.routes[target]["platform"]
        require(len(pattern) <= PATTERN_LIMIT and DEEP_LINKS[platform].fullmatch(pattern), "deep_link.grammar", target)
        key = (platform, match_shape(pattern))
        require(key not in model.redirects, "deep_link.redirect_duplicate", target)
        require(key not in model.shapes, "deep_link.redirect_shadowed", target)
        model.redirects[key] = target
    for identifier, (platform, hint) in model.registry.screens.items():
        host, key = model.placements[identifier]["host_route_id"], (platform, match_shape(hint))
        owner = model.shapes.get(key)
        if host is None:
            # An external entry resolves its own hint; a redirect leads to a route, never to a landing.
            require(owner is not None, "deep_link.hint_unmapped", identifier)
            require(owner == identifier, "deep_link.hint_misrouted", identifier)
        elif owner is not None:
            require(owner == host, "deep_link.hint_misrouted", identifier)
        else:
            require(model.redirects.get(key) == host, "deep_link.hint_unmapped", identifier)


_BASE_ROUTE_ID = {"type": "string", "pattern": r"^R-(AND|WEB|ADM)-[0-9]{3}$(?![\s\S])"}
# Only the fields compatibility reads, so a later schema version can still read an older published base.
BASE_SCHEMA = {
    "type": "object", "required": ["routes", "redirects", "retired_route_ids", "screen_placements"],
    "properties": {
        "routes": {"type": "array", "items": {
            "type": "object", "required": ["id", "patterns"],
            "properties": {"id": _BASE_ROUTE_ID, "patterns": {"type": "array", "items": {"type": "string"}}},
        }},
        "redirects": {"type": "array", "items": {
            "type": "object", "required": ["from_pattern", "to_route_id"],
            "properties": {"from_pattern": {"type": "string"}, "to_route_id": _BASE_ROUTE_ID},
        }},
        "retired_route_ids": {"type": "array", "items": _BASE_ROUTE_ID},
        "screen_placements": {"type": "array", "items": {
            "type": "object", "required": ["screen_id", "external"],
            "properties": {
                "screen_id": {"type": "string", "pattern": r"^S-(AND|WEB|ADM)-[0-9]{3}$(?![\s\S])"},
                "external": {"type": ["object", "null"], "required": ["patterns"],
                             "properties": {"patterns": {"type": "array", "items": {"type": "string"}}}},
            },
        }},
    },
}


def read_base(sources):
    """The route map at the merge base of HEAD and origin/main, or None while main has none."""
    try:
        raw = sources.base_routes()
    except LookupError:
        raise Refused("base.unavailable") from None
    if raw is None:
        return None
    try:
        base = loads(raw)
        shape(base, BASE_SCHEMA)
    except (ValueError, RecursionError):  # Refused is a ValueError: a base schema failure is an invalid base
        raise Refused("base.invalid") from None
    return base


def check_compatibility(model, base):
    """Against the published base: route IDs are never dropped or reused, published route and external-entry patterns
    keep resolving to their route or screen (by match shape) or gain a redirect, and redirects are never removed. A
    rollback is therefore a roll-forward: restore the earlier routes, labels and placements, retire the route IDs
    added since and keep every redirect and published pattern."""
    model.base = base
    if base is None:
        return
    retired = set(model.document["retired_route_ids"])
    for route in sorted(base["routes"], key=lambda item: natural_key(item["id"])):
        identifier = route["id"]
        require(identifier in model.routes or identifier in retired, "route.id_dropped", identifier)
        platform = INFIX[identifier[2:5]]
        for pattern in route["patterns"]:
            key = (platform, match_shape(pattern))
            require(model.shapes.get(key) == identifier or key in model.redirects, "deep_link.published_changed",
                    identifier)
    for item in sorted(base["screen_placements"], key=lambda item: natural_key(item["screen_id"])):
        if item["external"] is None:
            continue
        identifier = item["screen_id"]
        # Still the landing itself, or the route that now hosts that screen; otherwise a recorded redirect.
        current = {identifier, model.placements.get(identifier, {}).get("host_route_id")} - {None}
        for pattern in item["external"]["patterns"]:
            key = (INFIX[identifier[2:5]], match_shape(pattern))
            require(model.shapes.get(key) in current or key in model.redirects, "deep_link.published_changed",
                    identifier)
    for identifier in sorted(base["retired_route_ids"], key=natural_key):
        require(identifier in retired, "route.retired_dropped", identifier)
    for item in base["redirects"]:
        key = (INFIX[item["to_route_id"][2:5]], match_shape(item["from_pattern"]))
        require(key in model.redirects, "deep_link.redirect_removed", item["to_route_id"])


def check_research_and_decisions(model):
    """Tree tests, card sorts and the IA, Security and Accessibility decisions are held inputs this session cannot
    produce: one record each, kept not_run or pending with no evidence, metric, reference or approval filled in."""
    research = model.document["research"]
    require(sorted(item["platform"] for item in research) == sorted(PLATFORMS), "research.platform_set")
    for item in research:
        tree, card_sort = item["tree_test"], item["card_sort"]
        require(tree["status"] == "not_run" and tree["evidence_ref"] is None
                and all(value is None for value in tree["metrics"].values())
                and card_sort["status"] == "not_run" and card_sort["evidence_ref"] is None,
                "held.research_evidence", item["platform"])
    decisions = model.document["decisions"]
    require(sorted(item["decision"] for item in decisions) == sorted(DECISIONS), "decision.set_mismatch")
    for item in decisions:
        require(item["status"] == "pending" and item["ref"] is None, "held.approval", item["decision"])


def check_allocation(model):
    """D19: per capability and platform parity, divergent or absent, delivered by registry flows of that platform;
    every registry flow is allocated; a divergence carries a user/job rationale and a pending CDO approval record."""
    registry, allocated = model.registry, set()
    for identifier, capability in model.capabilities.items():
        for journey in capability["journey_ids"]:
            require(journey in registry.journeys, "reference.dangling", identifier, journey)
        divergent = False
        for platform in PLATFORMS:
            allocation = capability["platforms"][platform]
            for flow in allocation["flow_ids"]:
                require(flow in registry.flows, "reference.dangling", identifier, flow)
                require(registry.flows[flow] == platform, "allocation.flow_platform_mismatch", identifier, flow)
                allocated.add(flow)
            require((allocation["status"] == "absent") == (not allocation["flow_ids"]),
                    "allocation.status_flows_mismatch", identifier, platform)
            divergent = divergent or allocation["status"] != "parity"
        approval = capability["cdo_approval"]
        if divergent:
            require(capability["rationale"] is not None, "allocation.rationale_missing", identifier)
            require(approval is not None, "allocation.approval_missing", identifier)
            # Never recorded as approved by this session: no CDO decision record can be resolved offline.
            require(approval["status"] == "pending" and approval["ref"] is None, "held.approval", identifier)
        else:
            require(approval is None, "allocation.approval_without_divergence", identifier)
        # Persona and journey assumptions wait for docs#66 persona validation and docs#67 blueprints.
        require(capability["assumptions"] == "provisional", "held.assumptions", identifier)
    for flow in registry.flows:
        require(flow in allocated, "allocation.flow_unallocated", flow)


def check(routes, allocation, routes_schema, allocation_schema, sources, synthetic_ok=False):
    """Run every structure rule in a fixed order; raise Refused at the first violation, else return the model."""
    shape(routes, routes_schema)
    shape(allocation, allocation_schema)
    guard_content(routes)
    guard_content(allocation)
    registry = read_registry(routes, allocation, sources)
    model = Model(routes, allocation, registry)
    check_identifiers(model, synthetic_ok)
    check_topology(model)
    check_labels(model)
    check_presentation(model)
    check_access(model)
    check_placements(model)
    check_deep_links(model)
    check_compatibility(model, read_base(sources))
    check_research_and_decisions(model)
    check_allocation(model)
    return model


def read_current(root):
    """The working-tree registry: docs#75's canonical registry once integrated, else the planning import."""
    for path in (CANONICAL_PATH, IMPORT_PATH):
        target = Path(root) / path
        if target.exists():
            try:
                raw = target.read_bytes()
            except OSError:
                raise Refused("registry.current_invalid") from None
            return parse_registry(raw, "registry.current_invalid")
    raise Refused("registry.current_invalid")


def readiness(model, current=None):
    """Every visible gap by static rule, with sorted subjects; never filled in or waived. Each condition names the
    resolved state that would clear it, although the structure rules refuse every resolved value today (held.*)."""
    gaps = {rule: set() for rule in READINESS_RULES}
    for item in model.document["research"]:
        if item["tree_test"]["status"] != "completed":
            gaps["readiness.tree_test_not_run"].add(item["platform"])
        if item["card_sort"]["status"] != "completed":
            gaps["readiness.card_sort_not_run"].add(item["platform"])
    for item in model.document["decisions"]:
        if item["status"] != "approved":
            gaps["readiness.decision_pending"].add(item["decision"])
    for identifier, capability in model.capabilities.items():
        approval = capability["cdo_approval"]
        if approval is not None and approval["status"] != "approved":
            gaps["readiness.cdo_approval_pending"].add(identifier)
        if capability["assumptions"] != "validated":
            gaps["readiness.assumption_provisional"].add(identifier)
    for identifier, route in model.routes.items():
        if route["label"]["status"] != "approved" or route["label"]["message_key"] is None:
            gaps["readiness.label_provisional"].add(identifier)
    for identifier, role in model.roles.items():
        if role["status"] != "accepted":
            gaps["readiness.role_provisional"].add(identifier)
    if model.document["registry_ref"]["path"] != CANONICAL_PATH:
        gaps["readiness.registry_not_canonical"].add(REGISTRY_ISSUE)
    if current is not None:
        # TS-M8: IDs the live registry added or retired since the pin are gaps, never structure failures.
        pinned = set(model.registry.screens) | set(model.registry.flows) | model.registry.journeys
        live = set(current.screens) | set(current.flows) | current.journeys
        gaps["readiness.registry_id_added"].update(live - pinned)
        gaps["readiness.registry_id_retired"].update(pinned - live)
    return {rule: sorted(subjects, key=natural_key) for rule, subjects in gaps.items()}


def status_line(gaps):
    return NOT_GREEN if any(gaps.values()) else GREEN


def structure_line(model):
    routes, placements = model.routes.values(), model.placements.values()
    counts = {platform: sum(route["platform"] == platform for route in routes) for platform in PLATFORMS}
    primary = sum(route["primary"] for route in routes if route["platform"] == "android")
    external = sum(item["external"] is not None for item in placements)
    landing = sum(len(item["external"]["patterns"]) for item in placements if item["external"] is not None)
    divergent = sum(capability["cdo_approval"] is not None for capability in model.capabilities.values())
    base = "the published base" if model.base is not None else "no published base"
    return (
        f"Navigation map {model.document['ia_version']} structure valid: {len(model.routes)} routes "
        f"({counts['android']} Android, {counts['web']} web, {counts['admin']} admin; {primary} Android primary "
        f"destinations), 0 orphan routes, {len(model.placements)} registry screens placed exactly once "
        f"({len(model.placements) - external} hosted, {external} external), {len(model.patterns)} deep-link patterns "
        f"({landing} on external entries), {len(model.redirects)} redirects, "
        f"{len(model.document['retired_route_ids'])} retired route IDs checked against {base}; "
        f"{len(model.capabilities)} capabilities ({divergent} with a divergence) allocating "
        f"{len(model.registry.flows)} registry flows; registry pinned at {model.document['registry_ref']['path']}"
    )


def _text(value):
    """Data text inside Markdown: escape the characters that would format it, link it, open raw HTML (an HTML
    comment would hide the rest of the page) or break a table cell."""
    return re.sub(r"([\\`*_|<>\[\]~])", r"\\\1", value)


def _route_line(model, route):
    presentation, access = route["presentation"], route["access"]
    if route["platform"] == "android":
        layout = f"compact {presentation['compact']}, expanded {presentation['expanded']}"
    else:
        layout = f"narrow {presentation['narrow']}, wide {presentation['wide']}"
    parts = [route["audience"].replace("_", " "), layout]
    if route["entry_from_parent"] is not None:
        parts.append(f"entered by {route['entry_from_parent']}")
    if route["primary"]:
        parts.insert(0, "primary destination")
    if access is not None:
        parts.append("roles " + ", ".join(f"`{role}`" for role in access["roles"]) + "; absent for other roles")
    parts.append("patterns " + (", ".join(f"`{pattern}`" for pattern in route["patterns"]) or "none"))
    parts.append("screens " + (", ".join(model.hosted[route["id"]]) or "none (container)"))
    return f"`{route['id']}` {_text(route['label']['text'])}: " + "; ".join(parts)


def _tree(model, identifier, depth=0):
    lines = ["  " * depth + "- " + _route_line(model, model.routes[identifier])]
    for child in sorted(model.children[identifier], key=natural_key):
        lines += _tree(model, child, depth + 1)
    return lines


PLATFORM_NOTES = {
    "android": "Compact width uses the navigation bar for the primary destinations; expanded width adapts them to "
               "the navigation rail or drawer named per route (product/08 section 8.1).",
    "web": "No route is hidden by a breakpoint: narrow web stays a complete management fallback (product/08 "
           "section 8.2).",
    "admin": "Navigation is an authorization result: a destination outside the operator's roles is absent (not "
             "rendered, not addressable, no deep link), never disabled (product/08 section 8.3, ADR-020).",
}


def _platform_section(model, platform, title):
    routes = [route for route in model.routes.values() if route["platform"] == platform]
    lines = ["", f"## {title}", "", PLATFORM_NOTES[platform], ""]
    if platform == "android":
        primary = [f"`{route['id']}` {_text(route['label']['text'])}" for route in routes if route["primary"]]
        lines += [f"Primary destinations ({len(primary)}; product/08 allows three to five): {', '.join(primary)}.", ""]
    for audience in ("signed_out", "signed_in"):
        members = [f"`{route['id']}`" for route in routes if route["audience"] == audience]
        lines.append(f"- {audience.replace('_', ' ').capitalize()}: {', '.join(members) or 'none'}")
    lines += ["", "### Route tree", ""] + _tree(model, model.roots[platform][0])
    external = [(identifier, item["external"]) for identifier, item in model.placements.items()
                if item["external"] is not None and model.registry.screens[identifier][0] == platform]
    if external:
        lines += ["", "### External and system entries", "", "| Screen | Entry | Patterns | Rationale |",
                  "| --- | --- | --- | --- |"]
        lines += [f"| {identifier} | {entry['entry']} | {', '.join(f'`{item}`' for item in entry['patterns'])} | "
                  f"{_text(entry['rationale'])} |" for identifier, entry in external]
    if platform == "admin":
        lines += ["", "### Roles and per-role projection", "", "| Role | Name | Status | Source | Visible routes |",
                  "| --- | --- | --- | --- | --- |"]
        for identifier, role in model.roles.items():
            visible = [route["id"] for route in routes
                       if route["access"] is None or identifier in route["access"]["roles"]]
            lines.append(f"| `{identifier}` | {_text(role['name'])} | {role['status']} | `{role['source']}` | "
                         + ", ".join(visible) + " |")
    return lines


def _allocation_cell(allocation):
    flows = ", ".join(allocation["flow_ids"])
    return allocation["status"] + (f": {flows}" if flows else "")


def render_sitemaps(model):
    """The provisional sitemaps and the D19 matrix, from the H05 files and the pinned registry only (LF, no clock)."""
    document, reference = model.document, model.document["registry_ref"]
    lines = [
        "# Provisional navigation sitemaps",
        "",
        "<!-- Generated by scripts/check_navigation.py --write-sitemaps. Do not edit by hand. -->",
        "",
        f"Generated from `{ROUTES}` (IA version {document['ia_version']}, provisional) and `{ALLOCATION}` "
        f"against the experience-coverage registry pinned at `{reference['path']}`, commit `{reference['commit']}`, "
        f"`{reference['sha256']}`. The default mode and `--check-sitemaps` of `scripts/check_navigation.py` refuse "
        "any difference from this rendering.",
        "",
        "Every label is provisional text without a message key (PenniLogic/docs#84 owns the `nav.` key root). Tree "
        "tests and card sorts are not run; persona and journey assumptions wait for PenniLogic/docs#66 and "
        "PenniLogic/docs#67; the IA, Security, Accessibility and CDO decisions are pending. Nothing here is D1 "
        "approval, research evidence, a review or permission to build navigation.",
    ]
    for platform, title in (("android", "Android"), ("web", "Customer web"), ("admin", "Admin and operator")):
        lines += _platform_section(model, platform, title)
    lines += [
        "", "## D19 platform allocation", "",
        "Parity, divergence or absence per capability and platform, with the registry flows that deliver it. Every "
        "divergence records its user/job rationale and a pending CDO approval; none is approved.", "",
        "| Capability | Name | Journeys | Android | Web | Admin | Rationale | CDO approval |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for identifier, capability in model.capabilities.items():
        platforms, approval = capability["platforms"], capability["cdo_approval"]
        lines.append(
            f"| {identifier} | {_text(capability['name'])} | {', '.join(capability['journey_ids'])} | "
            + " | ".join(_allocation_cell(platforms[platform]) for platform in PLATFORMS)
            + f" | {_text(capability['rationale']) if capability['rationale'] is not None else 'none (parity)'} | "
            + ("not required (parity)" if approval is None else approval["status"]) + " |"
        )
    return "\n".join(lines) + "\n"


def load_and_check(root):
    """Published mode: the committed files, the local Git object store and no synthetic roles."""
    root = Path(root)
    return check(
        support.load_json(root / ROUTES), support.load_json(root / ALLOCATION),
        support.load_json(root / ROUTES_SCHEMA), support.load_json(root / ALLOCATION_SCHEMA), GitSources(root),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--structure", action="store_true", help="Check structure only; readiness is not evaluated.")
    modes.add_argument("--write-sitemaps", action="store_true", help=f"Regenerate {SITEMAPS} from the checked files.")
    modes.add_argument("--check-sitemaps", action="store_true", help=f"Fail unless {SITEMAPS} matches byte for byte.")
    args = parser.parse_args(argv)
    try:
        model = load_and_check(ROOT)
        if args.structure:
            print(structure_line(model) + "; readiness not evaluated.")
            return 0
        sitemaps = render_sitemaps(model)
        if args.write_sitemaps:
            target = ROOT / SITEMAPS
            if target.is_symlink() or target.parent.resolve() != (ROOT.resolve() / SITEMAPS).parent:
                raise OSError("refusing to write the sitemaps through a symlink")
            target.write_text(sitemaps, encoding="utf-8", newline="\n")
            print(f"Navigation sitemaps written to {SITEMAPS}.")
            return 0
        try:
            current = (ROOT / SITEMAPS).read_bytes()
        except OSError:
            current = None
        require(current == sitemaps.encode("utf-8"), "sitemaps.drift")
        if args.check_sitemaps:
            print(f"Navigation sitemaps {SITEMAPS} match the route map and allocation.")
            return 0
        gaps = readiness(model, read_current(ROOT))
        status = status_line(gaps)
        print(status)
        print(structure_line(model))
        if status == GREEN:
            return 0
        for rule in READINESS_RULES:
            print(f"{rule}: {len(gaps[rule])}")
        return 1
    except Refused as error:
        print(f"Navigation check refused: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, RecursionError, re.error):
        # Fail closed without a traceback, whose message could echo input content.
        print("Navigation check refused: input.unreadable_or_invalid", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
