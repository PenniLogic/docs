"""ADR-022 source conformance only: no DNS, TLS, sockets, firewall or runtime qualification."""

import copy
import hashlib
import importlib.util
import ipaddress
from pathlib import Path
import re
import unittest
from unittest.mock import patch
from urllib.parse import quote, unquote_to_bytes, urlsplit


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("egress_check_docs", ROOT / "scripts" / "check_docs.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
adr = checks.load_check("validate_adr_layout")
schema_check = checks.load_check("check_client_states")

RECORD = ROOT / "adr" / "ADR-022.md"
DATA = ROOT / "adr" / "ai-egress-consequences.json"
SCHEMA = ROOT / "adr" / "ai-egress-consequences.schema.json"
TICKET = "T-ADR-AIEGRESS-08"
GATES = {f"T{number}" for number in range(1, 21)}
CONSUMERS = {
    "T-AI-01", "T-AUTH-DLG-01", "T-AI-02", "T-PLT-01", "T-AI-03", "T-AI-05", "T-AI-04",
    "T-AI-06", "T-AI-07", "T-CON-EGRESS-01", "T-SCA-CON-01", "T-QA-02", "T-CON-06",
    "T-CON-03", "T-CON-12", "T-CON-04", "T-FAM-01", "T-CON-09", "T-CMP-01", "T-CMP-04",
    "T-ADM-08", "T-PLT-03", "T-PLT-02", "T-PLT-05", "T-PLT-04", "T-AIP-04", "T-UXA-11",
    "T-UXW-08", "T-QA-09", "T-ADR-ENT-09",
}
# Existing coordinator-created follow-ups postdate the unchanged offline issue inventory.
LATER_CONSUMERS = {
    "T-AUTH-DLG-01": "PenniLogic/api#87",
    "T-CON-EGRESS-01": "PenniLogic/contracts#27",
}


def validate_data(data, schema):
    schema_check.validate_schema(data, schema)
    gates = [item["id"] for item in data["runtime_gates"]]
    if len(set(gates)) != len(gates) or set(gates) != GATES:
        raise ValueError("Every runtime gate T1 through T20 must occur exactly once")
    consumers = data["delivery"]["consumers"]
    identities = [item["identity"] for item in consumers]
    issues = [item["issue"] for item in consumers]
    if len(set(identities)) != len(identities) or set(identities) != CONSUMERS:
        raise ValueError("Every original consumer identity must occur exactly once")
    if len(set(issues)) != len(issues):
        raise ValueError("Consumer issue references must be unique")
    inventory = adr.load_json_document(ROOT / "planning" / "issue-inventory.json")
    expected = {item["plan_id"]: item["reference"] for item in inventory["issues"] if item["plan_id"]}
    expected.update(LATER_CONSUMERS)
    for item in consumers:
        if expected.get(item["identity"]) != item["issue"]:
            raise ValueError(f"Consumer identity does not match original issue: {item['identity']}")
    for gate in data["runtime_gates"]:
        if not set(gate["owners"]) <= set(identities):
            raise ValueError(f"Runtime gate {gate['id']} has an unknown owner")
    for family in (4, 6):
        for cidr in data["address_policy"][f"denied_ipv{family}"]:
            network = ipaddress.ip_network(cidr, strict=True)
            # The schema pins spelling; Python 3.14 renders mapped IPv6 CIDRs differently.
            if network.version != family:
                raise ValueError("Deny networks must be strict networks in the declared family")
    states = set(data["enums"]["CustomDestinationState"])
    denials = data["state_denials"]
    if set(denials) != states - {"active"}:
        raise ValueError("Every inactive destination state needs one refusal mapping")
    if not set(denials.values()) <= set(data["enums"]["EgressDenialReason"]):
        raise ValueError("State refusal mapping must use the published denial vocabulary")
    headers = set(data["enums"]["CredentialHeader"])
    if headers != set(data["transport"]["credential_headers"]):
        raise ValueError("Credential headers must cover the published enum")
    if headers != set(data["transport"]["credential_schemes"]):
        raise ValueError("Credential schemes must cover the published enum")
    bounds = data["kill_switch"]
    if bounds["freshness_seconds"] + data["runtime"]["lease_seconds"] >= bounds["total_effect_bound_seconds"]:
        raise ValueError("Freshness and lease bounds must leave time for bounded connection teardown")


def validate_record(document, data_bytes, schema_bytes):
    data = adr.strict_json_loads(data_bytes.decode("utf-8"), DATA.name)
    schema = adr.strict_json_loads(schema_bytes.decode("utf-8"), SCHEMA.name)
    validate_data(data, schema)
    source = adr.parse_source(RECORD.name, document.encode("utf-8"))
    if (source.number, source.ticket, source.date, source.status) != (
        data["record"], data["ticket"], data["decision_date"], "ACCEPTED",
    ):
        raise ValueError("Record identity, date and decided status must match the consequences")
    for label, raw in (("Consequences", data_bytes), ("Schema", schema_bytes)):
        binding = re.search(rf"\*\*{label} SHA-256:\*\* `([0-9a-f]{{64}})`", document)
        if binding is None or binding[1] != hashlib.sha256(raw).hexdigest():
            raise ValueError(f"{label} differs from its dated ADR binding")
    if f'`{data["artifact_id"]}@{data["consequences_version"]}`' not in document:
        raise ValueError("The record must name the exact artifact version")
    for gate in GATES:
        if f"| `{gate}` |" not in document:
            raise ValueError(f"Missing runtime gate in record: {gate}")
    for item in data["delivery"]["consumers"]:
        if item["issue"] not in document or item["identity"] not in document:
            raise ValueError(f"Missing original consumer in record: {item['identity']}")
    if "source-only" not in document or "H1" not in document or "H2" not in document:
        raise ValueError("Source-only scope and real implementation gaps must be explicit")


def literal_host(host):
    """The deterministic lexical guard, not platform inet_aton or an IDNA implementation."""
    last_label = host.removesuffix(".").rsplit(".", 1)[-1]
    return (
        any(character in host for character in "[]:%")
        or re.fullmatch(r"[0-9]+|0[xX][0-9a-fA-F]*", last_label) is not None
    )


def binary_address_decision(packed, policy, self_prefixes=()):
    """Evaluate only the source's packed-address predicate, without resolving or connecting."""
    address = ipaddress.ip_address(packed)
    networks = (ipaddress.ip_network(cidr) for cidr in policy[f"denied_ipv{address.version}"])
    if any(address in network for network in networks):
        return "DENIED_RANGE"
    if address.version == 6 and address not in ipaddress.ip_network(policy["ipv6_allowed_scope"]):
        return "DENIED_SCOPE"
    if any(address in ipaddress.ip_network(cidr) for cidr in self_prefixes):
        return "DENIED_SELF"
    if not address.is_global:
        return "NON_GLOBAL"
    return "ALLOWED"


def address_decision(text, policy, self_prefixes=()):
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return "INVALID_ADDRESS"
    if "%" in text or str(address) != text:
        return "NONCANONICAL_ADDRESS"
    return binary_address_decision(address.packed, policy, self_prefixes)


def custom_pin_decision(pinned, answers, policy, self_prefixes=()):
    if not answers:
        return "EMPTY_RESOLUTION"
    if any(address_decision(value, policy, self_prefixes) != "ALLOWED" for value in answers):
        return "DENIED_RESOLUTION"
    if any(address_decision(value, policy, self_prefixes) != "ALLOWED" for value in pinned):
        return "DENIED_PIN"
    return "UNCHANGED_PIN" if set(pinned) == set(answers) else "SUSPEND_RESOLUTION_CHANGED"


def normalize_ascii_url(uri, data, self_domains=()):
    """Source model for already-ASCII URIs; real UTS-46, DNS and HTTP clients are runtime gates."""
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in uri):
        raise ValueError("Whitespace or control")
    if "\\" in uri or "?" in uri or "#" in uri:
        raise ValueError("Ambiguous URI component")
    parsed = urlsplit(uri)
    if parsed.scheme != "https" or not parsed.netloc or "@" in parsed.netloc:
        raise ValueError("HTTPS authority without userinfo required")
    host = parsed.netloc
    if host.endswith(":443"):
        host = host[:-4]
    if literal_host(host) or not host.isascii():
        raise ValueError("Literal, noncanonical port or non-ASCII source-model host")
    host = host.lower().removesuffix(".")
    labels = host.split(".")
    limits = data["normalization"]
    if len(labels) < 2 or len(host) > limits["host_max_bytes"] or literal_host(host):
        raise ValueError("Invalid host size, single label or mapped literal")
    if any(
        len(label) > limits["host_label_max_bytes"]
        or re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label) is None
        for label in labels
    ):
        raise ValueError("Invalid label")
    for suffix in [*data["address_policy"]["denied_name_suffixes"], *self_domains]:
        if host == suffix or host.endswith("." + suffix):
            raise ValueError("Special-use or self name")
    path = parsed.path or "/"
    if re.search(r"%(?![0-9a-fA-F]{2})|%(?:2[fF]|5[cC])", path):
        raise ValueError("Malformed escape or encoded path separator")
    decoded = unquote_to_bytes(path).decode("utf-8", errors="strict")
    if len(decoded.encode("utf-8")) > limits["path_prefix_max_bytes"]:
        raise ValueError("Path too long")
    if any(part in {".", ".."} for part in decoded.split("/")):
        raise ValueError("Dot path segment")
    if any(character in decoded for character in "%\\?#") or any(
        character.isspace() or ord(character) < 32 or ord(character) == 127 for character in decoded
    ):
        raise ValueError("Nested escape or unsafe decoded path")
    return host, quote(decoded, safe="/-._~")


def path_within_prefix(path, prefix):
    boundary = prefix.rstrip("/")
    return not boundary or path == boundary or path.startswith(boundary + "/")


class PublishedEgressDecisionTests(unittest.TestCase):
    def test_record_schema_and_artifact_are_bound_to_one_decision(self):
        validate_record(RECORD.read_text(encoding="utf-8"), DATA.read_bytes(), SCHEMA.read_bytes())

    def test_record_layout_owner_generated_slots_and_registry_agree(self):
        layout = adr.validate_sources(ROOT)
        self.assertEqual(layout.allocations["ADR-022"].ticket, TICKET)
        self.assertEqual(layout.sources["ADR-022"].ticket, TICKET)
        self.assertEqual(layout.sources["ADR-022"].status, "ACCEPTED")
        adr.check_layout(ROOT)
        registry = adr.load_json_document(ROOT / "adr" / "accepted-records.json")
        entry = next(item for item in registry["items"] if item["number"] == "ADR-022")
        raw = RECORD.read_bytes()
        self.assertEqual(entry["date"], layout.sources["ADR-022"].date)
        self.assertEqual(entry["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(entry["bytes"], len(raw))

    def test_source_validation_never_uses_network(self):
        with patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden in source test")), \
                patch("socket.socket", side_effect=AssertionError("Sockets forbidden in source test")):
            validate_record(RECORD.read_text(encoding="utf-8"), DATA.read_bytes(), SCHEMA.read_bytes())

    def test_new_files_use_ascii_lf_and_one_terminal_newline(self):
        for path in (DATA, SCHEMA, Path(__file__)):
            with self.subTest(path=path.name):
                raw = path.read_bytes()
                raw.decode("ascii")
                self.assertNotIn(b"\r", raw)
                self.assertTrue(raw.endswith(b"\n"))
                self.assertFalse(raw.endswith(b"\n\n"))

    def test_source_scope_never_asserts_runtime_or_approval(self):
        data = adr.load_json_document(DATA)
        self.assertEqual(data["runtime"]["state"], "FUTURE_NOT_DEPLOYED")
        self.assertEqual(data["effective_on"], "PROTECTED_MERGE")
        self.assertEqual(data["enablement"]["approved_providers"], [])
        self.assertEqual(data["enablement"]["approved_custom_destinations"], [])
        self.assertEqual(data["enablement"]["deployment_inventory"], [])
        self.assertIs(data["enablement"]["runtime_implementation_claimed"], False)
        self.assertIs(data["enablement"]["source_tests_are_network_evidence"], False)
        self.assertIs(data["delivery"]["remote_updates_claimed"], False)
        self.assertIs(data["delivery"]["independent_approval_claimed"], False)


class ContradictoryEgressSourceTests(unittest.TestCase):
    def setUp(self):
        self.data = adr.load_json_document(DATA)
        self.schema = adr.load_json_document(SCHEMA)

    def rejected(self, change):
        data = copy.deepcopy(self.data)
        change(data)
        with self.assertRaises(ValueError):
            validate_data(data, self.schema)

    def test_forged_versions_status_runtime_and_spend_are_rejected(self):
        for key, value in (
            ("schema_version", True), ("schema_version", 2), ("consequences_version", "0.9.0"),
            ("consequences_version", "1.0.1"), ("record", "ADR-023"),
            ("effective_on", "LOCAL_TEST_PASS"), ("evidence_scope", "RUNTIME_ENFORCED"),
        ):
            with self.subTest(key=key, value=value):
                self.rejected(lambda data: data.__setitem__(key, value))
        self.rejected(lambda data: data["runtime"].__setitem__("id", "KUBERNETES"))
        self.rejected(lambda data: data["runtime"].__setitem__("state", "DEPLOYED"))
        for field in ("runtime_implementation_claimed", "source_tests_are_network_evidence", "spend_authorized"):
            with self.subTest(field=field):
                self.rejected(lambda data: data["enablement"].__setitem__(field, True))

    def test_every_boolean_is_typed_and_its_security_value_cannot_be_flipped(self):
        def visit(value, path=()):
            if isinstance(value, dict):
                for key, item in value.items():
                    yield from visit(item, (*path, key))
            elif isinstance(value, bool):
                yield path, value

        for path, original in visit(self.data):
            for replacement in (not original, int(original)):
                with self.subTest(path=".".join(path), value=replacement):
                    def change(data):
                        target = data
                        for key in path[:-1]:
                            target = target[key]
                        target[path[-1]] = replacement
                    self.rejected(change)

    def test_all_declared_object_members_are_required_and_unknown_members_fail(self):
        def object_paths(value, path=()):
            if isinstance(value, dict):
                yield path, value
                for key, item in value.items():
                    yield from object_paths(item, (*path, key))
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    yield from object_paths(item, (*path, index))

        for path, value in object_paths(self.data):
            for removed in [*value, None]:
                with self.subTest(path=path, removed=removed):
                    def change(data):
                        target = data
                        for key in path:
                            target = target[key]
                        if removed is None:
                            target["synthetic_unknown"] = None
                        else:
                            del target[removed]
                    self.rejected(change)

    def test_enabling_defaults_inventories_or_destinations_in_source_is_rejected(self):
        for key in ("global_default", "custom_default"):
            self.rejected(lambda data: data["enablement"].__setitem__(key, "on"))
        for key in ("approved_providers", "approved_custom_destinations", "deployment_inventory"):
            self.rejected(lambda data: data["enablement"][key].append("synthetic-entry"))
        self.rejected(lambda data: data["enablement"]["required_prerequisites"].pop())
        self.rejected(lambda data: data["enablement"]["provider_inference_prerequisites"].pop())
        self.rejected(lambda data: data["enablement"]["custom_inference_prerequisites"].pop())

    def test_deny_range_deletion_widening_or_alternate_cidr_spelling_is_rejected(self):
        for key in ("denied_ipv4", "denied_ipv6", "named_metadata_and_credentials", "denied_name_suffixes"):
            with self.subTest(key=key):
                self.rejected(lambda data: data["address_policy"][key].pop())
        for cidr in ("0.0.0.1/8", "0.0.0.0/0", "127.000.0.0/8"):
            self.rejected(lambda data: data["address_policy"]["denied_ipv4"].__setitem__(0, cidr))
        self.rejected(lambda data: data["address_policy"].__setitem__("ipv6_allowed_scope", "::/0"))

    def test_kernel_order_metadata_exceptions_and_default_accept_are_rejected(self):
        self.rejected(lambda data: data["runtime"]["ordered_packet_rules"].reverse())
        self.rejected(lambda data: data["runtime"]["ordered_packet_rules"].__setitem__(0, "ACCEPT_ESTABLISHED"))
        self.rejected(lambda data: data["runtime"].__setitem__("lease_refresh_on_failure", "ALLOW"))
        self.rejected(lambda data: data["runtime"].__setitem__("control_exception", "ANY_PRIVATE_RANGE"))
        self.rejected(lambda data: data["runtime"].__setitem__("startup", "WORKLOAD_THEN_RULES"))

    def test_request_addresses_credential_leaks_and_probe_tunnels_are_rejected(self):
        for key in ("inference_target_fields", "inference_address_fields", "registration_fields"):
            self.rejected(lambda data: data["wire"][key].append("base_url"))
        self.rejected(lambda data: data["wire"].__setitem__("byok_custom_requests", "UNMETERED"))
        self.rejected(lambda data: data["wire"].__setitem__("byok_custom_tokens", "CONSUMED"))
        self.rejected(lambda data: data["proxy_authorization"].__setitem__("issuer", "ai-service"))
        self.rejected(lambda data: data["proxy_authorization"].__setitem__("tls_probe", "UNRESTRICTED_CONNECT"))
        self.rejected(lambda data: data["proxy_authorization"].__setitem__("maintenance_authority", "INFERENCE"))
        self.rejected(lambda data: data["proxy_authorization"].__setitem__("replay_enforcement", "BEST_EFFORT_CACHE"))
        self.rejected(lambda data: data["proxy_authorization"]["bindings"].remove("sub"))
        self.rejected(lambda data: data["transport"]["base_headers"].append("Cookie"))

    def test_looser_pinning_redirects_normalization_and_stale_controls_are_rejected(self):
        self.rejected(lambda data: data["pinning"].__setitem__("custom_dns_set", "ANY_INTERSECTION"))
        self.rejected(lambda data: data["redirects"].__setitem__("all_modes_origin", "ANY_ALLOWLISTED_HOST"))
        self.rejected(lambda data: data["redirects"]["allowed_status"].append(302))
        self.rejected(lambda data: data["redirects"].__setitem__("hop_limit", 3))
        self.rejected(lambda data: data["transport"].__setitem__("logical_request_max_attempts", 4))
        self.rejected(lambda data: data["normalization"]["order"].reverse())
        self.rejected(lambda data: data["normalization"].__setitem__("path_percent_decode_count", 2))
        self.rejected(lambda data: data["kill_switch"].__setitem__("stale_on_error_grace_seconds", 300))
        self.rejected(lambda data: data["kill_switch"].__setitem__("on", "DELAYED_SINGLE_OPERATOR"))
        self.rejected(lambda data: data["kill_switch"]["suite_manifest"]["bindings"].remove("inventory_digest"))

    def test_lifecycle_erasure_privacy_and_observability_weakening_is_rejected(self):
        self.rejected(lambda data: data["registration"].__setitem__("uniqueness", "APPLICATION_CHECK_ONLY"))
        self.rejected(lambda data: data["registration"].__setitem__("restore", "RESTORE_ACTIVE_DESTINATIONS"))
        self.rejected(lambda data: data["state_denials"].__setitem__("revoked", "unreachable"))
        self.rejected(lambda data: data["privacy"]["payload_forbidden"].remove("RAW_DERIVED_DIGEST"))
        self.rejected(lambda data: data["privacy"].__setitem__("mode_b_c_shared_data", "ANY_SHARED_DATA"))
        self.rejected(lambda data: data["observability"].__setitem__("revocation_measure", "LAST_DENIED_REQUEST"))
        self.rejected(lambda data: data["observability"].__setitem__("revocation_measure", "LAST_OUTBOUND_REQUEST_BYTE"))
        self.rejected(lambda data: data["observability"].__setitem__("failed_or_overdue_verification", "ALERT_ONLY"))

    def test_gate_coverage_and_original_owners_cannot_be_lost_or_fabricated(self):
        self.rejected(lambda data: data["runtime_gates"].pop())
        self.rejected(lambda data: data["runtime_gates"][0].__setitem__("id", "T2"))
        self.rejected(lambda data: data["runtime_gates"][0]["owners"].append("T-NEW-99"))
        self.rejected(lambda data: data["delivery"]["consumers"].pop())
        self.rejected(lambda data: data["delivery"]["consumers"][0].__setitem__("identity", "T-NEW-99"))
        self.rejected(lambda data: data["delivery"]["consumers"][0].__setitem__("issue", "PenniLogic/ai-service#3"))
        self.rejected(lambda data: data["delivery"]["replacement_tickets"].append("synthetic-replacement"))

    def test_duplicate_keys_unknown_schema_keywords_and_binding_drift_fail(self):
        text = DATA.read_text(encoding="utf-8").replace(
            '"schema_version": 1', '"schema_version": 1, "schema_version": 2', 1
        )
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            adr.strict_json_loads(text, DATA.name)
        self.schema["unknownSchemaKeyword"] = True
        with self.assertRaisesRegex(ValueError, "unsupported schema keyword"):
            validate_data(self.data, self.schema)
        document = RECORD.read_text(encoding="utf-8")
        for data_raw, schema_raw, label in (
            (DATA.read_bytes() + b" ", SCHEMA.read_bytes(), "Consequences"),
            (DATA.read_bytes(), SCHEMA.read_bytes() + b" ", "Schema"),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, f"{label} differs"):
                    validate_record(document, data_raw, schema_raw)

    def test_wrong_date_status_missing_gate_or_consumer_in_record_fail(self):
        document = RECORD.read_text(encoding="utf-8")
        for changed in (
            document.replace("2026-10-05", "2026-10-04"),
            document.replace("ACCEPTED", "PENDING"),
            document.replace("| `T20` |", "| T20 |"),
            document.replace("T-AUTH-DLG-01", "UNASSIGNED"),
        ):
            with self.subTest(change=changed[:80]):
                with self.assertRaises(ValueError):
                    validate_record(changed, DATA.read_bytes(), SCHEMA.read_bytes())


class AddressPolicySourceTests(unittest.TestCase):
    def setUp(self):
        self.data = adr.load_json_document(DATA)
        self.policy = self.data["address_policy"]

    def test_every_denied_network_first_middle_and_last_packed_address(self):
        for family in (4, 6):
            for cidr in self.policy[f"denied_ipv{family}"]:
                network = ipaddress.ip_network(cidr)
                for offset in (0, network.num_addresses // 2, network.num_addresses - 1):
                    address = network.network_address + offset
                    with self.subTest(cidr=cidr, address=str(address)):
                        self.assertEqual(binary_address_decision(address.packed, self.policy), "DENIED_RANGE")

    def test_each_named_metadata_and_container_credential_address_is_denied(self):
        for text in self.policy["named_metadata_and_credentials"]:
            with self.subTest(address=text):
                self.assertEqual(address_decision(text, self.policy), "DENIED_RANGE")
        self.assertIs(self.policy["metadata_denied_all_ports"], True)
        self.assertIs(self.data["runtime"]["metadata_exception"], False)

    def test_mapped_public_and_private_addresses_denied_on_bytes_not_spelling(self):
        for text in (
            "::ffff:169.254.170.2", "::ffff:a9fe:aa02", "::ffff:127.0.0.1",
            "::ffff:8.8.8.8", "::ffff:808:808", "::8.8.8.8", "64:ff9b::808:808",
            "64:ff9b:1::a9fe:aa02", "2002:0808:0808::1", "2001::1",
        ):
            with self.subTest(address=text):
                self.assertEqual(binary_address_decision(ipaddress.ip_address(text).packed, self.policy), "DENIED_RANGE")

    def test_noncanonical_address_text_is_refused_instead_of_reinterpreted(self):
        for text in (
            "127.1", "2130706433", "0177.0.0.1", "0x7f000001", "127.000.0.1",
            "8.8.8.008", "[::1]", "fe80::1%eth0", "2606:4700:4700:0:0:0:0:1111",
            "2606:4700:4700::ABCD", " 8.8.8.8", "8.8.8.8\n",
        ):
            with self.subTest(address=text):
                self.assertIn(address_decision(text, self.policy), {"INVALID_ADDRESS", "NONCANONICAL_ADDRESS"})

    def test_all_published_alternate_host_encodings_hit_lexical_guard(self):
        for host in self.data["source_normalization_vectors"]["literal_hosts_denied"]:
            with self.subTest(host=host):
                self.assertTrue(literal_host(host))

    def test_post_idna_vectors_check_guard_not_the_unimplemented_idna_library(self):
        for vector in self.data["source_normalization_vectors"]["post_idna_literal_outputs"]:
            with self.subTest(vector=vector):
                self.assertFalse(vector["input"].isascii())
                self.assertTrue(vector["a_label"].isascii())
                self.assertTrue(literal_host(vector["a_label"]))
        self.assertEqual(
            self.data["source_normalization_vectors"]["post_idna_test_scope"],
            "LITERAL_GUARD_ON_PUBLISHED_OUTPUT_NOT_UTS46_EXECUTION",
        )

    def test_public_binary_addresses_pass_only_the_address_predicate_not_registration(self):
        for text in ("8.8.8.8", "93.184.216.34", "2606:4700:4700::1111"):
            with self.subTest(address=text):
                self.assertEqual(address_decision(text, self.policy), "ALLOWED")
                self.assertTrue(literal_host(text))
        self.assertEqual(self.data["enablement"]["approved_providers"], [])

    def test_self_global_ipv6_and_public_prefixes_are_additional_denies(self):
        prefixes = ("93.184.216.0/24", "2606:4700:4700::/48")
        for text in ("93.184.216.34", "2606:4700:4700::1111"):
            self.assertEqual(address_decision(text, self.policy, prefixes), "DENIED_SELF")
        self.assertEqual(address_decision("8.8.8.8", self.policy, prefixes), "ALLOWED")
        self.assertEqual(address_decision("4000::1", self.policy), "DENIED_SCOPE")

    def test_exact_custom_pins_reject_overlapping_public_or_mixed_denied_answers(self):
        pinned = ("8.8.8.8", "93.184.216.34")
        cases = (
            (tuple(reversed(pinned)), "UNCHANGED_PIN"),
            (pinned[:1], "SUSPEND_RESOLUTION_CHANGED"),
            ((*pinned, "1.1.1.1"), "SUSPEND_RESOLUTION_CHANGED"),
            (("1.1.1.1",), "SUSPEND_RESOLUTION_CHANGED"),
            ((*pinned, "169.254.170.2"), "DENIED_RESOLUTION"),
            ((*pinned, "fd00:ec2::254"), "DENIED_RESOLUTION"),
            ((*pinned, "::ffff:8.8.8.8"), "DENIED_RESOLUTION"),
            ((), "EMPTY_RESOLUTION"),
        )
        for answers, expected in cases:
            with self.subTest(answers=answers):
                self.assertEqual(custom_pin_decision(pinned, answers, self.policy), expected)
        self.assertEqual(custom_pin_decision(
            pinned, pinned, self.policy, ("93.184.216.0/24",),
        ), "DENIED_RESOLUTION")
        self.assertEqual(custom_pin_decision(
            ("8.8.8.8", "10.0.0.1"), ("8.8.8.8",), self.policy,
        ), "DENIED_PIN")


class AsciiUriSourceTests(unittest.TestCase):
    def setUp(self):
        self.data = adr.load_json_document(DATA)

    def test_ascii_name_case_single_trailing_dot_and_percent_path_canonicalization(self):
        self.assertEqual(
            normalize_ascii_url("HTTPS://API.PROVIDER.TLD.:443/v1/%7Echat", self.data),
            ("api.provider.tld", "/v1/~chat"),
        )
        self.assertEqual(normalize_ascii_url("https://api.provider.tld", self.data), ("api.provider.tld", "/"))

    def test_raw_encoded_nested_and_ambiguous_address_paths_are_refused(self):
        for uri in (
            "http://api.provider.tld/", "//api.provider.tld/", "https://user@api.provider.tld/",
            "https://api.provider.tld:80/", "https://api.provider.tld:0443/", "https://api.provider.tld:/",
            "https://api..provider.tld/", "https://api.provider.tld../", "https://%61pi.provider.tld/",
            "https://127.1/", "https://0xA9FEA9FE/", "https://[::ffff:169.254.170.2]/",
            "https://api.provider.tld/?", "https://api.provider.tld/#", "https://api.provider.tld\\@else.tld/",
            "https://api.provider.tld/\n", "https://api.provider.tld/%0d%0a",
            "https://api.provider.tld/v1/%2e%2e/chat", "https://api.provider.tld/v1/../chat",
            "https://api.provider.tld/v1/%252e%252e/chat", "https://api.provider.tld/%2fadmin",
            "https://api.provider.tld/%5cadmin", "https://api.provider.tld/%3fsecret",
            "https://api.provider.tld/%23fragment", "https://api.provider.tld/%zz",
            "https://api.provider.tld/%00", "https://api.provider.tld/%C2%A0",
            "https://-api.provider.tld/", "https://api-.provider.tld/",
        ):
            with self.subTest(uri=uri):
                with self.assertRaises(ValueError):
                    normalize_ascii_url(uri, self.data)

    def test_label_host_and_path_limits_are_exact(self):
        self.assertEqual(normalize_ascii_url(
            f"https://{'a' * 63}.provider.tld/", self.data,
        )[0], f"{'a' * 63}.provider.tld")
        for uri in (
            f"https://{'a' * 64}.provider.tld/",
            "https://" + ".".join(["a" * 63] * 4) + "/",
            "https://api.provider.tld/" + "a" * 256,
        ):
            with self.subTest(uri=uri):
                with self.assertRaises(ValueError):
                    normalize_ascii_url(uri, self.data)
        path = "/" + "a" * 255
        self.assertEqual(normalize_ascii_url("https://api.provider.tld" + path, self.data)[1], path)

    def test_special_use_and_self_suffixes_compare_at_label_boundaries(self):
        for host in ("localhost", "metadata.google.internal", "home.arpa", "anything.local",
                     "anything.example", "metadata", "api.pennilogic.fixture.tld"):
            with self.subTest(host=host):
                with self.assertRaises(ValueError):
                    normalize_ascii_url(f"https://{host}/", self.data, ("pennilogic.fixture.tld",))
        self.assertEqual(normalize_ascii_url(
            "https://notpennilogic.fixture.tld/", self.data, ("pennilogic.fixture.tld",),
        )[0], "notpennilogic.fixture.tld")

    def test_normalized_prefix_is_not_a_string_prefix_escape(self):
        self.assertTrue(path_within_prefix("/v1", "/v1"))
        self.assertTrue(path_within_prefix("/v1/chat", "/v1"))
        self.assertTrue(path_within_prefix("/v1/chat", "/v1/"))
        self.assertTrue(path_within_prefix("/chat", "/"))
        self.assertFalse(path_within_prefix("/v10/chat", "/v1"))
        self.assertFalse(path_within_prefix("/v1-evil/chat", "/v1"))


if __name__ == "__main__":
    unittest.main()
