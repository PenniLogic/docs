"""Offline T-DSY-02 checks of the governed Figma library topology, component contribution and release records.

PenniLogic/docs#78 records the library topology (LIB-* libraries and which may consume which), releases keyed by
(library, SemVer), component governance records keyed by the experience-coverage registry's C-* IDs, a synthetic
permission/offboarding tabletop and the required approvals in governance/figma-libraries.json, validated against
governance/figma-libraries.schema.json (a self-contained draft-07 subset). Roles, the CDO-equivalent scope, artifact
classes and the reserved Figma topology are read from governance/design-gates.json; the SemVer and branch rules are
those of governance/design-operations.md section 6. Neither file is edited.

The registry is the imported planning/source/evidence/experience-coverage.json pinned by commit, path and sha256 and
read from the local Git object store through an absolute git outside the checkout (no replace refs or grafts). IDs
absent from the pin, and pinned components without a governance record, are readiness gaps, never structure failures.

Structure failures raise `Refused` with a static rule identifier plus, at most, identifiers that passed their own
grammar (C-*, LIB-*, LIB-*@SemVer, TT-NN, design-gates role IDs, PenniLogic/<repo>#N); input text is never echoed.
Readiness gaps (the docs#76 direction, the docs#55 token grammar, unrecorded approvals, a pending CDO decision or
migration plan, live Figma verification, the unchecked base-revision continuity of published records and registry
coverage) are counted, never filled in, and keep the default mode NOT GREEN; GREEN is unreachable in this version.
Nothing here contacts Figma or GitHub, records an approval, publishes a library, grants or revokes access, or proves
live permission enforcement: the tabletop is synthetic and `live_verified` stays false.

`--mirror` prints the generated section of governance/figma-library-governance.md, rendered from the validated JSON
only; a unit test fails when the committed section drifts from it. It writes nothing.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DATA = "governance/figma-libraries.json"
SCHEMA = "governance/figma-libraries.schema.json"
GATES = "governance/design-gates.json"
# TS-M8: consumers pin the imported registry on main until docs#75 (draft PR #176) merges.
REGISTRY_PIN = {
    "commit": "1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4",
    "path": "planning/source/evidence/experience-coverage.json",
    "sha256": "sha256:2f7b27c1f6683d4c256a938ccfb0fc06614f83fe57996a4d7aeaf0b7cae0bf3a",
}
GREEN = "GREEN: readiness complete"
NOT_GREEN = "NOT GREEN: readiness incomplete"
DIRECTION_ISSUE = "PenniLogic/docs#76"
TOKENS_ISSUE = "PenniLogic/docs#55"
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


support = _sibling("figma_libraries_schema_support", "check_client_states.py")
gates = _sibling("figma_libraries_design_gates", "check_design_gates.py")
KNOWN_ROLES = frozenset(gates.ROLES)

LIBRARIES = ("LIB-FOUNDATION", "LIB-COMPONENTS", "LIB-ANDROID", "LIB-WEB", "LIB-ADMIN", "LIB-CANDIDATE")
SHARED = LIBRARIES[:5]
PLATFORMS = ("android", "web", "admin")
# id: (kind, layer, design-gates artifact class, reserved file id, reserved page, platform). A library may consume
# only libraries of a strictly lower layer; candidates (feature-squad drafts) live in squad proposal branches.
TOPOLOGY = {
    "LIB-FOUNDATION": ("foundation", 0, "foundations_tokens", "f02", "Foundations", None),
    "LIB-COMPONENTS": ("shared_semantic", 1, "components", "f03", "Components", None),
    "LIB-ANDROID": ("platform_variant", 2, "components", "f03", "Android variants", "android"),
    "LIB-WEB": ("platform_variant", 2, "components", "f03", "Web variants", "web"),
    "LIB-ADMIN": ("platform_variant", 2, "components", "f03", "Admin variants", "admin"),
    "LIB-CANDIDATE": ("candidate", 3, "components", None, None, None),
}
REQUIRED_CONSUMES = {
    "LIB-FOUNDATION": (), "LIB-COMPONENTS": ("LIB-FOUNDATION",),
    "LIB-ANDROID": ("LIB-FOUNDATION", "LIB-COMPONENTS"), "LIB-WEB": ("LIB-FOUNDATION", "LIB-COMPONENTS"),
    "LIB-ADMIN": ("LIB-FOUNDATION", "LIB-COMPONENTS"), "LIB-CANDIDATE": ("LIB-FOUNDATION", "LIB-COMPONENTS"),
}
# DoD 2: Design Systems (systems), DesignOps, Accessibility, UX Engineering and the CDO (decision_coordinator).
APPROVAL_ROLES = ("systems", "design_ops", "accessibility", "ux_engineering", "decision_coordinator")
CDO_ROLE, CDO_SCOPE = "decision_coordinator", "shared_system_major"
TABLETOP_ID = re.compile(r"TT-[0-9]{2}")
SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
# The ID-authority grammar (hyphen-separated upper-case/digit segments), bounded to 64 characters for safe output.
COMPONENT = re.compile(r"(?=[A-Z0-9-]{3,64}\Z)C-[A-Z0-9]+(?:-[A-Z0-9]+)*")
# The registry schema's own grammar for pinned IDs; a pinned ID outside COMPONENT has no record and stays a gap.
REGISTRY_COMPONENT = re.compile(r"C-[A-Z0-9-]+")
# Repository-relative file paths at the exempt *.path fields (dotted file names are not host names there).
FILE_PATH = re.compile(r"(?=[a-z0-9_./-]{1,200}\Z)(?:[a-z0-9_-]+/)*[a-z0-9_-]+\.(?:json|md)")
# Component IDs with this prefix belong to test fixtures only and are refused in published data.
SYNTHETIC_PREFIX = "C-SYN-"
# The public PenniLogic repositories (check_test_strategy.REPOSITORY_IDS); issue numbers have at most six digits.
ISSUE_REF = re.compile(r"PenniLogic/(\.github|docs|contracts|api|ai-service|android|web|admin|infra)#([1-9][0-9]{0,5})")
COMMIT = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
RELEASE_ID = re.compile(r"(LIB-[A-Z]+)@((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))")
# camelCase property names of the schema grammar built from words: every capital starts a lower-case word and digit
# runs are at most two long, so a mixed-case key (a capital or digit run before another capital) never matches.
PROPERTY_NAME = re.compile(r"(?=[A-Za-z0-9]{1,40}\Z)[a-z]+(?:[A-Z][a-z]+|[0-9]{1,2}(?![0-9]))*")
TEXT_LIMIT = 400
NUMBER_PATHS = frozenset({("schema_version",)})
# Exempt from the content scan only at these paths and only with exactly this grammar (a digest is hex-shaped).
EXEMPT_PATHS = {("registry_ref", "commit"): COMMIT, ("registry_ref", "sha256"): DIGEST,
                ("registry_ref", "path"): FILE_PATH,
                ("releases", "*", "cdo_approval", "decision_source", "commit"): COMMIT,
                ("releases", "*", "cdo_approval", "decision_source", "sha256"): DIGEST,
                ("releases", "*", "cdo_approval", "decision_source", "path"): FILE_PATH,
                ("components", "*", "properties", "*", "name"): PROPERTY_NAME}
CONTENT_SHAPES = (
    ("content.unprintable_character", re.compile(r"[^\x20-\x7e]")),
    ("content.secret_shape", re.compile(
        r"\bgh[pousr]_[A-Za-z0-9]{8,}|\bgithub_pat_|-----BEGIN|\bAKIA[0-9A-Z]{16}\b|\bxox[abposr]-"
        r"|\bsk-[A-Za-z0-9_-]{20,}|\bfig[a-z]_"
        # Key-shaped runs: 32 or more letters, digits, + / = with a digit (hex, base64); 32 or more letters or digits
        # without one; 16 or more mixing upper case, lower case and digits (a Figma file key has 22).
        r"|(?=[A-Za-z0-9+/=]{32})[A-Za-z+/=]*[0-9][A-Za-z0-9+/=]*|[A-Za-z0-9]{32,}"
        r"|(?<![A-Za-z0-9])(?=[A-Za-z0-9]*[0-9])(?=[A-Za-z0-9]*[a-z])(?=[A-Za-z0-9]*[A-Z])[A-Za-z0-9]{16,}"
    )),
    # E34-F06: no public links, file keys or hosts: any scheme, www., dotted host name (any letter top-level label),
    # host:port or IPv4 shape is refused. Repository file paths are exempt only at EXEMPT_PATHS.
    ("content.url_shape", re.compile(
        r"[A-Za-z][A-Za-z0-9+.-]*:/|\bwww\.|\b(?:mailto|javascript|data|file|tel):"
        r"|\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b|\b[A-Za-z][A-Za-z0-9-]*:[0-9]{2,5}\b"
        r"|\b[0-9]{1,3}(?:\.[0-9]{1,3}){3}\b",
        re.IGNORECASE,
    )),
    ("content.email_shape", re.compile(r"@")),
    ("content.phone_shape", re.compile(r"[0-9](?:[^A-Za-z0-9]{0,3}[0-9]){8,}")),
)

STRUCTURE_RULES = (
    "input.unreadable_or_invalid", "schema.invalid", "policy.invalid",
    "content.too_long", "content.blank_or_padded", "content.unprintable_character", "content.secret_shape",
    "content.url_shape", "content.email_shape", "content.phone_shape",
    "registry.ref_mismatch", "registry.unavailable", "registry.digest_mismatch", "registry.invalid",
    "library.set_mismatch", "library.kind_mismatch", "library.location_mismatch", "library.owner_mismatch",
    "library.status_mismatch", "library.freeze_mismatch",
    "topology.invalid_consumption", "topology.missing_dependency",
    "role.unknown", "permission.feature_squad_publish", "permission.publish_not_maintainer",
    "permission.candidate_publish", "access.public_links", "access.external_sharing", "access.asset_export",
    "access.offboarding_not_revoking",
    "held.direction_ref", "held.token_refs", "held.publication", "held.cdo_recorded",
    "id.duplicate", "id.synthetic_reserved",
    "release.duplicate", "release.candidate_library", "release.previous_unknown", "release.version_not_increasing",
    "release.chain_invalid", "release.previous_unpublished",
    "release.breaking_not_major", "release.class_mismatch", "release.migration_plan_missing",
    "release.cdo_approval_missing", "release.cdo_pending_published", "release.migration_plan_pending_published",
    "release.rollback_target", "approval.source_mismatch",
    "reference.invalid",
    "component.library_invalid", "component.candidate_published", "component.platform_mismatch",
    "component.registry_platform_mismatch", "component.registry_name_mismatch",
    "component.variant_invalid", "component.variant_parent_unpublished", "component.owner_not_maintainer",
    "component.property_contract",
    "published.owner_missing", "published.name_missing", "published.description_missing", "published.properties_missing",
    "published.accessibility_missing", "published.platforms_missing", "published.semantic_role_missing",
    "published.release_missing",
    "deprecation.unexpected", "deprecation.missing", "deprecation.replacement_missing",
    "deprecation.replacement_invalid", "deprecation.removal_version_missing", "deprecation.removal_version_invalid",
    "deprecation.removal_not_breaking", "deprecation.unavailable",
    "duplicate.semantic_component",
    "contribution.branch_grammar", "contribution.branch_outside_candidates", "contribution.squad_mismatch",
    "contribution.branch_duplicate", "contribution.candidate_library",
    "contribution.candidate_incomplete",
    "tabletop.duplicate", "tabletop.live_claim", "tabletop.outcome_mismatch", "tabletop.coverage_missing",
    "approval.roles_mismatch",
)
READINESS_RULES = (
    "readiness.direction_missing", "readiness.tokens_unpublished", "readiness.approval_not_recorded",
    "readiness.cdo_decision_pending", "readiness.cdo_decision_unverified", "readiness.migration_plan_pending",
    "readiness.live_verification_missing", "readiness.continuity_unchecked",
    "readiness.component_not_in_registry", "readiness.registry_component_ungoverned",
)


class Refused(ValueError):
    """A static rule identifier plus at most grammar-validated identifiers; never echoes input text."""

    def __init__(self, rule, *subjects):
        self.rule = rule
        self.subject = " ".join(subjects) if subjects and all(printable(item) for item in subjects) else None
        super().__init__(rule if self.subject is None else f"{rule} {self.subject}")


def printable(value):
    """Only validated identifiers may appear in output; everything else is input text."""
    if not isinstance(value, str):
        return False
    if value in LIBRARIES or value in KNOWN_ROLES:
        return True
    release = RELEASE_ID.fullmatch(value)
    if release is not None:
        return release.group(1) in LIBRARIES
    return any(grammar.fullmatch(value) for grammar in (COMPONENT, TABLETOP_ID, ISSUE_REF))


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


def digest(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def shape(value, schema, definition=None, *subjects):
    """Validate with the shared subset validator; its messages echo input, so only a rule and record ID survive."""
    try:
        selected = schema if definition is None else schema["definitions"][definition]
        support.validate_schema(value, selected, schema)
    except (ValueError, KeyError, TypeError, RecursionError, re.error):
        raise Refused("schema.invalid", *subjects) from None


def _scan(text, subject):
    require(len(text) <= TEXT_LIMIT, "content.too_long", *subject)
    require(text.strip() == text and text != "", "content.blank_or_padded", *subject)
    for rule, pattern in CONTENT_SHAPES:
        require(pattern.search(text) is None, rule, *subject)


def guard_content(document):
    """Scan every string value and key; only EXEMPT_PATHS values with their exact grammar and the schema version
    number are exempt. A record's subject is its own validated ID (component, tabletop or release)."""
    def walk(value, subject, path):
        if isinstance(value, dict):
            identifier = value.get("id")
            if path[:1] == ("releases",) and len(path) == 2:
                identifier = f"{value.get('library')}@{value.get('version')}"
            if printable(identifier):
                subject = (identifier,)
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
            # Unreachable after the schema (every other field is typed); kept so the guard alone also fails closed.
            require(path in NUMBER_PATHS, "schema.invalid", *subject)

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


def read_registry(document, sources, pin, fixture):
    """The pinned registry's (platforms, name) by C-* ID, read at the pinned commit and digest-checked."""
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
    components = registry.get("components") if isinstance(registry, dict) else None
    require(isinstance(components, list), "registry.invalid")
    pinned = {}
    for record in components:
        identifier = record.get("id") if isinstance(record, dict) else None
        require(isinstance(identifier, str) and REGISTRY_COMPONENT.fullmatch(identifier) is not None
                and identifier not in pinned and (fixture or not identifier.startswith(SYNTHETIC_PREFIX)),
                "registry.invalid")
        platforms = record.get("platforms")
        # The registry's `shared` stands for android, web and admin together and is never mixed (TS-m2).
        if platforms == ["shared"]:
            platforms = list(PLATFORMS)
        require(isinstance(platforms, list) and platforms and set(platforms) <= set(PLATFORMS), "registry.invalid")
        name = record.get("name")
        require(isinstance(name, str) and name != "", "registry.invalid")
        pinned[identifier] = (tuple(platforms), name)
    return pinned


class Policy:
    """The accepted design-gates vocabulary this contract consumes (validated by check_design_gates first)."""

    def __init__(self, data, schema):
        try:
            gates.validate_policy(data, schema)
        except (ValueError, KeyError, TypeError, RecursionError, re.error):
            raise Refused("policy.invalid") from None
        require(CDO_SCOPE in data["cdo_equivalent_scopes"] and CDO_ROLE in {r["id"] for r in data["roles"]},
                "policy.invalid")
        self.roles = frozenset(role["id"] for role in data["roles"])
        classes = {item["id"]: item for item in data["artifact_classes"]}
        self.accountable = {name: item["accountable"] for name, item in classes.items()}
        # Named library-maintainer roles: the responsible and accountable roles of the library's artifact class.
        self.maintainers = {name: frozenset(item["responsible"]) | {item["accountable"]}
                            for name, item in classes.items()}
        self.files = {item["id"]: item for item in data["topology"]["files"]}
        # Feature squads: the owner roles of the platform product files; they contribute, never publish.
        self.feature_squads = frozenset(item["owner_role"] for item in self.files.values() if item["kind"] == "product")
        self.squads = frozenset(item["squad"] for item in self.files.values())
        # The squad a role works in: the squad of the reserved file it owns (design-operations.md section 6).
        self.squad_of = {item["owner_role"]: item["squad"] for item in self.files.values()}
        self.branch = re.compile(data["topology"]["branch_pattern"])
        require(not data["access"]["public_links_enabled"] and not data["access"]["external_sharing_enabled"],
                "policy.invalid")

    def library_maintainers(self, library):
        return self.maintainers[TOPOLOGY[library][2]]


def check_libraries(document, policy):
    """Exact library set, kinds, reserved Figma locations, owners, consumption topology and publish rights."""
    libraries = {}
    for library in document["libraries"]:
        require(library["id"] not in libraries, "library.set_mismatch", library["id"])
        libraries[library["id"]] = library
    require(tuple(libraries) == LIBRARIES, "library.set_mismatch")
    for identifier, library in libraries.items():
        kind, layer, artifact, file_id, page, _ = TOPOLOGY[identifier]
        require(library["kind"] == kind, "library.kind_mismatch", identifier)
        expected = (None, None) if file_id is None else (policy.files[file_id]["name"], page)
        require((library["figma_file"], library["figma_page"]) == expected
                and (file_id is None or page in policy.files[file_id]["pages"]), "library.location_mismatch",
                identifier)
        require(library["owner_role"] == policy.accountable[artifact], "library.owner_mismatch", identifier)
        for consumed in library["consumes"]:
            require(TOPOLOGY[consumed][1] < layer, "topology.invalid_consumption", identifier, consumed)
        for needed in REQUIRED_CONSUMES[identifier]:
            require(needed in library["consumes"], "topology.missing_dependency", identifier, needed)
        for role in library["publish_roles"]:
            require(role in policy.roles, "role.unknown", identifier)
            require(identifier != "LIB-CANDIDATE", "permission.candidate_publish", identifier, role)
            require(role not in policy.feature_squads, "permission.feature_squad_publish", identifier, role)
            require(role in policy.library_maintainers(identifier), "permission.publish_not_maintainer",
                    identifier, role)
    access = document["access"]
    require(not access["public_links_enabled"], "access.public_links")
    require(not access["external_sharing_enabled"], "access.external_sharing")
    require(not access["asset_export_enabled"], "access.asset_export")
    require(access["offboarding_revokes"], "access.offboarding_not_revoking")
    return libraries


def version(value):
    return tuple(int(part) for part in SEMVER.fullmatch(value).groups())


def change_class(current, previous):
    """The class of one canonical version step, or None for any other step. design-operations.md section 6 names
    the classes by content; the arithmetic is H07's reading (a proposal): a first release is x.0.0 with x >= 1,
    then major (x+1).0.0, minor x.(y+1).0 and patch x.y.(z+1) exactly."""
    if previous is None:
        return "major" if current[0] >= 1 and current[1:] == (0, 0) else None
    major, minor, patch = previous
    return {(major + 1, 0, 0): "major", (major, minor + 1, 0): "minor", (major, minor, patch + 1): "patch"}.get(current)


def check_reference(value, *subjects):
    """A designated *_ref is null, `PenniLogic/<repo>#N` or `pending:PenniLogic/<repo>#N` (global rule 8)."""
    if value is not None:
        require(ISSUE_REF.fullmatch(value.removeprefix("pending:")) is not None, "reference.invalid", *subjects)


def check_releases(document, schema, fixture):
    """Releases keyed by (library, SemVer): version steps, breaking changes, CDO approval and rollback."""
    releases = {}
    for release in document["releases"]:
        key = (release["library"], release["version"])
        name = "@".join(key)
        require(key not in releases, "release.duplicate", name)
        releases[key] = release
        require(fixture or release["status"] == "draft", "held.publication", name)
        require(release["library"] != "LIB-CANDIDATE", "release.candidate_library", name)
    roots, successors = set(), set()
    for (library, current), release in releases.items():
        name, previous = f"{library}@{current}", release["previous"]
        require(previous is None or (library, previous) in releases, "release.previous_unknown", name)
        require(previous is None or version(current) > version(previous), "release.version_not_increasing", name)
        # One chain per library: a single root and at most one successor per release (no forks, no second root).
        link = library if previous is None else (library, previous)
        require(link not in (roots if previous is None else successors), "release.chain_invalid", name)
        (roots if previous is None else successors).add(link)
        require(not release["breaking"] or release["change_class"] == "major", "release.breaking_not_major", name)
        require(change_class(version(current), None if previous is None else version(previous))
                == release["change_class"], "release.class_mismatch", name)
        check_reference(release["migration_plan_ref"], name)
        require(not release["breaking"] or release["migration_plan_ref"] is not None,
                "release.migration_plan_missing", name)
        approval = release["cdo_approval"]
        require(release["change_class"] != "major" or approval is not None, "release.cdo_approval_missing", name)
        if approval is not None:
            shape(approval, schema, "cdo_approval", name)
            # HC-m13: no session here records a decision_coordinator decision; published data keeps `pending`.
            require(fixture or approval["status"] == "pending", "held.cdo_recorded", name)
            source = approval["decision_source"]
            require((source is None) == (approval["status"] == "pending"), "approval.source_mismatch", name)
            if source is not None:
                shape(source, schema, "source", name)
        # A rolled-back release was published before the rollback unpublished it, so the criterion 3 publication
        # prerequisites hold for it too.
        published = release["status"] in ("published", "rolled_back")
        require(not (published and approval is not None and approval["status"] == "pending"),
                "release.cdo_pending_published", name)
        # A published (or rolled-back) release never sits on an unpublished one: by induction its whole chain is
        # published, so no pending CDO decision or migration plan lies below it (criterion 3) and, the chain being
        # linear, nothing is published above a rolled-back version (the design-operations.md section 6 rollback
        # freeze).
        require(not published or previous is None or releases[(library, previous)]["status"] == "published",
                "release.previous_unpublished", name)
        require(not (published and (release["migration_plan_ref"] or "").startswith("pending:")),
                "release.migration_plan_pending_published", name)
        target = release["rollback_to"]
        if release["status"] == "rolled_back":
            # Rollback unpublishes this version and restores the prior published one; components stay listed.
            require(target is not None and target == previous and releases[(library, target)]["status"] == "published",
                    "release.rollback_target", name)
        else:
            require(target is None, "release.rollback_target", name)
    return releases


PUBLISHED = ("published", "deprecated")


def check_properties(component):
    """The property contract: names unique after normalization (case and punctuation, as the duplicate lint compares
    them); enum values and defaults; booleans default to true/false or null."""
    names = set()
    for item in component["properties"]:
        require(_normal(item["name"]) not in names, "component.property_contract", component["id"])
        names.add(_normal(item["name"]))
        if item["type"] == "enum":
            valid = len(item["values"]) >= 2 and item["default"] in (None, *item["values"])
        elif item["type"] == "boolean":
            valid = not item["values"] and item["default"] in (None, "true", "false")
        else:
            valid = not item["values"] and (item["type"] == "text" or item["default"] is None)
        require(valid, "component.property_contract", component["id"])


def check_component(component, schema, policy, releases, fixture):
    """One record's own rules: reserved IDs, library placement, holds, ownership, contract and completeness."""
    identifier, library = component["id"], component["library"]
    require(fixture or not identifier.startswith(SYNTHETIC_PREFIX), "id.synthetic_reserved", identifier)
    require(library != "LIB-FOUNDATION", "component.library_invalid", identifier)
    published = component["status"] in PUBLISHED
    require(fixture or not published, "held.publication", identifier)
    # docs#55 has not published a token grammar: no token reference can be resolved, so none is recorded.
    require(not component["token_refs"], "held.token_refs", identifier)
    require(library != "LIB-CANDIDATE" or not published, "component.candidate_published", identifier)
    # Lifecycle: a `candidate` lives in LIB-CANDIDATE and LIB-CANDIDATE holds only candidates.
    candidate = component["status"] == "candidate"
    require(candidate == (library == "LIB-CANDIDATE"), "contribution.candidate_library", identifier)
    # A candidate names its proposing owner and branch, and declares what the duplicate lint compares: omitting the
    # semantic role or property contract, or writing a placeholder name or role such as '-', cannot hide a duplicate
    # (criterion 2).
    require(not candidate or (component["owner_role"] is not None and component["proposal_branch"] is not None
                              and _worded(component["name"]) and _worded(component["semantic_role"])
                              and bool(component["properties"])),
            "contribution.candidate_incomplete", identifier)
    platform = TOPOLOGY[library][5]
    require(platform is None or component["platforms"] == [platform], "component.platform_mismatch", identifier)
    owner = component["owner_role"]
    if owner is not None:
        require(owner in policy.roles, "role.unknown", identifier)
        require(library == "LIB-CANDIDATE" or owner in policy.library_maintainers(library),
                "component.owner_not_maintainer", identifier)
    check_properties(component)
    if component["accessibility"] is not None:
        shape(component["accessibility"], schema, "accessibility", identifier)
    deprecation = component["deprecation"]
    if deprecation is not None:
        shape(deprecation, schema, "deprecation", identifier)
    require(deprecation is None or component["status"] == "deprecated", "deprecation.unexpected", identifier)
    require(deprecation is not None or component["status"] != "deprecated", "deprecation.missing", identifier)
    branch = component["proposal_branch"]
    if branch is not None:
        require(library == "LIB-CANDIDATE", "contribution.branch_outside_candidates", identifier)
        match = policy.branch.fullmatch(branch)
        require(match is not None and branch.split("__")[1] in policy.squads, "contribution.branch_grammar",
                identifier)
        # "Squad and branch identity must agree": the branch's squad is the proposing owner role's squad.
        require(owner is not None and policy.squad_of.get(owner) == branch.split("__")[1],
                "contribution.squad_mismatch", identifier)
    if published:
        # Criterion 1: owner, description, property contract, accessibility behaviour and supported platforms.
        require(owner is not None, "published.owner_missing", identifier)
        # Each text names something: a placeholder such as '-' is missing text (_worded).
        require(_worded(component["name"]), "published.name_missing", identifier)
        require(_worded(component["description"]), "published.description_missing", identifier)
        require(_worded(component["semantic_role"]), "published.semantic_role_missing", identifier)
        require(bool(component["properties"]), "published.properties_missing", identifier)
        accessibility = component["accessibility"]
        require(accessibility is not None and all(_worded(text) for text in accessibility.values()),
                "published.accessibility_missing", identifier)
        require(bool(component["platforms"]), "published.platforms_missing", identifier)
        since = component["since_version"]
        require(since is not None and releases.get((library, since), {}).get("status") == "published",
                "published.release_missing", identifier)


def _normal(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


# Function words carry no semantics: 52 of the 57 pinned registry names contain "and".
STOP_WORDS = frozenset({"a", "an", "and", "for", "of", "or", "the", "to", "with"})


def _stem(word):
    """Drop a plural ending (-ies, -es after s/ch/sh/x/z, -s) so plurals do not hide a duplicate."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith(("sses", "ches", "shes", "xes", "zes")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _tokens(text):
    return [word for word in re.findall(r"[a-z0-9]+", (text or "").lower()) if word not in STOP_WORDS]


def _words(text):
    """Stemmed content-word set, so word order, case, punctuation, function words and plurals do not hide a
    duplicate."""
    return frozenset(_stem(word) for word in _tokens(text))


def _joined(text):
    """The content words run together with the plural dropped, so camelCase and spaced spellings compare equal."""
    return _stem("".join(_tokens(text)))


def _worded(text):
    """Criterion 1 text names something: at least one run of two letters (a placeholder such as '-' does not)."""
    return text is not None and re.search(r"[A-Za-z]{2}", text) is not None


def duplicates(component, other):
    """Criterion 2 against one published record: the same name or semantic role (as word sets or run together),
    or the published property signature contained in this one together with a shared content word. An equal
    signature alone is not a duplicate: distinct components may share property names and types."""
    for field in ("name", "semantic_role"):
        words, joined = _words(component[field]), _joined(component[field])
        if (words and words == _words(other[field])) or (joined and joined == _joined(other[field])):
            return True
    signature = {(_normal(item["name"]), item["type"]) for item in component["properties"]}
    other_signature = {(_normal(item["name"]), item["type"]) for item in other["properties"]}
    shared = (_words(component["name"]) | _words(component["semantic_role"])) & (
        _words(other["name"]) | _words(other["semantic_role"]))
    return bool(other_signature) and other_signature <= signature and bool(shared)


def _family(component):
    return component["variant_of"] or component["id"]


def _counterparts(component, other, components):
    """Pairs the duplicate lint does not compare: one component family (a parent and its variants) across
    libraries; a deprecated family and its declared replacement's family; and two shared-library records whose
    platform sets are disjoint (cross-platform counterparts). Candidates and same-platform records are compared."""
    if _family(component) == _family(other) and component["library"] != other["library"]:
        return True
    for first, second in ((component, other), (other, component)):
        for record in (first, components.get(_family(first))):
            deprecation = record["deprecation"] if record is not None else None
            if deprecation is not None and deprecation["replacement"] in (second["id"], _family(second)):
                return True
    return "candidate" not in (component["status"], other["status"]) and not (
        set(component["platforms"]) & set(other["platforms"]))


def check_component_graph(components, releases):
    """Variants, deprecations (criterion 4) and the duplicate semantic component lint (criterion 2)."""
    for identifier, component in components.items():
        variant = component["variant_of"]
        if TOPOLOGY[component["library"]][5] is not None:
            target = components.get(variant)
            require(target is not None and target["library"] == "LIB-COMPONENTS"
                    and set(component["platforms"]) <= set(target["platforms"]), "component.variant_invalid",
                    identifier)
            # A published variant never carries a semantic its parent has not published.
            require(component["status"] not in PUBLISHED or target["status"] in PUBLISHED,
                    "component.variant_parent_unpublished", identifier)
        else:
            require(variant is None, "component.variant_invalid", identifier)
        deprecation = component["deprecation"]
        if deprecation is None:
            continue
        replacement = deprecation["replacement"]
        require(replacement is not None, "deprecation.replacement_missing", identifier)
        target = components.get(replacement)
        require(replacement != identifier and target is not None and target["status"] == "published"
                and target["library"] == component["library"], "deprecation.replacement_invalid", identifier)
        removal = deprecation["removal_version"]
        require(removal is not None, "deprecation.removal_version_missing", identifier)
        majors = [version(key[1])[0] for key, release in releases.items()
                  if key[0] == component["library"] and release["status"] == "published"]
        current = max(majors, default=0)
        # Removal is a breaking change, so it lands in a later major release and never before it.
        require(version(removal)[1:] == (0, 0) and version(removal)[0] > current, "deprecation.removal_version_invalid",
                identifier)
        # The removal release, when this document records it, is declared breaking, so the migration plan and the
        # CDO record of criterion 3 are required for it.
        removal_release = releases.get((component["library"], removal))
        require(removal_release is None or removal_release["breaking"], "deprecation.removal_not_breaking",
                identifier)
        require(deprecation["available_until_removal"], "deprecation.unavailable", identifier)
    # Every record is linted against every published or deprecated record of every shared library (semantic and
    # platform), except the counterparts _counterparts names.
    published = [item for item in components.values() if item["status"] in PUBLISHED]
    for identifier, component in components.items():
        for other in published:
            if other["id"] == identifier or _counterparts(component, other, components):
                continue
            require(not duplicates(component, other), "duplicate.semantic_component", identifier, other["id"])


def decide(scenario, policy, libraries):
    """The source permission model's outcome for one tabletop request; it is not Figma enforcement."""
    library, role, action = scenario["library"], scenario["role"], scenario["action"]
    if scenario["offboarded"] or role not in policy.roles:
        return "refused"  # offboarding revokes every grant and session (design-operations.md section 7)
    if action in ("public_link", "external_share", "export"):
        return "refused"  # E34-F06 (public links, external sharing) and the ticket (asset export) disable these
    if action == "publish":
        return "model_permitted" if role in libraries[library]["publish_roles"] else "refused"
    if action == "edit":
        # Feature squads contribute candidates in LIB-CANDIDATE (on their proposal branches), never by editing a
        # shared library; the library's maintainers review and edit both.
        squads = policy.feature_squads if library == "LIB-CANDIDATE" else frozenset()
        return "model_permitted" if role in policy.library_maintainers(library) | squads else "refused"
    return "model_permitted"


def check_tabletop(document, policy, libraries):
    """Synthetic permission/offboarding tabletop: never live-verified, outcomes match, required cases covered."""
    seen = set()
    for scenario in document["tabletop"]:
        identifier = scenario["id"]
        require(identifier not in seen, "tabletop.duplicate", identifier)
        seen.add(identifier)
        require(not scenario["live_verified"], "tabletop.live_claim", identifier)
        require(scenario["role"] in policy.roles, "role.unknown", identifier)
        require(decide(scenario, policy, libraries) == scenario["expected"], "tabletop.outcome_mismatch", identifier)
    scenarios = document["tabletop"]
    for library in SHARED:
        require(any(item["action"] == "publish" and item["library"] == library and item["role"] in policy.feature_squads
                    and not item["offboarded"] for item in scenarios), "tabletop.coverage_missing", library)
        require(any(item["action"] == "publish" and item["library"] == library and item["offboarded"]
                    and item["role"] in policy.library_maintainers(library) for item in scenarios),
                "tabletop.coverage_missing", library)
    for action in ("public_link", "external_share", "export"):
        require(any(item["action"] == action for item in scenarios), "tabletop.coverage_missing")
    # The contribution path itself: a feature squad edits its candidate in LIB-CANDIDATE.
    require(any(item["action"] == "edit" and item["library"] == "LIB-CANDIDATE" and not item["offboarded"]
                and item["role"] in policy.feature_squads for item in scenarios), "tabletop.coverage_missing",
            "LIB-CANDIDATE")


def check_approvals(document):
    """DoD 2: exactly one record per required role, each `not_recorded` or `pending` (never recorded here)."""
    roles = [item["role"] for item in document["approvals"]]
    require(sorted(roles) == sorted(APPROVAL_ROLES) and len(set(roles)) == len(roles), "approval.roles_mismatch")


class Model:
    """The structurally checked document and the pinned registry's component IDs."""

    def __init__(self, document, libraries, releases, components, pinned):
        self.document, self.libraries, self.releases = document, libraries, releases
        self.components, self.pinned = components, pinned


def check(document, schema, policy_data, policy_schema, sources, pin=None, fixture=False):
    """Every structure rule, fail closed; `fixture` (tests only, never the CLI) admits C-SYN-* IDs, publication and
    recorded CDO approvals so the published-component and release rules can be exercised synthetically."""
    pin = REGISTRY_PIN if pin is None else pin
    shape(document, schema)
    guard_content(document)
    policy = Policy(policy_data, policy_schema)
    # The docs#76 direction decision and the docs#55 token grammar are held: neither can be referenced yet.
    require(document["direction_ref"] is None, "held.direction_ref")
    pinned = read_registry(document, sources, pin, fixture)
    libraries = check_libraries(document, policy)
    releases = check_releases(document, schema, fixture)
    for identifier, library in libraries.items():
        # Governed shells are published empty before component work; an active library has a published release.
        released = any(key[0] == identifier and item["status"] == "published" for key, item in releases.items())
        # A rollback freezes its library (read-only, promotion stopped); only a rollback freezes a library.
        rolled = any(key[0] == identifier and item["status"] == "rolled_back" for key, item in releases.items())
        require(rolled == (library["status"] == "frozen"), "library.freeze_mismatch", identifier)
        require(rolled or released == (library["status"] == "active"), "library.status_mismatch", identifier)
    components, branches = {}, set()
    for component in document["components"]:
        require(component["id"] not in components, "id.duplicate", component["id"])
        components[component["id"]] = component
        check_component(component, schema, policy, releases, fixture)
        # A reused branch stops promotion (design-operations.md section 6): one proposal branch, one record.
        branch = component["proposal_branch"]
        require(branch is None or branch not in branches, "contribution.branch_duplicate", component["id"])
        branches.add(branch)
        # A record keyed by a pinned registry ID supports exactly the platforms the registry assigns to it.
        require(component["id"] not in pinned or set(component["platforms"]) == set(pinned[component["id"]][0]),
                "component.registry_platform_mismatch", component["id"])
        # The registry owns the name of a pinned ID; a record copies it verbatim (re-pins surface renames).
        require(component["id"] not in pinned or component["name"] == pinned[component["id"]][1],
                "component.registry_name_mismatch", component["id"])
    check_component_graph(components, releases)
    check_tabletop(document, policy, libraries)
    check_approvals(document)
    return Model(document, libraries, releases, components, pinned)


def readiness(model):
    """Every visible gap by static rule: sorted, de-duplicated subjects; never filled in or waived."""
    gaps = {rule: set() for rule in READINESS_RULES}
    document = model.document
    if document["direction_ref"] is None:
        gaps["readiness.direction_missing"].add(DIRECTION_ISSUE)
    # Token references stay empty until docs#55 publishes a grammar.
    gaps["readiness.tokens_unpublished"].add(TOKENS_ISSUE)
    for item in document["approvals"]:
        gaps["readiness.approval_not_recorded"].add(item["role"])
    for (library, current), release in model.releases.items():
        approval = release["cdo_approval"]
        if approval is not None:
            # A recorded decision cannot be resolved offline yet, so it stays a gap rather than a pass.
            rule = "readiness.cdo_decision_pending" if approval["status"] == "pending" else \
                "readiness.cdo_decision_unverified"
            gaps[rule].add(f"{library}@{current}")
        if (release["migration_plan_ref"] or "").startswith("pending:"):
            # Global rule 8: a `pending:` reference is a visible gap until the plan exists.
            gaps["readiness.migration_plan_pending"].add(f"{library}@{current}")
    for library in SHARED:
        # Live evidence per governed shared library (feature-squad publish denial, maintainer offboarding revocation,
        # link/export/external-access audit); the synthetic tabletop never closes it (`tabletop.live_claim`).
        gaps["readiness.live_verification_missing"].add(library)
        # One document is checked, never its base revision: an in-place contract change, or the removal or reversion
        # of a published or deprecated record, is not detected until a later checker change adds that comparison.
        gaps["readiness.continuity_unchecked"].add(library)
    gaps["readiness.component_not_in_registry"].update(set(model.components) - set(model.pinned))
    gaps["readiness.registry_component_ungoverned"].update(set(model.pinned) - set(model.components))
    return {rule: sorted(subjects) for rule, subjects in gaps.items()}


def structure_line(model):
    document, components = model.document, model.components.values()
    return (
        f"Figma library governance {document['contract_version']} structure valid: {len(model.libraries)} libraries, "
        f"{len(model.releases)} releases, {len(model.components)} components "
        f"({sum(item['status'] in PUBLISHED for item in components)} published or deprecated), "
        f"{len(document['tabletop'])} tabletop scenarios (not live-verified), {len(document['approvals'])} approvals "
        f"required; registry pin {len(model.pinned)} components"
    )


MIRROR = "governance/figma-library-governance.md"
MIRROR_BEGIN = "<!-- BEGIN GENERATED: governance/figma-libraries.json (check_figma_libraries.py --mirror) -->"
MIRROR_END = "<!-- END GENERATED: governance/figma-libraries.json -->"
# Free text cannot break a table cell or the generated-section markers, nor add emphasis, strikethrough, code or
# links; `_` is escaped where it could open or close emphasis (intraword `_`, as in role IDs, cannot).
_CELL_ESCAPES = str.maketrans({character: "\\" + character for character in "\\|`*[]~"}
                              | {"&": "&amp;", "<": "&lt;", ">": "&gt;"})
_EMPHASIS_UNDERSCORE = re.compile(r"(?<![A-Za-z0-9])_|_(?![A-Za-z0-9])")


def cell(value):
    """One Markdown table cell: escaped free text, a hyphen for null or empty, lists joined by commas."""
    if value is None or value == []:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        value = ", ".join(value)
    return _EMPHASIS_UNDERSCORE.sub(r"\\_", str(value).translate(_CELL_ESCAPES))


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(cell(value) for value in row) + " |" for row in rows]
    return lines


def platforms_of(component):
    return [platform for platform in PLATFORMS if platform in component["platforms"]]


def render_mirror(model):
    """The governance document's generated section: a deterministic rendering of the validated JSON only."""
    document = model.document
    lines = [MIRROR_BEGIN, "", f"Contract version {document['contract_version']}; registry pin "
             f"{document['registry_ref']['commit']} {cell(document['registry_ref']['path'])}; direction reference "
             f"{cell(document['direction_ref'])}.", "", "### Library topology", ""]
    lines += table(("Library", "Kind", "Layer", "Figma file", "Figma page", "Owner role", "Publish roles", "Consumes",
                    "Status"),
                   [(key, item["kind"], str(TOPOLOGY[key][1]), item["figma_file"], item["figma_page"],
                     item["owner_role"], item["publish_roles"], item["consumes"], item["status"])
                    for key, item in model.libraries.items()])
    # Library level only: records carry no component-to-component dependency, so that part of D14 is held.
    lines += ["", "### D14 library consumption and variant map (library level)", ""]
    for key, item in model.libraries.items():
        members = sorted(identifier for identifier, component in model.components.items()
                         if component["library"] == key)
        variants = sorted(f"{identifier} of {component['variant_of']}" for identifier, component
                          in model.components.items() if component["library"] == key and component["variant_of"])
        lines.append(f"- {key} consumes {cell(item['consumes'])}; {len(members)} component records; "
                     f"variants: {cell(variants)}")
    lines += ["", "### Releases", ""]
    lines += table(("Release", "Previous", "Change", "Breaking", "Status", "Migration plan", "CDO approval",
                    "Rollback to"),
                   [(f"{library}@{current}", item["previous"], item["change_class"], item["breaking"], item["status"],
                     item["migration_plan_ref"], (item["cdo_approval"] or {}).get("status"), item["rollback_to"])
                    for (library, current), item in model.releases.items()])
    lines += ["", "### Component records and proposed placement", ""]
    lines += table(("Component", "Name", "Library", "Status", "Platforms", "Variant of", "Owner role",
                    "In registry pin"),
                   [(identifier, item["name"], item["library"], item["status"], platforms_of(item), item["variant_of"],
                     item["owner_role"], identifier in model.pinned) for identifier, item in model.components.items()])
    lines += ["", "### Permission and offboarding tabletop (synthetic, not live-verified)", ""]
    lines += table(("Scenario", "Action", "Role", "Library", "Offboarded", "Expected", "Live verified"),
                   [(item["id"], item["action"], item["role"], item["library"], item["offboarded"], item["expected"],
                     item["live_verified"]) for item in document["tabletop"]])
    lines += ["", "### Required approvals", ""]
    lines += table(("Role", "Status"), [(item["role"], item["status"]) for item in document["approvals"]])
    lines += ["", "### Readiness gaps (default mode)", ""]
    gaps = readiness(model)
    lines += table(("Rule", "Count"), [(rule, str(len(gaps[rule]))) for rule in READINESS_RULES])
    lines += ["", MIRROR_END]
    return "\n".join(lines) + "\n"


def mirror_section(text):
    """The generated section of the governance document, markers included, or None when absent or ambiguous."""
    if text.count(MIRROR_BEGIN) != 1 or text.count(MIRROR_END) != 1:
        return None
    start, end = text.index(MIRROR_BEGIN), text.index(MIRROR_END) + len(MIRROR_END) + 1
    return text[start:end] if start < end <= len(text) and text[end - 1] == "\n" else None


def load_and_check(root):
    root = Path(root)
    return check(
        support.load_json(root / DATA), support.load_json(root / SCHEMA),
        support.load_json(root / GATES), support.load_json(root / gates.SCHEMA), GitSources(root),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--structure", action="store_true", help="Check structure only; readiness is not evaluated.")
    mode.add_argument("--mirror", action="store_true",
                      help="Check structure, then print the governance document's generated section (writes nothing).")
    args = parser.parse_args(argv)
    try:
        model = load_and_check(ROOT)
        if args.mirror:
            sys.stdout.write(render_mirror(model))
            return 0
        if args.structure:
            print(structure_line(model) + "; readiness not evaluated.")
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
        print(f"Figma library check refused: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, RecursionError, re.error):
        # Fail closed without a traceback, whose message could echo input content.
        print("Figma library check refused: input.unreadable_or_invalid", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
