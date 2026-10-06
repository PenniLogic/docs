"""Synthetic T-UXR-01 failure fixtures, not appointments, consent or live SaaS evidence."""

import contextlib
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_design_gates", ROOT / "scripts/check_design_gates.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
POLICY = module.support.load_json(ROOT / module.DATA)
SCHEMA = module.support.load_json(ROOT / module.SCHEMA)
DOCUMENT = (ROOT / module.DOCUMENT).read_text(encoding="utf-8")
NOW = datetime(2026, 10, 5, 10, tzinfo=timezone.utc)
BASE = "3e4afcb9575badf8669a50136da69fcc6f634500"


def stamp(value):
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def context(number):
    return f"{number:08x}-0000-4000-8000-000000000000"


class Fixture:
    def __init__(self, gate=0):
        self.policy, self.schema, self.blobs = copy.deepcopy(POLICY), copy.deepcopy(SCHEMA), {}
        self.contexts = {role["id"]: context(index + 1) for index, role in enumerate(POLICY["roles"])}
        self.assignments = [
            {
                "context_id": self.contexts[role["id"]], "runtime": "synthetic-test-context-not-an-appointment",
                "login": "basiltt", "roles": [role["id"]],
                "artifact_ids": [f"A{number}" for number in range(10)] + ["component_library", "research_synthesis"],
                "issued_at": stamp(NOW - timedelta(hours=24)), "expires_at": stamp(NOW + timedelta(hours=24)),
                "evidence": self.source("assignment_" + role["id"]),
            }
            for role in POLICY["roles"]
        ]
        records = []
        classes = (
            "product_truth", "sitemaps", "visual_direction", "android_experience", "components",
            "prototype_validation", "readiness", "build_conformance", "release_design_qa", "outcome_review",
        )
        raci = {item["id"]: item for item in POLICY["artifact_classes"]}
        for number in range(gate + 1):
            spec = POLICY["gates"][number]
            artifact = raci[classes[number]]
            record = {
                "id": f"A{number}", "artifact_class": classes[number], "squad": "fixture",
                "version": "1.0.0", "source": self.source(f"artifact_{number}"),
                "author_contexts": [context(0)], "status": "approved", "gate_id": spec["id"],
                "change_kind": "standard",
                "inputs": [{"id": "contract", "version": "fixture-contract-1", "source": self.source(f"input_{number}")}],
                "evidence": [self.evidence(key, number) for key in spec["required_evidence"]],
                "dependencies": [] if number == 0 else [{
                    "artifact_id": records[-1]["id"], "gate_id": records[-1]["gate_id"],
                    "scope_sha256": module.scope_digest(records[-1]),
                }],
                "comments": [], "reviews": [],
            }
            approver = artifact["accountable"] if spec["approver"] == "artifact_accountable" else spec["approver"]
            record["reviews"] = [
                self.review(record, approver, "approval"),
                self.review(record, artifact["verifiers"][0], "verification"),
            ]
            records.append(record)
        self.snapshot = {"contract_version": "1.0.0", "target": f"A{gate}", "records": records}

    def source(self, name):
        path = f"fixtures/{name}.txt"
        content = f"Synthetic nonparticipant source fixture: {name}\n".encode("ascii")
        self.blobs[("1" * 40, path)] = content
        return {"commit": "1" * 40, "path": path, "sha256": module.digest(content)}

    def evidence(self, key, number=0):
        return {
            "id": key, "source": self.source(f"evidence_{number}_{key}"),
            "observed_at": stamp(NOW - timedelta(hours=4)), "expires_at": stamp(NOW + timedelta(hours=6)),
        }

    def review(self, record, role, purpose):
        return {
            "role": role, "context_id": self.contexts[role], "purpose": purpose, "decision": "approved",
            "scope_sha256": module.scope_digest(record),
            "decided_at": stamp(NOW - timedelta(hours=1)), "expires_at": stamp(NOW + timedelta(hours=6)),
            "evidence": self.source(f"review_{record['id']}_{purpose}_{role}"),
        }

    def checker(self, now=NOW):
        return module.Checker(
            self.policy, self.schema, self.assignments, now,
            read_blob=lambda commit, path: self.blobs[(commit, path)],
        )

    def close(self, now=NOW):
        return self.checker(now).close_gate(self.snapshot)

    def resign(self, record=None):
        record = self.snapshot["records"][-1] if record is None else record
        scope = module.scope_digest(record)
        for review in record["reviews"]:
            review["scope_sha256"] = scope
        return scope

    def comment(self, resolved=False):
        record = self.snapshot["records"][-1]
        role = next(item for item in POLICY["artifact_classes"] if item["id"] == record["artifact_class"])["verifiers"][0]
        item = {
            "id": "comment_one", "blocking": True, "author_context_id": self.contexts[role],
            "evidence": self.source("blocking_comment"), "resolution": None,
        }
        record["comments"].append(item)
        scope = self.resign(record)
        if resolved:
            item["resolution"] = {
                "context_id": self.contexts[role], "role": role, "scope_sha256": scope,
                "resolved_at": stamp(NOW - timedelta(hours=2)), "evidence": self.source("comment_retest"),
            }
        return item

    def state(self):
        return {
            "artifact_id": "component_library", "artifact_class": "components", "version": "1.0.0",
            "source": self.source("canonical_components"), "history": [], "archived": [],
            "publishing_frozen": False, "status": "approved",
        }

    def proposal(self, squad="android", name="variant"):
        return {
            "squad": squad, "branch": f"T-UXS-01__{squad}__{name}",
            "source": self.source(squad + "_" + name),
        }

    def decision(self, state, identity="DEC1", kind="source_change"):
        proposal = self.proposal()
        actor = "design_ops" if kind == "freeze" else "systems"
        if kind in {"shared_system_major", "material_exception"}:
            actor = "decision_coordinator"
        return {
            "id": identity, "artifact_id": state["artifact_id"], "artifact_class": state["artifact_class"],
            "kind": kind, "disposition": "accept", "author_contexts": [context(0)],
            "actor_context_id": self.contexts[actor], "actor_role": actor,
            "verifier_context_id": self.contexts["design_qa"], "verifier_role": "design_qa",
            "base_sha256": state["source"]["sha256"], "target_version": "1.1.0",
            "proposals": [proposal], "result": proposal["source"] if kind == "source_change" else None,
            "reason": self.source("decision_rationale_" + identity), "related_decisions": [],
            "occurred_at": stamp(NOW - timedelta(minutes=30)), "expires_at": stamp(NOW + timedelta(hours=4)),
        }

    def grant(self, role="android_design"):
        return {
            "context_id": self.contexts[role], "role": role, "artifact_id": "A3",
            "file_ids": ["f10"], "permissions": ["view", "comment", "edit"], "classification": "synthetic",
            "external": False, "revoked": False, "issued_at": stamp(NOW - timedelta(hours=1)),
            "expires_at": stamp(NOW + timedelta(hours=6)), "audit": self.source("grant_audit"),
        }


class PolicyTests(unittest.TestCase):
    def test_published_policy_schema_and_document(self):
        self.assertEqual(module.validate_policy(POLICY, SCHEMA, DOCUMENT),
                         {"contract_version": "1.0.0", "artifact_classes": 24, "gates": 10})
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(module.main([]), 0)
        self.assertIn("Role rights unapproved", output.getvalue())

    def test_missing_and_multiple_accountables(self):
        for replacement in (None, ["design_ops", "research"]):
            policy = copy.deepcopy(POLICY)
            if replacement is None:
                del policy["artifact_classes"][0]["accountable"]
            else:
                policy["artifact_classes"][0]["accountable"] = replacement
            with self.subTest(replacement=replacement), self.assertRaises(module.Refused):
                module.validate_policy(policy, SCHEMA)

    def test_duplicate_artifact_and_role_ids(self):
        for key in ("artifact_classes", "roles"):
            policy = copy.deepcopy(POLICY)
            policy[key].append(copy.deepcopy(policy[key][0]))
            with self.subTest(key=key), self.assertRaisesRegex(module.Refused, "identity.duplicate"):
                module.validate_policy(policy, SCHEMA)

    def test_missing_unknown_and_self_verifier(self):
        for verifier in ([], ["unknown"], ["product_owner"]):
            policy = copy.deepcopy(POLICY)
            policy["artifact_classes"][0]["verifiers"] = verifier
            with self.subTest(verifier=verifier), self.assertRaises(module.Refused):
                module.validate_policy(policy, SCHEMA)

    def test_missing_class_or_operational_role(self):
        for key in ("artifact_classes", "roles"):
            policy = copy.deepcopy(POLICY)
            policy[key].pop()
            with self.subTest(key=key), self.assertRaisesRegex(module.Refused, "vocabulary.missing"):
                module.validate_policy(policy, SCHEMA)

    def test_cdo_cannot_expand_to_d0_or_d9(self):
        for index in (0, 9):
            policy = copy.deepcopy(POLICY)
            policy["gates"][index]["approver"] = "decision_coordinator"
            with self.subTest(index=index), self.assertRaisesRegex(module.Refused, "wrong_approver"):
                module.validate_policy(policy, SCHEMA)

    def test_missing_gate_approver_and_prerequisite(self):
        policy = copy.deepcopy(POLICY)
        del policy["gates"][4]["approver"]
        with self.assertRaises(module.Refused):
            module.validate_policy(policy, SCHEMA)
        policy = copy.deepcopy(POLICY)
        policy["gates"][6]["required_gates"] = []
        with self.assertRaisesRegex(module.Refused, "gate.prerequisites"):
            module.validate_policy(policy, SCHEMA)

    def test_original_gate_specific_ttl_ceiling_cannot_be_widened(self):
        for number, cap in enumerate((720, 720, 720, 336, 336, 168, 168, 72, 24, 720)):
            policy = copy.deepcopy(POLICY)
            policy["gates"][number]["ttl_hours"] = cap + 1
            with self.subTest(gate=number), self.assertRaisesRegex(module.Refused, "gate.lifetime"):
                module.validate_policy(policy, SCHEMA)

    def test_original_required_evidence_vocabulary(self):
        expected = [
            "product_truth constraints known_evidence open_decisions research_ethics",
            "personas_jobs journeys blueprints platform_allocation sitemaps coverage_registry",
            "tested_alternatives direction_decision accessibility_precheck",
            "task_flows wireflows content_hierarchy edge_cases contract_assumptions telemetry_intent",
            "high_fidelity adaptive_variants components tokens content motion",
            "interactive_paths heuristic_review accessibility_audit usability_results comprehension_results",
            "versioned_handoff assets component_mapping state_table api_fields test_ids known_limitations",
            "design_code_comparison visual_regression interaction_parity accessibility_parity deviations",
            "device_browser_operator_walkthroughs localization destructive_flows privacy final_uat",
            "aggregate_metrics redacted_support_synthesis longitudinal_research design_debt_decisions",
        ]
        for gate, keys in zip(POLICY["gates"], expected):
            self.assertEqual(gate["required_evidence"], keys.split())

    def test_unbounded_limits_and_lifetimes(self):
        for key in POLICY["flow_control"]:
            for value in (0, 10000, True):
                policy = copy.deepcopy(POLICY)
                policy["flow_control"][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(module.Refused):
                    module.validate_policy(policy, SCHEMA)

    def test_operational_enabling_and_external_sharing_refused(self):
        for key in ("figma_access_verified", "figma_publishing_enabled", "participant_contact_enabled", "role_rights_approved"):
            policy = copy.deepcopy(POLICY)
            policy["workspace"][key] = True
            with self.subTest(key=key), self.assertRaises(module.Refused):
                module.validate_policy(policy, SCHEMA)
        for key in ("public_links_enabled", "external_sharing_enabled"):
            policy = copy.deepcopy(POLICY)
            policy["access"][key] = True
            with self.subTest(key=key), self.assertRaises(module.Refused):
                module.validate_policy(policy, SCHEMA)

    def test_topology_names_and_controlled_pages(self):
        names = [item["name"] for item in POLICY["topology"]["files"]]
        self.assertEqual(names, [
            "00 - Product truth and research", "01 - Service and IA", "02 - Foundations library",
            "03 - Components library", "10 - Android product", "20 - Customer web product",
            "30 - Admin product", "40 - Content and localization", "50 - Design QA", "90 - Archive",
        ])
        policy = copy.deepcopy(POLICY)
        policy["topology"]["files"][0]["pages"].remove("Archive")
        with self.assertRaisesRegex(module.Refused, "topology.owner_or_page"):
            module.validate_policy(policy, SCHEMA)

    def test_unknown_schema_keyword_fails_instead_of_being_ignored(self):
        schema = copy.deepcopy(SCHEMA)
        schema["unevaluatedProperties"] = False
        with self.assertRaisesRegex(module.Refused, "schema.invalid"):
            module.validate_policy(POLICY, schema)

    def test_boolean_version_and_control_character_identifiers_fail(self):
        policy = copy.deepcopy(POLICY)
        policy["schema_version"] = True
        with self.assertRaises(module.Refused):
            module.validate_policy(policy, SCHEMA)
        fixture = Fixture()
        fixture.snapshot["target"] += "\n"
        with self.assertRaises(module.Refused):
            fixture.close()

    def test_consumer_definitions_and_research_boundary(self):
        self.assertTrue({"snapshot", "assignment", "decision", "source_state", "grant", "work"} <= SCHEMA["definitions"].keys())
        self.assertFalse(POLICY["workspace"]["participant_contact_enabled"])
        for identifier in ("research", "privacy", "legal", "accessibility", "research_store_owner"):
            self.assertIn(f"`{identifier}`", DOCUMENT)


class GateTests(unittest.TestCase):
    def test_every_gate_recursively_checks_current_evidence(self):
        for number in range(10):
            with self.subTest(gate=number):
                fixture = Fixture(number)
                before = copy.deepcopy(fixture.snapshot)
                result = fixture.close()
                self.assertEqual(result["checked_artifacts"], number + 1)
                self.assertEqual(result["expires_at"], stamp(NOW + timedelta(hours=6)))
                self.assertEqual(fixture.snapshot, before)

    def test_in_review_target_may_be_checked_but_not_used_as_approved_dependency(self):
        fixture = Fixture(1)
        fixture.snapshot["records"][-1]["status"] = "in_review"
        fixture.close()
        fixture.snapshot["records"][0]["status"] = "in_review"
        with self.assertRaisesRegex(module.Refused, "gate.not_reviewable"):
            fixture.close()

    def test_exact_expiry_boundary_no_grace(self):
        fixture = Fixture()
        review = fixture.snapshot["records"][0]["reviews"][0]
        review["expires_at"] = stamp(NOW)
        fixture.close(NOW - timedelta(microseconds=1))
        for offset in (0, 1):
            with self.subTest(offset=offset), self.assertRaisesRegex(module.Refused, "time.expired_or_future"):
                fixture.close(NOW + timedelta(microseconds=offset))

    def test_future_reversed_overlong_and_malformed_times(self):
        for field, value in (
            ("decided_at", stamp(NOW + timedelta(seconds=1))),
            ("expires_at", stamp(NOW - timedelta(days=1))),
            ("expires_at", stamp(NOW + timedelta(days=32))),
            ("expires_at", "2026-02-30T10:00:00Z"),
            ("expires_at", "2026-10-05T16:00:00"),
            ("expires_at", "2026-10-05T16:00:00+05:30"),
        ):
            fixture = Fixture()
            fixture.snapshot["records"][0]["reviews"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(module.Refused):
                fixture.close()
        with self.assertRaisesRegex(module.Refused, "time.untrusted_clock"):
            Fixture().close(NOW.replace(tzinfo=None))

    def test_stale_artifact_version_and_input_revision(self):
        for change in ("version", "input", "authors"):
            fixture = Fixture()
            record = fixture.snapshot["records"][0]
            if change == "version":
                record["version"] = "1.0.1"
            elif change == "input":
                record["inputs"][0]["version"] = "fixture-contract-2"
            else:
                record["author_contexts"].append(context(999))
            with self.subTest(change=change), self.assertRaisesRegex(module.Refused, "approval.stale"):
                fixture.close()

    def test_immutable_source_commit_is_part_of_review_scope(self):
        fixture = Fixture()
        source = fixture.snapshot["records"][0]["source"]
        fixture.blobs[("2" * 40, source["path"])] = fixture.blobs[(source["commit"], source["path"])]
        source["commit"] = "2" * 40
        with self.assertRaisesRegex(module.Refused, "approval.stale"):
            fixture.close()

    def test_missing_evidence_key_or_blob_and_wrong_digest(self):
        for change in ("key", "blob", "digest"):
            fixture = Fixture()
            record = fixture.snapshot["records"][0]
            source = record["evidence"][0]["source"]
            if change == "key":
                record["evidence"].pop()
            elif change == "blob":
                del fixture.blobs[(source["commit"], source["path"])]
            else:
                source["sha256"] = module.ZERO
            fixture.resign()
            with self.subTest(change=change), self.assertRaises(module.Refused):
                fixture.close()

    def test_every_required_evidence_key_prevents_closure_when_missing(self):
        for number, gate in enumerate(POLICY["gates"]):
            for key in gate["required_evidence"]:
                fixture = Fixture(number)
                record = fixture.snapshot["records"][-1]
                record["evidence"] = [item for item in record["evidence"] if item["id"] != key]
                fixture.resign()
                with self.subTest(gate=number, key=key), self.assertRaisesRegex(module.Refused, "gate.missing_evidence"):
                    fixture.close()

    def test_evidence_expiry_and_review_before_evidence(self):
        fixture = Fixture()
        record = fixture.snapshot["records"][0]
        record["evidence"][0]["expires_at"] = stamp(NOW)
        fixture.resign()
        with self.assertRaisesRegex(module.Refused, "time.expired_or_future"):
            fixture.close()
        fixture = Fixture()
        fixture.snapshot["records"][0]["evidence"][0]["observed_at"] = stamp(NOW - timedelta(minutes=5))
        fixture.resign()
        with self.assertRaisesRegex(module.Refused, "approval.precedes_evidence"):
            fixture.close()

    def test_unresolved_blocking_comment_fails(self):
        fixture = Fixture()
        fixture.comment()
        with self.assertRaisesRegex(module.Refused, "comment.unresolved_blocking"):
            fixture.close()

    def test_nonblocking_comment_does_not_block_but_new_scope_needs_review(self):
        fixture = Fixture()
        comment = fixture.comment()
        comment["blocking"] = False
        with self.assertRaisesRegex(module.Refused, "approval.stale"):
            fixture.close()
        fixture.resign()
        fixture.close()

    def test_current_independent_resolution_passes(self):
        fixture = Fixture()
        fixture.comment(resolved=True)
        fixture.close()

    def test_specialist_finder_can_resolve_without_claiming_another_role(self):
        fixture = Fixture()
        comment = fixture.comment(resolved=True)
        comment["author_context_id"] = fixture.contexts["security"]
        comment["resolution"].update(context_id=fixture.contexts["security"], role="security")
        scope = fixture.resign()
        comment["resolution"]["scope_sha256"] = scope
        specialist = next(item for item in fixture.assignments if item["roles"] == ["security"])
        specialist["expires_at"] = stamp(NOW + timedelta(hours=1))
        self.assertEqual(fixture.close()["expires_at"], specialist["expires_at"])
        fixture.assignments.remove(specialist)
        with self.assertRaisesRegex(module.Refused, "assignment.missing_or_revoked"):
            fixture.close()

    def test_author_resolution_stale_resolution_and_future_resolution_fail(self):
        for change in ("author", "scope", "future"):
            fixture = Fixture()
            comment = fixture.comment(resolved=True)
            if change == "author":
                comment["resolution"]["context_id"] = context(0)
            elif change == "scope":
                comment["resolution"]["scope_sha256"] = module.ZERO
            else:
                comment["resolution"]["resolved_at"] = stamp(NOW + timedelta(seconds=1))
            with self.subTest(change=change), self.assertRaises(module.Refused):
                fixture.close()

    def test_rejected_review_and_missing_approver(self):
        fixture = Fixture()
        fixture.snapshot["records"][0]["reviews"][0]["decision"] = "rejected"
        with self.assertRaisesRegex(module.Refused, "review.rejected"):
            fixture.close()
        fixture = Fixture()
        record = fixture.snapshot["records"][0]
        record["reviews"][0] = fixture.review(record, "content", "approval")
        with self.assertRaisesRegex(module.Refused, "gate.missing_or_wrong_approver"):
            fixture.close()

    def test_same_account_independent_contexts_are_not_two_humans(self):
        fixture = Fixture()
        self.assertEqual({item["login"] for item in fixture.assignments}, {"basiltt"})
        fixture.close()
        record = fixture.snapshot["records"][0]
        producer = record["author_contexts"][0]
        record["reviews"][0]["context_id"] = producer
        with self.assertRaisesRegex(module.Refused, "review.author_is_reviewer"):
            fixture.close()

    def test_same_context_cannot_verify_under_another_role(self):
        fixture = Fixture()
        record = fixture.snapshot["records"][0]
        owner = next(item for item in fixture.assignments if item["roles"] == ["product_owner"])
        owner["roles"].append("design_qa")
        record["reviews"][1]["context_id"] = owner["context_id"]
        with self.assertRaisesRegex(module.Refused, "review.context_not_independent"):
            fixture.close()

    def test_missing_or_wrong_independent_verifier(self):
        fixture = Fixture()
        record = fixture.snapshot["records"][0]
        record["reviews"][1] = fixture.review(record, "content", "verification")
        with self.assertRaisesRegex(module.Refused, "gate.missing_independent_verifier"):
            fixture.close()
        record["reviews"].pop()
        with self.assertRaises(module.Refused):
            fixture.close()

    def test_missing_revoked_expired_or_wrong_scope_assignment(self):
        for change in ("missing", "expired", "scope", "role"):
            fixture = Fixture()
            owner = next(item for item in fixture.assignments if item["roles"] == ["product_owner"])
            if change == "missing":
                fixture.assignments.remove(owner)
            elif change == "expired":
                owner["expires_at"] = stamp(NOW)
            elif change == "scope":
                owner["artifact_ids"] = ["unrelated"]
            else:
                owner["roles"] = ["research"]
            with self.subTest(change=change), self.assertRaises(module.Refused):
                fixture.close()

    def test_review_before_or_outliving_assignment(self):
        for field, value in (
            ("issued_at", stamp(NOW - timedelta(minutes=10))),
            ("expires_at", stamp(NOW + timedelta(hours=1))),
        ):
            fixture = Fixture()
            owner = next(item for item in fixture.assignments if item["roles"] == ["product_owner"])
            owner[field] = value
            with self.subTest(field=field), self.assertRaises(module.Refused):
                fixture.close()

    def test_duplicate_review_record_and_assignment(self):
        fixture = Fixture()
        fixture.snapshot["records"][0]["reviews"].append(copy.deepcopy(fixture.snapshot["records"][0]["reviews"][0]))
        with self.assertRaisesRegex(module.Refused, "review.duplicate"):
            fixture.close()
        fixture = Fixture()
        fixture.assignments.append(copy.deepcopy(fixture.assignments[0]))
        with self.assertRaisesRegex(module.Refused, "identity.duplicate"):
            fixture.close()

    def test_missing_stale_and_reopened_prerequisites(self):
        fixture = Fixture(2)
        fixture.snapshot["records"][-1]["dependencies"] = []
        with self.assertRaisesRegex(module.Refused, "gate.missing_prerequisite"):
            fixture.close()
        fixture = Fixture(2)
        fixture.snapshot["records"][1]["version"] = "2.0.0"
        with self.assertRaisesRegex(module.Refused, "gate.stale_dependency"):
            fixture.close()
        for status in ("blocked", "reopened", "archived", "superseded", "draft"):
            fixture = Fixture(2)
            fixture.snapshot["records"][0]["status"] = status
            with self.subTest(status=status), self.assertRaisesRegex(module.Refused, "gate.not_reviewable"):
                fixture.close()

    def test_expired_ancestor_blocks_current_descendant(self):
        fixture = Fixture(6)
        fixture.snapshot["records"][0]["reviews"][0]["expires_at"] = stamp(NOW)
        with self.assertRaisesRegex(module.Refused, "time.expired_or_future"):
            fixture.close()

    def test_prerequisite_newer_than_dependent_review_fails(self):
        fixture = Fixture(1)
        fixture.snapshot["records"][0]["reviews"][0]["decided_at"] = stamp(NOW - timedelta(minutes=30))
        with self.assertRaisesRegex(module.Refused, "approval.precedes_evidence"):
            fixture.close()

    def test_verifier_who_authored_consumed_evidence_is_not_independent(self):
        fixture = Fixture(1)
        parent, target = fixture.snapshot["records"]
        parent["author_contexts"].append(fixture.contexts["service_design"])
        fixture.resign(parent)
        target["dependencies"][0]["scope_sha256"] = module.scope_digest(parent)
        fixture.resign(target)
        with self.assertRaisesRegex(module.Refused, "review.author_is_reviewer"):
            fixture.close()

    def test_shared_major_requires_additional_coordinator_and_no_single_context_votes(self):
        fixture = Fixture(4)
        record = fixture.snapshot["records"][-1]
        record["change_kind"] = "shared_system_major"
        record["evidence"].append(fixture.evidence("shared_system_major", 4))
        fixture.resign()
        with self.assertRaisesRegex(module.Refused, "gate.missing_or_wrong_approver"):
            fixture.close()
        record["reviews"].append(fixture.review(record, "decision_coordinator", "approval"))
        fixture.close()
        systems = next(item for item in fixture.assignments if item["roles"] == ["systems"])
        systems["roles"].append("decision_coordinator")
        record["reviews"][-1]["context_id"] = systems["context_id"]
        with self.assertRaisesRegex(module.Refused, "review.multiple_roles_one_context"):
            fixture.close()

    def test_major_authority_cannot_be_attached_to_an_unrelated_class(self):
        fixture = Fixture()
        record = fixture.snapshot["records"][0]
        record["change_kind"] = "shared_system_major"
        record["evidence"].append(fixture.evidence("shared_system_major"))
        fixture.resign()
        with self.assertRaisesRegex(module.Refused, "authority.major_scope"):
            fixture.close()

    def test_material_exception_does_not_bypass_blockers_or_expiry(self):
        fixture = Fixture()
        record = fixture.snapshot["records"][0]
        record["change_kind"] = "material_exception"
        record["evidence"].append(fixture.evidence("material_exception"))
        fixture.resign()
        record["reviews"].append(fixture.review(record, "decision_coordinator", "approval"))
        fixture.close()
        fixture.comment()
        with self.assertRaisesRegex(module.Refused, "comment.unresolved_blocking"):
            fixture.close()

    def test_duplicate_ids_unknown_gate_and_dependency_cycle_fail(self):
        for change in ("record", "evidence", "gate", "cycle"):
            fixture = Fixture()
            record = fixture.snapshot["records"][0]
            if change == "record":
                fixture.snapshot["records"].append(copy.deepcopy(record))
            elif change == "evidence":
                record["evidence"].append(copy.deepcopy(record["evidence"][0]))
            elif change == "gate":
                record["gate_id"] = "D10"
            else:
                record["dependencies"] = [{"artifact_id": "A0", "gate_id": "D0", "scope_sha256": module.ZERO}]
            with self.subTest(change=change), self.assertRaises(module.Refused):
                fixture.close()

    def test_canonical_scope_ignores_array_order_not_content(self):
        fixture = Fixture()
        record = fixture.snapshot["records"][0]
        expected = module.scope_digest(record)
        record["evidence"].reverse()
        record["reviews"].reverse()
        self.assertEqual(module.scope_digest(record), expected)
        fixture.close()


class DecisionTabletopTests(unittest.TestCase):
    def test_two_squads_resolve_without_overwriting_either_proposal(self):
        fixture = Fixture()
        state = fixture.state()
        original = copy.deepcopy(state)
        stale_revision = module.digest(state)
        android, web = fixture.proposal(), fixture.proposal("web")
        conflict = fixture.decision(state, "CONFLICT", "conflict")
        conflict.update(disposition="defer", result=None, proposals=[android, web])
        held = fixture.checker().source_change(state, conflict, stale_revision)
        self.assertEqual(state, original)
        self.assertEqual(held["source"], state["source"])
        self.assertEqual(held["history"][0]["proposals"], [android, web])
        for proposal in (android, web):
            attempted = fixture.decision(state)
            attempted.update(proposals=[proposal], result=proposal["source"])
            before = copy.deepcopy(held)
            with self.assertRaisesRegex(module.Refused, "ownership.stale_revision"):
                fixture.checker().source_change(held, attempted, stale_revision)
            self.assertEqual(held, before)
            with self.assertRaisesRegex(module.Refused, "conflict.unresolved"):
                fixture.checker().source_change(held, attempted, module.digest(held))
        combined = fixture.proposal("systems", "additive-both")
        resolution = fixture.decision(held, "RESOLVE")
        resolution.update(proposals=[android, web, combined], result=combined["source"], related_decisions=["CONFLICT"])
        result = fixture.checker().source_change(held, resolution, module.digest(held))
        self.assertEqual(result["source"], combined["source"])
        self.assertEqual(result["status"], "reopened")
        self.assertEqual(result["archived"], [{"version": "1.0.0", "source": original["source"]}])
        self.assertEqual(result["history"][:1], held["history"])
        self.assertEqual(result["history"][-1]["proposals"][:2], [android, web])
        self.assertEqual(fixture.blobs[("1" * 40, android["source"]["path"])],
                         b"Synthetic nonparticipant source fixture: android_variant\n")

    def test_branch_collision_and_wrong_squad_fail_without_mutation(self):
        for change in ("collision", "squad"):
            fixture = Fixture()
            state, entry = fixture.state(), None
            entry = fixture.decision(state)
            if change == "collision":
                entry["proposals"].append(copy.deepcopy(entry["proposals"][0]))
            else:
                entry["proposals"][0]["squad"] = "web"
            before = copy.deepcopy(state)
            with self.subTest(change=change), self.assertRaises(module.Refused):
                fixture.checker().source_change(state, entry, module.digest(state))
            self.assertEqual(state, before)

    def test_wrong_base_version_result_and_unresolved_reference_fail(self):
        for change in ("base", "version", "result", "related"):
            fixture = Fixture()
            state = fixture.state()
            entry = fixture.decision(state)
            if change == "base":
                entry["base_sha256"] = module.ZERO
            elif change == "version":
                entry["target_version"] = "1.0.0"
            elif change == "result":
                entry["result"] = fixture.source("unproposed")
            else:
                entry["related_decisions"] = ["DOES_NOT_EXIST"]
            with self.subTest(change=change), self.assertRaises(module.Refused):
                fixture.checker().source_change(state, entry, module.digest(state))

    def test_history_is_append_only_and_anchored_to_expected_head(self):
        fixture = Fixture()
        state = fixture.state()
        entry = fixture.decision(state)
        history = fixture.checker().append_decision([], entry, module.ZERO)
        module.validate_history(history, SCHEMA)
        later = fixture.decision(state, "LATER")
        with self.assertRaisesRegex(module.Refused, "decision.stale_head"):
            fixture.checker().append_decision(history, later, module.ZERO)
        corrupted = copy.deepcopy(history)
        corrupted[0]["disposition"] = "decline"
        with self.assertRaisesRegex(module.Refused, "decision.history_changed"):
            module.validate_history(corrupted, SCHEMA)
        with self.assertRaisesRegex(module.Refused, "decision.duplicate"):
            fixture.checker().append_decision(history, entry, history[-1]["sha256"])
        later["occurred_at"] = stamp(NOW - timedelta(hours=1))
        with self.assertRaisesRegex(module.Refused, "decision.backdated"):
            fixture.checker().append_decision(history, later, history[-1]["sha256"])

    def test_changed_state_cannot_reuse_a_trusted_revision(self):
        fixture = Fixture()
        state = fixture.state()
        trusted = module.digest(state)
        state["publishing_frozen"] = True
        with self.assertRaisesRegex(module.Refused, "ownership.stale_revision"):
            fixture.checker().source_change(state, fixture.decision(state), trusted)

    def test_decision_author_cannot_approve_or_verify_proposals(self):
        for role in ("actor_context_id", "verifier_context_id"):
            fixture = Fixture()
            state = fixture.state()
            entry = fixture.decision(state)
            entry["author_contexts"].append(entry[role])
            with self.subTest(role=role), self.assertRaisesRegex(module.Refused, "decision.author_is_reviewer"):
                fixture.checker().source_change(state, entry, module.digest(state))

    def test_malformed_and_logically_invalid_decision_shapes_fail(self):
        for change in ("missing", "declined_result", "accepted_no_result", "invented_hash", "expired", "overlong"):
            fixture = Fixture()
            state = fixture.state()
            entry = fixture.decision(state)
            if change == "missing":
                del entry["artifact_id"]
            elif change == "declined_result":
                entry["disposition"] = "decline"
            elif change == "accepted_no_result":
                entry["result"] = None
            elif change == "invented_hash":
                entry["sha256"] = module.ZERO
            elif change == "expired":
                entry["expires_at"] = stamp(NOW)
            else:
                entry["expires_at"] = stamp(NOW + timedelta(hours=25))
            with self.subTest(change=change), self.assertRaises(module.Refused):
                fixture.checker().source_change(state, entry, module.digest(state))

    def test_expired_history_is_retained_but_cannot_be_reused_as_a_new_decision(self):
        fixture = Fixture()
        entry = fixture.decision(fixture.state())
        history = fixture.checker().append_decision([], entry, module.ZERO)
        self.assertEqual(module.validate_history(history, SCHEMA), history[-1]["sha256"])
        with self.assertRaisesRegex(module.Refused, "time.expired_or_future"):
            fixture.checker(NOW + timedelta(hours=5)).append_decision([], entry, module.ZERO)
        self.assertEqual(module.validate_history(history, SCHEMA), history[-1]["sha256"])

    def test_freeze_and_restore_retain_history_and_never_unfreeze_or_reapprove(self):
        fixture = Fixture()
        baseline = fixture.state()
        changed = fixture.checker().source_change(baseline, fixture.decision(baseline), module.digest(baseline))
        freeze = fixture.decision(changed, "FREEZE", "freeze")
        frozen = fixture.checker().source_change(changed, freeze, module.digest(changed))
        self.assertTrue(frozen["publishing_frozen"])
        self.assertEqual(frozen["history"][:1], changed["history"])
        self.assertEqual(frozen["source"], changed["source"])
        with self.assertRaisesRegex(module.Refused, "publish.frozen"):
            module.check_publishing(POLICY, SCHEMA, frozen)
        restore = fixture.decision(frozen, "RESTORE", "restore")
        restore.update(result=baseline["source"], target_version="1.2.0")
        restored = fixture.checker().source_change(frozen, restore, module.digest(frozen))
        self.assertTrue(restored["publishing_frozen"])
        self.assertEqual(restored["source"], baseline["source"])
        self.assertEqual(restored["version"], "1.2.0")
        self.assertEqual(restored["status"], "reopened")
        self.assertEqual(restored["history"][:2], frozen["history"])
        self.assertEqual(len(restored["archived"]), 2)
        with self.assertRaisesRegex(module.Refused, "publish.frozen"):
            module.check_publishing(POLICY, SCHEMA, restored)
        with self.assertRaisesRegex(module.Refused, "publish.figma_disabled"):
            module.check_publishing(POLICY, SCHEMA, baseline)

    def test_material_exception_has_real_scope_expiry_and_separate_verifier(self):
        for change in ("authority", "expiry", "verifier"):
            fixture = Fixture()
            state = fixture.state()
            entry = fixture.decision(state, kind="material_exception")
            if change == "authority":
                entry["actor_role"] = "systems"
                entry["actor_context_id"] = fixture.contexts["systems"]
            elif change == "expiry":
                entry["expires_at"] = stamp(NOW)
            else:
                entry["verifier_context_id"] = entry["actor_context_id"]
            with self.subTest(change=change), self.assertRaises(module.Refused):
                fixture.checker().append_decision([], entry, module.ZERO)

    def test_research_source_disposition_is_not_legal_or_contact_authorization(self):
        fixture = Fixture()
        state = fixture.state()
        state.update(artifact_id="research_synthesis", artifact_class="research_synthesis")
        entry = fixture.decision(state, kind="research_disposition")
        entry.update(
            actor_context_id=fixture.contexts["research"], actor_role="research",
            verifier_context_id=fixture.contexts["privacy"], verifier_role="privacy",
        )
        result = fixture.checker().append_decision([], entry, module.ZERO)
        self.assertEqual(result[-1]["disposition"], "accept")
        self.assertFalse(fixture.policy["workspace"]["participant_contact_enabled"])
        self.assertFalse(fixture.policy["workspace"]["role_rights_approved"])


class AccessTests(unittest.TestCase):
    def test_owned_source_region_with_scoped_grant(self):
        fixture = Fixture()
        fixture.checker().access(fixture.grant(), "f10", "Flows", "edit")

    def test_view_is_not_edit_and_cross_file_or_shared_region_is_denied(self):
        for change in ("permission", "file", "controlled", "library"):
            fixture = Fixture()
            grant = fixture.grant()
            file_id, page = "f10", "Flows"
            if change == "permission":
                grant["permissions"] = ["view"]
            elif change == "file":
                file_id = "f20"
            elif change == "controlled":
                page = "Cover"
            else:
                grant["file_ids"].append("f03")
                file_id, page = "f03", "Components"
            with self.subTest(change=change), self.assertRaises(module.Refused):
                fixture.checker().access(grant, file_id, page, "edit")

    def test_archive_cannot_be_overwritten_even_by_designops(self):
        fixture = Fixture()
        grant = fixture.grant("design_ops")
        with self.assertRaisesRegex(module.Refused, "access.archive_read_only"):
            fixture.checker().access(grant, "f10", "Archive", "edit")

    def test_revoked_expired_external_and_sensitive_grants_are_denied(self):
        for key, value in (
            ("revoked", True), ("expires_at", stamp(NOW)), ("external", True),
            ("classification", "raw_participant"), ("permissions", ["publish"]),
        ):
            fixture = Fixture()
            grant = fixture.grant()
            grant[key] = value
            with self.subTest(key=key), self.assertRaises(module.Refused):
                fixture.checker().access(grant, "f10", "Flows", "view")

    def test_offboarding_removal_and_future_or_overlong_grants_fail(self):
        for change in ("assignment", "future", "overlong"):
            fixture = Fixture()
            grant = fixture.grant()
            if change == "assignment":
                fixture.assignments = [item for item in fixture.assignments if item["context_id"] != grant["context_id"]]
            elif change == "future":
                grant["issued_at"] = stamp(NOW + timedelta(minutes=1))
            else:
                grant["expires_at"] = stamp(NOW + timedelta(hours=25))
            with self.subTest(change=change), self.assertRaises(module.Refused):
                fixture.checker().access(grant, "f10", "Flows", "view")

    def test_access_grant_cannot_outlive_its_assignment(self):
        fixture = Fixture()
        grant = fixture.grant()
        assigned = next(item for item in fixture.assignments if item["context_id"] == grant["context_id"])
        assigned["expires_at"] = stamp(NOW + timedelta(hours=1))
        with self.assertRaisesRegex(module.Refused, "access.outlives_assignment"):
            fixture.checker().access(grant, "f10", "Flows", "view")

    def test_live_figma_denied_even_with_an_otherwise_valid_grant(self):
        fixture = Fixture()
        for action in ("view", "comment", "edit"):
            with self.subTest(action=action), self.assertRaisesRegex(module.Refused, "access.figma_unverified"):
                fixture.checker().access(fixture.grant(), "f10", "Flows", action, channel="figma")

    def test_unknown_page_and_unauthorized_action_fail(self):
        fixture = Fixture()
        for page, action in (("Unknown", "view"), ("Flows", "publish"), ("Flows", "admin")):
            with self.subTest(page=page, action=action), self.assertRaises(module.Refused):
                fixture.checker().access(fixture.grant(), "f10", page, action)


class QueueAndMetricsTests(unittest.TestCase):
    def work(self, identity="W1", squad="android", hours=1, role="design_qa", reviewer=99):
        return {
            "id": identity, "squad": squad, "phase": "review", "review_role": role,
            "review_context_id": context(reviewer), "submitted_at": stamp(NOW - timedelta(hours=hours)),
            "acknowledged_at": None,
        }

    def metrics(self, work, coordinator=False, remove_scope=False):
        fixture = Fixture()
        fixture.assignments = []
        for reviewer in {item["review_context_id"] for item in work}:
            roles = {item["review_role"] for item in work if item["review_context_id"] == reviewer}
            if coordinator:
                roles.add("decision_coordinator")
            fixture.assignments.append({
                "context_id": reviewer, "runtime": "synthetic-queue-context-not-an-appointment",
                "login": "basiltt", "roles": sorted(roles),
                "artifact_ids": ["unrelated"] if remove_scope else sorted({item["id"] for item in work}),
                "issued_at": stamp(NOW - timedelta(hours=1)), "expires_at": stamp(NOW + timedelta(hours=1)),
                "evidence": fixture.source("queue_assignment"),
            })
        return module.queue_metrics(
            POLICY, SCHEMA, work, NOW, fixture.assignments,
            read_blob=lambda commit, path: fixture.blobs[(commit, path)],
        )

    def test_exact_sla_boundaries_and_blocked_items_keep_age(self):
        for hours, expected in ((23, (0, 0, 0)), (24, (1, 0, 0)), (48, (1, 1, 0)), (72, (1, 1, 1))):
            item = self.work(hours=hours)
            item["phase"] = "blocked"
            result = self.metrics([item])
            self.assertEqual((result["unacknowledged_count"], result["overdue_count"], result["escalated_count"]), expected)
            self.assertEqual(result["review_age_hours"], hours)
            self.assertEqual(result["blocked_artifact_count"], 1)

    def test_squad_and_verifier_wip_ceilings(self):
        squad_work = [self.work(identity=f"W{number}") for number in range(3)]
        self.metrics(squad_work[:2])
        with self.assertRaisesRegex(module.Refused, "queue.squad_wip"):
            self.metrics(squad_work)
        verifier_work = [self.work(identity=f"W{number}", squad=f"squad{number}") for number in range(4)]
        self.metrics(verifier_work[:3])
        with self.assertRaisesRegex(module.Refused, "queue.reviewer_wip"):
            self.metrics(verifier_work)

    def test_coordinator_cannot_multiply_capacity_by_role_alias(self):
        work = [self.work(identity=f"W{number}", squad=f"squad{number}") for number in range(3)]
        work[0]["review_role"] = "decision_coordinator"
        work[1]["review_role"] = "product_owner"
        self.metrics(work[:2])
        with self.assertRaisesRegex(module.Refused, "queue.reviewer_wip"):
            self.metrics(work)
        for item in work:
            item["review_role"] = "product_owner"
        with self.assertRaisesRegex(module.Refused, "queue.reviewer_wip"):
            self.metrics(work, coordinator=True)

    def test_queue_requires_a_current_scoped_assignment(self):
        with self.assertRaisesRegex(module.Refused, "assignment.out_of_scope"):
            self.metrics([self.work()], remove_scope=True)

    def test_duplicate_and_invalid_acknowledgement_refused(self):
        item = self.work()
        with self.assertRaisesRegex(module.Refused, "identity.duplicate"):
            self.metrics([item, copy.deepcopy(item)])
        item["acknowledged_at"] = stamp(NOW + timedelta(seconds=1))
        with self.assertRaisesRegex(module.Refused, "queue.invalid_ack"):
            self.metrics([item])

    def test_metrics_expose_only_counts_identifiers_and_deadlines(self):
        fixture = Fixture(1)
        fixture.snapshot["records"][0]["status"] = "reopened"
        fixture.snapshot["records"][0]["reviews"][0]["expires_at"] = stamp(NOW)
        self.assertEqual(module.artifact_metrics(fixture.snapshot, SCHEMA, NOW), {
            "reopened_gate_count": 1,
            "approval_expiry": {"expired_review_count": 1, "next_deadline": stamp(NOW + timedelta(hours=6))},
        })


class InputBoundaryTests(unittest.TestCase):
    def test_real_local_git_blob_read(self):
        blob = module.git_blob(BASE, "governance/DELIVERY.md")
        self.assertTrue(blob.startswith(b"# Public organization delivery"))
        fixture = Fixture()
        checker = module.Checker(POLICY, SCHEMA, fixture.assignments, NOW)
        checker.source({"commit": BASE, "path": "governance/DELIVERY.md", "sha256": module.digest(blob)})
        with self.assertRaisesRegex(module.Refused, "evidence.blob_unavailable"):
            checker.source({"commit": BASE, "path": "does-not-exist.txt", "sha256": module.ZERO})

    def test_local_path_traversal_absolute_paths_and_controls_refused(self):
        fixture = Fixture()
        for path in ("../secret", "/secret", "C:/secret", "a\\b", "a/../b", "a/./b", "a\nb", "a//b"):
            with self.subTest(path=path), self.assertRaisesRegex(module.Refused, "evidence.unsafe_path"):
                fixture.checker().source({"commit": "1" * 40, "path": path, "sha256": module.ZERO})

    def test_cli_refuses_bad_shapes_without_echoing_contents(self):
        fixture = Fixture()
        with tempfile.TemporaryDirectory() as directory:
            snapshot, assignments = Path(directory) / "candidate.json", Path(directory) / "assignments.json"
            snapshot.write_text('{"unexpected": "DO_NOT_ECHO_SYNTHETIC_SENTINEL"}', encoding="utf-8")
            assignments.write_text(json.dumps(fixture.assignments), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(module.main(["--snapshot", str(snapshot), "--assignments", str(assignments)]), 1)
            self.assertNotIn("DO_NOT_ECHO", stdout.getvalue() + stderr.getvalue())
            self.assertIn("schema.invalid", stderr.getvalue())

    def test_duplicate_json_keys_and_missing_cli_assignments_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"id": 1, "id": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
                module.support.load_json(path)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            module.main(["--snapshot", "candidate.json"])
        self.assertEqual(result.exception.code, 2)


LEXEME_AFFIXES = (
    "\n", "\r\n", "\r", " ", "\t", "\x00", "\v", "\f", "\x7f", "\x85",
    "\u00a0", "\u200b", "\u2028", "\u2029", "\ufeff", "\n\n",
)


def research_decision(fixture):
    state = fixture.state()
    state.update(artifact_id="research_synthesis", artifact_class="research_synthesis")
    entry = fixture.decision(state, kind="research_disposition")
    entry.update(
        actor_context_id=fixture.contexts["research"], actor_role="research",
        verifier_context_id=fixture.contexts["privacy"], verifier_role="privacy",
    )
    return entry


class CanonicalLexemeTests(unittest.TestCase):
    def test_canonical_context_version_and_related_lexemes(self):
        samples = {
            "id": "Artifact_1",
            "context": context(0xabcdefab),
            "version": "10.20.30",
            "digest": module.ZERO,
            "timestamp": stamp(NOW),
        }
        for definition, value in samples.items():
            module.shape(value, SCHEMA, definition)
            for affix in LEXEME_AFFIXES:
                for alias in (value + affix, affix + value, value[:1] + affix + value[1:]):
                    with self.subTest(definition=definition, alias=alias):
                        with self.assertRaisesRegex(module.Refused, "schema.invalid"):
                            module.shape(alias, SCHEMA, definition)
        for value in ("0.0.0", "1.2.3", "10.20.30"):
            module.shape(value, SCHEMA, "version")
            self.assertEqual(module.version(value), tuple(map(int, value.split("."))))
        for value in (context(0xabcdefab).upper(), "{" + context(0) + "}", context(0).replace("-", "")):
            with self.subTest(context=value), self.assertRaisesRegex(module.Refused, "schema.invalid"):
                module.shape(value, SCHEMA, "context")
        for value in ("01.0.0", "1.02.0", "1.2.03", "+1.2.3", "v1.2.3"):
            with self.subTest(version=value), self.assertRaisesRegex(module.Refused, "schema.invalid"):
                module.shape(value, SCHEMA, "version")

    def test_gate_terminal_lf_alias_cannot_hide_approver_or_verifier_authorship(self):
        for purpose in ("approval", "verification"):
            fixture = Fixture()
            fixture.close()
            record = fixture.snapshot["records"][0]
            reviewer = next(item["context_id"] for item in record["reviews"] if item["purpose"] == purpose)
            assignments = copy.deepcopy(fixture.assignments)
            record["author_contexts"] = [reviewer]
            fixture.resign()
            with self.assertRaisesRegex(module.Refused, "review.author_is_reviewer"):
                fixture.close()
            record["author_contexts"] = [reviewer + "\n"]
            fixture.resign()
            before = copy.deepcopy(record)
            with self.subTest(purpose=purpose), self.assertRaisesRegex(module.Refused, "schema.invalid"):
                fixture.close()
            self.assertEqual(record, before)
            self.assertEqual(fixture.assignments, assignments)

    def test_research_terminal_lf_alias_cannot_hide_actor_or_verifier_authorship(self):
        for field in ("actor_context_id", "verifier_context_id"):
            fixture = Fixture()
            entry = research_decision(fixture)
            fixture.checker().append_decision([], entry, module.ZERO)
            assignments = copy.deepcopy(fixture.assignments)
            entry["author_contexts"] = [entry[field]]
            with self.assertRaisesRegex(module.Refused, "decision.author_is_reviewer"):
                fixture.checker().append_decision([], entry, module.ZERO)
            entry["author_contexts"] = [entry[field] + "\n"]
            before = copy.deepcopy(entry)
            with self.subTest(field=field), self.assertRaisesRegex(module.Refused, "schema.invalid"):
                fixture.checker().append_decision([], entry, module.ZERO)
            self.assertEqual(entry, before)
            self.assertEqual(fixture.assignments, assignments)

    def test_all_context_consumers_reject_control_and_whitespace_aliases(self):
        fixture = Fixture()
        comment = fixture.comment(resolved=True)
        record = fixture.snapshot["records"][0]
        decision = fixture.checker().append_decision([], research_decision(fixture), module.ZERO)[0]
        work = {
            "id": "A0", "squad": "fixture", "phase": "review", "review_role": "design_qa",
            "review_context_id": fixture.contexts["design_qa"],
            "submitted_at": stamp(NOW - timedelta(hours=1)), "acknowledged_at": None,
        }
        samples = [
            ("assignment", fixture.assignments[0], "context_id"),
            ("gate_record", record, "author_contexts"),
            ("review", record["reviews"][0], "context_id"),
            ("comment", comment, "author_context_id"),
            ("resolution", comment["resolution"], "context_id"),
            ("decision", decision, "author_contexts"),
            ("decision", decision, "actor_context_id"),
            ("decision", decision, "verifier_context_id"),
            ("grant", fixture.grant(), "context_id"),
            ("work", work, "review_context_id"),
        ]
        for definition, original, field in samples:
            module.shape(original, SCHEMA, definition)
            for affix in LEXEME_AFFIXES:
                candidate = copy.deepcopy(original)
                value = candidate[field]
                candidate[field] = [value[0] + affix] if isinstance(value, list) else value + affix
                with self.subTest(definition=definition, field=field, affix=affix):
                    with self.assertRaisesRegex(module.Refused, "schema.invalid"):
                        module.shape(candidate, SCHEMA, definition)

    def test_noncanonical_gate_and_research_versions_fail_after_rescoping(self):
        for affix in LEXEME_AFFIXES:
            fixture = Fixture()
            record = fixture.snapshot["records"][0]
            record["version"] += affix
            fixture.resign()
            with self.subTest(surface="gate", affix=affix), self.assertRaisesRegex(module.Refused, "schema.invalid"):
                fixture.close()
            entry = research_decision(fixture)
            entry["target_version"] += affix
            with self.subTest(surface="research", affix=affix), self.assertRaisesRegex(module.Refused, "schema.invalid"):
                fixture.checker().append_decision([], entry, module.ZERO)

    def test_source_and_archive_versions_fail_before_state_change(self):
        for field in ("version", "archived", "target_version"):
            for affix in LEXEME_AFFIXES:
                fixture = Fixture()
                state = fixture.state()
                entry = fixture.decision(state)
                if field == "target_version":
                    entry[field] += affix
                elif field == "archived":
                    state["archived"] = [{"version": "0.9.0" + affix, "source": copy.deepcopy(state["source"])}]
                else:
                    state[field] += affix
                before = copy.deepcopy(state)
                with self.subTest(field=field, affix=affix), self.assertRaisesRegex(module.Refused, "schema.invalid"):
                    fixture.checker().source_change(state, entry, module.digest(state))
                self.assertEqual(state, before)

    def test_commits_and_nullable_timestamps_have_exact_lexeme_boundaries(self):
        fixture = Fixture()
        source = fixture.source("canonical_commit")
        result_schema = SCHEMA["definitions"]["decision"]["properties"]["result"]
        timestamp_schema = SCHEMA["definitions"]["work"]["properties"]["acknowledged_at"]
        module.support.validate_schema(None, timestamp_schema, SCHEMA)
        for affix in LEXEME_AFFIXES:
            candidate = {**source, "commit": source["commit"] + affix}
            with self.subTest(surface="source_commit", affix=affix), self.assertRaisesRegex(module.Refused, "schema.invalid"):
                module.shape(candidate, SCHEMA, "source")
            with self.subTest(surface="result_commit", affix=affix), self.assertRaises(ValueError):
                module.support.validate_schema(candidate, result_schema, SCHEMA)
            with self.subTest(surface="nullable_timestamp", affix=affix), self.assertRaises(ValueError):
                module.support.validate_schema(stamp(NOW) + affix, timestamp_schema, SCHEMA)

    def test_history_alias_refused_even_with_a_recomputed_hash(self):
        fixture = Fixture()
        history = fixture.checker().append_decision([], research_decision(fixture), module.ZERO)
        for field in ("actor_context_id", "verifier_context_id", "target_version"):
            corrupted = copy.deepcopy(history)
            corrupted[0][field] += "\n"
            corrupted[0]["sha256"] = module.digest({
                key: value for key, value in corrupted[0].items() if key != "sha256"
            })
            with self.subTest(field=field), self.assertRaisesRegex(module.Refused, "schema.invalid"):
                module.validate_history(corrupted, SCHEMA)

    def test_exact_lexemes_do_not_change_generic_schema_pattern_or_opaque_input_versions(self):
        module.support.validate_schema("prefix needle suffix", {"type": "string", "pattern": "needle"})
        module.support.validate_schema("needle\n", {"type": "string", "pattern": "^needle$"})
        with self.assertRaises(ValueError):
            module.support.validate_schema("unrelated", {"type": "string", "pattern": "needle"})
        fixture = Fixture()
        self.assertEqual(fixture.snapshot["records"][0]["inputs"][0]["version"], "fixture-contract-1")
        fixture.close()


class CanonicalCliTests(unittest.TestCase):
    def setUp(self):
        self.fixture = Fixture()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        source = {
            "commit": BASE, "path": "governance/DELIVERY.md",
            "sha256": module.digest(module.git_blob(BASE, "governance/DELIVERY.md")),
        }
        times = {
            "issued_at": stamp(now - timedelta(hours=1)),
            "observed_at": stamp(now - timedelta(minutes=30)),
            "decided_at": stamp(now - timedelta(minutes=10)),
            "expires_at": stamp(now + timedelta(hours=1)),
        }

        # These are synthetic shape/reader fixtures, not actual approvals of the referenced prose.
        def pin(value):
            if isinstance(value, dict):
                if set(value) == {"commit", "path", "sha256"}:
                    value.update(source)
                else:
                    for key, item in value.items():
                        if key in times:
                            value[key] = times[key]
                        else:
                            pin(item)
            elif isinstance(value, list):
                for item in value:
                    pin(item)

        pin(self.fixture.snapshot)
        pin(self.fixture.assignments)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.assignment_path = self.folder / "assignments.json"
        self.assignment_bytes = json.dumps(self.fixture.assignments).encode("utf-8")
        self.assignment_path.write_bytes(self.assignment_bytes)

    def run_cli(self, snapshot, expected, refusal=None):
        for record in snapshot["records"]:
            scope = module.scope_digest(record)
            for review in record["reviews"]:
                review["scope_sha256"] = scope
        candidate = self.folder / "candidate.json"
        candidate.write_text(json.dumps(snapshot), encoding="utf-8")
        env = os.environ.copy()
        for name in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
            env.pop(name, None)
        result = subprocess.run(
            [
                sys.executable, str(ROOT / "scripts/check_design_gates.py"),
                "--snapshot", str(candidate), "--assignments", str(self.assignment_path),
            ],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30, env=env,
        )
        self.assertEqual(self.assignment_path.read_bytes(), self.assignment_bytes)
        evidence = (
            f"assignment_sha256={module.digest(self.assignment_bytes)}; "
            f"stdout={result.stdout!r}; stderr={result.stderr!r}"
        )
        self.assertEqual(result.returncode, expected, evidence)
        if expected == 0:
            output = json.loads(result.stdout)
            self.assertEqual(set(output), {"checked_artifacts", "expires_at", "scope_sha256"})
            self.assertEqual(output["checked_artifacts"], 1)
            self.assertEqual(output["scope_sha256"], module.scope_digest(snapshot["records"][0]))
            self.assertEqual(result.stderr, "")
        else:
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr.strip(), "Design check refused: " + refusal)

    def test_cli_canonical_and_terminal_lf_context_controls(self):
        self.run_cli(copy.deepcopy(self.fixture.snapshot), 0)
        for purpose in ("approval", "verification"):
            canonical = copy.deepcopy(self.fixture.snapshot)
            record = canonical["records"][0]
            record["author_contexts"] = [
                next(item["context_id"] for item in record["reviews"] if item["purpose"] == purpose)
            ]
            self.run_cli(canonical, 1, "review.author_is_reviewer")
            alias = copy.deepcopy(canonical)
            alias["records"][0]["author_contexts"][0] += "\n"
            with self.subTest(purpose=purpose):
                self.run_cli(alias, 1, "schema.invalid")

    def test_cli_canonical_and_terminal_lf_version_controls(self):
        self.run_cli(copy.deepcopy(self.fixture.snapshot), 0)
        malformed = copy.deepcopy(self.fixture.snapshot)
        malformed["records"][0]["version"] = "01.0.0"
        self.run_cli(malformed, 1, "schema.invalid")
        malformed["records"][0]["version"] = "1.0.0\n"
        self.run_cli(malformed, 1, "schema.invalid")

    def test_cli_other_control_and_whitespace_aliases_are_not_trimmed(self):
        for affix in LEXEME_AFFIXES[1:]:
            for field in ("author_contexts", "version"):
                candidate = copy.deepcopy(self.fixture.snapshot)
                record = candidate["records"][0]
                if field == "author_contexts":
                    record[field] = [record["reviews"][0]["context_id"] + affix]
                else:
                    record[field] += affix
                with self.subTest(field=field, affix=affix):
                    self.run_cli(candidate, 1, "schema.invalid")


if __name__ == "__main__":
    unittest.main()
