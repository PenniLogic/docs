"""Offline T-UXR-01 checks; no remote actions, role appointments or live Figma claims."""

import argparse
from collections import Counter
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DATA = "governance/design-gates.json"
SCHEMA = "governance/design-gates.schema.json"
DOCUMENT = "governance/design-operations.md"
spec = importlib.util.spec_from_file_location("design_schema_support", ROOT / "scripts/check_client_states.py")
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)

GATES = tuple(f"D{number}" for number in range(10))
APPROVERS = (
    "product_owner", "service_design", "decision_coordinator", "artifact_accountable", "systems",
    "design_qa", "decision_coordinator", "artifact_accountable", "decision_coordinator", "product_owner",
)
GATE_TTL_CAPS = (720, 720, 720, 336, 336, 168, 168, 72, 24, 720)
STATUSES = {"draft", "in_review", "blocked", "approved", "reopened", "superseded", "archived"}
SCOPES = {"D2", "D6", "D8", "shared_system_major", "material_exception"}
REOPEN = {
    "contract", "user_visible_policy", "information_architecture", "component_major", "critical_acceptance",
    "artifact_version", "evidence", "blocking_comment", "approval_expiry", "role_revocation",
}
ROLES = {
    "product_owner", "decision_coordinator", "design_ops", "research", "service_design", "android_design",
    "web_design", "admin_design", "systems", "content", "accessibility", "ux_engineering", "design_qa",
    "engineering", "privacy", "security", "legal", "research_store_owner", "release",
}
ARTIFACTS = {
    "product_truth", "design_governance", "research_plan", "research_synthesis", "research_access",
    "personas_jobs", "journeys_blueprints", "sitemaps", "visual_direction", "foundations_tokens",
    "components", "android_experience", "web_experience", "admin_experience", "content_localization",
    "accessibility_evidence", "prototype_validation", "handoff", "readiness", "build_conformance",
    "release_design_qa", "outcome_review", "traceability_registry", "archive",
}
BRANCH = r"^T-[A-Z0-9]+-[0-9]+__[a-z][a-z0-9-]*__[a-z][a-z0-9-]*$"
ZERO = "sha256:" + "0" * 64


class Refused(ValueError):
    """A static rule identifier, safe to print without echoing input content."""


def require(condition, code):
    if not condition:
        raise Refused(code)


def digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def shape(value, schema, definition=None):
    try:
        selected = schema if definition is None else schema["definitions"][definition]
        support.validate_schema(value, selected, schema)
    except (ValueError, KeyError, TypeError):
        raise Refused("schema.invalid") from None


def unique(items, field="id"):
    result = {item[field]: item for item in items}
    require(len(result) == len(items), "identity.duplicate")
    return result


def instant(value):
    try:
        require(isinstance(value, str) and re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value
        ), "time.invalid")
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        raise Refused("time.invalid") from None


def window(start, end, now, hours):
    require(isinstance(now, datetime) and now.tzinfo is not None and now.utcoffset() == timedelta(0),
            "time.untrusted_clock")
    start, end = instant(start), instant(end)
    require(start <= now < end, "time.expired_or_future")
    require(start < end <= start + timedelta(hours=hours), "time.excessive_lifetime")
    return start, end


def validate_policy(data, schema, document=None):
    shape(data, schema)
    roles = unique(data["roles"])
    artifacts = unique(data["artifact_classes"])
    gates = unique(data["gates"])
    require(ROLES <= roles.keys() and ARTIFACTS <= artifacts.keys(), "vocabulary.missing")
    require(set(data["artifact_statuses"]) == STATUSES, "status.vocabulary")
    require(set(data["cdo_equivalent_scopes"]) == SCOPES, "authority.scope")
    require(set(data["reopen_on"]) == REOPEN, "reopen.vocabulary")
    require(tuple(gates) == GATES, "gate.vocabulary")
    for item in artifacts.values():
        named = set(item["responsible"] + item["consulted"] + item["informed"] + item["verifiers"])
        require(named | {item["accountable"]} <= roles.keys(), "raci.unknown_role")
        require(not (set(item["verifiers"]) & (set(item["responsible"]) | {item["accountable"]})),
                "raci.self_verifier")
    for number, gate in enumerate(gates.values()):
        require(set(gate["artifact_classes"]) <= artifacts.keys(), "gate.unknown_class")
        require(gate["approver"] == APPROVERS[number], "gate.missing_or_wrong_approver")
        require(gate["required_gates"] == ([] if number == 0 else [GATES[number - 1]]),
                "gate.prerequisites")
        require(1 <= gate["ttl_hours"] <= GATE_TTL_CAPS[number], "gate.lifetime")
        for class_id in gate["artifact_classes"]:
            approver = artifacts[class_id]["accountable"] if gate["approver"] == "artifact_accountable" else gate["approver"]
            require(approver != "decision_coordinator" or gate["id"] in SCOPES, "authority.scope")
    caps = {
        "wip_per_squad": 2, "wip_per_verifier": 3, "wip_coordinator": 2,
        "acknowledge_hours": 24, "disposition_hours": 48, "escalate_hours": 72,
        "exception_hours": 24, "assignment_hours": 72, "access_hours": 24,
    }
    require(all(1 <= data["flow_control"][key] <= cap for key, cap in caps.items()), "queue.unbounded")
    flow = data["flow_control"]
    require(flow["acknowledge_hours"] < flow["disposition_hours"] < flow["escalate_hours"], "queue.sla_order")
    files = unique(data["topology"]["files"])
    require(set(files) == {"f00", "f01", "f02", "f03", "f10", "f20", "f30", "f40", "f50", "f90"},
            "topology.missing_file")
    require(len({item["name"] for item in files.values()}) == len(files), "topology.duplicate_name")
    require(data["topology"]["branch_pattern"] == BRANCH, "topology.branch_pattern")
    require(set(data["topology"]["controlled_pages"]) == {"Cover", "Changelog", "Handoff", "Archive"},
            "topology.controlled_pages")
    for item in files.values():
        required = {"Cover", "Changelog", "Archive"}
        if item["kind"] != "archive":
            required.add("Handoff")
        require(required <= set(item["pages"]) and item["owner_role"] in roles, "topology.owner_or_page")
        require(item["kind"] != "library" or item["owner_role"] == "systems", "topology.library_owner")
    require(set(data["access"]["classifications"]) == {"synthetic", "redacted_nonparticipant"}, "access.classification")
    require(set(data["observability"]) == {
        "review_age_hours", "blocked_artifact_count", "approval_expiry", "wip_by_squad", "reopened_gate_count",
    }, "metrics.vocabulary")
    if document is not None:
        for name in roles.keys() | artifacts.keys() | set(GATES) | STATUSES:
            require(f"`{name}`" in document, "document.missing_identifier")
        for item in files.values():
            require(item["name"] in document, "document.missing_file")
    return {"contract_version": data["contract_version"], "artifact_classes": len(artifacts), "gates": len(gates)}


def git_blob(commit, path):
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1"}
    try:
        kind = subprocess.run(
            ["git", "--no-pager", "cat-file", "-t", commit], cwd=ROOT,
            capture_output=True, timeout=30, env=env,
        )
        require(kind.returncode == 0 and kind.stdout.strip() == b"commit", "evidence.commit_unavailable")
        result = subprocess.run(
            ["git", "--no-pager", "cat-file", "blob", f"{commit}:{path}"], cwd=ROOT,
            capture_output=True, timeout=30, env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Refused("evidence.read_failed") from None
    require(result.returncode == 0, "evidence.blob_unavailable")
    return result.stdout


class Checker:
    """Use coordinator-verified assignments separately from an author's candidate snapshot."""

    def __init__(self, policy, schema, assignments, now, read_blob=git_blob):
        validate_policy(policy, schema)
        shape(assignments, schema, "assignments")
        self.policy, self.schema, self.now, self.read_blob = policy, schema, now, read_blob
        self.assignments = unique(assignments, "context_id")
        self.artifacts = unique(policy["artifact_classes"])
        self.gates = unique(policy["gates"])
        self.roles = set(unique(policy["roles"]))
        self.blobs = {}
        for assignment in assignments:
            require(set(assignment["roles"]) <= self.roles, "assignment.unknown_role")

    def source(self, reference):
        shape(reference, self.schema, "source")
        path = reference["path"]
        require(re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", path)
                and not {".", ".."} & set(path.split("/")), "evidence.unsafe_path")
        key = reference["commit"], path
        if key not in self.blobs:
            try:
                self.blobs[key] = self.read_blob(*key)
            except (OSError, KeyError):
                raise Refused("evidence.unavailable") from None
        blob = self.blobs[key]
        require(isinstance(blob, bytes) and digest(blob) == reference["sha256"], "evidence.digest_mismatch")

    def binding(self, context, role, artifact_id, at=None):
        require(context in self.assignments, "assignment.missing_or_revoked")
        assignment = self.assignments[context]
        issued, expires = window(
            assignment["issued_at"], assignment["expires_at"], self.now,
            self.policy["flow_control"]["assignment_hours"],
        )
        require(role in assignment["roles"] and artifact_id in assignment["artifact_ids"], "assignment.out_of_scope")
        require(at is None or issued <= at < expires, "assignment.not_active_at_decision")
        self.source(assignment["evidence"])
        return expires

    def close_gate(self, snapshot):
        shape(snapshot, self.schema, "snapshot")
        records = unique(snapshot["records"])
        require(snapshot["target"] in records, "gate.missing_target")
        visited, visiting = {}, set()

        def check(record_id, dependency=False):
            require(record_id in records, "gate.missing_dependency")
            record = records[record_id]
            require(record["status"] == "approved" if dependency else record["status"] in {"in_review", "approved"},
                    "gate.not_reviewable")
            require(record_id not in visiting, "gate.dependency_cycle")
            if record_id in visited:
                return visited[record_id]
            visiting.add(record_id)
            require(record["gate_id"] in self.gates and record["artifact_class"] in self.artifacts, "gate.unknown")
            gate, raci = self.gates[record["gate_id"]], self.artifacts[record["artifact_class"]]
            require(record["artifact_class"] in gate["artifact_classes"], "gate.wrong_class")
            scope = scope_digest(record)
            self.source(record["source"])
            evidence = unique(record["evidence"])
            inputs = unique(record["inputs"])
            unique(record["comments"])
            dependencies = unique(record["dependencies"], "artifact_id")
            require(set(gate["required_gates"]) <= {item["gate_id"] for item in dependencies.values()},
                    "gate.missing_prerequisite")
            required_evidence = set(gate["required_evidence"])
            approver = raci["accountable"] if gate["approver"] == "artifact_accountable" else gate["approver"]
            required_approvals = {approver}
            ttl = gate["ttl_hours"]
            if record["change_kind"] != "standard":
                required_approvals.add("decision_coordinator")
                required_evidence.add(record["change_kind"])
                ttl = min(ttl, self.policy["flow_control"]["exception_hours"])
                if record["change_kind"] == "shared_system_major":
                    require(record["artifact_class"] in {"foundations_tokens", "components"}, "authority.major_scope")
            require(required_evidence <= evidence.keys(), "gate.missing_evidence")
            latest = datetime.min.replace(tzinfo=timezone.utc)
            expiries, producers = [], set(record["author_contexts"])
            for item in inputs.values():
                self.source(item["source"])
            for item in evidence.values():
                observed, expires = window(item["observed_at"], item["expires_at"], self.now, gate["ttl_hours"])
                self.source(item["source"])
                latest = max(latest, observed)
                expiries.append(expires)
            for item in dependencies.values():
                require(item["artifact_id"] in records, "gate.missing_dependency")
                parent = records[item["artifact_id"]]
                require(parent["gate_id"] == item["gate_id"] and scope_digest(parent) == item["scope_sha256"],
                        "gate.stale_dependency")
                checked = check(item["artifact_id"], True)
                latest = max(latest, checked["last_decided_at"])
                expiries.append(checked["expires_at"])
                producers.update(checked["producers"])
            for comment in record["comments"]:
                self.source(comment["evidence"])
                resolution = comment["resolution"]
                require(not comment["blocking"] or resolution is not None, "comment.unresolved_blocking")
                if resolution is not None:
                    require(resolution["context_id"] == comment["author_context_id"]
                            and resolution["context_id"] not in producers
                            and resolution["role"] in self.roles, "comment.invalid_resolver")
                    resolved = instant(resolution["resolved_at"])
                    require(resolved <= self.now and resolution["scope_sha256"] == scope, "comment.stale_resolution")
                    expiries.append(self.binding(resolution["context_id"], resolution["role"], record_id, resolved))
                    self.source(resolution["evidence"])
                    latest = max(latest, resolved)
            review_keys, approvals, verifiers = set(), {}, {}
            for review in record["reviews"]:
                key = review["purpose"], review["role"]
                require(key not in review_keys, "review.duplicate")
                review_keys.add(key)
                require(review["decision"] == "approved", "review.rejected")
                require(review["scope_sha256"] == scope, "approval.stale")
                require(review["context_id"] not in producers, "review.author_is_reviewer")
                decided, expires = window(review["decided_at"], review["expires_at"], self.now, ttl)
                require(decided >= latest, "approval.precedes_evidence")
                assigned_until = self.binding(review["context_id"], review["role"], record_id, decided)
                require(expires <= assigned_until, "approval.outlives_assignment")
                self.source(review["evidence"])
                expiries.append(expires)
                target = approvals if review["purpose"] == "approval" else verifiers
                target[review["role"]] = review["context_id"]
            require(set(approvals) == required_approvals, "gate.missing_or_wrong_approver")
            require(bool(verifiers) and verifiers.keys() <= set(raci["verifiers"]), "gate.missing_independent_verifier")
            require(not set(approvals.values()) & set(verifiers.values()), "review.context_not_independent")
            require(len(set(approvals.values())) == len(approvals), "review.multiple_roles_one_context")
            visiting.remove(record_id)
            result = {
                "scope_sha256": scope, "expires_at": min(expiries), "producers": producers,
                "last_decided_at": max(instant(review["decided_at"]) for review in record["reviews"]),
            }
            visited[record_id] = result
            return result

        result = check(snapshot["target"])
        return {
            "scope_sha256": result["scope_sha256"],
            "expires_at": result["expires_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "checked_artifacts": len(visited),
        }

    def append_decision(self, history, entry, expected_head):
        head = validate_history(history, self.schema)
        require(head == expected_head, "decision.stale_head")
        require("sha256" not in entry and "previous_sha256" not in entry, "decision.caller_supplied_hash")
        logged = copy.deepcopy(entry)
        logged["previous_sha256"] = head
        logged["sha256"] = digest(logged)
        shape(logged, self.schema, "decision")
        require(logged["id"] not in {item["id"] for item in history}, "decision.duplicate")
        occurred, _ = window(
            logged["occurred_at"], logged["expires_at"], self.now, self.policy["flow_control"]["exception_hours"],
        )
        require(not history or occurred >= instant(history[-1]["occurred_at"]), "decision.backdated")
        require(logged["artifact_class"] in self.artifacts, "decision.unknown_class")
        raci = self.artifacts[logged["artifact_class"]]
        authority = raci["accountable"]
        if logged["kind"] in {"shared_system_major", "material_exception"}:
            authority = "decision_coordinator"
        elif logged["kind"] == "freeze":
            authority = "design_ops"
        if logged["kind"] == "shared_system_major":
            require(logged["artifact_class"] in {"foundations_tokens", "components"}, "authority.major_scope")
        if logged["kind"] == "research_disposition":
            require(logged["artifact_class"] in {"research_plan", "research_synthesis"}, "authority.research_scope")
        require(logged["actor_role"] == authority and logged["verifier_role"] in raci["verifiers"],
                "decision.wrong_authority")
        require(logged["actor_context_id"] != logged["verifier_context_id"], "decision.self_verification")
        require(not set(logged["author_contexts"]) & {logged["actor_context_id"], logged["verifier_context_id"]},
                "decision.author_is_reviewer")
        promotes_draft = logged["kind"] in {"source_change", "restore"} and logged["disposition"] == "accept"
        require((logged["result"] is not None) == promotes_draft, "decision.invalid_result")
        if logged["kind"] == "conflict":
            require(logged["disposition"] == "defer"
                    and len({item["squad"] for item in logged["proposals"]}) >= 2, "conflict.invalid")
        if logged["kind"] == "freeze":
            require(logged["disposition"] == "accept", "freeze.invalid")
        for context, role in (
            (logged["actor_context_id"], logged["actor_role"]),
            (logged["verifier_context_id"], logged["verifier_role"]),
        ):
            expires = self.binding(context, role, logged["artifact_id"], occurred)
            require(instant(logged["expires_at"]) <= expires, "decision.outlives_assignment")
        self.source(logged["reason"])
        branches = set()
        for proposal in logged["proposals"]:
            require(re.fullmatch(BRANCH, proposal["branch"])
                    and proposal["branch"].split("__")[1] == proposal["squad"], "branch.invalid")
            require(proposal["branch"] not in branches, "branch.collision")
            branches.add(proposal["branch"])
            self.source(proposal["source"])
        if logged["result"] is not None:
            self.source(logged["result"])
        require(set(logged["related_decisions"]) <= {item["id"] for item in history}, "decision.missing_reference")
        return copy.deepcopy(history) + [logged]

    def source_change(self, state, entry, expected_revision):
        """Tabletop compare-and-swap, returning a new draft state; never edits a file or publishes."""
        shape(state, self.schema, "source_state")
        require(digest(state) == expected_revision, "ownership.stale_revision")
        history = self.append_decision(
            state["history"], entry, state["history"][-1]["sha256"] if state["history"] else ZERO,
        )
        require(entry["artifact_id"] == state["artifact_id"]
                and entry["artifact_class"] == state["artifact_class"]
                and entry["base_sha256"] == state["source"]["sha256"], "ownership.wrong_base")
        self.source(state["source"])
        result = copy.deepcopy(state)
        result["history"] = history
        unresolved = set()
        for item in state["history"]:
            if item["kind"] == "conflict":
                unresolved.add(item["id"])
            elif item["kind"] == "source_change" and item["disposition"] == "accept":
                unresolved.difference_update(item["related_decisions"])
        if entry["kind"] == "freeze":
            result["publishing_frozen"] = True
        elif entry["kind"] in {"source_change", "restore"} and entry["disposition"] == "accept":
            require(unresolved <= set(entry["related_decisions"]), "conflict.unresolved")
            require(entry["result"] is not None and version(entry["target_version"]) > version(state["version"]),
                    "version.not_new")
            if entry["kind"] == "restore":
                require(entry["result"] in [item["source"] for item in state["archived"]], "restore.unknown_version")
            else:
                require(entry["result"] in [item["source"] for item in entry["proposals"]], "decision.result_not_proposed")
            result["archived"].append({"version": state["version"], "source": copy.deepcopy(state["source"])})
            result.update(version=entry["target_version"], source=copy.deepcopy(entry["result"]), status="reopened")
        else:
            require(entry["result"] is None, "decision.cannot_promote")
        return result

    def access(self, grant, file_id, page, action, channel="controlled_git"):
        shape(grant, self.schema, "grant")
        require(channel == "controlled_git", "access.figma_unverified")
        require(not grant["external"] and not grant["revoked"], "access.external_or_revoked")
        issued, expires = window(
            grant["issued_at"], grant["expires_at"], self.now, self.policy["flow_control"]["access_hours"],
        )
        assigned_until = self.binding(grant["context_id"], grant["role"], grant["artifact_id"], issued)
        require(expires <= assigned_until, "access.outlives_assignment")
        self.source(grant["audit"])
        files = unique(self.policy["topology"]["files"])
        require(file_id in grant["file_ids"] and file_id in files, "access.file_out_of_scope")
        require(action in grant["permissions"], "access.action_denied")
        require(page in files[file_id]["pages"], "access.unknown_page")
        if action == "edit":
            owner = "design_ops" if page in self.policy["topology"]["controlled_pages"] else files[file_id]["owner_role"]
            require(grant["role"] == owner, "access.not_region_owner")
            require(page != "Archive", "access.archive_read_only")


def scope_digest(record):
    scope = {key: record[key] for key in (
        "id", "artifact_class", "squad", "version", "source", "gate_id", "change_kind",
    )}
    scope["author_contexts"] = sorted(record["author_contexts"])
    for key in ("inputs", "evidence"):
        scope[key] = sorted(record[key], key=lambda item: item["id"])
    scope["dependencies"] = sorted(record["dependencies"], key=lambda item: item["artifact_id"])
    scope["comments"] = sorted(
        ({key: value for key, value in item.items() if key != "resolution"} for item in record["comments"]),
        key=lambda item: item["id"],
    )
    return digest(scope)


def version(value):
    require(isinstance(value, str) and re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value),
            "version.invalid")
    return tuple(int(part) for part in value.split("."))


def validate_history(history, schema):
    head, identities = ZERO, set()
    for item in history:
        shape(item, schema, "decision")
        require(item["id"] not in identities and item["previous_sha256"] == head
                and item["sha256"] == digest({key: value for key, value in item.items() if key != "sha256"}),
                "decision.history_changed")
        identities.add(item["id"])
        head = item["sha256"]
    return head


def check_publishing(policy, schema, state):
    validate_policy(policy, schema)
    shape(state, schema, "source_state")
    require(not state["publishing_frozen"], "publish.frozen")
    require(policy["workspace"]["figma_access_verified"] and policy["workspace"]["figma_publishing_enabled"],
            "publish.figma_disabled")


def queue_metrics(policy, schema, work, now, assignments, read_blob=git_blob):
    checker = Checker(policy, schema, assignments, now, read_blob)
    require(isinstance(now, datetime) and now.tzinfo is not None and now.utcoffset() == timedelta(0),
            "time.untrusted_clock")
    for item in work:
        shape(item, schema, "work")
    unique(work)
    squads, reviewers = Counter(), Counter()
    ages, blocked, unacknowledged, overdue, escalated = [], 0, 0, 0, 0
    limits = policy["flow_control"]
    roles = unique(policy["roles"])
    coordinators = {
        item["context_id"] for item in assignments if "decision_coordinator" in item["roles"]
    }
    for item in work:
        require(item["review_role"] in roles, "queue.unknown_reviewer")
        checker.binding(item["review_context_id"], item["review_role"], item["id"])
        squads[item["squad"]] += 1
        require(squads[item["squad"]] <= limits["wip_per_squad"], "queue.squad_wip")
        submitted = instant(item["submitted_at"])
        require(submitted <= now, "queue.future")
        if item["acknowledged_at"] is not None:
            require(submitted <= instant(item["acknowledged_at"]) <= now, "queue.invalid_ack")
        if item["phase"] != "draft":
            context = item["review_context_id"]
            reviewers[context] += 1
            cap = limits["wip_coordinator"] if context in coordinators else limits["wip_per_verifier"]
            require(reviewers[context] <= cap, "queue.reviewer_wip")
            age = (now - submitted).total_seconds() / 3600
            ages.append(age)
            unacknowledged += item["acknowledged_at"] is None and age >= limits["acknowledge_hours"]
            overdue += age >= limits["disposition_hours"]
            escalated += age >= limits["escalate_hours"]
        blocked += item["phase"] == "blocked"
    return {
        "review_age_hours": max(ages, default=0), "blocked_artifact_count": blocked,
        "wip_by_squad": dict(sorted(squads.items())), "unacknowledged_count": unacknowledged,
        "overdue_count": overdue, "escalated_count": escalated,
    }


def artifact_metrics(snapshot, schema, now):
    shape(snapshot, schema, "snapshot")
    unique(snapshot["records"])
    require(isinstance(now, datetime) and now.tzinfo is not None and now.utcoffset() == timedelta(0),
            "time.untrusted_clock")
    expiries = [instant(review["expires_at"]) for record in snapshot["records"] for review in record["reviews"]]
    future = [item for item in expiries if item > now]
    return {
        "reopened_gate_count": sum(record["status"] == "reopened" for record in snapshot["records"]),
        "approval_expiry": {
            "expired_review_count": sum(item <= now for item in expiries),
            "next_deadline": min(future).strftime("%Y-%m-%dT%H:%M:%SZ") if future else None,
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, help="Candidate gate snapshot; not an assignment authority.")
    parser.add_argument("--assignments", type=Path, help="Separately coordinator-verified, immutable role assignments.")
    args = parser.parse_args(argv)
    if bool(args.snapshot) != bool(args.assignments):
        parser.error("--snapshot and --assignments must be supplied together")
    try:
        data, schema = support.load_json(ROOT / DATA), support.load_json(ROOT / SCHEMA)
        summary = validate_policy(data, schema, (ROOT / DOCUMENT).read_text(encoding="utf-8"))
        if args.snapshot:
            checker = Checker(data, schema, support.load_json(args.assignments), datetime.now(timezone.utc))
            result = checker.close_gate(support.load_json(args.snapshot))
            print(json.dumps(result, sort_keys=True))
        else:
            print(
                f"Design source {summary['contract_version']} valid: {summary['artifact_classes']} artifact classes, "
                f"{summary['gates']} gates. Role rights unapproved; Figma publishing and participant contact disabled."
            )
    except Refused as error:
        print(f"Design check refused: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError):
        print("Design check refused: input.unreadable_or_invalid", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
