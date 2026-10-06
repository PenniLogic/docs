"""Source checks for Docs56's prohibition proposal; no database gate or runtime proof."""

import copy
import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import stat
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("embedding_check_docs", ROOT / "scripts" / "check_docs.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
adr = checks.load_check("validate_adr_layout")
schema_check = checks.load_check("check_client_states")

RECORD = ROOT / "adr" / "ADR-025.md"
DATA = ROOT / "adr" / "embedding-policy.json"
SCHEMA = ROOT / "adr" / "embedding-policy.schema.json"
TICKET = "T-ADR-EMBED-12"
REOPENING_IDS = {
    "REOPEN-NEED-MINIMISATION", "REOPEN-INVERSION-MEMBERSHIP", "REOPEN-TENANCY-PROTECTION",
    "REOPEN-MODEL-REINDEX", "REOPEN-RETENTION-ERASURE", "REOPEN-PROVIDER-ECONOMICS",
    "REOPEN-PURPOSE-REVIEW",
}
CONSUMER_TEST_IDS = {
    "DBEXT-UNACCEPTED-PGVECTOR", "DBCOLUMN-USER-DERIVED", "DBPOLICY-ACCEPTED-BYTE-BINDINGS",
    "DBPOLICY-PROHIBITED-AFTER-ACCEPTANCE", "DBPOLICY-ACTUAL-OWNING-PATH",
}
REQUIRED_BOUNDARIES = (
    "The deterministic-first categorisation baseline is unchanged.",
    "Retrieval-augmented authoritative financial arithmetic is prohibited.",
    "AC2 and DoD3 remain UNMET: no actual database-extension gate consumes this artifact.",
)


def validate_data(data, schema):
    schema_check.validate_schema(data, schema)
    adr.canonical_date(data["decision_date"], "embedding policy decision_date")
    identifiers = [item["id"] for item in data["reopening"]["required_evidence"]]
    if len(set(identifiers)) != len(identifiers) or set(identifiers) != REOPENING_IDS:
        raise ValueError("Reopening evidence must name every required identifier exactly once")
    for item in data["reopening"]["required_evidence"]:
        if item["acceptance"] != item["acceptance"].strip() or not item["acceptance"].strip():
            raise ValueError("Reopening acceptance text must be nonempty and trimmed")


def validate_record(document, data_bytes, schema_bytes):
    data = adr.strict_json_loads(data_bytes.decode("utf-8"), DATA.name)
    schema = adr.strict_json_loads(schema_bytes.decode("utf-8"), SCHEMA.name)
    validate_data(data, schema)
    source = adr.parse_source(RECORD.name, document.encode("utf-8"))
    if (source.number, source.ticket, source.date) != (data["record"], data["ticket"], data["decision_date"]):
        raise ValueError("Decision record, ticket and date must match the policy")
    if source.status != "ACCEPTED" or source.supersedes is not None or source.superseded_by is not None:
        raise ValueError("This proposal must not replace or loosen another decision")
    for label, raw in (("Policy", data_bytes), ("Schema", schema_bytes)):
        bindings = re.findall(rf"\*\*{label} SHA-256:\*\* `([0-9a-f]{{64}})`", document)
        if bindings != [hashlib.sha256(raw).hexdigest()]:
            raise ValueError(f"{label} must have exactly one matching dated raw-byte binding")
    if f'`{data["artifact_id"]}@{data["policy_version"]}`' not in document:
        raise ValueError("The ADR must name its exact policy identifier and version")
    identifiers = REOPENING_IDS | CONSUMER_TEST_IDS | {
        data["consumer_gate"]["id"], data["future_implementation"]["activation_gate_id"],
    }
    for identifier in identifiers:
        if f"`{identifier}`" not in document:
            raise ValueError(f"Missing named required gate: {identifier}")
    normalized = re.sub(r"\s+", " ", document)
    for boundary in REQUIRED_BOUNDARIES:
        if boundary not in normalized:
            raise ValueError(f"Missing source acceptance boundary: {boundary}")


def object_paths(value, path=()):
    if isinstance(value, dict):
        yield path, value
        for key, item in value.items():
            yield from object_paths(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from object_paths(item, path + (index,))


def at_path(value, path):
    for key in path:
        value = value[key]
    return value


class PublishedEmbeddingSourceTests(unittest.TestCase):
    def test_policy_schema_and_dated_record_agree(self):
        validate_record(RECORD.read_text(encoding="utf-8"), DATA.read_bytes(), SCHEMA.read_bytes())

    def test_original_ticket_allocation_index_and_registry_agree(self):
        layout = adr.validate_sources(ROOT)
        self.assertEqual(layout.allocations["ADR-025"].ticket, TICKET)
        self.assertEqual(layout.sources["ADR-025"].ticket, TICKET)
        self.assertEqual(layout.sources["ADR-025"].status, "ACCEPTED")
        adr.check_layout(ROOT)
        entry = next(item for item in adr.load_json_document(
            ROOT / "adr" / "accepted-records.json"
        )["items"] if item["number"] == "ADR-025")
        self.assertEqual(entry, {
            "number": "ADR-025", "date": layout.sources["ADR-025"].date,
            "sha256": hashlib.sha256(RECORD.read_bytes()).hexdigest(), "bytes": len(RECORD.read_bytes()),
        })

    def test_static_request_local_and_prohibited_durable_classes_are_distinct(self):
        data = adr.load_json_document(DATA)
        self.assertEqual(set(data["classes"]), {
            "STATIC_CATEGORY_PROTOTYPE", "EPHEMERAL_USER_INFERENCE", "DURABLE_USER_DERIVED",
        })
        static, ephemeral, durable = data["classes"].values()
        self.assertIs(static["user_data_derived"], False)
        self.assertEqual(static["permitted_stores"], ["VERSIONED_READ_ONLY_PRODUCT_ASSET"])
        self.assertIs(ephemeral["user_data_derived"], True)
        self.assertEqual(ephemeral["permitted_stores"], ["SERVER_REQUEST_MEMORY", "DEVICE_OPERATION_MEMORY"])
        self.assertEqual(durable["permitted_stores"], [])
        for item in data["classes"].values():
            self.assertEqual(item["permitted_model_versions"], [])

    def test_schema_objects_are_closed_and_every_published_field_is_required(self):
        schema = adr.load_json_document(SCHEMA)
        for path, node in object_paths(schema):
            if node.get("type") == "object":
                with self.subTest(path=path):
                    self.assertIs(node["additionalProperties"], False)
                    self.assertEqual(set(node["required"]), set(node["properties"]))

    def test_before_and_after_acceptance_keep_vector_extensions_and_columns_denied(self):
        data = adr.load_json_document(DATA)
        database = data["database"]
        self.assertEqual(database["denied_extension_identifiers"], ["pgvector", "vector"])
        self.assertEqual(database["permitted_user_derived_embedding_columns"], [])
        self.assertEqual(database["permitted_user_derived_vector_stores"], [])
        self.assertEqual(database["before_source_acceptance"], database["after_prohibited_source_acceptance"])
        self.assertEqual(database["before_source_acceptance"], database["on_missing_unaccepted_stale_or_unknown_policy"])
        self.assertIs(database["semantic_column_classification_required"], True)

    def test_actual_consumer_gate_and_original_completion_remain_explicitly_unmet(self):
        data = adr.load_json_document(DATA)
        gate = data["consumer_gate"]
        self.assertEqual(gate["owner_ticket"], "T-PLT-01")
        self.assertEqual(gate["owner_issue"], "https://github.com/PenniLogic/infra/issues/25")
        self.assertIsNone(gate["implementation_source"])
        self.assertEqual(gate["evidence_status"], "UNMET_IN_THIS_SOURCE_UNIT")
        self.assertEqual(set(gate["required_consumer_test_ids"]), CONSUMER_TEST_IDS)
        self.assertIs(gate["runtime_enforcement_claimed"], False)
        self.assertIs(data["delivery"]["original_issue_complete"], False)
        self.assertEqual(data["delivery"]["assigned_sprint"], "Future")
        self.assertIs(data["authority"]["specific_owner_embedding_attestation"], False)

    def test_persistence_only_tests_are_conditional_not_simulated_execution(self):
        conditional = adr.load_json_document(DATA)["persistence_only"]
        self.assertIsNone(conditional["model"])
        self.assertIsNone(conditional["dimension"])
        self.assertEqual(conditional["hard_delete_similarity_residue_test"], "NOT_APPLICABLE_PERSISTENCE_PROHIBITED")
        self.assertEqual(conditional["model_version_and_complete_reindex"], "NOT_APPLICABLE_PERSISTENCE_PROHIBITED")
        self.assertEqual(conditional["live_serving_acceptance"], "NOT_PERFORMED_PERSISTENCE_PROHIBITED")
        self.assertIs(conditional["crypto_shredding_sufficient"], False)
        self.assertIs(conditional["searchable_vector_encryption_solves_inversion"], False)

    def test_new_machine_artifacts_and_tests_are_ascii_lf_with_one_final_newline(self):
        for path in (DATA, SCHEMA, Path(__file__), RECORD):
            with self.subTest(path=path.name):
                raw = path.read_bytes()
                if path != RECORD:
                    raw.decode("ascii")
                self.assertNotIn(b"\r", raw)
                self.assertTrue(raw.endswith(b"\n"))
                self.assertFalse(raw.endswith(b"\n\n"))


class ContradictoryEmbeddingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.data = adr.load_json_document(DATA)
        self.schema = adr.load_json_document(SCHEMA)

    def rejected(self, change, pattern=None):
        data = copy.deepcopy(self.data)
        change(data)
        if pattern is None:
            with self.assertRaises(ValueError):
                validate_data(data, self.schema)
        else:
            with self.assertRaisesRegex(ValueError, pattern):
                validate_data(data, self.schema)

    def test_unknown_policy_version_identifier_record_ticket_or_schema_is_rejected(self):
        for key, value in (
            ("schema_version", 2), ("schema_version", True), ("policy_version", "0.9.0"),
            ("policy_version", "1.0.1"), ("artifact_id", "synthetic-unknown-policy"),
            ("record", "ADR-022"), ("ticket", "T-ADR-AIEGRESS-08"),
            ("schema", "synthetic-unknown-schema.json"), ("decision", "ALLOWED"),
            ("effective_on", "LOCAL_AUTHOR_COMMIT"),
        ):
            with self.subTest(key=key, value=value):
                self.rejected(lambda data: data.__setitem__(key, value))

    def test_every_missing_required_field_is_rejected(self):
        for path, node in object_paths(self.data):
            for key in node:
                with self.subTest(path=path, key=key):
                    self.rejected(lambda data: at_path(data, path).pop(key))

    def test_unknown_fields_at_every_object_boundary_are_rejected(self):
        for path, _ in object_paths(self.data):
            with self.subTest(path=path):
                self.rejected(lambda data: at_path(data, path).__setitem__("synthetic_unknown_field", None))

    def test_unknown_or_relabelled_embedding_classes_are_rejected(self):
        self.rejected(lambda data: data["classes"].__setitem__("ANONYMISED_USER_VECTOR", {}))
        self.rejected(lambda data: data["classes"]["STATIC_CATEGORY_PROTOTYPE"].__setitem__("user_data_derived", True))
        self.rejected(lambda data: data["classes"]["STATIC_CATEGORY_PROTOTYPE"].__setitem__(
            "source_provenance", "USER_MERCHANT_OR_CORRECTION"
        ))
        self.rejected(lambda data: data["classes"]["STATIC_CATEGORY_PROTOTYPE"].__setitem__(
            "user_correction_adaptation", "ALLOWED"
        ))

    def test_all_user_source_kinds_and_unknown_source_classes_are_bounded(self):
        for name in ("EPHEMERAL_USER_INFERENCE", "DURABLE_USER_DERIVED"):
            for source in self.data["classes"][name]["source_kinds"]:
                with self.subTest(name=name, source=source):
                    self.rejected(lambda data: data["classes"][name]["source_kinds"].remove(source))
            self.rejected(lambda data: data["classes"][name]["source_kinds"].append("SYNTHETIC_UNKNOWN_SOURCE"))

    def test_durable_vector_escape_to_every_copy_surface_is_rejected(self):
        for destination in self.data["forbidden_user_derived_destinations"]:
            with self.subTest(destination=destination):
                self.rejected(lambda data: data["classes"]["DURABLE_USER_DERIVED"]["permitted_stores"].append(destination))
                self.rejected(lambda data: data["forbidden_user_derived_destinations"].remove(destination))

    def test_ephemeral_vector_escape_to_every_copy_surface_is_rejected(self):
        for destination in self.data["forbidden_user_derived_destinations"]:
            with self.subTest(destination=destination):
                self.rejected(lambda data: data["classes"]["EPHEMERAL_USER_INFERENCE"]["permitted_stores"].append(destination))

    def test_unknown_store_or_model_version_is_rejected_for_every_class(self):
        for name in self.data["classes"]:
            with self.subTest(name=name):
                self.rejected(lambda data: data["classes"][name]["permitted_stores"].append("SYNTHETIC_UNKNOWN_STORE"))
                self.rejected(lambda data: data["classes"][name]["permitted_model_versions"].append(
                    "synthetic-unapproved-model@1"
                ))

    def test_request_completion_cancellation_timeout_and_error_cannot_retain_vectors(self):
        for condition in self.data["classes"]["EPHEMERAL_USER_INFERENCE"]["end_conditions"]:
            with self.subTest(condition=condition):
                self.rejected(lambda data: data["classes"]["EPHEMERAL_USER_INFERENCE"]["end_conditions"].remove(condition))
        for key in ("durable_spill", "cross_request_reuse", "training_or_reindex", "export", "lifetime",
                    "if_nondurable_execution_unproven"):
            with self.subTest(key=key):
                self.rejected(lambda data: data["classes"]["EPHEMERAL_USER_INFERENCE"].__setitem__(key, "ALLOWED"))

    def test_zero_day_retention_encryption_hashing_or_anonymisation_is_not_an_exception(self):
        for days in (0, 1, True):
            with self.subTest(days=days):
                self.rejected(lambda data: data["classes"]["DURABLE_USER_DERIVED"].__setitem__("retention_period_days", days))
        self.rejected(lambda data: data["classes"]["DURABLE_USER_DERIVED"].__setitem__("retention", "TEMPORARY"))
        for bypass in self.data["prohibited_transform_bypasses"]:
            with self.subTest(bypass=bypass):
                self.rejected(lambda data: data["prohibited_transform_bypasses"].remove(bypass))
        for key in ("crypto_shredding_sufficient", "searchable_vector_encryption_solves_inversion"):
            with self.subTest(key=key):
                self.rejected(lambda data: data["persistence_only"].__setitem__(key, True))

    def test_pgvector_sql_vector_and_other_vector_extension_exceptions_are_rejected(self):
        for identifier in self.data["database"]["denied_extension_identifiers"]:
            with self.subTest(identifier=identifier):
                self.rejected(lambda data: data["database"]["denied_extension_identifiers"].remove(identifier))
        self.rejected(lambda data: data["database"].__setitem__("other_vector_extensions", "ALLOWED"))
        self.rejected(lambda data: data["database"]["permitted_user_derived_vector_stores"].append("synthetic-store"))

    def test_renamed_array_json_or_binary_embedding_columns_are_not_exempt(self):
        for column in ("synthetic_vector", "synthetic_float_array", "synthetic_json", "synthetic_binary", "synthetic_features"):
            with self.subTest(column=column):
                self.rejected(lambda data: data["database"]["permitted_user_derived_embedding_columns"].append(column))
        for key in ("array_json_binary_or_renamed_columns_exempt", "static_prototype_label_overrides_denial"):
            with self.subTest(key=key):
                self.rejected(lambda data: data["database"].__setitem__(key, True))
        self.rejected(lambda data: data["database"].__setitem__("semantic_column_classification_required", False))

    def test_missing_stale_or_unaccepted_policy_must_not_be_an_allow_fallback(self):
        for key in ("before_source_acceptance", "after_prohibited_source_acceptance",
                    "on_missing_unaccepted_stale_or_unknown_policy"):
            with self.subTest(key=key):
                self.rejected(lambda data: data["database"].__setitem__(key, "ALLOW"))
        for binding in self.data["consumer_gate"]["required_bindings"]:
            with self.subTest(binding=binding):
                self.rejected(lambda data: data["consumer_gate"]["required_bindings"].remove(binding))

    def test_absent_consumer_requirement_or_fabricated_gate_proof_is_rejected(self):
        self.rejected(lambda data: data.pop("consumer_gate"))
        for key, value in (
            ("owner_ticket", "T-ADR-EMBED-12"), ("id", "SYNTHETIC-DOCS-CHECKER"),
            ("implementation_source", "synthetic-unused-workflow.yml"), ("evidence_status", "PASSED"),
            ("provider_acceptance_required", "AUTHOR_HEADER_ONLY"), ("runtime_enforcement_claimed", True),
        ):
            with self.subTest(key=key):
                self.rejected(lambda data: data["consumer_gate"].__setitem__(key, value))
        for identifier in CONSUMER_TEST_IDS:
            with self.subTest(identifier=identifier):
                self.rejected(lambda data: data["consumer_gate"]["required_consumer_test_ids"].remove(identifier))

    def test_cross_purpose_history_enrichment_training_or_consent_exceptions_are_rejected(self):
        for key in ("conversation_enrichment_shared_embedding_store", "cross_purpose_payload_or_vector_reuse",
                    "conversation_or_enrichment_training"):
            with self.subTest(key=key):
                self.rejected(lambda data: data["cross_purpose"].__setitem__(key, "ALLOWED"))
        for key in ("history_opt_in_permits_embedding_retention", "sharing_grant_permits_embedding_retention"):
            with self.subTest(key=key):
                self.rejected(lambda data: data["cross_purpose"].__setitem__(key, True))
        self.rejected(lambda data: data["cross_purpose"].__setitem__(
            "ordinary_record_database_colocation", "SHARED_UNSCOPED_PAYLOAD_STORE"
        ))
        self.rejected(lambda data: data["cross_purpose"].__setitem__("existing_structured_merchant_rules", "VECTOR_TRAINING"))

    def test_deterministic_money_egress_crypto_or_sharing_cannot_be_redefined(self):
        for key in self.data["boundaries"]:
            with self.subTest(key=key):
                value = True if key == "new_datastore_provider_or_spend_authorized" else "ALLOWED"
                self.rejected(lambda data: data["boundaries"].__setitem__(key, value))

    def test_unselected_persistent_model_dimension_and_unperformed_tests_cannot_be_claimed(self):
        for key in self.data["persistence_only"]:
            with self.subTest(key=key):
                value = 42 if key == "dimension" else "SYNTHETIC_PASSED_OR_APPROVED"
                self.rejected(lambda data: data["persistence_only"].__setitem__(key, value))

    def test_missing_duplicate_unknown_or_blank_reopening_evidence_is_rejected(self):
        self.rejected(lambda data: data["reopening"]["required_evidence"].pop())
        self.rejected(lambda data: data["reopening"]["required_evidence"][0].__setitem__(
            "id", data["reopening"]["required_evidence"][1]["id"]
        ), "identifier exactly once")
        self.rejected(lambda data: data["reopening"]["required_evidence"][0].__setitem__("id", "SYNTHETIC-UNKNOWN-GATE"))
        for text in ("", " ", " untrimmed "):
            with self.subTest(text=text):
                self.rejected(lambda data: data["reopening"]["required_evidence"][0].__setitem__("acceptance", text))

    def test_automatic_reopening_or_partial_evidence_is_rejected(self):
        self.rejected(lambda data: data["reopening"].__setitem__("automatic", True))
        for key in ("all_evidence_required", "new_explicit_superseding_decision_required", "policy_version_bump_required"):
            with self.subTest(key=key):
                self.rejected(lambda data: data["reopening"].__setitem__(key, False))

    def test_default_on_activation_missing_checks_or_unverified_removal_is_rejected(self):
        self.rejected(lambda data: data["future_implementation"].__setitem__("default", "ON"))
        self.rejected(lambda data: data["future_implementation"].__setitem__("created_only_after_new_merged_decision", False))
        self.rejected(lambda data: data["future_implementation"].__setitem__("reopening_alone_enables_nothing", False))
        self.rejected(lambda data: data["future_implementation"].__setitem__("acceptance_status", "PASSED"))
        self.rejected(lambda data: data["future_implementation"].__setitem__("rollback", "DROP_STORE_WITHOUT_RESIDUE_CHECK"))
        for check in self.data["future_implementation"]["required_activation_checks"]:
            with self.subTest(check=check):
                self.rejected(lambda data: data["future_implementation"]["required_activation_checks"].remove(check))

    def test_bespoke_authority_independent_approval_runtime_completion_or_sprint_change_is_rejected(self):
        self.rejected(lambda data: data["authority"].__setitem__("specific_owner_embedding_attestation", True))
        for key in ("original_issue_complete", "sprint_assignment_changed", "runtime_enforcement_claimed", "independent_review_claimed"):
            with self.subTest(key=key):
                self.rejected(lambda data: data["delivery"].__setitem__(key, True))
        self.rejected(lambda data: data["delivery"].__setitem__("assigned_sprint", "Sprint 01"))

    def test_boolean_integer_confusion_is_rejected(self):
        for path, node in object_paths(self.data):
            for key, value in node.items():
                if isinstance(value, bool):
                    with self.subTest(path=path, key=key):
                        self.rejected(lambda data: at_path(data, path).__setitem__(key, int(value)))

    def test_invalid_calendar_date_or_noncanonical_date_is_rejected(self):
        for value in ("2026-02-30", "2026-13-01", "2026-1-04", "2026-10-04T00:00:00Z"):
            with self.subTest(value=value):
                self.rejected(lambda data: data.__setitem__("decision_date", value))

    def test_duplicate_keys_nonfinite_numbers_and_lone_surrogates_are_rejected(self):
        original = DATA.read_text(encoding="utf-8")
        for text in (
            original.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1', 1),
            original.replace('"dimension": null', '"dimension": NaN', 1),
            original.replace('"dimension": null', '"dimension": 1e999', 1),
            original.replace('"model": null', '"model": "\\ud800"', 1),
        ):
            with self.subTest(text_sha256=hashlib.sha256(text.encode()).hexdigest()):
                with self.assertRaises(ValueError):
                    adr.strict_json_loads(text, DATA.name)

    def test_unsupported_schema_keyword_is_an_error_not_a_silent_capability(self):
        schema = copy.deepcopy(self.schema)
        schema["minimum"] = 0
        with self.assertRaisesRegex(schema_check.SchemaError, "unsupported schema keyword"):
            validate_data(self.data, schema)

    def test_policy_or_schema_raw_byte_drift_breaks_the_dated_record_binding(self):
        document = RECORD.read_text(encoding="utf-8")
        for data_raw, schema_raw, label in (
            (DATA.read_bytes() + b" ", SCHEMA.read_bytes(), "Policy"),
            (DATA.read_bytes(), SCHEMA.read_bytes() + b" ", "Schema"),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, f"{label} must have exactly one"):
                    validate_record(document, data_raw, schema_raw)

    def test_missing_duplicate_or_stale_digest_and_missing_version_are_rejected(self):
        document = RECORD.read_text(encoding="utf-8")
        for label in ("Policy", "Schema"):
            binding = re.search(rf"\*\*{label} SHA-256:\*\* `([0-9a-f]{{64}})`", document)[0]
            for changed in (document.replace(binding, ""), document + binding + "\n",
                            document.replace(binding, f"**{label} SHA-256:** `{'0' * 64}`")):
                with self.subTest(label=label):
                    with self.assertRaisesRegex(ValueError, f"{label} must have exactly one"):
                        validate_record(changed, DATA.read_bytes(), SCHEMA.read_bytes())
        with self.assertRaisesRegex(ValueError, "exact policy identifier and version"):
            validate_record(document.replace("adr-025-embedding-policy@1.0.0", "synthetic-stale-policy@0"),
                            DATA.read_bytes(), SCHEMA.read_bytes())

    def test_stale_date_relationship_or_missing_named_boundary_is_rejected(self):
        document = RECORD.read_text(encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "date must match"):
            validate_record(document.replace("2026-10-04", "2026-10-03"), DATA.read_bytes(), SCHEMA.read_bytes())
        with self.assertRaisesRegex(ValueError, "must not replace"):
            validate_record(document.replace("supersedes: null", "supersedes: ADR-018"),
                            DATA.read_bytes(), SCHEMA.read_bytes())
        for boundary in REQUIRED_BOUNDARIES:
            with self.subTest(boundary=boundary):
                changed = re.sub(re.escape(boundary).replace(r"\ ", r"\s+"), "", document)
                with self.assertRaisesRegex(ValueError, "Missing source acceptance boundary"):
                    validate_record(changed, DATA.read_bytes(), SCHEMA.read_bytes())
        with self.assertRaisesRegex(ValueError, "Missing named required gate"):
            validate_record(document.replace("`DBPOLICY-ACTUAL-OWNING-PATH`", "unbound gate"),
                            DATA.read_bytes(), SCHEMA.read_bytes())


class EmbeddingLayoutBoundaryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        shutil.copytree(ROOT / "adr", self.root / "adr")

    def outputs(self):
        return {name: (self.root / "adr" / name).read_bytes()
                for name in ("README.md", "accepted-records.json")}

    def test_real_scoped_render_is_idempotent_and_preserves_all_bytes_and_modes(self):
        paths = sorted((self.root / "adr").iterdir())
        before = [(path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) for path in paths]
        self.assertEqual(adr.render(self.root, TICKET), [])
        self.assertEqual(adr.render(self.root, TICKET), [])
        self.assertEqual(before, [(path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) for path in paths])
        adr.check_layout(self.root)

    def test_foreign_generated_slot_drift_refuses_before_any_output_write(self):
        path = self.root / "adr" / "README.md"
        raw = path.read_bytes()
        marker = b"<!-- SLOT START ADR-024 -->\n### ADR-024\n"
        self.assertEqual(raw.count(marker), 2)
        path.write_bytes(raw.replace(marker, marker + b"synthetic foreign drift\n", 1))
        before = self.outputs()
        with self.assertRaisesRegex(adr.LayoutError, "outside the slots owned"):
            adr.render(self.root, TICKET)
        self.assertEqual(self.outputs(), before)

    def test_foreign_acceptance_entry_drift_refuses_before_any_output_write(self):
        path = self.root / "adr" / "accepted-records.json"
        registry = adr.load_json_document(path)
        next(item for item in registry["items"] if item["number"] == "ADR-024")["sha256"] = "0" * 64
        path.write_bytes(adr.render_registry(registry["items"]).encode("utf-8"))
        before = self.outputs()
        with self.assertRaisesRegex(adr.LayoutError, "outside the entries owned"):
            adr.render(self.root, TICKET)
        self.assertEqual(self.outputs(), before)

    def test_undated_own_source_edit_or_unknown_ticket_is_not_laundered_by_render(self):
        before = self.outputs()
        with self.assertRaisesRegex(adr.LayoutError, "owns no allocation"):
            adr.render(self.root, "T-ADR-UNKNOWN-99")
        self.assertEqual(self.outputs(), before)
        path = self.root / "adr" / "ADR-025.md"
        path.write_bytes(path.read_bytes() + b"\nSynthetic undated edit.\n")
        with self.assertRaisesRegex(adr.LayoutError, "accepted record edited without a date change"):
            adr.render(self.root, TICKET)
        self.assertEqual(self.outputs(), before)


if __name__ == "__main__":
    unittest.main()
