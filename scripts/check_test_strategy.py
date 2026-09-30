"""Validate the published test strategy and reconcile every verification category with its owner.

PenniLogic/docs#22 publishes the test strategy as data in governance/test-strategy.json (JSON Schema
in governance/test-strategy.schema.json, prose in governance/test-strategy.md). Every verification
category names the public issue that owns its executable evidence, every named package carries a
numeric line and branch floor and, on money paths, a mutation floor, and the flake, retry, pipeline
and performance numbers live in the data file so the harnesses read them instead of restating them.

The reconciliation runs offline against planning/issue-inventory.json, a committed snapshot of the
public issue inventory, because CI has no network access to GitHub and no token. A category with no
owner, an owner reference that does not resolve to a snapshotted issue, an owner that carries a
different plan identity than the strategy expects, an owner closed as not planned, a named package
with no published number, a money-path floor in a repository with neither a mutation owner nor a
recorded enforcement gap, or a gate assertion of the client state taxonomy with no category all fail
the check.

`--refresh-inventory` regenerates the snapshot from the live API through the stored `gh` credential
of `basiltt`. It removes the inherited token variables from the child process, verifies the login,
the organization id and every repository id, and never reads, prints or stores a token.
"""

import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
STRATEGY = "governance/test-strategy.json"
SCHEMA = "governance/test-strategy.schema.json"
DOCUMENT = "governance/test-strategy.md"
INVENTORY = "planning/issue-inventory.json"
# The client state taxonomy supplies the state identifiers and gate assertions the strategy must cover.
TAXONOMY_DATA = "product/client-state-taxonomy.json"
TAXONOMY_DOCUMENT = "product/client-state-taxonomy.md"
# The canonical Definition of Ready and Done; this strategy only adds test-evidence requirements to it.
DELIVERY_PLAN = "product/03-delivery-plan.md"
REFRESH_COMMAND = "python scripts/check_test_strategy.py --refresh-inventory"
GH_TIMEOUT_SECONDS = 180

ORGANIZATION = "PenniLogic"
ORGANIZATION_ID = 335295566
OPERATOR = "basiltt"
OPERATOR_ID = 54134686
REPOSITORY_IDS = {
    "PenniLogic/.github": 1394134381,
    "PenniLogic/docs": 1394134442,
    "PenniLogic/contracts": 1394134505,
    "PenniLogic/api": 1394134582,
    "PenniLogic/ai-service": 1394134652,
    "PenniLogic/android": 1394134737,
    "PenniLogic/web": 1394134850,
    "PenniLogic/admin": 1394135000,
    "PenniLogic/infra": 1394135059,
}
REPOSITORY_ORDER = {name: index for index, name in enumerate(REPOSITORY_IDS)}
TOKEN_VARIABLES = ("GH_TOKEN", "GITHUB_TOKEN", "GIT_CONFIG_PARAMETERS")

# The backlog ticket reference format both the strategy and the inventory conform to.
REFERENCE = re.compile(
    r"^PenniLogic/(" + "|".join(re.escape(name.split("/")[1]) for name in REPOSITORY_IDS) + r")#([1-9][0-9]*)$"
)
SOURCE_REFERENCE = re.compile(r"^PenniLogic-old/([A-Za-z0-9_.-]+)#([1-9][0-9]*)$")
PLAN_ID = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*$")
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
PACKAGE_ID = re.compile(r"^([a-z][a-z0-9_]*)\.([a-z][a-z0-9_]*)$")
# Markers the published issue bodies carry; the refresh derives identity from them, never from titles.
PLAN_MARKER = re.compile(r"<!-- plan-id: ([A-Z][A-Z0-9-]*) -->")
SOURCE_MARKER = re.compile(
    r"Original specification: \[?https://github\.com/PenniLogic-old/([A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)"
)
TOKEN_SHAPE = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{10,}|github_pat_[A-Za-z0-9_]{10,})\b")

STATES = ("open", "closed")
STATE_REASONS = (None, "completed", "not_planned", "duplicate", "reopened")
# A closed owner with one of these reasons has renounced the work, so the category is unowned.
UNOWNED_REASONS = ("not_planned", "duplicate")

REQUIRED_CATEGORIES = (
    "unit_tests", "domain_ledger_property", "debt_maths_independent_model", "mutation_testing",
    "parser_golden_corpus", "api_contract", "contract_provider_consumer", "android_unit_instrumented",
    "web_e2e_journeys", "admin_e2e_journeys", "accessibility_conformance", "performance_budgets",
    "security_negative_tests", "log_redaction_gate", "static_dependency_secret_gates", "security_regression_smoke",
    "supply_chain_verification", "load_stress_soak", "chaos_fault_injection", "disaster_recovery_restore",
    "privacy_traffic_inspection", "billing_webhook_replay", "model_evaluation", "threat_model_refresh",
    "penetration_test", "flaky_test_quarantine", "client_state_coverage", "client_state_taxonomy_first",
    "release_evidence_gates", "strategy_reconciliation",
)
# Phrases a category's text must keep, so a review-mandated scope cannot be quietly dropped later.
# Matching is case-insensitive on the named field.
REQUIRED_CATEGORY_PHRASES = {
    "security_negative_tests": {
        "approach": (
            "cross-tenant", "object authorization", "mass assignment", "authentication bypass", "token replay",
            "entitlement tampering", "rate limiting", "lockout", "credential stuffing", "step-up",
            "default deny", "expired grant", "aggregate-versus-detail", "differencing",
        ),
        "evidence": ("negative test per gated feature", "per grant scope", "step-up replay"),
    },
    "log_redaction_gate": {
        "approach": ("field allowlist", "static rule", "runtime scan", "planted money value", "fail-closed", "exception messages", "before upload"),
        "evidence": ("planted money value",),
    },
    "accessibility_conformance": {
        "approach": ("section 8", "switch access", "accessibility test framework", "lint"),
        "evidence": ("unannounced state",),
    },
    "client_state_coverage": {"evidence": ("section 8",)},
}
# Change classes that must carry a category, because the reviewers found the class incomplete without it.
REQUIRED_MANDATORY_CATEGORIES = {
    "money_path": ("unit_tests", "domain_ledger_property", "mutation_testing", "debt_maths_independent_model", "log_redaction_gate"),
    "api_service": ("log_redaction_gate", "security_negative_tests"),
    "billing": ("log_redaction_gate", "security_negative_tests", "mutation_testing"),
    "security_boundary": ("security_negative_tests", "log_redaction_gate", "threat_model_refresh"),
    "android_client": ("accessibility_conformance", "client_state_coverage", "client_state_taxonomy_first"),
    "web_client": ("accessibility_conformance", "client_state_coverage", "client_state_taxonomy_first"),
    "admin_console": ("accessibility_conformance", "client_state_coverage", "client_state_taxonomy_first"),
}
REQUIRED_DELIVERABLES = ("independent_model_harness", "red_team_scenarios", "physical_test_device")
REQUIRED_MONEY_DOMAINS = ("ledger", "debt", "budget", "split")
REQUIRED_READY_ITEMS = ("threat_model_refreshed", "privacy_payload_reviewed")
REQUIRED_DONE_ITEMS = ("coverage_floors_met", "mutation_floor_met", "flake_policy_respected")
REQUIRED_CHANGE_CLASSES = (
    "money_path", "parser", "contract", "api_service", "security_boundary", "billing",
    "android_client", "web_client", "admin_console",
)
REQUIRED_DEVICE_LANES = (
    "emulator_api_31", "emulator_current", "emulator_large_text", "emulator_talkback", "physical_mid_range_indian_sim",
)
# No lane is ever recorded as running: an emulator lane is provisionable on the hosted runner until the
# Android gate wires it, and a hardware lane is required until its procurement is done.
LANE_AVAILABILITY = ("provisionable_in_ci", "required_not_yet_available")
LANE_AVAILABILITY_TEXT = {
    "provisionable_in_ci": "provisionable in CI, not yet running",
    "required_not_yet_available": "required, not yet available",
}
PHYSICAL_DEVICE_LANE = "physical_mid_range_indian_sim"
PHYSICAL_DEVICE_PROCUREMENT = "T-QA-07"
THREAT_MODEL_OWNER = "T-QA-14"
ACCESSIBILITY_TARGET = {"standard": "WCAG", "version": "2.2", "level": "AA"}
ACCESSIBILITY_PHRASE = "WCAG 2.2 AA"
# The document must state the target as a sentence, not only reference the standard as a goal.
CONFORMANCE_STATEMENT = "The conformance target is WCAG 2.2 AA."
# The automated bar is conformance, not "critical only": axe-style impact levels put contrast and target
# size at serious, so a critical-only gate would pass the very defects the signal promises to catch.
AUTOMATED_GATE_STATEMENT = (
    "zero violations at any impact level for rules tagged WCAG 2.0, 2.1 and 2.2 Level A and AA on the core "
    "journeys; best-practice rules that are not WCAG success criteria are advisory; an exception requires a "
    "recorded reason and an expiry on the pull request"
)
AUTOMATED_GATE_PHRASE = "zero violations at any impact level for rules tagged WCAG 2.0, 2.1 and 2.2 Level A and AA"
FORBIDDEN_ACCESSIBILITY_PHRASES = ("critical violations", "keyboard-only or switch", "keyboard or switch access completing")
REQUIRED_BROWSER_CONFIGURATIONS = ("200 percent zoom", "prefers-reduced-motion: reduce", "forced-colors: active")
REQUIRED_WCAG_NAMED_CHECKS = ("3.3.1 Error Identification", "4.1.3 Status Messages")
REQUIRED_WCAG_2_2_NAMED_CHECKS = ("2.5.8 Target Size (Minimum)", "3.3.8 Accessible Authentication (Minimum)")
ANDROID_MECHANISM_PHRASES = ("accessibility test framework", "lint", "pinned")
EVIDENCE_NAME = re.compile(r"^[a-z][a-z0-9-]*__[a-z][a-z0-9_]*__[0-9a-f]{12}__[0-9]{8}\.[a-z0-9]+$")

ISSUES_QUERY = """
query($owner: String!, $name: String!, $after: String) {
  repository(owner: $owner, name: $name) {
    databaseId
    issues(first: 100, after: $after, states: [OPEN, CLOSED], orderBy: {field: CREATED_AT, direction: ASC}) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { number title state stateReason body }
    }
  }
}
"""


def load_json(path):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"Duplicate JSON key {key!r} in {path.name}")
            value[key] = item
        return value
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def load_check(name):
    """Load a sibling check module by path so this script works from any working directory."""
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_reference(reference):
    """Split `PenniLogic/<repository>#<number>`; anything else is not a valid owner reference."""
    match = REFERENCE.match(reference) if isinstance(reference, str) else None
    if not match:
        raise ValueError(
            f"Reference {reference!r} is not of the form PenniLogic/<repository>#<number>; "
            "bare repo#N identifiers are PenniLogic-old identities and do not own anything here"
        )
    return f"{ORGANIZATION}/{match.group(1)}", int(match.group(2))


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _percent(value, label):
    if value is None:
        raise ValueError(f"{label} has no published number")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
        raise ValueError(f"{label} must be a number between 0 and 100, not {value!r}")
    return value


def _count(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{label} must be an integer of at least {minimum}, not {value!r}")
    return value


def _timestamp(value):
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        raise ValueError(f"Timestamp {value!r} is not of the form YYYY-MM-DDTHH:MM:SSZ") from None


def _unique_ids(items, label, pattern=IDENTIFIER):
    if not isinstance(items, list) or not items:
        raise ValueError(f"No {label} entries published")
    if not all(isinstance(item, dict) for item in items):
        raise ValueError(f"Every {label} entry must be an object")
    ids = [item.get("id") for item in items]
    for identifier in ids:
        if not isinstance(identifier, str) or not pattern.match(identifier):
            raise ValueError(f"Invalid {label} identifier {identifier!r}")
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate {label} identifier")
    return {item["id"]: item for item in items}


# --- inventory -----------------------------------------------------------------------------------

def validate_inventory(inventory):
    """Validate the committed snapshot and return its issues indexed by public reference."""
    if inventory.get("schema_version") != 1:
        raise ValueError("Inventory schema_version must be 1")
    if inventory.get("organization") != ORGANIZATION or inventory.get("organization_id") != ORGANIZATION_ID:
        raise ValueError(f"Inventory must be a snapshot of {ORGANIZATION} (id {ORGANIZATION_ID})")
    if inventory.get("operator") != OPERATOR:
        raise ValueError(f"Inventory must be refreshed as {OPERATOR}")
    _timestamp(inventory.get("snapshot_at"))
    repositories = inventory.get("repositories")
    if not isinstance(repositories, dict) or set(repositories) != set(REPOSITORY_IDS):
        raise ValueError("Inventory must cover exactly the nine public repositories")
    for name, record in repositories.items():
        if not isinstance(record, dict) or record.get("id") != REPOSITORY_IDS[name]:
            raise ValueError(f"Inventory repository {name} does not carry id {REPOSITORY_IDS[name]}")
        # planning/README.md rule 1: the drained count is recorded beside the connection's totalCount.
        if record.get("total_count") != record.get("issue_count") or isinstance(record.get("issue_count"), bool):
            raise ValueError(f"Inventory repository {name} does not record total_count equal to its drained issue_count")
    issues = inventory.get("issues")
    if not isinstance(issues, list) or not issues:
        raise ValueError("Inventory has no issues")
    index = {}
    plan_ids = {}
    counts = dict.fromkeys(REPOSITORY_IDS, 0)
    for issue in issues:
        if not isinstance(issue, dict):
            raise ValueError("Inventory issue is not an object")
        reference = issue.get("reference")
        repository, number = parse_reference(reference)
        if issue.get("repository") != repository or issue.get("number") != number or isinstance(issue.get("number"), bool):
            raise ValueError(f"Inventory issue {reference} disagrees with its repository or number")
        if reference in index:
            raise ValueError(f"Duplicate inventory issue {reference}")
        if not _text(issue.get("title")):
            raise ValueError(f"Inventory issue {reference} has no title")
        state, reason = issue.get("state"), issue.get("state_reason")
        if state not in STATES:
            raise ValueError(f"Inventory issue {reference} has unknown state {state!r}")
        if reason not in STATE_REASONS:
            raise ValueError(f"Inventory issue {reference} has unknown state_reason {reason!r}")
        if state == "open" and reason not in (None, "reopened"):
            raise ValueError(f"Inventory issue {reference} is open with a closed-state reason {reason!r}")
        source = issue.get("source")
        if source is not None and not SOURCE_REFERENCE.match(source):
            raise ValueError(f"Inventory issue {reference} has a malformed source identity {source!r}")
        plan_id = issue.get("plan_id")
        if plan_id is not None:
            if not isinstance(plan_id, str) or not PLAN_ID.match(plan_id):
                raise ValueError(f"Inventory issue {reference} has a malformed plan identity {plan_id!r}")
            if plan_id in plan_ids:
                raise ValueError(f"Plan identity {plan_id} is carried by both {plan_ids[plan_id]} and {reference}")
            plan_ids[plan_id] = reference
        index[reference] = issue
        counts[repository] += 1
    if inventory.get("issue_count") != len(index):
        raise ValueError("Inventory issue_count does not match its issues")
    for name, record in repositories.items():
        if record.get("issue_count") != counts[name]:
            raise ValueError(f"Inventory repository {name} issue_count does not match its issues")
    return index


def identities(issue):
    """The identities an owner may claim for an issue: its plan id, its source, or itself if it has neither."""
    known = [value for value in (issue.get("plan_id"), issue.get("source")) if value]
    return known or [issue["reference"]]


def resolve_owner(owner, index, label):
    """An owner must resolve to a snapshotted issue that carries the claimed identity and still owns work."""
    if not isinstance(owner, dict):
        raise ValueError(f"{label}: owner must be an object with reference and identity")
    reference = owner.get("reference")
    parse_reference(reference)
    issue = index.get(reference)
    if issue is None:
        raise ValueError(f"{label}: owner {reference} does not resolve to an issue in the inventory (dangling identifier)")
    identity = owner.get("identity")
    if identity not in identities(issue):
        raise ValueError(
            f"{label}: owner {reference} carries identity {'/'.join(identities(issue))}, not {identity!r}; "
            "the number points at a different issue than the strategy intends"
        )
    if issue["state"] == "closed" and issue.get("state_reason") in UNOWNED_REASONS:
        raise ValueError(f"{label}: owner {reference} is closed as {issue['state_reason']} and owns nothing")
    return issue


def _resolve_owners(item, index, label):
    owners = item.get("owners")
    if not isinstance(owners, list) or not owners:
        raise ValueError(f"{label} has no owning issue; a category asserted without an executable owner fails")
    seen = set()
    resolved = []
    for owner in owners:
        issue = resolve_owner(owner, index, label)
        if issue["reference"] in seen:
            raise ValueError(f"{label} names owner {issue['reference']} twice")
        seen.add(issue["reference"])
        resolved.append(issue)
    return resolved


# --- strategy -----------------------------------------------------------------------------------

def _require_phrases(text, phrases, label):
    lowered = text.lower()
    for phrase in phrases:
        if phrase.lower() not in lowered:
            raise ValueError(f"{label} must keep the phrase {phrase!r}")


def _check_categories(strategy, index, taxonomy_assertions):
    categories = _unique_ids(strategy["categories"], "category")
    for missing in [name for name in REQUIRED_CATEGORIES if name not in categories]:
        raise ValueError(f"Missing required verification category: {missing}")
    owners = set()
    claimed = {}
    for category_id, category in categories.items():
        label = f"Category {category_id}"
        for key in ("name", "layer", "approach", "evidence"):
            if not _text(category.get(key)):
                raise ValueError(f"{label} has no {key}")
        for key, phrases in REQUIRED_CATEGORY_PHRASES.get(category_id, {}).items():
            _require_phrases(category[key], phrases, f"{label} {key}")
        assertion = category.get("taxonomy_assertion")
        if assertion is not None:
            if assertion in claimed:
                raise ValueError(f"Taxonomy assertion {assertion} is claimed by both {claimed[assertion]} and {category_id}")
            if assertion not in taxonomy_assertions:
                raise ValueError(f"{label} claims unknown taxonomy assertion {assertion!r}")
            claimed[assertion] = category_id
        for issue in _resolve_owners(category, index, label):
            owners.add(issue["reference"])
    # Every gate assertion the client state taxonomy publishes must be a category here, so a client
    # change class cannot under-state the evidence the taxonomy already requires of the same gates.
    for assertion in taxonomy_assertions:
        if assertion not in claimed:
            raise ValueError(f"Taxonomy coverage assertion {assertion!r} is not covered by any category")
    return categories, owners


def _check_deliverables(strategy, index):
    deliverables = _unique_ids(strategy["deliverables"], "deliverable")
    for missing in [name for name in REQUIRED_DELIVERABLES if name not in deliverables]:
        raise ValueError(f"Missing required deliverable: {missing}")
    for deliverable_id, deliverable in deliverables.items():
        label = f"Deliverable {deliverable_id}"
        if not _text(deliverable.get("name")) or not _text(deliverable.get("description")):
            raise ValueError(f"{label} has no name or description")
        _resolve_owners(deliverable, index, label)
    return deliverables


def _check_change_classes(strategy, categories):
    classes = _unique_ids(strategy["change_classes"], "change class")
    for missing in [name for name in REQUIRED_CHANGE_CLASSES if name not in classes]:
        raise ValueError(f"Missing required change class: {missing}")
    for class_id, change_class in classes.items():
        label = f"Change class {class_id}"
        if not _text(change_class.get("description")):
            raise ValueError(f"{label} has no description")
        mandatory = change_class.get("mandatory_categories")
        if not isinstance(mandatory, list) or not mandatory or len(mandatory) != len(set(mandatory)):
            raise ValueError(f"{label} must name at least one mandatory category, each once")
        for category_id in mandatory:
            if category_id not in categories:
                raise ValueError(f"{label} names unknown category {category_id!r}")
        if not isinstance(change_class.get("manual_evidence"), list):
            raise ValueError(f"{label} must list its manual evidence, possibly empty")
    for class_id, required in REQUIRED_MANDATORY_CATEGORIES.items():
        for category_id in required:
            if category_id not in classes[class_id]["mandatory_categories"]:
                raise ValueError(f"Change class {class_id} must make {category_id} mandatory")
    return classes


def _check_mutation_enforcement(policy, packages, categories):
    """A money-path floor in repository X needs a mutation owner in X, or an explicit recorded gap."""
    money_by_repository = {}
    for package_id, package in packages.items():
        if package["money_path"]:
            money_by_repository.setdefault(package["repository"], set()).add(package_id)
    owner_repositories = {
        parse_reference(owner["reference"])[0] for owner in categories["mutation_testing"]["owners"]
    }
    gaps = policy.get("mutation_enforcement_gaps")
    if not isinstance(gaps, list):
        raise ValueError("floor_policy.mutation_enforcement_gaps must be a list, possibly empty")
    recorded = {}
    for gap in gaps:
        if not isinstance(gap, dict):
            raise ValueError("floor_policy.mutation_enforcement_gaps entries must be objects")
        repository = gap.get("repository")
        if repository in recorded:
            raise ValueError(f"Mutation enforcement gap for {repository} is recorded twice")
        if repository not in money_by_repository:
            raise ValueError(f"Mutation enforcement gap for {repository} names a repository with no money-path package")
        if repository in owner_repositories:
            raise ValueError(f"Mutation enforcement gap for {repository} is stale: a mutation_testing owner exists there")
        if set(gap.get("packages") or []) != money_by_repository[repository]:
            raise ValueError(f"Mutation enforcement gap for {repository} must list exactly its money-path packages")
        for key in ("reason", "resolution"):
            if not _text(gap.get(key)):
                raise ValueError(f"Mutation enforcement gap for {repository} has no {key}")
        recorded[repository] = gap
    for repository, package_ids in sorted(money_by_repository.items()):
        if repository not in owner_repositories and repository not in recorded:
            raise ValueError(
                f"Money-path packages {', '.join(sorted(package_ids))} carry mutation floors but {repository} has no "
                "mutation_testing owner and no recorded enforcement gap"
            )
    return recorded


def _check_packages(strategy, categories):
    packages = _unique_ids(strategy["packages"], "package", PACKAGE_ID)
    policy = strategy["floor_policy"]
    money_minimum, other_minimum = policy["money_path_minimum"], policy["other_minimum"]
    for key in ("line", "branch", "mutation"):
        _percent(money_minimum.get(key), f"floor_policy.money_path_minimum.{key}")
    for key in ("line", "branch"):
        _percent(other_minimum.get(key), f"floor_policy.other_minimum.{key}")
    if policy.get("money_path_ratchet") is not True:
        raise ValueError("floor_policy.money_path_ratchet must be true: money-path coverage may not decline")
    if not _text(policy.get("mutation_enforcement_rule")):
        raise ValueError("floor_policy.mutation_enforcement_rule must be stated")
    domains = set()
    money_count = 0
    for package_id, package in packages.items():
        label = f"Package {package_id}"
        match = PACKAGE_ID.match(package_id)
        repository = package.get("repository")
        if repository not in REPOSITORY_IDS or repository.split("/")[1].replace("-", "_") != match.group(1):
            raise ValueError(f"{label}: identifier prefix must be the repository short name of {repository!r}")
        if not _text(package.get("description")):
            raise ValueError(f"{label} has no description")
        money = package.get("money_path")
        if not isinstance(money, bool):
            raise ValueError(f"{label}: money_path must be true or false")
        line = _percent(package.get("line_coverage_floor_percent"), f"{label} line coverage floor")
        branch = _percent(package.get("branch_coverage_floor_percent"), f"{label} branch coverage floor")
        mutation = package.get("mutation_score_floor_percent")
        if money:
            money_count += 1
            if mutation is None:
                raise ValueError(
                    f"{label} is a money-path package with no published mutation-score floor; "
                    "a package without a mutation floor may not carry money-path code"
                )
            _percent(mutation, f"{label} mutation score floor")
            minimum = money_minimum
            if mutation < minimum["mutation"]:
                raise ValueError(f"{label}: mutation floor {mutation} is below the money-path minimum {minimum['mutation']}")
            domains.add(package.get("domain"))
        else:
            if mutation is not None:
                _percent(mutation, f"{label} mutation score floor")
            minimum = other_minimum
        if line < minimum["line"] or branch < minimum["branch"]:
            raise ValueError(
                f"{label}: floors {line}/{branch} are below the published minimum "
                f"{minimum['line']}/{minimum['branch']} for its class"
            )
    for domain in REQUIRED_MONEY_DOMAINS:
        if domain not in domains:
            raise ValueError(
                f"No money-path package carries the {domain} domain; ledger, debt, budget and split "
                "must each be a money-path package with a mutation floor"
            )
    gaps = _check_mutation_enforcement(policy, packages, categories)
    return packages, money_count, gaps


def _check_flake_policy(policy):
    _percent(policy.get("quarantine_rate_ceiling_percent"), "flake_policy.quarantine_rate_ceiling_percent")
    _count(policy.get("retry_limit"), "flake_policy.retry_limit")
    _count(policy.get("money_path_retry_limit"), "flake_policy.money_path_retry_limit")
    if policy["money_path_retry_limit"] > policy["retry_limit"]:
        raise ValueError("flake_policy.money_path_retry_limit may not exceed the general retry limit")
    _count(policy.get("quarantine_after_flakes"), "flake_policy.quarantine_after_flakes", 1)
    _count(policy.get("flake_window_days"), "flake_policy.flake_window_days", 1)
    _count(policy.get("quarantine_max_age_days"), "flake_policy.quarantine_max_age_days", 1)
    for key in (
        "on_quarantine_ceiling_exceeded", "on_retry_limit_exceeded", "on_quarantine_expired",
        "retry_semantics",
    ):
        if not _text(policy.get(key)):
            raise ValueError(f"flake_policy.{key} must state what happens")


def _check_budgets(strategy, categories):
    pipeline = strategy["pipeline_budgets"]
    for key in ("money_path_harness_minutes", "pull_request_gate_minutes", "release_candidate_gate_minutes"):
        _count(pipeline.get(key), f"pipeline_budgets.{key}", 1)
    if pipeline["money_path_harness_minutes"] > pipeline["pull_request_gate_minutes"]:
        raise ValueError("The money-path harness budget must fit inside the pull request gate budget")
    budgets = _unique_ids(strategy["performance_budgets"], "performance budget")
    for budget_id, budget in budgets.items():
        label = f"Performance budget {budget_id}"
        for key in ("surface", "metric", "unit", "condition"):
            if not _text(budget.get(key)):
                raise ValueError(f"{label} has no {key}")
        value = budget.get("budget")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{label} must publish a non-negative numeric budget")
        if budget.get("comparison") not in ("at_most", "at_least"):
            raise ValueError(f"{label} must state whether the budget is at_most or at_least")
        if budget.get("gate") not in categories:
            raise ValueError(f"{label} names unknown gate category {budget.get('gate')!r}")
    objectives = strategy["recovery_objectives"]
    for key in ("rpo_minutes", "rto_minutes"):
        _count(objectives.get(key), f"recovery_objectives.{key}", 1)
    if not _text(objectives.get("status")):
        raise ValueError("recovery_objectives.status must state that the objectives are targets, not measurements")
    return budgets


def _check_accessibility(accessibility, taxonomy_states):
    for key, expected in ACCESSIBILITY_TARGET.items():
        if accessibility.get(key) != expected:
            raise ValueError(f"accessibility.{key} must be {expected!r}; the conformance target is {ACCESSIBILITY_PHRASE}")
    if accessibility.get("conformance_target") != ACCESSIBILITY_PHRASE:
        raise ValueError(f"accessibility.conformance_target must read {ACCESSIBILITY_PHRASE!r}")
    if accessibility.get("automated_gate") != AUTOMATED_GATE_STATEMENT:
        raise ValueError("accessibility.automated_gate must be the published conformance bar, not a weaker impact threshold")
    # A weaker bar or an optional assistive technology anywhere in the object is a regression, wherever it hides.
    for phrase in FORBIDDEN_ACCESSIBILITY_PHRASES:
        if phrase in json.dumps(accessibility).lower():
            raise ValueError(f"accessibility must not contain the phrase {phrase!r}")
    surfaces = accessibility.get("surfaces")
    if not isinstance(surfaces, dict) or set(surfaces) != {"web", "admin", "android"}:
        raise ValueError("accessibility.surfaces must state the target for web, admin and android")
    for surface, statement in surfaces.items():
        if not _text(statement) or ACCESSIBILITY_PHRASE not in statement:
            raise ValueError(f"accessibility.surfaces.{surface} must state the {ACCESSIBILITY_PHRASE} target explicitly")
    for surface in ("web", "admin"):
        if AUTOMATED_GATE_PHRASE not in surfaces[surface]:
            raise ValueError(f"accessibility.surfaces.{surface} must carry the automated gate bar {AUTOMATED_GATE_PHRASE!r}")
    _require_phrases(surfaces["android"], ("Switch Access",), "accessibility.surfaces.android")
    mechanisms = accessibility.get("automated_mechanisms")
    if not isinstance(mechanisms, dict) or set(mechanisms) != {"web", "admin", "android"}:
        raise ValueError("accessibility.automated_mechanisms must name the automated check for web, admin and android")
    for surface, statement in mechanisms.items():
        if not _text(statement):
            raise ValueError(f"accessibility.automated_mechanisms.{surface} must name the mechanism")
    _require_phrases(mechanisms["android"], ANDROID_MECHANISM_PHRASES, "accessibility.automated_mechanisms.android")
    for key in ("ruleset_named_and_pinned", "undecidable_rules_route_to_manual_walkthrough"):
        if accessibility.get(key) is not True:
            raise ValueError(f"accessibility.{key} must be true")
    lists = (
        "manual_walkthrough", "browser_configurations", "wcag_2_2_criteria_requiring_named_checks",
        "wcag_criteria_requiring_named_checks", "taxonomy_states",
    )
    for key in lists:
        items = accessibility.get(key)
        if not isinstance(items, list) or not items or not all(_text(item) for item in items):
            raise ValueError(f"accessibility.{key} must be a non-empty list of statements")
    for configuration in REQUIRED_BROWSER_CONFIGURATIONS:
        if configuration not in accessibility["browser_configurations"]:
            raise ValueError(f"accessibility.browser_configurations must include {configuration!r}")
    for criterion in REQUIRED_WCAG_NAMED_CHECKS:
        if criterion not in accessibility["wcag_criteria_requiring_named_checks"]:
            raise ValueError(f"accessibility.wcag_criteria_requiring_named_checks must include {criterion!r}")
    for criterion in REQUIRED_WCAG_2_2_NAMED_CHECKS:
        if criterion not in accessibility["wcag_2_2_criteria_requiring_named_checks"]:
            raise ValueError(f"accessibility.wcag_2_2_criteria_requiring_named_checks must include {criterion!r}")
    walkthrough = " ".join(accessibility["manual_walkthrough"])
    _require_phrases(walkthrough, ("Switch Access (Android)", "section 8", "announced once", "not re-announced"), "accessibility.manual_walkthrough")
    # The states the walkthrough must cover are the taxonomy's states, read from the taxonomy, not restated.
    if sorted(accessibility["taxonomy_states"]) != sorted(taxonomy_states):
        raise ValueError("accessibility.taxonomy_states must list exactly the client state taxonomy's state identifiers")
    if not _text(accessibility.get("not_claimed")):
        raise ValueError("accessibility.not_claimed must state what the conformance claim excludes")


def _check_device_matrix(strategy, index):
    lanes = _unique_ids(strategy["device_matrix"], "device lane")
    for missing in [name for name in REQUIRED_DEVICE_LANES if name not in lanes]:
        raise ValueError(f"Missing required device lane: {missing}")
    for lane_id, lane in lanes.items():
        label = f"Device lane {lane_id}"
        if lane.get("kind") not in ("emulator", "managed_device", "physical"):
            raise ValueError(f"{label} has unknown kind {lane.get('kind')!r}")
        for key in ("purpose", "required_for", "configuration"):
            if not lane.get(key):
                raise ValueError(f"{label} has no {key}")
        if lane.get("availability") not in LANE_AVAILABILITY:
            raise ValueError(f"{label} must state its availability as one of {', '.join(LANE_AVAILABILITY)}; no lane runs yet")
        if lane["kind"] == "emulator" and lane["availability"] != "provisionable_in_ci":
            raise ValueError(f"{label} is an emulator lane and must be recorded as provisionable_in_ci")
        if lane["kind"] != "emulator" and lane["availability"] != "required_not_yet_available":
            raise ValueError(f"{label} needs hardware and must be recorded as required_not_yet_available")
        _resolve_owners(lane, index, label)
    if lanes["emulator_api_31"].get("android_api_level") != 31:
        raise ValueError("Device lane emulator_api_31 must pin Android API level 31")
    if lanes["emulator_current"].get("android_api_level") != "current":
        raise ValueError("Device lane emulator_current must track the current Android release")
    _require_phrases(lanes["emulator_large_text"]["configuration"], ("font scale", "display size", "reduced motion"), "Device lane emulator_large_text configuration")
    if "pull_request" not in lanes["emulator_large_text"]["required_for"]:
        raise ValueError("Device lane emulator_large_text is required on every pull request")
    _require_phrases(lanes["emulator_talkback"]["configuration"], ("TalkBack",), "Device lane emulator_talkback configuration")
    physical = lanes[PHYSICAL_DEVICE_LANE]
    if physical.get("kind") != "physical" or physical.get("tier") != "mid-range":
        raise ValueError(f"Device lane {PHYSICAL_DEVICE_LANE} must be a physical mid-range device")
    sim = physical.get("sim")
    if not isinstance(sim, dict) or sim.get("required") is not True or sim.get("country") != "IN":
        raise ValueError(f"Device lane {PHYSICAL_DEVICE_LANE} must require an Indian SIM")
    if physical.get("availability") != "required_not_yet_available":
        raise ValueError(
            f"Device lane {PHYSICAL_DEVICE_LANE} is a requirement; the device is not recorded as available "
            "until the procurement ticket is done"
        )
    procurement = resolve_owner(physical.get("procurement"), index, f"Device lane {PHYSICAL_DEVICE_LANE} procurement")
    if PHYSICAL_DEVICE_PROCUREMENT not in identities(procurement):
        raise ValueError(f"Device lane {PHYSICAL_DEVICE_LANE} procurement must be {PHYSICAL_DEVICE_PROCUREMENT}")
    return lanes


def _check_test_data_policy(policy, index):
    if policy.get("synthetic_only") is not True:
        raise ValueError("test_data_policy.synthetic_only must be true")
    for key in ("production_data_in_lower_environments", "raw_message_content_in_fixtures", "real_credentials_in_fixtures"):
        if policy.get(key) is not False:
            raise ValueError(f"test_data_policy.{key} must be false")
    rules = policy.get("rules")
    if not isinstance(rules, list) or not rules or not all(_text(rule) for rule in rules):
        raise ValueError("test_data_policy.rules must be a non-empty list of statements")
    families = _unique_ids(policy["fixture_families"], "fixture family")
    for family_id, family in families.items():
        label = f"Fixture family {family_id}"
        if not _text(family.get("description")):
            raise ValueError(f"{label} has no description")
        consumers = family.get("consumers")
        if not isinstance(consumers, list) or not consumers or any(c not in REPOSITORY_IDS for c in consumers):
            raise ValueError(f"{label} must name its consuming repositories")
        _resolve_owners(family, index, label)
    return families


def _check_definitions(strategy, index):
    ready = _unique_ids(strategy["definition_of_ready"], "definition of ready item")
    done = _unique_ids(strategy["definition_of_done"], "definition of done item")
    for missing in [name for name in REQUIRED_READY_ITEMS if name not in ready]:
        raise ValueError(f"Definition of Ready lacks required item: {missing}")
    for missing in [name for name in REQUIRED_DONE_ITEMS if name not in done]:
        raise ValueError(f"Definition of Done lacks required item: {missing}")
    for label, items in (("Definition of Ready", ready), ("Definition of Done", done)):
        for item_id, item in items.items():
            if not _text(item.get("text")):
                raise ValueError(f"{label} item {item_id} has no text")
            if "owners" in item:
                _resolve_owners(item, index, f"{label} item {item_id}")
    threat = ready["threat_model_refreshed"]
    owners = {identity for issue in _resolve_owners(threat, index, "Definition of Ready item threat_model_refreshed") for identity in identities(issue)}
    if THREAT_MODEL_OWNER not in owners:
        raise ValueError(f"Definition of Ready item threat_model_refreshed must be owned by {THREAT_MODEL_OWNER}")
    text = threat["text"].lower()
    for phrase in ("ingestion boundary", "raw", "parser-config signing"):
        if phrase not in text:
            raise ValueError(f"Definition of Ready item threat_model_refreshed must name the {phrase} scope")
    _resolve_owners(ready["privacy_payload_reviewed"], index, "Definition of Ready item privacy_payload_reviewed")
    return ready, done


def _check_evidence(evidence):
    if not _text(evidence.get("artifact_name_pattern")) or not _text(evidence.get("artifact_name_regex")):
        raise ValueError("evidence must publish the artifact name pattern and its regex")
    regex = re.compile(evidence["artifact_name_regex"])
    example = evidence.get("artifact_name_example")
    if not _text(example) or not regex.match(example) or not EVIDENCE_NAME.match(example):
        raise ValueError("evidence.artifact_name_example must match the published artifact name regex")
    fields = evidence.get("required_fields")
    if not isinstance(fields, list) or not fields or not all(_text(field) for field in fields):
        raise ValueError("evidence.required_fields must be a non-empty list")
    for field in ("category_id", "owner_reference", "commit_sha", "produced_at", "verdict"):
        if field not in fields:
            raise ValueError(f"evidence.required_fields must include {field}")
    _count(evidence.get("ci_artifact_retention_days"), "evidence.ci_artifact_retention_days", 1)
    _count(evidence.get("release_evidence_retention_days"), "evidence.release_evidence_retention_days", 1)
    _count(evidence.get("freshness_window_days"), "evidence.freshness_window_days", 1)
    if evidence["release_evidence_retention_days"] <= evidence["ci_artifact_retention_days"]:
        raise ValueError("Release evidence must outlive transient CI artifacts")
    if not _text(evidence.get("release_evidence_location")):
        raise ValueError("evidence.release_evidence_location must be stated")


def _check_cadence(cadence):
    triggers = cadence.get("triggers")
    if not isinstance(triggers, list) or not triggers or not all(_text(trigger) for trigger in triggers):
        raise ValueError("review_cadence.triggers must be a non-empty list")
    if cadence.get("inventory_refresh_command") != REFRESH_COMMAND:
        raise ValueError(f"review_cadence.inventory_refresh_command must be {REFRESH_COMMAND!r}")
    _count(cadence.get("snapshot_age_warning_days"), "review_cadence.snapshot_age_warning_days", 1)


# --- document -----------------------------------------------------------------------------------

def _owner_cell(item):
    return ", ".join(f"{owner['reference']} ({owner['identity']})" for owner in item["owners"])


def _table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def render_category_table(strategy):
    return _table(
        ("Category", "Layer", "Approach", "Owning issues", "Pass/fail signal"),
        [(f"`{c['id']}`", c["layer"], c["approach"], _owner_cell(c), c["evidence"]) for c in strategy["categories"]],
    )


def render_deliverable_table(strategy):
    return _table(
        ("Deliverable", "What it is", "Owning issues"),
        [(f"`{d['id']}`", d["description"], _owner_cell(d)) for d in strategy["deliverables"]],
    )


def render_change_class_table(strategy):
    return _table(
        ("Change class", "Mandatory categories", "Manual evidence"),
        [
            (
                f"`{c['id']}`",
                ", ".join(f"`{name}`" for name in c["mandatory_categories"]),
                "; ".join(c["manual_evidence"]) or "none",
            )
            for c in strategy["change_classes"]
        ],
    )


def render_package_table(strategy):
    rows = []
    for package in strategy["packages"]:
        mutation = package.get("mutation_score_floor_percent")
        rows.append((
            f"`{package['id']}`", package["repository"], "yes" if package["money_path"] else "no",
            package["line_coverage_floor_percent"], package["branch_coverage_floor_percent"],
            "not required" if mutation is None else mutation,
        ))
    return _table(("Package", "Repository", "Money path", "Line floor %", "Branch floor %", "Mutation floor %"), rows)


def render_mutation_gap_table(strategy):
    gaps = strategy["floor_policy"]["mutation_enforcement_gaps"]
    if not gaps:
        return "Every repository that carries a money-path package has a mutation-testing owner in that repository.\n"
    return _table(
        ("Repository", "Money-path packages without an enforcement owner", "Reason", "Resolution"),
        [
            (gap["repository"], ", ".join(f"`{name}`" for name in gap["packages"]), gap["reason"], gap["resolution"])
            for gap in gaps
        ],
    )


def render_flake_table(strategy):
    policy = strategy["flake_policy"]
    return _table(
        ("Number", "Value", "Consequence when exceeded"),
        [
            ("Quarantine rate ceiling", f"{policy['quarantine_rate_ceiling_percent']}% of a repository's tests", policy["on_quarantine_ceiling_exceeded"]),
            ("Automatic retry limit", f"{policy['retry_limit']} re-execution (money-path change class: {policy['money_path_retry_limit']})", policy["on_retry_limit_exceeded"]),
            ("Quarantine trigger", f"{policy['quarantine_after_flakes']} flake events within {policy['flake_window_days']} days", policy["retry_semantics"]),
            ("Quarantine maximum age", f"{policy['quarantine_max_age_days']} days", policy["on_quarantine_expired"]),
        ],
    )


def render_budget_table(strategy):
    rows = [
        (f"`{b['id']}`", b["surface"], b["metric"], f"{'<=' if b['comparison'] == 'at_most' else '>='} {b['budget']} {b['unit']}", b["condition"], f"`{b['gate']}`")
        for b in strategy["performance_budgets"]
    ]
    return _table(("Budget", "Surface", "Metric", "Budget", "Condition", "Gate"), rows)


def render_device_table(strategy):
    rows = []
    for lane in strategy["device_matrix"]:
        api = lane.get("android_api_level", "n/a")
        rows.append((
            f"`{lane['id']}`", lane["kind"], api, lane["configuration"], lane["purpose"], ", ".join(lane["required_for"]),
            LANE_AVAILABILITY_TEXT[lane["availability"]], _owner_cell(lane),
        ))
    return _table(("Lane", "Kind", "API level", "Configuration", "Purpose", "Required for", "Availability", "Owning issues"), rows)


def _bullets(items):
    return "\n".join(f"- {item}" for item in items) + "\n"


def render_accessibility_block(strategy):
    """Section 10 rendered from the data: target, gate, mechanisms, configurations, named checks, walkthrough."""
    accessibility = strategy["accessibility"]
    parts = [
        f"**{CONFORMANCE_STATEMENT}** Standard `{accessibility['standard']}`, version `{accessibility['version']}`, level `{accessibility['level']}`.\n",
        f"**Automated gate (web and admin):** {accessibility['automated_gate']}.\n",
        _table(
            ("Surface", "Target", "Automated mechanism"),
            [(surface, accessibility["surfaces"][surface], accessibility["automated_mechanisms"][surface]) for surface in ("web", "admin", "android")],
        ),
        "**Browser configurations (web and admin core journeys):**\n" + _bullets(accessibility["browser_configurations"]),
        "**WCAG 2.2 criteria that need a named check or a recorded manual step:**\n" + _bullets(accessibility["wcag_2_2_criteria_requiring_named_checks"]),
        "**Other WCAG criteria that need a named check, automated where the ruleset can decide them and otherwise a recorded manual step:**\n" + _bullets(accessibility["wcag_criteria_requiring_named_checks"]),
        "**Manual walkthrough:**\n" + _bullets(accessibility["manual_walkthrough"]),
        "**Client state taxonomy states asserted on every core journey:** " + ", ".join(f"`{state}`" for state in accessibility["taxonomy_states"]) + ".\n",
        f"**Not claimed:** {accessibility['not_claimed']}.\n",
    ]
    return "\n".join(parts)


def render_fixture_table(strategy):
    return _table(
        ("Fixture family", "Description", "Consumers", "Owning issues"),
        [
            (f"`{f['id']}`", f["description"], ", ".join(f["consumers"]), _owner_cell(f))
            for f in strategy["test_data_policy"]["fixture_families"]
        ],
    )


def render_checklist(items):
    lines = []
    for item in items:
        suffix = f" ({_owner_cell(item)})" if item.get("owners") else ""
        lines.append(f"- [ ] `{item['id']}` -- {item['text']}{suffix}")
    return "\n".join(lines) + "\n"


def render_numbers_table(strategy):
    """Every scalar number the strategy publishes outside the package, flake and budget tables."""
    floors, pipeline = strategy["floor_policy"], strategy["pipeline_budgets"]
    recovery, evidence, cadence = strategy["recovery_objectives"], strategy["evidence"], strategy["review_cadence"]
    return _table(
        ("Number", "Value", "Read by"),
        [
            ("Money-path minimum floors (line / branch / mutation)", f"{floors['money_path_minimum']['line']} / {floors['money_path_minimum']['branch']} / {floors['money_path_minimum']['mutation']} percent", "`mutation_testing`, `unit_tests`"),
            ("Other-package minimum floors (line / branch)", f"{floors['other_minimum']['line']} / {floors['other_minimum']['branch']} percent", "`unit_tests`"),
            ("Money-path harness pipeline budget", f"{pipeline['money_path_harness_minutes']} minutes", "`mutation_testing`, `debt_maths_independent_model`"),
            ("Pull request gate pipeline budget", f"{pipeline['pull_request_gate_minutes']} minutes", "every pull request gate"),
            ("Release candidate gate pipeline budget", f"{pipeline['release_candidate_gate_minutes']} minutes", "`release_evidence_gates`"),
            ("Recovery point objective", f"{recovery['rpo_minutes']} minutes", "`disaster_recovery_restore`"),
            ("Recovery time objective", f"{recovery['rto_minutes']} minutes", "`disaster_recovery_restore`"),
            ("CI artifact retention (transient, never evidence)", f"{evidence['ci_artifact_retention_days']} days", "every category"),
            ("Release evidence retention", f"{evidence['release_evidence_retention_days']} days", "`release_evidence_gates`"),
            ("Release evidence freshness window", f"{evidence['freshness_window_days']} days", "`release_evidence_gates`"),
            ("Inventory snapshot age warning", f"{cadence['snapshot_age_warning_days']} days", "`strategy_reconciliation`"),
        ],
    )


def render_document_blocks(strategy):
    """Every block the document must carry verbatim, so prose and data cannot drift apart."""
    return {
        "categories": render_category_table(strategy),
        "deliverables": render_deliverable_table(strategy),
        "change_classes": render_change_class_table(strategy),
        "packages": render_package_table(strategy),
        "mutation_enforcement_gaps": render_mutation_gap_table(strategy),
        "flake_policy": render_flake_table(strategy),
        "numbers": render_numbers_table(strategy),
        "performance_budgets": render_budget_table(strategy),
        "accessibility": render_accessibility_block(strategy),
        "device_matrix": render_device_table(strategy),
        "fixture_families": render_fixture_table(strategy),
        "definition_of_ready": render_checklist(strategy["definition_of_ready"]),
        "definition_of_done": render_checklist(strategy["definition_of_done"]),
        "not_asserted": _bullets(strategy["not_asserted"]),
    }


def _check_document(strategy, document):
    for name, block in render_document_blocks(strategy).items():
        if block not in document:
            raise ValueError(f"Document does not carry the {name} block rendered from the data verbatim; run --render")
    mentions = [
        (CONFORMANCE_STATEMENT, "the accessibility conformance target as an explicit statement"),
        (STRATEGY, f"data file {STRATEGY}"), (SCHEMA, f"schema file {SCHEMA}"),
        (INVENTORY, f"inventory file {INVENTORY}"), (REFRESH_COMMAND, "the inventory refresh command"),
        (strategy["strategy_version"], f"strategy version {strategy['strategy_version']}"),
        (DELIVERY_PLAN, f"the canonical Definition of Ready and Done in {DELIVERY_PLAN}"),
        (TAXONOMY_DOCUMENT, f"the client state taxonomy document {TAXONOMY_DOCUMENT}"),
    ]
    for needle, label in mentions:
        if needle not in document:
            raise ValueError(f"Document does not mention {label}")


# --- entry points -------------------------------------------------------------------------------

def check_strategy(strategy, inventory, document, taxonomy=None):
    """Enforce the acceptance criteria of PenniLogic/docs#22; return a short summary.

    `taxonomy` is the client state taxonomy data (product/client-state-taxonomy.json); it supplies the
    state identifiers and gate assertions this strategy must cover. Defaults to the published file.
    """
    taxonomy = load_json(ROOT / TAXONOMY_DATA) if taxonomy is None else taxonomy
    taxonomy_states = [state["id"] for state in taxonomy["states"]]
    taxonomy_assertions = [assertion["id"] for assertion in taxonomy["adoption"]["coverage_assertions"]]
    index = validate_inventory(inventory)
    if strategy.get("schema_version") != 1:
        raise ValueError("Strategy schema_version must be 1")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", strategy.get("strategy_version", "")):
        raise ValueError("strategy_version must be a semantic version")
    for key, expected in (("document", DOCUMENT), ("schema", SCHEMA), ("inventory", INVENTORY)):
        if strategy.get(key) != expected:
            raise ValueError(f"Strategy {key} must be {expected}")
    if strategy.get("reference_format") != REFERENCE.pattern:
        raise ValueError("Strategy reference_format must publish the exact owner reference pattern the check enforces")
    resolve_owner(strategy.get("source_issue"), index, "Strategy source_issue")
    categories, owners = _check_categories(strategy, index, taxonomy_assertions)
    _check_deliverables(strategy, index)
    _check_change_classes(strategy, categories)
    packages, money_count, gaps = _check_packages(strategy, categories)
    _check_flake_policy(strategy["flake_policy"])
    _check_budgets(strategy, categories)
    _check_accessibility(strategy["accessibility"], taxonomy_states)
    _check_device_matrix(strategy, index)
    _check_test_data_policy(strategy["test_data_policy"], index)
    _check_definitions(strategy, index)
    _check_evidence(strategy["evidence"])
    _check_cadence(strategy["review_cadence"])
    _check_document(strategy, document)
    return {
        "strategy_version": strategy["strategy_version"],
        "categories": len(categories),
        "owners": len(owners),
        "owner_repositories": len({reference.split("#")[0] for reference in owners}),
        "packages": len(packages),
        "money_path_packages": money_count,
        "mutation_enforcement_gaps": len(gaps),
        "issues": len(index),
        "snapshot_at": inventory["snapshot_at"],
    }


def validate_strategy(root):
    strategy = load_json(root / STRATEGY)
    schema = load_json(root / SCHEMA)
    load_check("check_client_states").validate_schema(strategy, schema)
    inventory = load_json(root / INVENTORY)
    document = (root / DOCUMENT).read_text(encoding="utf-8")
    taxonomy = load_json(root / TAXONOMY_DATA)
    return check_strategy(strategy, inventory, document, taxonomy)


def child_environment(environ=None):
    """The environment for `gh`: the inherited token and credential-helper overrides are removed."""
    environ = os.environ if environ is None else environ
    return {key: value for key, value in environ.items() if key not in TOKEN_VARIABLES}


def redact(text):
    return TOKEN_SHAPE.sub("[redacted]", text or "")


def gh(args, payload=None, runner=subprocess.run, environ=None):
    """Run `gh` process-locally as the stored personal credential; never touch a token."""
    try:
        process = runner(
            ["gh", *args], input=None if payload is None else json.dumps(payload), capture_output=True,
            text=True, encoding="utf-8", env=child_environment(environ), timeout=GH_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        # The timeout carries the child's stderr; it must pass through redact() like every other failure.
        stderr = error.stderr.decode("utf-8", "replace") if isinstance(error.stderr, bytes) else (error.stderr or "")
        raise RuntimeError(
            f"gh {' '.join(args[:2])} timed out after {GH_TIMEOUT_SECONDS} s: {redact(stderr.strip())[:600]}"
        ) from None
    if process.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])} failed: {redact(process.stderr.strip())[:600]}")
    return json.loads(process.stdout) if process.stdout.strip() else None


def inventory_record(repository, node):
    body = node.get("body") or ""
    plan = PLAN_MARKER.search(body)
    source = SOURCE_MARKER.search(body)
    reason = node.get("stateReason")
    return {
        "reference": f"{repository}#{node['number']}",
        "repository": repository,
        "number": node["number"],
        "title": " ".join(node["title"].split()),
        "state": node["state"].lower(),
        "state_reason": reason.lower() if reason else None,
        "source": f"PenniLogic-old/{source.group(1)}#{source.group(2)}" if source else None,
        "plan_id": plan.group(1) if plan else None,
    }


def fetch_inventory(run=gh, now=None):
    """Read the live public issue inventory as basiltt after verifying identity and repository ids."""
    user = run(["api", "user"])
    if user.get("login") != OPERATOR or user.get("id") != OPERATOR_ID:
        raise RuntimeError(f"gh is authenticated as {user.get('login')!r}, not {OPERATOR}; refusing to refresh")
    organization = run(["api", f"orgs/{ORGANIZATION}"])
    if organization.get("id") != ORGANIZATION_ID:
        raise RuntimeError(f"Organization {ORGANIZATION} resolved to id {organization.get('id')}, expected {ORGANIZATION_ID}")
    repositories = {}
    issues = []
    for full_name, expected_id in REPOSITORY_IDS.items():
        owner, name = full_name.split("/")
        after = None
        count = 0
        total = None
        while True:
            variables = {"owner": owner, "name": name, "after": after}
            data = run(["api", "graphql", "--input", "-"], {"query": ISSUES_QUERY, "variables": variables})
            if not data or data.get("errors"):
                raise RuntimeError(f"GraphQL query for {full_name} failed: {redact(json.dumps(data))[:600]}")
            repository = data["data"]["repository"]
            if repository["databaseId"] != expected_id:
                raise RuntimeError(f"Repository {full_name} resolved to id {repository['databaseId']}, expected {expected_id}")
            page = repository["issues"]
            total = page["totalCount"]
            for node in page["nodes"]:
                issues.append(inventory_record(full_name, node))
                count += 1
            if not page["pageInfo"]["hasNextPage"]:
                break
            after = page["pageInfo"]["endCursor"]
        # planning/README.md rule 1: a connection drained by hasNextPage alone has not proven it read the
        # whole population; the fetched count must equal totalCount, and both are recorded.
        if count != total:
            raise RuntimeError(f"{full_name}: drained {count} issues but the connection reports totalCount {total}")
        repositories[full_name] = {"id": expected_id, "issue_count": count, "total_count": total}
    issues.sort(key=lambda issue: (REPOSITORY_ORDER[issue["repository"]], issue["number"]))
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return {
        "schema_version": 1,
        "organization": ORGANIZATION,
        "organization_id": ORGANIZATION_ID,
        "operator": OPERATOR,
        "snapshot_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "refresh_command": REFRESH_COMMAND,
        "note": (
            "Offline snapshot of the public issue inventory for the test strategy reconciliation; "
            "identity comes from the plan-id marker and the original-specification source each issue "
            "body carries, never from titles. Refresh at each review-cadence trigger."
        ),
        "issue_count": len(issues),
        "open_count": sum(issue["state"] == "open" for issue in issues),
        "closed_count": sum(issue["state"] == "closed" for issue in issues),
        "repositories": repositories,
        "issues": issues,
    }


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")


def inventory_diff(before, after):
    """Read-back receipt (planning/README.md rule 4): what changed between two snapshots, by reference."""
    old = {issue["reference"]: issue for issue in before.get("issues", [])}
    new = {issue["reference"]: issue for issue in after["issues"]}
    identity = ("plan_id", "source")
    state = ("state", "state_reason")
    return {
        "added": sorted(reference for reference in new if reference not in old),
        "removed": sorted(reference for reference in old if reference not in new),
        "state_changed": sorted(
            reference for reference in new if reference in old
            and any(old[reference].get(key) != new[reference].get(key) for key in state)
        ),
        "identity_changed": sorted(
            reference for reference in new if reference in old
            and any(old[reference].get(key) != new[reference].get(key) for key in identity)
        ),
    }


def _refresh_inventory():
    """Refresh the snapshot as basiltt, validate it, write it and print the receipt against the previous one."""
    target = ROOT / INVENTORY
    previous = load_json(target) if target.exists() else {"issues": []}
    inventory = fetch_inventory()
    validate_inventory(inventory)
    write_json(target, inventory)
    drained = ", ".join(
        f"{name.split('/')[1]} {record['issue_count']}/{record['total_count']}" for name, record in inventory["repositories"].items()
    )
    diff = inventory_diff(previous, inventory)
    print(f"Issue inventory refreshed as {OPERATOR}: {inventory['issue_count']} issues at {inventory['snapshot_at']}.")
    print(f"Drained/totalCount per repository: {drained}.")
    print(
        f"Receipt against the previous snapshot: {len(diff['added'])} added, {len(diff['removed'])} removed, "
        f"{len(diff['state_changed'])} state changes, {len(diff['identity_changed'])} identity changes."
    )
    for key in ("added", "removed", "identity_changed"):
        if diff[key]:
            print(f"  {key}: {', '.join(diff[key])}")
    return inventory


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate the published test strategy against the issue inventory.")
    parser.add_argument("--refresh-inventory", action="store_true", help=f"regenerate {INVENTORY} from the live API as {OPERATOR}")
    parser.add_argument("--render", action="store_true", help="print the tables the document must carry verbatim")
    args = parser.parse_args(argv)
    try:
        if args.refresh_inventory:
            _refresh_inventory()
        if args.render:
            for name, block in render_document_blocks(load_json(ROOT / STRATEGY)).items():
                print(f"<!-- {name} -->\n{block}")
            return 0
        summary = validate_strategy(ROOT)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Test strategy check failed: {redact(str(error))}", file=sys.stderr)
        return 1
    print(
        f"Test strategy {summary['strategy_version']} valid: {summary['categories']} categories owned by "
        f"{summary['owners']} public issues across {summary['owner_repositories']} repositories, "
        f"{summary['packages']} packages with floors ({summary['money_path_packages']} money-path, "
        f"{summary['mutation_enforcement_gaps']} recorded mutation enforcement gap(s)), "
        f"inventory of {summary['issues']} issues snapshotted {summary['snapshot_at']}; "
        "no harness, coverage or acceptance implied."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
