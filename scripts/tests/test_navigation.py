"""T-UXR-05 navigation validator tests: synthetic in-test fixtures, plus read-only checks of the published files.

Every rule test builds a fresh deep copy of one synthetic route map, allocation and pinned registry, proves it passes
(the control), applies exactly one mutation and asserts the exact static rule identifier and offending identifier.
The fixtures hold no real routes, roles, research, approvals, people, money or contact data: screen, flow, journey
and persona IDs belong to a synthetic registry served from memory, and roles use the reserved ROLE-SYN- prefix
(command-line fixtures renumber them ROLE-NN only because published mode refuses that prefix).
Readiness tests start from the synthetic baseline, whose only gaps are the held inputs, and use model-level controls
to show that each gap clears for a resolved subject. Command-line and Git tests run against hermetic temporary
repositories under the system temporary directory. The published-data tests read this repository's committed route
map, allocation and sitemaps (and the pinned registry through the local Git object store) without writing; nothing
here writes inside this repository or uses the network.
"""

import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_navigation", ROOT / "scripts/check_navigation.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ROUTES_SCHEMA = module.support.load_json(ROOT / module.ROUTES_SCHEMA)
ALLOCATION_SCHEMA = module.support.load_json(ROOT / module.ALLOCATION_SCHEMA)
PIN_COMMIT = "1" * 40


def screen(identifier, hint, flow):
    platform = module.INFIX[identifier[2:5]]
    return {"id": identifier, "platform": platform, "name": f"Synthetic screen {identifier[-3:]}", "route": hint,
            "flow_ids": [flow]}


SCREENS = [
    screen("S-AND-001", "android://launch", "F-AND-01"), screen("S-AND-002", "android://home", "F-AND-01"),
    screen("S-AND-003", "android://debts", "F-AND-01"), screen("S-AND-004", "android://debts/:id", "F-AND-01"),
    screen("S-AND-005", "android://transactions", "F-AND-01"),
    screen("S-AND-006", "android://notifications/:id", "F-AND-01"),
    screen("S-AND-007", "android-widget://debt-progress", "F-AND-01"),
    screen("S-AND-008", "android://plan", "F-AND-01"),
    screen("S-WEB-001", "/login", "F-WEB-01"), screen("S-WEB-002", "/overview", "F-WEB-01"),
    screen("S-WEB-003", "/transactions", "F-WEB-01"), screen("S-WEB-004", "/transactions/:id", "F-WEB-01"),
    screen("S-WEB-005", "/split/invites/:token", "F-WEB-01"),
    screen("S-ADM-001", "/operator/login", "F-ADM-01"), screen("S-ADM-002", "/operator", "F-ADM-01"),
    screen("S-ADM-003", "/operator/support", "F-ADM-01"), screen("S-ADM-004", "/operator/audit", "F-ADM-01"),
]
REGISTRY = {
    "kind": "experience_coverage", "schema_version": 1,
    "personas": [{"id": "P01", "platforms": ["android", "web"]}, {"id": "P10", "platforms": ["admin"]}],
    "journeys": [{"id": "J01", "persona_ids": ["P01"]}, {"id": "J11", "persona_ids": ["P10"]}],
    "flows": [{"id": f"F-{infix}-01", "platform": module.INFIX[infix]} for infix in ("AND", "WEB", "ADM")],
    "screens": SCREENS,
}
REGISTRY_BYTES = json.dumps(REGISTRY, indent=2).encode("utf-8")
REGISTRY_REF = {"commit": PIN_COMMIT, "path": module.IMPORT_PATH, "sha256": module.gates.digest(REGISTRY_BYTES)}
ANDROID = {"compact": "stack", "expanded": "stack", "narrow": None, "wide": None}
ANDROID_PRIMARY = {"compact": "navigation_bar", "expanded": "navigation_rail", "narrow": None, "wide": None}
BROWSER = {"compact": None, "expanded": None, "narrow": "stack", "wide": "stack"}
BROWSER_SECTION = {"compact": None, "expanded": None, "narrow": "collapsed_menu", "wide": "side_navigation"}


def route(identifier, parent, entry, text, patterns, presentation, primary=False, audience="signed_in", roles=None):
    return {
        "id": identifier, "platform": module.INFIX[identifier[2:5]], "parent_route_id": parent,
        "entry_from_parent": entry, "label": {"text": text, "status": "provisional", "message_key": None},
        "audience": audience, "primary": primary, "presentation": dict(presentation), "patterns": patterns,
        "access": None if roles is None else {"roles": roles, "unauthorized": "absent"},
    }


ROUTES = [
    route("R-AND-001", None, None, "Launch", ["android://launch"], ANDROID, audience="signed_out"),
    route("R-AND-002", "R-AND-001", "primary_navigation", "Home", ["android://home"], ANDROID_PRIMARY, True),
    route("R-AND-003", "R-AND-001", "primary_navigation", "Debts", ["android://debts"], ANDROID_PRIMARY, True),
    route("R-AND-004", "R-AND-003", "list_item", "Debt detail", ["android://debts/:id"], ANDROID),
    route("R-AND-005", "R-AND-001", "primary_navigation", "Transactions", ["android://transactions"],
          ANDROID_PRIMARY, True),
    route("R-AND-006", "R-AND-001", "primary_navigation", "Plan", ["android://plan"], ANDROID_PRIMARY, True),
    route("R-WEB-001", None, None, "Sign in", ["/login"], BROWSER, audience="signed_out"),
    route("R-WEB-002", "R-WEB-001", "navigation_link", "Overview", ["/overview"], BROWSER_SECTION, True),
    route("R-WEB-003", "R-WEB-001", "navigation_link", "Transactions", ["/transactions"], BROWSER_SECTION, True),
    route("R-WEB-004", "R-WEB-003", "list_item", "Transaction detail", ["/transactions/:id"], BROWSER),
    route("R-ADM-001", None, None, "Operator sign in", ["/operator/login"], BROWSER, audience="signed_out"),
    route("R-ADM-002", "R-ADM-001", "navigation_link", "Console", ["/operator"], BROWSER_SECTION, True,
          roles=["ROLE-SYN-01", "ROLE-SYN-02"]),
    route("R-ADM-003", "R-ADM-002", "menu", "Support queue", ["/operator/support"], BROWSER, roles=["ROLE-SYN-01"]),
    route("R-ADM-004", "R-ADM-002", "menu", "Audit", ["/operator/audit"], BROWSER, roles=["ROLE-SYN-02"]),
]
HOSTS = {
    "S-AND-001": "R-AND-001", "S-AND-002": "R-AND-002", "S-AND-003": "R-AND-003", "S-AND-004": "R-AND-004",
    "S-AND-005": "R-AND-005", "S-AND-008": "R-AND-006", "S-WEB-001": "R-WEB-001", "S-WEB-002": "R-WEB-002",
    "S-WEB-003": "R-WEB-003", "S-WEB-004": "R-WEB-004", "S-ADM-001": "R-ADM-001", "S-ADM-002": "R-ADM-002",
    "S-ADM-003": "R-ADM-003", "S-ADM-004": "R-ADM-004",
}
EXTERNAL = {
    "S-AND-006": ("notification", "Synthetic fixture: reached only from a notification, then back to Home."),
    "S-AND-007": ("widget", "Synthetic fixture: a home-screen widget outside the app tree."),
    "S-WEB-005": ("deep_link", "Synthetic fixture: an invitation link opened from outside the product."),
}
ROLES = [
    {"id": "ROLE-SYN-01", "name": "Synthetic support role", "status": "provisional",
     "source": "product/08-experience-design-and-sdlc-plan.md"},
    {"id": "ROLE-SYN-02", "name": "Synthetic audit role", "status": "provisional", "source": "adr/ADR-020.md"},
]


def placement(identifier):
    if identifier in EXTERNAL:
        entry, rationale = EXTERNAL[identifier]
        return {"screen_id": identifier, "host_route_id": None, "external": {"entry": entry, "rationale": rationale}}
    return {"screen_id": identifier, "host_route_id": HOSTS[identifier], "external": None}


ROUTE_MAP = {
    "schema_version": 1, "ia_version": "0.1.0", "status": "provisional", "source_issue": "PenniLogic/docs#74",
    "plan_id": "T-UXR-05", "registry_ref": REGISTRY_REF, "roles": ROLES, "routes": ROUTES,
    "screen_placements": [placement(item["id"]) for item in SCREENS], "redirects": [], "retired_route_ids": [],
    "research": [
        {"platform": platform,
         "tree_test": {"status": "not_run", "evidence_ref": None,
                       "metrics": {"task_success": None, "first_click_correctness": None, "backtrack_rate": None}},
         "card_sort": {"status": "not_run", "evidence_ref": None}}
        for platform in module.PLATFORMS
    ],
    "decisions": [{"decision": name, "status": "pending", "ref": None} for name in module.DECISIONS],
}


def capability(identifier, journeys, android, web, admin, rationale=None):
    platforms = {name: {"status": status, "flow_ids": flows}
                 for name, (status, flows) in zip(module.PLATFORMS, (android, web, admin))}
    divergent = any(status != "parity" for status, _ in (android, web, admin))
    return {
        "id": identifier, "name": f"Synthetic capability {identifier[-3:]}", "journey_ids": journeys,
        "platforms": platforms, "rationale": rationale,
        "cdo_approval": {"status": "pending", "ref": None} if divergent else None, "assumptions": "provisional",
    }


ALLOCATION = {
    "schema_version": 1, "status": "provisional", "source_issue": "PenniLogic/docs#74", "plan_id": "T-UXR-05",
    "diagram_id": "D19", "registry_ref": REGISTRY_REF,
    "capabilities": [
        capability("CAP-001", ["J01"], ("parity", ["F-AND-01"]), ("divergent", ["F-WEB-01"]), ("absent", []),
                   "Synthetic fixture: web favours review over capture; operators never act for a user."),
        capability("CAP-002", ["J11"], ("absent", []), ("absent", []), ("parity", ["F-ADM-01"]),
                   "Synthetic fixture: operator work happens only in the separate admin console."),
        capability("CAP-003", ["J01", "J11"], ("parity", ["F-AND-01"]), ("parity", ["F-WEB-01"]),
                   ("parity", ["F-ADM-01"])),
    ],
}


class Sources:
    """In-memory stand-in for GitSources: the pinned registry blob, whether it is published and the base."""

    def __init__(self, blobs, published=True, base=None, base_error=False):
        self.blobs, self.published, self.base, self.base_error = blobs, published, base, base_error

    def blob(self, commit, path):
        try:
            return self.blobs[(commit, path)]
        except KeyError:
            raise LookupError(path) from None

    def is_published(self, commit):
        if self.published is None:
            raise LookupError("no ancestry")
        return self.published

    def base_routes(self):
        if self.base_error:
            raise LookupError("no base")
        return self.base


class Fixture:
    """A fresh deep copy of the synthetic route map, allocation and inputs; roles are synthetic, so allowed here."""

    def __init__(self):
        self.routes, self.allocation = copy.deepcopy(ROUTE_MAP), copy.deepcopy(ALLOCATION)
        self.routes_schema, self.allocation_schema = copy.deepcopy(ROUTES_SCHEMA), copy.deepcopy(ALLOCATION_SCHEMA)
        self.blobs = {(PIN_COMMIT, module.IMPORT_PATH): REGISTRY_BYTES}
        self.published, self.base, self.base_error, self.synthetic_ok = True, None, False, True

    def check(self):
        return module.check(
            self.routes, self.allocation, self.routes_schema, self.allocation_schema,
            Sources(self.blobs, self.published, self.base, self.base_error), synthetic_ok=self.synthetic_ok,
        )

    def route(self, identifier):
        return next(item for item in self.routes["routes"] if item["id"] == identifier)

    def placement(self, identifier):
        return next(item for item in self.routes["screen_placements"] if item["screen_id"] == identifier)

    def capability(self, identifier):
        return next(item for item in self.allocation["capabilities"] if item["id"] == identifier)

    def set_registry(self, document):
        """Serve another synthetic registry at the pin and re-pin both files to its digest."""
        raw = json.dumps(document, indent=2).encode("utf-8")
        self.blobs[(PIN_COMMIT, module.IMPORT_PATH)] = raw
        for target in (self.routes, self.allocation):
            target["registry_ref"]["sha256"] = module.gates.digest(raw)

    def freeze_base(self):
        """Record the current route map as the committed compatibility base."""
        self.base = json.dumps(self.routes).encode("utf-8")


def planted_token():
    """A GitHub-token-shaped string built at runtime so no secret-shaped literal exists in source."""
    return "gh" + "p_" + "A1b2C3d4" * 5


class NavigationCase(unittest.TestCase):
    def refused(self, mutate, rule, subject=None, prepare=None):
        """Passing control, exactly one mutation, then the exact static rule and offending identifier."""
        fixture = Fixture()
        if prepare is not None:
            prepare(fixture)
        fixture.check()
        mutate(fixture)
        with self.assertRaises(module.Refused) as caught:
            fixture.check()
        self.assertIn(rule, module.STRUCTURE_RULES)
        self.assertEqual((caught.exception.rule, caught.exception.subject), (rule, subject))
        return fixture

    def passes(self, mutate, prepare=None):
        """A boundary control: the mutation keeps the fixture valid."""
        fixture = Fixture()
        if prepare is not None:
            prepare(fixture)
        mutate(fixture)
        return fixture.check()


class BaselineTests(NavigationCase):
    def test_synthetic_fixture_passes_every_structure_rule(self):
        model = Fixture().check()
        self.assertEqual(len(model.routes), 14)
        self.assertEqual(set(model.registry.screens), {item["id"] for item in SCREENS})

    def test_rule_tables_are_static_and_distinct(self):
        rules = module.STRUCTURE_RULES + module.READINESS_RULES
        self.assertEqual(len(rules), len(set(rules)))
        for rule in rules:
            self.assertRegex(rule, r"^[a-z_]+\.[a-z_]+$")

    def test_refusal_prints_only_validated_identifiers(self):
        self.assertEqual(str(module.Refused("route.cycle", "R-AND-001")), "route.cycle R-AND-001")
        self.assertEqual(str(module.Refused("route.cycle", "Home <script>")), "route.cycle")
        self.assertEqual(str(module.Refused("route.root_count", "android")), "route.root_count android")
        self.assertIsNone(module.Refused("schema.invalid", "R-AND-001", "free text").subject)


class IdentifierTests(NavigationCase):
    def test_duplicate_route_id_is_refused(self):
        def mutate(fixture):
            fixture.routes["routes"].append(copy.deepcopy(fixture.route("R-AND-004")))
        self.refused(mutate, "id.duplicate", "R-AND-004")

    def test_route_infix_must_match_its_platform(self):
        self.refused(lambda fixture: fixture.route("R-WEB-004").update(platform="admin"),
                     "id.platform_infix_mismatch", "R-WEB-004")

    def test_route_number_zero_is_out_of_range(self):
        def mutate(fixture):
            fixture.route("R-AND-004")["id"] = "R-AND-000"
            fixture.placement("S-AND-004")["host_route_id"] = "R-AND-000"
        self.refused(mutate, "id.out_of_range", "R-AND-000")

    def test_duplicate_capability_id_is_refused(self):
        self.refused(lambda fixture: fixture.capability("CAP-003").update(id="CAP-002"), "id.duplicate", "CAP-002")

    def test_synthetic_role_is_refused_outside_fixtures(self):
        def mutate(fixture):
            fixture.synthetic_ok = False
        self.refused(mutate, "role.synthetic_reserved", "ROLE-SYN-01")

    def test_role_must_cite_an_accepted_source(self):
        self.refused(lambda fixture: fixture.routes["roles"][1].update(source="governance/design-operations.md"),
                     "role.source_unaccepted", "ROLE-SYN-02")

    def test_role_cannot_be_recorded_as_accepted(self):
        self.refused(lambda fixture: fixture.routes["roles"][0].update(status="accepted"),
                     "held.role_accepted", "ROLE-SYN-01")

    def test_retired_route_id_is_never_reused(self):
        self.refused(lambda fixture: fixture.routes["retired_route_ids"].append("R-WEB-004"),
                     "route.retired_reused", "R-WEB-004")


class TopologyTests(NavigationCase):
    """Orphan and reachability rules: one root per platform, one same-platform parent, no cycle, no search edge."""

    def test_platform_without_root_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-WEB-001").update(parent_route_id="R-WEB-002"),
                     "route.root_count", "web")

    def test_second_root_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-WEB-004").update(parent_route_id=None),
                     "route.root_count", "web")

    def test_dangling_parent_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-AND-004").update(parent_route_id="R-AND-099"),
                     "route.parent_dangling", "R-AND-004")

    def test_parent_on_another_platform_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-WEB-004").update(parent_route_id="R-ADM-002"),
                     "route.parent_platform_mismatch", "R-WEB-004")

    def test_parent_cycle_is_unreachable_from_the_root(self):
        self.refused(lambda fixture: fixture.route("R-AND-003").update(parent_route_id="R-AND-004"),
                     "route.cycle", "R-AND-003")

    def test_child_route_needs_a_navigation_entry(self):
        self.refused(lambda fixture: fixture.route("R-AND-004").update(entry_from_parent=None),
                     "route.entry_mismatch", "R-AND-004")

    def test_root_route_has_no_navigation_entry(self):
        self.refused(lambda fixture: fixture.route("R-ADM-001").update(entry_from_parent="menu"),
                     "route.entry_mismatch", "R-ADM-001")

    def test_search_only_route_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-WEB-004").update(entry_from_parent="global_search"),
                     "route.search_only", "R-WEB-004")

    def test_every_non_search_entry_is_a_navigation_edge(self):
        for entry in ("primary_navigation", "navigation_link", "list_item", "tab", "menu"):
            with self.subTest(entry=entry):
                self.passes(lambda fixture: fixture.route("R-WEB-004").update(entry_from_parent=entry))

    def test_signed_out_route_under_a_signed_in_parent_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-WEB-004").update(audience="signed_out"),
                     "route.audience_widened", "R-WEB-004")

    def test_signed_out_route_under_a_signed_out_parent_passes(self):
        model = self.passes(lambda fixture: fixture.route("R-WEB-002").update(audience="signed_out"))
        self.assertEqual(model.routes["R-WEB-002"]["audience"], "signed_out")


def make_primary(fixture, identifier):
    fixture.route(identifier).update(primary=True, presentation=dict(ANDROID_PRIMARY),
                                     entry_from_parent="primary_navigation")


def demote(fixture, identifier):
    fixture.route(identifier).update(primary=False, presentation=dict(ANDROID), entry_from_parent="navigation_link")


def add_notification_route(fixture):
    """Host the external notification screen on a new non-primary Android route (a sixth candidate destination)."""
    fixture.routes["routes"].append(
        route("R-AND-007", "R-AND-002", "navigation_link", "Notifications", ["android://notifications/:id"], ANDROID))
    fixture.placement("S-AND-006").update(host_route_id="R-AND-007", external=None)


class LabelTests(NavigationCase):
    def test_label_cannot_be_recorded_as_approved(self):
        self.refused(lambda fixture: fixture.route("R-AND-002")["label"].update(status="approved"),
                     "held.label_status", "R-AND-002")

    def test_label_has_no_message_key_until_h04_publishes_one(self):
        self.refused(lambda fixture: fixture.route("R-AND-002")["label"].update(message_key="nav.home"),
                     "held.message_key", "R-AND-002")

    def test_label_never_carries_dynamic_content(self):
        for text in ("Debt {name}", "Debt :id", "Debt <b>", "Debt %s", "Debt [x]"):
            with self.subTest(text=text):
                self.refused(lambda fixture: fixture.route("R-AND-004")["label"].update(text=text),
                             "label.dynamic_content", "R-AND-004")


class PresentationTests(NavigationCase):
    def test_android_route_uses_compact_and_expanded_only(self):
        self.refused(lambda fixture: fixture.route("R-AND-004")["presentation"].update(narrow="stack"),
                     "presentation.platform_mismatch", "R-AND-004")

    def test_web_route_uses_narrow_and_wide_only(self):
        self.refused(lambda fixture: fixture.route("R-WEB-004")["presentation"].update(compact="stack"),
                     "presentation.platform_mismatch", "R-WEB-004")

    def test_web_route_hidden_at_narrow_width_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-WEB-004")["presentation"].update(narrow="hidden"),
                     "presentation.narrow_hidden", "R-WEB-004")

    def test_admin_route_hidden_at_narrow_width_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-ADM-003")["presentation"].update(narrow="hidden"),
                     "presentation.narrow_hidden", "R-ADM-003")

    def test_five_primary_destinations_pass_and_six_fail(self):
        def prepare(fixture):
            add_notification_route(fixture)
            make_primary(fixture, "R-AND-004")
        self.refused(lambda fixture: make_primary(fixture, "R-AND-007"), "android.primary_count", "android",
                     prepare=prepare)

    def test_three_primary_destinations_pass_and_two_fail(self):
        self.refused(lambda fixture: demote(fixture, "R-AND-005"), "android.primary_count", "android",
                     prepare=lambda fixture: demote(fixture, "R-AND-006"))

    def test_primary_destination_defines_expanded_adaptation(self):
        self.refused(lambda fixture: fixture.route("R-AND-002")["presentation"].update(expanded="stack"),
                     "android.primary_adaptation", "R-AND-002")

    def test_primary_destination_uses_the_navigation_bar_when_compact(self):
        self.refused(lambda fixture: fixture.route("R-AND-002")["presentation"].update(compact="stack"),
                     "android.primary_adaptation", "R-AND-002")

    def test_navigation_drawer_is_an_expanded_adaptation(self):
        self.passes(lambda fixture: fixture.route("R-AND-002")["presentation"].update(expanded="navigation_drawer"))

    def test_bar_entry_outside_the_primary_count_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-AND-004")["presentation"].update(compact="navigation_bar"),
                     "android.unlisted_primary", "R-AND-004")

    def test_primary_navigation_entry_outside_the_primary_count_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-AND-004").update(entry_from_parent="primary_navigation"),
                     "android.unlisted_primary", "R-AND-004")


class RoleDenialTests(NavigationCase):
    """Admin destinations outside an operator's roles are absent: not rendered, not addressable, no deep link."""

    def test_customer_route_carries_no_operator_roles(self):
        self.refused(lambda fixture: fixture.route("R-WEB-002").update(
            access={"roles": ["ROLE-SYN-01"], "unauthorized": "absent"}), "access.customer_route_roles", "R-WEB-002")

    def test_signed_in_admin_route_declares_its_roles(self):
        self.refused(lambda fixture: fixture.route("R-ADM-003").update(access=None),
                     "admin.access_mismatch", "R-ADM-003")

    def test_signed_out_admin_route_has_no_roles(self):
        self.refused(lambda fixture: fixture.route("R-ADM-001").update(
            access={"roles": ["ROLE-SYN-01"], "unauthorized": "absent"}), "admin.access_mismatch", "R-ADM-001")

    def test_unknown_role_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-ADM-004")["access"].update(roles=["ROLE-SYN-03"]),
                     "admin.role_unknown", "R-ADM-004")

    def test_unauthorized_destination_is_never_disabled_greyed_or_hidden(self):
        for presentation in ("disabled", "greyed", "hidden"):
            with self.subTest(presentation=presentation):
                self.refused(lambda fixture: fixture.route("R-ADM-003")["access"].update(unauthorized=presentation),
                             "admin.unauthorized_not_absent", "R-ADM-003")

    def test_role_denied_the_parent_is_denied_the_child(self):
        self.refused(lambda fixture: fixture.route("R-ADM-002")["access"].update(roles=["ROLE-SYN-01"]),
                     "admin.role_wider_than_parent", "R-ADM-004")

    def test_child_may_narrow_its_parent_roles(self):
        model = self.passes(lambda fixture: fixture.route("R-ADM-003")["access"].update(roles=["ROLE-SYN-01"]))
        self.assertEqual(model.routes["R-ADM-003"]["access"]["roles"], ["ROLE-SYN-01"])

    def test_admin_route_cannot_drop_its_sign_in_and_roles(self):
        # A signed-out admin route carries no roles, so under the role-bound console it would be open to every role.
        self.refused(lambda fixture: fixture.route("R-ADM-003").update(audience="signed_out", access=None),
                     "route.audience_widened", "R-ADM-003")

    def test_admin_screen_is_never_an_external_entry(self):
        # Outside every route an operator screen would carry no role at all.
        self.refused(lambda fixture: fixture.placement("S-ADM-004").update(host_route_id=None, external={
            "entry": "deep_link", "rationale": "Synthetic fixture: an operator screen opened from a link."}),
                     "admin.external_entry", "S-ADM-004")


class PlacementTests(NavigationCase):
    """Exactly one placement per registry screen: orphan, duplicate and dangling placements fail."""

    def test_placement_of_an_unknown_screen_is_refused(self):
        self.refused(lambda fixture: fixture.routes["screen_placements"].append(
            {"screen_id": "S-AND-099", "host_route_id": "R-AND-002", "external": None}),
            "placement.unknown_screen", "S-AND-099")

    def test_duplicate_placement_is_refused(self):
        self.refused(lambda fixture: fixture.routes["screen_placements"].append(
            {"screen_id": "S-WEB-002", "host_route_id": "R-WEB-003", "external": None}),
            "placement.duplicate", "S-WEB-002")

    def test_orphan_screen_is_refused(self):
        self.refused(lambda fixture: fixture.routes["screen_placements"].remove(fixture.placement("S-WEB-004")),
                     "placement.orphan_screen", "S-WEB-004")

    def test_dangling_host_route_is_refused(self):
        self.refused(lambda fixture: fixture.placement("S-WEB-004").update(host_route_id="R-WEB-099"),
                     "placement.route_dangling", "S-WEB-004")

    def test_host_on_another_platform_is_refused(self):
        self.refused(lambda fixture: fixture.placement("S-WEB-004").update(host_route_id="R-ADM-003"),
                     "placement.platform_mismatch", "S-WEB-004")

    def test_hosted_and_external_at_once_is_refused(self):
        self.refused(lambda fixture: fixture.placement("S-AND-006").update(host_route_id="R-AND-002"),
                     "placement.host_and_external", "S-AND-006")

    def test_neither_hosted_nor_external_is_refused(self):
        self.refused(lambda fixture: fixture.placement("S-AND-004").update(host_route_id=None),
                     "placement.host_and_external", "S-AND-004")

    def test_external_entry_needs_a_rationale(self):
        self.refused(lambda fixture: fixture.placement("S-AND-007")["external"].update(rationale=None),
                     "placement.rationale_missing", "S-AND-007")

    def test_route_without_screens_or_children_is_refused(self):
        self.refused(lambda fixture: fixture.placement("S-WEB-004").update(host_route_id=None, external={
            "entry": "deep_link", "rationale": "Synthetic fixture: opened from an export file."}),
            "route.empty_leaf", "R-WEB-004")

    def test_container_route_with_children_needs_no_screen(self):
        def mutate(fixture):
            fixture.placement("S-AND-003")["host_route_id"] = "R-AND-004"
            fixture.route("R-AND-003")["patterns"] = []
            fixture.route("R-AND-004")["patterns"].append("android://debts")
        model = self.passes(mutate)
        self.assertEqual((model.hosted["R-AND-003"], model.children["R-AND-003"]), ([], ["R-AND-004"]))


class DeepLinkTests(NavigationCase):
    """Deep-link compatibility: unique, unambiguous patterns; imported hints map to the hosting route; redirects."""

    def test_pattern_outside_its_platform_grammar_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-AND-004")["patterns"].append("/debts/:id"),
                     "deep_link.grammar", "R-AND-004")

    def test_pattern_length_is_bounded(self):
        # An over-length pattern loses its exemption from the text scan, so the letters are not hex digits.
        self.passes(lambda fixture: fixture.route("R-WEB-004")["patterns"].append("/" + "x" * 119))
        self.refused(lambda fixture: fixture.route("R-WEB-004")["patterns"].append("/" + "x" * 120),
                     "deep_link.grammar", "R-WEB-004")
        self.refused(lambda fixture: fixture.route("R-AND-004")["patterns"].append("android://" + "x" * 111),
                     "content.url_shape", "R-AND-004")

    def test_duplicate_pattern_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-AND-005")["patterns"].append("android://debts"),
                     "deep_link.duplicate_pattern", "R-AND-005")

    def test_same_path_on_web_and_admin_resolves_per_platform(self):
        self.passes(lambda fixture: fixture.route("R-ADM-003")["patterns"].append("/overview"))

    def test_parameter_name_does_not_make_patterns_distinct(self):
        self.refused(lambda fixture: fixture.route("R-WEB-002")["patterns"].append("/transactions/:key"),
                     "deep_link.ambiguous_pattern", "R-WEB-004")

    def test_hint_resolving_to_a_route_that_does_not_host_its_screen_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-AND-002")["patterns"].append("android://notifications/:id"),
                     "deep_link.hint_misrouted", "S-AND-006")

    def test_imported_hint_must_map_to_the_hosting_route(self):
        self.refused(lambda fixture: fixture.route("R-WEB-004").update(patterns=["/transactions/detail/:id"]),
                     "deep_link.hint_unmapped", "S-WEB-004")

    def test_renamed_hint_maps_through_a_redirect_to_its_host(self):
        def prepare(fixture):
            fixture.route("R-WEB-004")["patterns"] = ["/transactions/detail/:id"]
            fixture.routes["redirects"].append({"from_pattern": "/transactions/:id", "to_route_id": "R-WEB-004",
                                                "reason": "Synthetic fixture: detail path renamed."})
        self.refused(lambda fixture: fixture.routes["redirects"][0].update(to_route_id="R-WEB-003"),
                     "deep_link.hint_unmapped", "S-WEB-004", prepare=prepare)

    def test_redirect_to_an_unknown_route_is_refused(self):
        self.refused(lambda fixture: fixture.routes["redirects"].append(
            redirect("/old-overview", "R-WEB-099")), "deep_link.redirect_dangling", "R-WEB-099")

    def test_redirect_to_a_retired_route_is_refused(self):
        def prepare(fixture):
            fixture.routes["redirects"].append(redirect("/old-overview", "R-WEB-002"))
            fixture.routes["retired_route_ids"].append("R-WEB-005")
        self.refused(lambda fixture: fixture.routes["redirects"][0].update(to_route_id="R-WEB-005"),
                     "deep_link.redirect_dangling", "R-WEB-005", prepare=prepare)

    def test_duplicate_redirect_is_refused(self):
        self.refused(lambda fixture: fixture.routes["redirects"].append(redirect("/old-overview", "R-WEB-003")),
                     "deep_link.redirect_duplicate", "R-WEB-003",
                     prepare=lambda fixture: fixture.routes["redirects"].append(redirect("/old-overview", "R-WEB-002")))

    def test_redirect_from_an_active_pattern_is_refused(self):
        self.refused(lambda fixture: fixture.routes["redirects"].append(redirect("/overview", "R-WEB-003")),
                     "deep_link.redirect_shadowed", "R-WEB-003")

    def test_redirect_pattern_follows_its_target_platform(self):
        self.refused(lambda fixture: fixture.routes["redirects"].append(redirect("android://overview", "R-WEB-002")),
                     "deep_link.grammar", "R-WEB-002")


def redirect(pattern, target):
    return {"from_pattern": pattern, "to_route_id": target, "reason": "Synthetic fixture: path renamed."}


def retire_transaction_detail(fixture):
    """Fold R-WEB-004 into R-WEB-003 compatibly: its screen moves, its pattern redirects, its ID is retired."""
    fixture.routes["routes"].remove(fixture.route("R-WEB-004"))
    fixture.placement("S-WEB-004")["host_route_id"] = "R-WEB-003"
    fixture.routes["redirects"].append(redirect("/transactions/:id", "R-WEB-003"))
    fixture.routes["retired_route_ids"].append("R-WEB-004")


def publish_extra_pattern(fixture):
    fixture.route("R-WEB-003")["patterns"].append("/transactions/all")
    fixture.freeze_base()


class CompatibilityTests(NavigationCase):
    """The route map at the merge base with origin/main is the published map later changes must stay compatible with."""

    def test_base_identical_to_the_candidate_passes(self):
        self.assertIsNotNone(self.passes(lambda fixture: fixture.freeze_base()).base)

    def test_unreadable_base_is_refused(self):
        self.refused(lambda fixture: setattr(fixture, "base_error", True), "base.unavailable")

    def test_malformed_base_is_refused(self):
        self.refused(lambda fixture: setattr(fixture, "base", b"{"), "base.invalid")

    def test_schema_invalid_base_is_refused(self):
        self.refused(lambda fixture: setattr(fixture, "base", b"{}"), "base.invalid")

    def test_base_is_read_by_the_fields_compatibility_needs(self):
        def mutate(fixture):
            published = json.loads(json.dumps(fixture.routes))
            published["schema_version"], published["legacy_field"] = 0, "an older or newer published shape"
            fixture.base = json.dumps(published).encode("utf-8")
        self.assertIsNotNone(self.passes(mutate).base)

    def test_retired_route_with_redirected_pattern_passes(self):
        model = self.passes(retire_transaction_detail, prepare=lambda fixture: fixture.freeze_base())
        self.assertNotIn("R-WEB-004", model.routes)

    def test_published_route_id_is_never_dropped(self):
        def prepare(fixture):
            fixture.freeze_base()
            retire_transaction_detail(fixture)
        self.refused(lambda fixture: fixture.routes["retired_route_ids"].remove("R-WEB-004"),
                     "route.id_dropped", "R-WEB-004", prepare=prepare)

    def test_removed_published_pattern_needs_a_redirect(self):
        self.refused(lambda fixture: fixture.route("R-WEB-003")["patterns"].remove("/transactions/all"),
                     "deep_link.published_changed", "R-WEB-003", prepare=publish_extra_pattern)

    def test_moved_published_pattern_needs_a_redirect(self):
        def mutate(fixture):
            fixture.route("R-WEB-003")["patterns"].remove("/transactions/all")
            fixture.route("R-WEB-002")["patterns"].append("/transactions/all")
        self.refused(mutate, "deep_link.published_changed", "R-WEB-003", prepare=publish_extra_pattern)

    def test_changed_published_pattern_with_a_redirect_passes(self):
        def mutate(fixture):
            fixture.route("R-WEB-003")["patterns"].remove("/transactions/all")
            fixture.routes["redirects"].append(redirect("/transactions/all", "R-WEB-003"))
        self.passes(mutate, prepare=publish_extra_pattern)

    def test_published_retirement_is_never_undone(self):
        def prepare(fixture):
            fixture.routes["retired_route_ids"].append("R-WEB-005")
            fixture.freeze_base()
        self.refused(lambda fixture: fixture.routes["retired_route_ids"].remove("R-WEB-005"),
                     "route.retired_dropped", "R-WEB-005", prepare=prepare)

    def test_published_redirect_is_never_removed(self):
        def prepare(fixture):
            fixture.routes["redirects"].append(redirect("/old-overview", "R-WEB-002"))
            fixture.freeze_base()
        self.refused(lambda fixture: fixture.routes["redirects"].clear(), "deep_link.redirect_removed", "R-WEB-002",
                     prepare=prepare)
        self.passes(lambda fixture: fixture.routes["redirects"][0].update(to_route_id="R-WEB-003"), prepare=prepare)


class ResearchAndDecisionTests(NavigationCase):
    """Tree tests, card sorts and decisions are held inputs: never fabricated, refused when filled in."""

    def test_every_platform_has_one_research_record(self):
        self.refused(lambda fixture: fixture.routes["research"].pop(), "research.platform_set")
        self.refused(lambda fixture: fixture.routes["research"][2].update(platform="android"), "research.platform_set")

    def test_research_evidence_is_never_recorded(self):
        mutations = {
            "tree test completed": lambda item: item["tree_test"].update(status="completed"),
            "tree test evidence": lambda item: item["tree_test"].update(evidence_ref="synthetic-report"),
            "tree test metric": lambda item: item["tree_test"]["metrics"].update(task_success=0.8),
            "card sort completed": lambda item: item["card_sort"].update(status="completed"),
            "card sort evidence": lambda item: item["card_sort"].update(evidence_ref="synthetic-report"),
        }
        for name, change in mutations.items():
            with self.subTest(name):
                self.refused(lambda fixture: change(fixture.routes["research"][1]), "held.research_evidence", "web")

    def test_decision_set_is_ia_security_and_accessibility(self):
        self.refused(lambda fixture: fixture.routes["decisions"].pop(), "decision.set_mismatch")

    def test_decision_is_never_recorded_as_approved(self):
        self.refused(lambda fixture: fixture.routes["decisions"][1].update(status="approved"),
                     "held.approval", "security")
        self.refused(lambda fixture: fixture.routes["decisions"][2].update(ref="synthetic-decision"),
                     "held.approval", "accessibility")


class AllocationTests(NavigationCase):
    """D19 allocation: parity, divergent or absent per platform, rationale and pending CDO approval for divergence."""

    def test_unknown_journey_is_refused(self):
        self.refused(lambda fixture: fixture.capability("CAP-001")["journey_ids"].append("J99"),
                     "reference.dangling", "CAP-001 J99")

    def test_unknown_flow_is_refused(self):
        self.refused(lambda fixture: fixture.capability("CAP-001")["platforms"]["android"]["flow_ids"].append(
            "F-AND-09"), "reference.dangling", "CAP-001 F-AND-09")

    def test_flow_of_another_platform_is_refused(self):
        self.refused(lambda fixture: fixture.capability("CAP-001")["platforms"]["android"].update(
            flow_ids=["F-WEB-01"]), "allocation.flow_platform_mismatch", "CAP-001 F-WEB-01")

    def test_absent_platform_has_no_flows(self):
        self.refused(lambda fixture: fixture.capability("CAP-001")["platforms"]["admin"].update(
            flow_ids=["F-ADM-01"]), "allocation.status_flows_mismatch", "CAP-001 admin")

    def test_present_platform_has_flows(self):
        self.refused(lambda fixture: fixture.capability("CAP-003")["platforms"]["web"].update(flow_ids=[]),
                     "allocation.status_flows_mismatch", "CAP-003 web")

    def test_every_registry_flow_is_allocated(self):
        def mutate(fixture):
            fixture.set_registry({**REGISTRY, "flows": REGISTRY["flows"] + [{"id": "F-AND-02", "platform": "android"}]})
        self.refused(mutate, "allocation.flow_unallocated", "F-AND-02")

    def test_divergence_needs_a_rationale(self):
        self.refused(lambda fixture: fixture.capability("CAP-001").update(rationale=None),
                     "allocation.rationale_missing", "CAP-001")

    def test_divergent_platform_alone_is_a_divergence(self):
        def mutate(fixture):
            fixture.capability("CAP-003")["platforms"]["web"]["status"] = "divergent"
        self.refused(mutate, "allocation.rationale_missing", "CAP-003")

    def test_divergence_needs_a_cdo_approval_record(self):
        self.refused(lambda fixture: fixture.capability("CAP-002").update(cdo_approval=None),
                     "allocation.approval_missing", "CAP-002")

    def test_cdo_approval_is_never_recorded_as_approved(self):
        self.refused(lambda fixture: fixture.capability("CAP-002")["cdo_approval"].update(status="approved"),
                     "held.approval", "CAP-002")
        self.refused(lambda fixture: fixture.capability("CAP-002")["cdo_approval"].update(ref="synthetic-decision"),
                     "held.approval", "CAP-002")

    def test_parity_needs_no_cdo_approval_record(self):
        self.refused(lambda fixture: fixture.capability("CAP-003").update(
            cdo_approval={"status": "pending", "ref": None}), "allocation.approval_without_divergence", "CAP-003")

    def test_assumptions_stay_provisional(self):
        self.refused(lambda fixture: fixture.capability("CAP-003").update(assumptions="validated"),
                     "held.assumptions", "CAP-003")


def pin_both(fixture, **changes):
    for target in (fixture.routes, fixture.allocation):
        target["registry_ref"].update(changes)


class RegistryPinTests(NavigationCase):
    """Both files pin one registry blob by commit, accepted path and digest; IDs come only from that blob."""

    def test_files_pinning_different_registries_are_refused(self):
        self.refused(lambda fixture: fixture.allocation["registry_ref"].update(commit="2" * 40),
                     "registry.ref_mismatch")

    def test_pin_outside_the_registry_paths_is_refused(self):
        self.refused(lambda fixture: pin_both(fixture, path="product/client-state-taxonomy.json"),
                     "registry.path_unaccepted")

    def test_pinned_commit_missing_from_the_object_store_is_refused(self):
        self.refused(lambda fixture: pin_both(fixture, commit="2" * 40), "registry.unavailable")

    def test_unanswerable_ancestry_is_refused(self):
        self.refused(lambda fixture: setattr(fixture, "published", None), "registry.unavailable")

    def test_pinned_commit_outside_the_published_history_is_refused(self):
        self.refused(lambda fixture: setattr(fixture, "published", False), "registry.commit_unpublished")

    def test_pinned_bytes_must_match_the_digest(self):
        self.refused(lambda fixture: fixture.blobs.update({(PIN_COMMIT, module.IMPORT_PATH): REGISTRY_BYTES + b" "}),
                     "registry.digest_mismatch")

    def test_unparsable_registry_is_refused(self):
        def mutate(fixture):
            raw = b'{"screens": [], "screens": []}'
            fixture.blobs[(PIN_COMMIT, module.IMPORT_PATH)] = raw
            pin_both(fixture, sha256=module.gates.digest(raw))
        self.refused(mutate, "registry.invalid")

    def test_registry_with_a_malformed_hint_is_refused(self):
        screens = [dict(item, route="https://example.com/x") if item["id"] == "S-AND-002" else item for item in SCREENS]
        self.refused(lambda fixture: fixture.set_registry({**REGISTRY, "screens": screens}), "registry.invalid")

    def test_registry_screen_platform_must_match_its_infix(self):
        screens = [dict(item, platform="web") if item["id"] == "S-AND-002" else item for item in SCREENS]
        self.refused(lambda fixture: fixture.set_registry({**REGISTRY, "screens": screens}), "registry.invalid")

    def test_repin_to_the_canonical_registry_is_one_reference_change(self):
        def mutate(fixture):
            screens = [{key: value for key, value in item.items() if key != "route"} | {"route_hint": item["route"]}
                       for item in SCREENS]
            raw = json.dumps({**REGISTRY, "screens": screens}).encode("utf-8")
            fixture.blobs[(PIN_COMMIT, module.CANONICAL_PATH)] = raw
            pin_both(fixture, path=module.CANONICAL_PATH, sha256=module.gates.digest(raw))
        model = self.passes(mutate)
        self.assertEqual(model.registry.screens["S-AND-002"], ("android", "android://home"))


class ContentAndSchemaTests(NavigationCase):
    def test_route_with_an_unknown_field_is_refused_by_record(self):
        self.refused(lambda fixture: fixture.route("R-AND-002").update(icon="home"), "schema.invalid", "R-AND-002")

    def test_capability_with_an_unknown_field_is_refused_by_record(self):
        self.refused(lambda fixture: fixture.capability("CAP-002").update(owner="x"), "schema.invalid", "CAP-002")

    def test_missing_top_level_field_is_refused(self):
        self.refused(lambda fixture: fixture.routes.pop("decisions"), "schema.invalid")

    def test_schema_keyword_outside_the_shared_subset_fails_closed(self):
        self.refused(lambda fixture: fixture.routes_schema.update(oneOf=[]), "schema.invalid")

    def test_secret_shaped_label_is_refused(self):
        self.refused(lambda fixture: fixture.route("R-AND-002")["label"].update(text=planted_token()),
                     "content.secret_shape", "R-AND-002")

    def test_text_shapes_are_refused_wherever_they_appear(self):
        cases = (
            ("content.url_shape", "S-AND-007", lambda f: f.placement("S-AND-007")["external"].update(
                rationale="See www.example.com")),
            ("content.email_shape", "ROLE-SYN-01", lambda f: f.routes["roles"][0].update(name="ops@example")),
            ("content.phone_shape", "CAP-001", lambda f: f.capability("CAP-001").update(name="Call 98765 43210")),
            ("content.amount_shape", "CAP-001", lambda f: f.capability("CAP-001").update(rationale="Above Rs 500")),
            ("content.unprintable_character", "R-AND-003", lambda f: f.route("R-AND-003")["label"].update(
                text="Débts")),
            ("content.blank_or_padded", "R-AND-002", lambda f: f.route("R-AND-002")["label"].update(text=" Home")),
            ("content.url_shape", "R-AND-004", lambda f: f.route("R-AND-004")["patterns"].append(
                "https://example.com/debts")),
        )
        for rule, subject, mutate in cases:
            with self.subTest(rule=rule, subject=subject):
                self.refused(mutate, rule, subject)

    def test_text_length_is_bounded(self):
        # "x", not a hex digit: 32 or more hex digits in a row are refused as key-shaped whatever their length.
        self.passes(lambda fixture: fixture.capability("CAP-001").update(rationale="x" * 400))
        self.refused(lambda fixture: fixture.capability("CAP-001").update(rationale="x" * 401),
                     "content.too_long", "CAP-001")

    def test_numbers_appear_only_where_the_schema_allows_them(self):
        with self.assertRaises(module.Refused) as caught:
            module.guard_content({"routes": [{"id": "R-AND-001", "label": {"text": 5}}]})
        self.assertEqual((caught.exception.rule, caught.exception.subject), ("content.unexpected_number", "R-AND-001"))


ROUTE_IDS = [item["id"] for item in ROUTES]
# The synthetic baseline is complete except for the held inputs, so exactly these gaps remain.
BASELINE_GAPS = {
    "readiness.tree_test_not_run": ["android", "web", "admin"],
    "readiness.card_sort_not_run": ["android", "web", "admin"],
    "readiness.decision_pending": ["accessibility", "information_architecture", "security"],
    "readiness.cdo_approval_pending": ["CAP-001", "CAP-002"],
    "readiness.assumption_provisional": ["CAP-001", "CAP-002", "CAP-003"],
    "readiness.label_provisional": ROUTE_IDS,
    "readiness.role_provisional": ["ROLE-SYN-01", "ROLE-SYN-02"],
    "readiness.registry_not_canonical": ["PenniLogic/docs#75"],
    "readiness.registry_id_added": [],
    "readiness.registry_id_retired": [],
}
# Model-level resolutions (registry data cannot carry them: the structure rules refuse each as held.*).
RESOLUTIONS = {
    "readiness.tree_test_not_run": ("web", lambda m: m.document["research"][1]["tree_test"].update(status="completed")),
    "readiness.card_sort_not_run": ("admin", lambda m: m.document["research"][2]["card_sort"].update(
        status="completed")),
    "readiness.decision_pending": ("security", lambda m: m.document["decisions"][1].update(status="approved")),
    "readiness.cdo_approval_pending": ("CAP-002", lambda m: m.capabilities["CAP-002"]["cdo_approval"].update(
        status="approved")),
    "readiness.assumption_provisional": ("CAP-003", lambda m: m.capabilities["CAP-003"].update(
        assumptions="validated")),
    "readiness.label_provisional": ("R-AND-002", lambda m: m.routes["R-AND-002"]["label"].update(
        status="approved", message_key="nav.home")),
    "readiness.role_provisional": ("ROLE-SYN-01", lambda m: m.roles["ROLE-SYN-01"].update(status="accepted")),
    "readiness.registry_not_canonical": ("PenniLogic/docs#75", lambda m: m.document["registry_ref"].update(
        path=module.CANONICAL_PATH)),
}


def current_registry(screens=SCREENS, flows=REGISTRY["flows"], journeys=REGISTRY["journeys"]):
    return module.Registry({**REGISTRY, "screens": screens, "flows": flows, "journeys": journeys},
                           "registry.current_invalid")


class ReadinessTests(NavigationCase):
    def test_baseline_has_exactly_the_held_gaps(self):
        model = Fixture().check()
        self.assertEqual(module.readiness(model), BASELINE_GAPS)
        self.assertEqual(module.readiness(model, current_registry()), BASELINE_GAPS)
        self.assertEqual(module.status_line(BASELINE_GAPS), module.NOT_GREEN)

    def test_each_gap_clears_for_its_resolved_subject_only(self):
        for rule, (subject, resolve) in RESOLUTIONS.items():
            with self.subTest(rule=rule):
                model = Fixture().check()
                resolve(model)
                expected = [item for item in BASELINE_GAPS[rule] if item != subject]
                self.assertNotEqual(expected, BASELINE_GAPS[rule])
                self.assertEqual(module.readiness(model), {**BASELINE_GAPS, rule: expected})

    def test_green_only_when_every_gap_resolves(self):
        model = Fixture().check()
        for research in model.document["research"]:
            research["tree_test"]["status"] = research["card_sort"]["status"] = "completed"
        for decision in model.document["decisions"]:
            decision["status"] = "approved"
        for capability in model.capabilities.values():
            capability["assumptions"] = "validated"
            if capability["cdo_approval"] is not None:
                capability["cdo_approval"]["status"] = "approved"
        for route in model.routes.values():
            route["label"].update(status="approved", message_key="nav.synthetic")
        for role in model.roles.values():
            role["status"] = "accepted"
        model.document["registry_ref"]["path"] = module.CANONICAL_PATH
        gaps = module.readiness(model, current_registry())
        self.assertEqual(module.status_line(gaps), module.GREEN)
        retired = current_registry(screens=SCREENS[:-1])
        self.assertEqual(module.status_line(module.readiness(model, retired)), module.NOT_GREEN)

    def test_live_registry_changes_are_gaps_not_structure_failures(self):
        model = Fixture().check()
        live = current_registry(
            screens=[item for item in SCREENS if item["id"] != "S-AND-007"]
            + [screen("S-WEB-006", "/help", "F-WEB-02")],
            flows=REGISTRY["flows"] + [{"id": "F-WEB-02", "platform": "web"}],
            journeys=REGISTRY["journeys"][:1] + [{"id": "J12"}],
        )
        self.assertEqual(module.readiness(model, live), {
            **BASELINE_GAPS, "readiness.registry_id_added": ["F-WEB-02", "J12", "S-WEB-006"],
            "readiness.registry_id_retired": ["J11", "S-AND-007"],
        })


class SitemapTests(NavigationCase):
    def test_rendering_names_every_route_screen_and_capability(self):
        rendered = module.render_sitemaps(Fixture().check())
        for identifier in ROUTE_IDS + [item["id"] for item in SCREENS] + ["CAP-001", "CAP-002", "CAP-003"]:
            self.assertIn(identifier, rendered)
        self.assertTrue(rendered.endswith("\n") and not rendered.endswith("\n\n"))
        self.assertTrue(rendered.isascii())
        self.assertNotIn("\r", rendered)

    def test_rendering_is_independent_of_record_order(self):
        reordered = Fixture()
        for key in ("routes", "screen_placements", "roles"):
            reordered.routes[key].reverse()
        reordered.allocation["capabilities"].reverse()
        self.assertEqual(module.render_sitemaps(reordered.check()), module.render_sitemaps(Fixture().check()))

    def test_rendering_shows_role_projection_and_absence(self):
        rendered = module.render_sitemaps(Fixture().check())
        self.assertIn("| `ROLE-SYN-01` | Synthetic support role | provisional | "
                      "`product/08-experience-design-and-sdlc-plan.md` | R-ADM-001, R-ADM-002, R-ADM-003 |", rendered)
        self.assertIn("roles `ROLE-SYN-02`; absent for other roles", rendered)

    def test_rendering_shows_primary_destinations_and_divergence(self):
        rendered = module.render_sitemaps(Fixture().check())
        self.assertIn("Primary destinations (4; product/08 allows three to five): `R-AND-002` Home, `R-AND-003` Debts, "
                      "`R-AND-005` Transactions, `R-AND-006` Plan.", rendered)
        self.assertIn("| CAP-002 | Synthetic capability 002 | J11 | absent | absent | parity: F-ADM-01 |", rendered)
        self.assertIn("| none (parity) | not required (parity) |", rendered)

    def test_data_text_cannot_break_the_markdown(self):
        fixture = Fixture()
        fixture.capability("CAP-001")["name"] = "Debt | plan *now*"
        rendered = module.render_sitemaps(fixture.check())
        self.assertIn("| CAP-001 | Debt \\| plan \\*now\\* |", rendered)

    def test_data_text_cannot_inject_markup(self):
        # An HTML comment would hide the rest of the rendered sitemaps; links, images and strike-through restyle it.
        fixture = Fixture()
        fixture.capability("CAP-001")["rationale"] = "See <!-- hidden --> and ![image](elsewhere) ~~struck~~."
        rendered = module.render_sitemaps(fixture.check())
        self.assertIn("| See \\<!-- hidden --\\> and !\\[image\\](elsewhere) \\~\\~struck\\~\\~. |", rendered)


def git(root, *args):
    env = {key: value for key, value in os.environ.items() if key not in module.SCRUBBED_GIT_VARIABLES}
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_AUTHOR_NAME": "Synthetic Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@invalid", "GIT_COMMITTER_NAME": "Synthetic Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@invalid", "GIT_AUTHOR_DATE": "2026-10-01T00:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-10-01T00:00:00+00:00",
    })
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30,
                            env=env)
    if result.returncode != 0:
        raise AssertionError(f"fixture git {args[0]} failed: {result.stderr}")
    return result.stdout.strip()


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def published_fixture():
    """The synthetic fixture with ROLE-NN instead of the reserved ROLE-SYN-NN, as published mode requires."""
    fixture = Fixture()
    text = json.dumps(fixture.routes).replace("ROLE-SYN-", "ROLE-")
    fixture.routes = json.loads(text)
    return fixture


class Checkout:
    """A hermetic temporary Git checkout laid out like docs, created outside this repository: a base commit with the
    pinned registry (and optionally a published route map) under refs/remotes/origin/main, then a candidate commit."""

    def __init__(self, case, fixture=None, base_routes=None, origin=True):
        folder = tempfile.TemporaryDirectory()
        case.addCleanup(folder.cleanup)
        self.root, self.fixture = Path(folder.name), fixture or published_fixture()
        git(self.root, "init", "-q", "--template=", "-b", "main")
        self.write(module.IMPORT_PATH, REGISTRY_BYTES)
        if base_routes is not None:
            self.write(module.ROUTES, encode(base_routes))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "synthetic base")
        self.base = git(self.root, "rev-parse", "HEAD")
        if origin:
            git(self.root, "update-ref", "refs/remotes/origin/main", self.base)
        self.save()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "synthetic candidate")
        case.addCleanup(setattr, module, "ROOT", module.ROOT)
        module.ROOT = self.root

    def write(self, relative, raw):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def save(self, commit=None):
        """Write both data files pinned to this checkout's base commit (or another commit) and the real schemas."""
        for target in (self.fixture.routes, self.fixture.allocation):
            target["registry_ref"].update(commit=commit or self.base, sha256=module.gates.digest(REGISTRY_BYTES))
        self.write(module.ROUTES, encode(self.fixture.routes))
        self.write(module.ALLOCATION, encode(self.fixture.allocation))
        self.write(module.ROUTES_SCHEMA, (ROOT / module.ROUTES_SCHEMA).read_bytes())
        self.write(module.ALLOCATION_SCHEMA, (ROOT / module.ALLOCATION_SCHEMA).read_bytes())

    def run(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main(list(argv))
        return code, out.getvalue(), err.getvalue()


STRUCTURE_LINE = (
    "Navigation map 0.1.0 structure valid: 14 routes (6 Android, 4 web, 4 admin; 4 Android primary destinations), "
    "0 orphan routes, 17 registry screens placed exactly once (14 hosted, 3 external), 14 deep-link patterns, "
    "0 redirects, 0 retired route IDs checked against {base}; 3 capabilities (2 with a divergence) allocating "
    "3 registry flows; registry pinned at planning/source/evidence/experience-coverage.json"
)
GAP_COUNTS = [
    "readiness.tree_test_not_run: 3", "readiness.card_sort_not_run: 3", "readiness.decision_pending: 3",
    "readiness.cdo_approval_pending: 2", "readiness.assumption_provisional: 3", "readiness.label_provisional: 14",
    "readiness.role_provisional: 2", "readiness.registry_not_canonical: 1", "readiness.registry_id_added: 0",
    "readiness.registry_id_retired: 0",
]


def refusal(rule):
    return f"Navigation check refused: {rule}\n"


class CommandLineTests(unittest.TestCase):
    def assertRun(self, result, code, stdout="", stderr=""):
        self.assertEqual(result, (code, stdout, stderr))

    def test_structure_mode_reports_counts_only(self):
        checkout = Checkout(self)
        self.assertRun(checkout.run("--structure"), 0,
                       STRUCTURE_LINE.format(base="no published base") + "; readiness not evaluated.\n")

    def test_default_mode_is_not_green_with_exact_gap_counts(self):
        checkout = Checkout(self)
        self.assertEqual(checkout.run("--write-sitemaps"),
                         (0, f"Navigation sitemaps written to {module.SITEMAPS}.\n", ""))
        lines = [module.NOT_GREEN, STRUCTURE_LINE.format(base="no published base")] + GAP_COUNTS
        self.assertRun(checkout.run(), 1, "\n".join(lines) + "\n")

    def test_written_sitemaps_match_until_edited(self):
        checkout = Checkout(self)
        self.assertRun(checkout.run("--check-sitemaps"), 1, stderr=refusal("sitemaps.drift"))
        self.assertEqual(checkout.run("--write-sitemaps")[0], 0)
        target = checkout.root / module.SITEMAPS
        self.assertEqual(target.read_bytes(), module.render_sitemaps(module.load_and_check(checkout.root)).encode())
        self.assertRun(checkout.run("--check-sitemaps"), 0,
                       f"Navigation sitemaps {module.SITEMAPS} match the route map and allocation.\n")
        target.write_bytes(target.read_bytes() + b"\n")
        self.assertRun(checkout.run("--check-sitemaps"), 1, stderr=refusal("sitemaps.drift"))
        self.assertRun(checkout.run(), 1, stderr=refusal("sitemaps.drift"))

    def test_write_refuses_a_symlinked_target(self):
        checkout = Checkout(self)
        outside = checkout.root / "outside.md"
        outside.write_bytes(b"unchanged\n")
        os.symlink(outside, checkout.root / module.SITEMAPS)
        self.assertRun(checkout.run("--write-sitemaps"), 1, stderr=refusal("input.unreadable_or_invalid"))
        self.assertEqual(outside.read_bytes(), b"unchanged\n")

    def test_write_refuses_a_symlinked_directory(self):
        checkout = Checkout(self)
        folder = checkout.root / "product" / "navigation"
        elsewhere = checkout.root / "elsewhere"
        folder.rename(elsewhere)
        os.symlink(elsewhere, folder, target_is_directory=True)
        self.assertEqual(checkout.run("--structure")[0], 0)
        self.assertRun(checkout.run("--write-sitemaps"), 1, stderr=refusal("input.unreadable_or_invalid"))
        self.assertFalse((elsewhere / "sitemaps.md").exists())

    def test_published_mode_refuses_synthetic_roles(self):
        checkout = Checkout(self, fixture=Fixture())
        self.assertRun(checkout.run("--structure"), 1, stderr=refusal("role.synthetic_reserved ROLE-SYN-01"))

    def test_refusal_never_echoes_input(self):
        fixture = published_fixture()
        fixture.routes["routes"][1]["label"]["text"] = planted_token()
        checkout = Checkout(self, fixture=fixture)
        self.assertRun(checkout.run("--structure"), 1, stderr=refusal("content.secret_shape R-AND-002"))

    def test_malformed_input_fails_closed(self):
        checkout = Checkout(self)
        checkout.write(module.ROUTES, b"{")
        self.assertRun(checkout.run("--structure"), 1, stderr=refusal("input.unreadable_or_invalid"))

    def test_missing_origin_main_fails_closed(self):
        checkout = Checkout(self, origin=False)
        self.assertRun(checkout.run("--structure"), 1, stderr=refusal("registry.unavailable"))

    def test_published_base_is_read_from_git(self):
        published = published_fixture()
        published.routes["routes"][8]["patterns"].append("/transactions/all")
        checkout = Checkout(self, base_routes=published.routes)
        self.assertRun(checkout.run("--structure"), 1, stderr=refusal("deep_link.published_changed R-WEB-003"))

    def test_identical_published_base_passes(self):
        checkout = Checkout(self, base_routes=published_fixture().routes)
        self.assertRun(checkout.run("--structure"), 0,
                       STRUCTURE_LINE.format(base="the published base") + "; readiness not evaluated.\n")

    def test_registry_pin_outside_the_published_history_is_refused(self):
        checkout = Checkout(self)
        git(checkout.root, "checkout", "-q", "--orphan", "side")
        git(checkout.root, "commit", "-q", "-m", "synthetic side history")
        side = git(checkout.root, "rev-parse", "HEAD")
        git(checkout.root, "checkout", "-q", "main")
        checkout.save(commit=side)
        self.assertRun(checkout.run("--structure"), 1, stderr=refusal("registry.commit_unpublished"))

    def test_registry_pin_to_an_unpublished_branch_commit_is_refused(self):
        checkout = Checkout(self)
        checkout.save(commit=git(checkout.root, "rev-parse", "HEAD"))
        self.assertRun(checkout.run("--structure"), 1, stderr=refusal("registry.commit_unpublished"))

    def test_conflicting_modes_are_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            module.main(["--structure", "--check-sitemaps"])
        self.assertEqual(caught.exception.code, 2)


class TrustedGitTests(unittest.TestCase):
    """The pinned registry and the base are read only through a git outside the checked repository."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.real = Path(shutil.which("git")).resolve().parent
        planted = self.root / "bin"
        planted.mkdir()
        (planted / "git").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (planted / "git").chmod(0o755)
        self.planted = planted

    def test_relative_and_repository_entries_are_skipped(self):
        path = os.pathsep.join([str(self.planted), "bin", str(self.real)])
        with mock.patch.dict(os.environ, {"PATH": path}):
            self.assertEqual(Path(module.trusted_git(self.root)).parent, self.real)

    def test_no_git_outside_the_repository_is_a_lookup_failure(self):
        with mock.patch.dict(os.environ, {"PATH": os.pathsep.join([str(self.planted), "bin"])}):
            with self.assertRaises(LookupError):
                module.trusted_git(self.root)

    def test_check_without_trusted_git_refuses_the_pin(self):
        checkout = Checkout(self, fixture=published_fixture())
        planted = checkout.root / "bin"
        planted.mkdir()
        shutil.copy(self.planted / "git", planted / "git")
        with mock.patch.dict(os.environ, {"PATH": str(planted)}):
            self.assertEqual(checkout.run("--structure"), (1, "", refusal("registry.unavailable")))

    def test_inherited_repository_variables_are_ignored(self):
        checkout = Checkout(self)
        with mock.patch.dict(os.environ, {"GIT_DIR": str(self.root / "missing.git"), "GIT_WORK_TREE": str(self.root)}):
            sources = module.GitSources(checkout.root)
            self.assertEqual(sources.blob(checkout.base, module.IMPORT_PATH), REGISTRY_BYTES)
            self.assertTrue(sources.is_published(checkout.base))
            self.assertIsNone(sources.base_routes())

    def test_unpinned_commit_is_never_resolved(self):
        sources = module.GitSources(self.root)
        for commit in ("HEAD", "1722fc7", None):
            with self.subTest(commit=commit), self.assertRaises(LookupError):
                sources.blob(commit, module.IMPORT_PATH)


class LiveRegistryTests(unittest.TestCase):
    """The working-tree registry (docs#75's canonical file once it exists) only adds readiness gaps."""

    def checkout_with_canonical(self, raw):
        checkout = Checkout(self)
        checkout.write(module.CANONICAL_PATH, raw)
        self.assertEqual(checkout.run("--write-sitemaps")[0], 0)
        return checkout

    def test_new_canonical_screen_is_a_readiness_gap(self):
        screens = [{key: value for key, value in item.items() if key != "route"} | {"route_hint": item["route"]}
                   for item in SCREENS] + [{"id": "S-WEB-006", "platform": "web", "route_hint": "/help"}]
        checkout = self.checkout_with_canonical(encode({**REGISTRY, "screens": screens}))
        counts = [line if line != "readiness.registry_id_added: 0" else "readiness.registry_id_added: 1"
                  for line in GAP_COUNTS]
        lines = [module.NOT_GREEN, STRUCTURE_LINE.format(base="no published base")] + counts
        self.assertEqual(checkout.run(), (1, "\n".join(lines) + "\n", ""))
        self.assertEqual(checkout.run("--check-sitemaps")[0], 0)

    def test_unreadable_canonical_registry_fails_closed(self):
        checkout = self.checkout_with_canonical(b'{"screens": []}')
        self.assertEqual(checkout.run(), (1, "", refusal("registry.current_invalid")))
        self.assertEqual(checkout.run("--structure")[0], 0)


PUBLISHED_STRUCTURE = (
    "Navigation map 0.1.0 structure valid: 122 routes (46 Android, 45 web, 31 admin; 5 Android primary "
    "destinations), 0 orphan routes, 141 registry screens placed exactly once (134 hosted, 7 external), 134 deep-link "
    "patterns, 0 redirects, 0 retired route IDs checked against {base}; 16 capabilities (16 with a divergence) "
    "allocating 38 registry flows; registry pinned at planning/source/evidence/experience-coverage.json"
)
# The recorded readiness gaps of the published route map and allocation against their pinned registry.
PUBLISHED_GAP_COUNTS = {
    "readiness.tree_test_not_run": 3, "readiness.card_sort_not_run": 3, "readiness.decision_pending": 3,
    "readiness.cdo_approval_pending": 16, "readiness.assumption_provisional": 16, "readiness.label_provisional": 122,
    "readiness.role_provisional": 3, "readiness.registry_not_canonical": 1, "readiness.registry_id_added": 0,
    "readiness.registry_id_retired": 0,
}
LIVE_REGISTRY_RULES = ("readiness.registry_id_added", "readiness.registry_id_retired")


class PublishedDataTests(unittest.TestCase):
    """The committed files of this repository, checked read-only exactly as published mode checks them: the pinned
    registry and the compatibility base come from the local Git object store and nothing is written. The exact gaps
    depend only on this ticket's files and the pinned blob; a later registry change only adds live-registry gaps
    (TS-M8), so it can never fail these tests."""

    def test_published_structure_passes(self):
        model = module.load_and_check(ROOT)
        base = "the published base" if model.base is not None else "no published base"
        self.assertEqual(module.structure_line(model), PUBLISHED_STRUCTURE.format(base=base))
        self.assertEqual(set(model.placements), set(model.registry.screens))
        # The only admin routes without roles are the operator sign-in and its recovery: any other operator screen
        # on a role-free route needs a Security review that changes this pin.
        unbound = {identifier: model.hosted[identifier] for identifier, route in model.routes.items()
                   if route["platform"] == "admin" and route["access"] is None}
        self.assertEqual(unbound, {"R-ADM-001": ["S-ADM-001"], "R-ADM-002": ["S-ADM-030"]})

    def test_published_readiness_reports_exact_gaps(self):
        model = module.load_and_check(ROOT)
        gaps = module.readiness(model)
        self.assertEqual({rule: len(subjects) for rule, subjects in gaps.items()}, PUBLISHED_GAP_COUNTS)
        capabilities = [f"CAP-{number:03d}" for number in range(1, 17)]
        self.assertEqual(gaps, {
            "readiness.tree_test_not_run": ["android", "web", "admin"],
            "readiness.card_sort_not_run": ["android", "web", "admin"],
            "readiness.decision_pending": ["accessibility", "information_architecture", "security"],
            "readiness.cdo_approval_pending": capabilities, "readiness.assumption_provisional": capabilities,
            "readiness.label_provisional": list(model.routes),
            "readiness.role_provisional": ["ROLE-01", "ROLE-02", "ROLE-03"],
            "readiness.registry_not_canonical": ["PenniLogic/docs#75"],
            "readiness.registry_id_added": [], "readiness.registry_id_retired": [],
        })
        self.assertEqual(module.status_line(gaps), module.NOT_GREEN)
        live = module.readiness(model, module.read_current(ROOT))
        self.assertEqual({rule: subjects for rule, subjects in live.items() if rule not in LIVE_REGISTRY_RULES},
                         {rule: subjects for rule, subjects in gaps.items() if rule not in LIVE_REGISTRY_RULES})

    def test_published_sitemaps_match(self):
        rendered = module.render_sitemaps(module.load_and_check(ROOT))
        self.assertEqual((ROOT / module.SITEMAPS).read_bytes(), rendered.encode("utf-8"))
