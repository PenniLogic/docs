"""Tests for the ADR layout generator and validator (adr/LAYOUT.md, PenniLogic/docs#141).

Scratch cases run against a copy of the *baseline* layout, which ``setUpModule`` builds once from
the pinned pre-split reference with ``split``; nothing runs against the repository files and no
test depends on how many reserved records the committed tree currently holds. The baseline is
cross-checked against the committed frozen files (legacy sources, historical manifest, original
allocations, untouched README slots), so a wrong ``split`` cannot hide behind a fixture it produced.
Live-tree tests derive their expectations from the tree under test. Each planted negative proves
that the validator fails closed; the positive cases prove byte-exact reproduction of the committed
README, ticket-scoped rendering and deterministic output. Nothing here writes an architecture
decision.
"""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adr = load("validate_adr_layout")
LIVE_README = (ROOT / "adr" / "README.md").read_bytes()
REFERENCE = (ROOT / "adr" / "presplit-reference.md").read_bytes()
LEGACY_FILES = [f"ADR-{index:03d}.md" for index in range(1, 15)]
SPLIT_OUTPUT = LEGACY_FILES + ["legacy-bodies.json", "reservations.json", "accepted-records.json", "README.md"]
MONEY, CAT, CRYPTO = "T-ADR-MONEY-01", "T-ADR-CAT-02", "T-ADR-CRYPTO-04"
# A slot block together with the blank line that follows it in the rendered README.
SLOT_BLOCK = re.compile(adr.SLOT_PATTERN.pattern + r"\n", re.DOTALL)
# The proving-tests section every synthetic decided record carries (adr/LAYOUT.md, accepted-record integrity).
TESTS_SECTION = "\n### 1. Tests implementation tickets must add\n\n`sample_conformance_test` proves the sample rule.\n"
DECISION = "\n**Decision.** Sample text.\n"


class Baseline:
    """The initial split layout: 14 legacy records, the 9 original allocations, nothing published."""

    directory = None
    adr = None

    @classmethod
    def build(cls):
        cls.directory = tempfile.TemporaryDirectory()
        root = Path(cls.directory.name)
        (root / "adr").mkdir()
        (root / "adr" / "presplit-reference.md").write_bytes(REFERENCE)
        (root / "adr" / "README.md").write_bytes(REFERENCE)
        adr.split(root)
        cls.adr = root / "adr"

    @classmethod
    def read(cls, name):
        return (cls.adr / name).read_bytes()

    @classmethod
    def readme(cls):
        return cls.read("README.md").decode("utf-8")


def setUpModule():
    Baseline.build()


def tearDownModule():
    Baseline.directory.cleanup()


def live_state():
    """Facts about the committed tree read straight from headers and JSON, not via the generator."""
    headers = {}
    for path in sorted((ROOT / "adr").glob("ADR-*.md")):
        text = path.read_text(encoding="utf-8")
        headers[path.stem] = dict(line.split(": ", 1) for line in text[4:text.index("\n---\n")].split("\n"))
    allocations = [item["number"] for item in json.loads((ROOT / "adr" / "reservations.json").read_bytes())["items"]]
    return {
        "allocations": allocations,
        "published": [number for number in headers if int(number[4:]) > 14],
        "pending": [n for n in allocations if headers.get(n, {}).get("status", "PENDING") == "PENDING"],
        "decided": [n for n in allocations if headers.get(n, {}).get("status", "PENDING") != "PENDING"],
        "superseded": {fields["supersedes"] for fields in headers.values()} - {"null"},
    }


def live_expectations():
    state = live_state()
    return {
        "legacy": 14, "allocations": len(state["allocations"]), "published": len(state["published"]),
        "pending": len(state["pending"]), "superseded": len(state["superseded"]),
    }


def make_writable(path):
    for item in [path, *path.rglob("*")]:
        try:
            os.chmod(item, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
        except OSError:
            pass


def source(number="ADR-015", ticket=MONEY, title="Money wire format, time and idempotency",
           status="ACCEPTED", date="2026-10-01", supersedes="null", superseded_by="null",
           body_status=None, body_date=None, extra_header=(), tail=DECISION + TESTS_SECTION):
    """A synthetic decision source; the text is a placeholder, not an architecture decision."""
    header = ["---", f"number: {number}"]
    if ticket is not None:
        header.append(f"ticket: {ticket}")
    header += [
        f"title: {title}", f"status: {status}", f"date: {date}",
        f"supersedes: {supersedes}", f"superseded-by: {superseded_by}", *extra_header, "---",
    ]
    body = f"## {number} — {title}\n**Status:** {body_status or status} · {body_date or date}\n{tail}"
    return "\n".join(header) + "\n" + body


def slot_rows(text, number):
    """Rows of the index slot and the pending slot of one number, as (field -> value) dicts."""
    return [
        {field: value for field, value in adr.CELL_PATTERN.findall(slot) if field != "Field"}
        for slot in adr.collect_slots(text)[number]
    ]


class ScratchCase(unittest.TestCase):
    """A scratch repository root holding a copy of the baseline layout."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.root = Path(directory.name)
        self.addCleanup(self.cleanup, directory)
        shutil.copytree(Baseline.adr, self.root / "adr")
        self.adr = self.root / "adr"

    def cleanup(self, directory):
        make_writable(self.root)
        directory.cleanup()

    def write(self, name, text):
        (self.adr / name).write_bytes(text.encode("utf-8") if isinstance(text, str) else text)

    def read(self, name):
        return (self.adr / name).read_bytes()

    def edit(self, name, old, new, count=1):
        data = self.read(name)
        self.assertEqual(data.count(old.encode("utf-8")), count, f"{name} must contain {old!r} {count}x")
        self.write(name, data.replace(old.encode("utf-8"), new.encode("utf-8")))

    def assert_fails(self, pattern, action=None):
        with self.assertRaisesRegex(adr.LayoutError, pattern):
            (action or adr.check_layout)(self.root)

    def readme(self):
        return self.read("README.md").decode("utf-8")


class LiveTreeTests(unittest.TestCase):
    """The committed tree, read only. Expectations are derived from it, never pinned."""

    def test_check_passes_on_the_committed_tree(self):
        self.assertEqual(adr.check_layout(ROOT), live_expectations())

    def test_render_reproduces_the_committed_readme_bytes(self):
        layout = adr.validate_sources(ROOT)
        self.assertEqual(adr.render_readme(layout).encode("utf-8"), LIVE_README)
        self.assertNotIn(b"\r", LIVE_README)

    def test_unscoped_render_is_a_no_op_on_a_copy_of_the_committed_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "adr", root / "adr")
            self.assertFalse(adr.render(root))
            self.assertEqual((root / "adr" / "README.md").read_bytes(), LIVE_README)

    def test_cli_check_reports_success(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(adr.main(["check", "--root", str(ROOT)]), 0)
        self.assertTrue(out.getvalue().startswith("ADR layout valid: 14 legacy records, "), out.getvalue())
        self.assertTrue(out.getvalue().endswith("; adr/README.md and adr/accepted-records.json match.\n"), out.getvalue())

    def test_reference_pins_verify(self):
        self.assertEqual(adr.blob_oid(REFERENCE), adr.REFERENCE_BLOB_OID)
        adr.verify_reference(REFERENCE)

    def test_legacy_set_is_complete_in_the_committed_tree(self):
        self.assertEqual(sorted(adr.validate_sources(ROOT).legacy), [f"ADR-{i:03d}" for i in range(1, 15)])

    def test_committed_registry_pins_every_decided_record_by_its_bytes(self):
        """Read straight from the files: each decided record's date, SHA-256 and length are registered,
        each undecided allocation is a null entry, and the file is in canonical form."""
        live = live_state()
        registry = json.loads((ROOT / "adr" / "accepted-records.json").read_bytes())
        self.assertEqual(registry["schema_version"], 1)
        self.assertEqual([item["number"] for item in registry["items"]], live["allocations"])
        for item in registry["items"]:
            number = item["number"]
            with self.subTest(entry=number):
                if number in live["decided"]:
                    data = (ROOT / "adr" / f"{number}.md").read_bytes()
                    text = data.decode("utf-8")
                    header = dict(line.split(": ", 1) for line in text[4:text.index("\n---\n")].split("\n"))
                    self.assertEqual(item, {
                        "number": number, "date": header["date"],
                        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                    })
                else:
                    self.assertEqual(item, {"number": number, "date": None, "sha256": None, "bytes": None})
        self.assertEqual(
            (ROOT / "adr" / "accepted-records.json").read_bytes(), adr.render_registry(registry["items"]).encode("utf-8")
        )

    def test_committed_decided_records_name_their_tests_and_carry_valid_json_blocks(self):
        layout = adr.validate_sources(ROOT)
        for number, source in layout.sources.items():
            if number in layout.legacy:
                continue
            with self.subTest(record=number):
                adr.check_json_blocks(source)
                if source.decided:
                    adr.check_proving_tests(source)

    def test_grandfather_pins_are_well_formed_and_name_their_record(self):
        for (number, digest), note in adr.UNVERSIONED_JSON_BLOCKS.items():
            with self.subTest(pin=number):
                self.assertRegex(number, r"^ADR-\d{3}$")
                self.assertRegex(digest, r"^[0-9a-f]{64}$")
                self.assertIn(number, note)


class BaselineTests(ScratchCase):
    def test_baseline_is_the_initial_split(self):
        self.assertEqual(adr.check_layout(self.root), {
            "legacy": 14, "allocations": 9, "published": 0, "pending": 9, "superseded": 0,
        })
        self.assertEqual(sorted(p.name for p in self.adr.iterdir()), sorted(SPLIT_OUTPUT + ["presplit-reference.md"]))

    def test_reference_byte_change_is_rejected_by_both_pins(self):
        tampered = REFERENCE[:-2] + b"x" + REFERENCE[-1:]
        with self.assertRaisesRegex(adr.LayoutError, "SHA-256"):
            adr.verify_reference(tampered)
        self.assertNotEqual(adr.blob_oid(tampered), adr.REFERENCE_BLOB_OID)
        self.write("presplit-reference.md", tampered)
        self.assert_fails("SHA-256 .* does not match the pinned")

    def test_missing_reference_has_no_fallback(self):
        (self.adr / "presplit-reference.md").unlink()
        self.assert_fails("presplit-reference.md is missing; there is no fallback")

    def test_manifest_is_derived_from_the_reference_not_trusted(self):
        legacy = adr.derive_legacy(REFERENCE.decode("utf-8"))
        self.assertEqual(adr.render_manifest(legacy).encode("utf-8"), self.read("legacy-bodies.json"))
        manifest = json.loads(self.read("legacy-bodies.json"))
        for item, record in zip(manifest["items"], legacy.values()):
            segment = record.segment.encode("utf-8")
            self.assertTrue(segment.endswith(b"\n---\n\n"))
            self.assertEqual(item["bytes"], len(segment))
            self.assertEqual(record.body.encode("utf-8"), segment[:-1])

    def test_check_docs_hook_runs_the_layout_check(self):
        check_docs = load("check_docs")
        for name in ("planning", "product"):
            shutil.copytree(ROOT / name, self.root / name)
        (self.root / "scripts").mkdir()
        for path in SCRIPTS.glob("*.py"):
            shutil.copy(path, self.root / "scripts" / path.name)
        check_docs.ROOT = self.root
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(check_docs.main(), 0)
        self.assertIn("14 carried-forward ADRs, 0 published reserved records, 9 pending", out.getvalue())
        # A PENDING draft coexists with its reservation: no overlap error.
        self.write("ADR-015.md", source(status="PENDING"))
        adr.render(self.root, MONEY)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(check_docs.main(), 0)
        self.assertIn("1 published reserved records, 9 pending", out.getvalue())
        self.edit("README.md", "| Status | PENDING |\n| Ticket | T-ADR-MONEY-01 |", "| Status | ACCEPTED |\n| Ticket | T-ADR-MONEY-01 |")
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(check_docs.main(), 1)
        self.assertIn("does not match the rendered layout: generated slot ADR-015", err.getvalue())


class SplitTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.root = Path(directory.name)
        self.addCleanup(directory.cleanup)
        (self.root / "adr").mkdir()
        (self.root / "adr" / "presplit-reference.md").write_bytes(REFERENCE)
        (self.root / "adr" / "README.md").write_bytes(REFERENCE)

    def produced(self, name):
        return (self.root / "adr" / name).read_bytes()

    def test_split_reproduces_the_committed_frozen_files_from_the_monolith(self):
        """Files the contract freezes must come out of the monolith exactly as committed; slots
        that no later record has published or superseded must match the committed README."""
        summary = adr.split(self.root)
        self.assertEqual(summary, {"legacy": 14, "allocations": 9, "published": 0, "pending": 9, "superseded": 0})
        self.assertEqual(sorted(p.name for p in (self.root / "adr").iterdir()), sorted(SPLIT_OUTPUT + ["presplit-reference.md"]))
        for name in LEGACY_FILES + ["legacy-bodies.json"]:
            with self.subTest(name=name):
                self.assertEqual(self.produced(name), (ROOT / "adr" / name).read_bytes())
        committed = {item["number"]: item for item in json.loads((ROOT / "adr" / "reservations.json").read_bytes())["items"]}
        for item in json.loads(self.produced("reservations.json"))["items"]:
            self.assertEqual(item, committed[item["number"]])
        live = live_state()
        produced_readme = self.produced("README.md").decode("utf-8")
        committed_slots = adr.collect_slots(LIVE_README.decode("utf-8"))
        for number, slots in adr.collect_slots(produced_readme).items():
            if number not in live["published"] and number not in live["superseded"]:
                with self.subTest(slot=number):
                    self.assertEqual(committed_slots[number], slots)
        self.assertEqual(SLOT_BLOCK.sub("", produced_readme), SLOT_BLOCK.sub("", LIVE_README.decode("utf-8")))
        # The registry starts empty: every allocation is a null entry, and the committed registry keeps
        # exactly those null entries for numbers no decided record has claimed.
        produced_registry = {item["number"]: item for item in json.loads(self.produced("accepted-records.json"))["items"]}
        committed_registry = {item["number"]: item for item in json.loads((ROOT / "adr" / "accepted-records.json").read_bytes())["items"]}
        self.assertEqual(list(produced_registry), list(committed)[:9])
        for number, item in produced_registry.items():
            self.assertEqual(item, {"number": number, "date": None, "sha256": None, "bytes": None})
            if number not in live["decided"]:
                with self.subTest(entry=number):
                    self.assertEqual(committed_registry[number], item)
        if live["allocations"] == list(committed)[:9] and not live["published"]:
            for name in SPLIT_OUTPUT:
                with self.subTest(name=name):
                    self.assertEqual(self.produced(name), (ROOT / "adr" / name).read_bytes())

    def test_split_output_matches_the_module_baseline(self):
        adr.split(self.root)
        for name in SPLIT_OUTPUT:
            with self.subTest(name=name):
                self.assertEqual(self.produced(name), Baseline.read(name))

    def test_split_refuses_an_already_split_layout(self):
        adr.split(self.root)
        with self.assertRaisesRegex(adr.LayoutError, "refusing to overwrite an already split layout"):
            adr.split(self.root)
        (self.root / "adr" / "ADR-001.md").unlink()
        with self.assertRaisesRegex(adr.LayoutError, "already split layout: ADR-002.md"):
            adr.split(self.root)

    def test_split_accepts_only_the_original_readme(self):
        (self.root / "adr" / "README.md").write_bytes(REFERENCE.replace(b"ADR-001 to ADR-014", b"ADR-001 to ADR-013"))
        with self.assertRaisesRegex(adr.LayoutError, "split accepts only the original"):
            adr.split(self.root)
        self.assertFalse((self.root / "adr" / "ADR-001.md").exists())

    def test_split_requires_a_verified_reference(self):
        (self.root / "adr" / "presplit-reference.md").write_bytes(REFERENCE + b"\n")
        with self.assertRaisesRegex(adr.LayoutError, "SHA-256"):
            adr.split(self.root)
        (self.root / "adr" / "presplit-reference.md").unlink()
        with self.assertRaisesRegex(adr.LayoutError, "split requires"):
            adr.split(self.root)

    def test_split_through_the_cli(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(adr.main(["split", "--root", str(self.root)]), 0)
        self.assertIn("Split complete: 14 legacy records", out.getvalue())
        with contextlib.redirect_stdout(out):
            self.assertEqual(adr.main(["check", "--root", str(self.root)]), 0)


class GeneratedReadmeTests(ScratchCase):
    def test_hand_edited_generated_slot_fails(self):
        self.edit("README.md", "| Date | 2026-09-01 |\n| Supersedes | — |\n| Superseded by | — |\n<!-- SLOT END ADR-001 -->",
                  "| Date | 2026-09-02 |\n| Supersedes | — |\n| Superseded by | — |\n<!-- SLOT END ADR-001 -->")
        self.assert_fails("does not match the rendered layout: generated slot ADR-001 differs")

    def test_hand_edited_pending_row_fails(self):
        self.edit("README.md", "| State | PENDING |\n| Question the record must settle | Money wire",
                  "| State | ACCEPTED |\n| Question the record must settle | Money wire")
        self.assert_fails("generated slot ADR-015 differs")

    def test_hand_edited_prose_fails(self):
        self.edit("README.md", "Short, durable records", "Short durable records")
        self.assert_fails("text outside the generated slots differs")

    def test_deleted_slot_and_crlf_and_missing_readme_fail(self):
        original = self.read("README.md")
        self.write("README.md", original.replace(b"\n", b"\r\n"))
        self.assert_fails("CR bytes are present")
        self.write("README.md", original[:original.index(b"<!-- SLOT START ADR-016 -->")] + original[original.index(b"<!-- SLOT START ADR-017 -->"):])
        self.assert_fails("generated slot ADR-016 differs")
        (self.adr / "README.md").unlink()
        self.assert_fails("README.md is missing")

    def test_check_does_not_write(self):
        self.edit("README.md", "Short, durable records", "Short durable records")
        before = self.read("README.md")
        self.assert_fails("outside the generated slots")
        self.assertEqual(self.read("README.md"), before)


class OwnershipTests(ScratchCase):
    def test_wrong_owner_ticket_claim_fails(self):
        self.write("ADR-015.md", source(ticket=CAT))
        self.assert_fails(r"ADR-015\.md: ticket T-ADR-CAT-02 does not own ADR-015, which is allocated to T-ADR-MONEY-01")

    def test_published_record_without_allocation_fails(self):
        self.write("ADR-024.md", source(number="ADR-024", ticket="T-ADR-NEW-13"))
        self.assert_fails(r"ADR-024\.md: ADR-024 has no allocation")

    def test_new_record_without_ticket_fails(self):
        self.write("ADR-015.md", source(ticket=None))
        self.assert_fails(r"ADR-015\.md: new records must claim their allocation with ticket: T-ADR-MONEY-01")

    def test_legacy_record_must_not_acquire_ticket_data(self):
        self.edit("ADR-001.md", "number: ADR-001\n", "number: ADR-001\nticket: T-ADR-MONEY-01\n")
        self.assert_fails(r"ADR-001\.md: legacy records must not acquire ticket data")

    def test_reviewed_addition_above_023_is_accepted(self):
        reservations = json.loads(self.read("reservations.json"))
        reservations["items"].append({
            "number": "ADR-024", "ticket": "T-ADR-NEW-13", "state": "PENDING",
            "question": "Sample question", "blocks": "Sample dependents",
        })
        self.write("reservations.json", json.dumps(reservations, indent=2) + "\n")
        self.assert_fails("generated slot ADR-024 differs")
        self.assertTrue(adr.render(self.root))
        rows = slot_rows(self.readme(), "ADR-024")
        self.assertEqual(rows[0]["Source"], "reserved for `T-ADR-NEW-13`")
        self.assertEqual(rows[1]["State"], "PENDING")
        self.assertEqual(adr.check_layout(self.root)["allocations"], 10)
        self.write("ADR-024.md", source(number="ADR-024", ticket="T-ADR-NEW-13", title="Sample"))
        self.assertTrue(adr.render(self.root, "T-ADR-NEW-13"))
        self.assertEqual(adr.check_layout(self.root)["published"], 1)


class ReservationFileTests(ScratchCase):
    def test_duplicate_json_key_fails(self):
        self.edit("reservations.json", '"schema_version": 1,', '"schema_version": 1,\n  "schema_version": 1,')
        self.assert_fails("reservations.json: duplicate JSON key 'schema_version'")

    def test_duplicate_item_key_fails(self):
        self.edit("reservations.json", '"state": "PENDING",\n      "question": "Money', '"state": "PENDING",\n      "state": "PENDING",\n      "question": "Money')
        self.assert_fails("duplicate JSON key 'state'")

    def test_schema_version_must_be_the_integer_one(self):
        original = self.read("reservations.json")
        for value in (b"true", b'"1"', b"2", b"1.0"):
            with self.subTest(value=value):
                self.write("reservations.json", original.replace(b'"schema_version": 1,', b'"schema_version": ' + value + b","))
                self.assert_fails("schema_version must be the integer 1")

    def test_unknown_or_missing_item_fields_fail(self):
        self.edit("reservations.json", '"blocks": "Contracts, generated clients, every financial write path"',
                  '"blocks": "Contracts, generated clients, every financial write path", "owner": "x"')
        self.assert_fails("each item declares exactly number, ticket, state, question, blocks")

    def test_duplicate_number_fails(self):
        self.edit("reservations.json", '"number": "ADR-016"', '"number": "ADR-015"')
        self.assert_fails("duplicate number ADR-015")

    def test_state_must_remain_pending(self):
        self.edit("reservations.json", '"number": "ADR-015",\n      "ticket": "T-ADR-MONEY-01",\n      "state": "PENDING"',
                  '"number": "ADR-015",\n      "ticket": "T-ADR-MONEY-01",\n      "state": "ACCEPTED"')
        self.assert_fails("ADR-015 state must remain PENDING; effective state is derived")

    def test_original_allocation_cannot_be_removed(self):
        reservations = json.loads(self.read("reservations.json"))
        reservations["items"] = [item for item in reservations["items"] if item["number"] != "ADR-019"]
        self.write("reservations.json", json.dumps(reservations, indent=2) + "\n")
        self.assert_fails(r"original allocation ADR-019 \(T-ADR-AUTH-05\) was removed")

    def test_original_allocation_cannot_be_reassigned_or_changed(self):
        self.edit("reservations.json", '"ticket": "T-ADR-CAT-02"', '"ticket": "T-ADR-CAT-99"')
        self.assert_fails("original allocation ADR-016 was changed or reassigned")
        self.write("reservations.json", Baseline.read("reservations.json"))
        self.edit("reservations.json", "Category model: append-only", "Category model: mutable")
        self.assert_fails("original allocation ADR-016 was changed or reassigned")

    def test_legacy_number_cannot_be_allocated(self):
        reservations = json.loads(self.read("reservations.json"))
        reservations["items"].append({
            "number": "ADR-010", "ticket": "T-ADR-NEW-13", "state": "PENDING", "question": "q", "blocks": "b",
        })
        self.write("reservations.json", json.dumps(reservations, indent=2) + "\n")
        self.assert_fails("ADR-010 cannot be allocated; reviewed additions use numbers above ADR-023")

    def test_ticket_cannot_be_allocated_twice(self):
        reservations = json.loads(self.read("reservations.json"))
        reservations["items"].append({
            "number": "ADR-024", "ticket": MONEY, "state": "PENDING", "question": "q", "blocks": "b",
        })
        self.write("reservations.json", json.dumps(reservations, indent=2) + "\n")
        self.assert_fails("ticket T-ADR-MONEY-01 is allocated twice")

    def test_non_printable_and_marker_text_in_cells_is_rejected(self):
        original = self.read("reservations.json")
        cases = {
            "\r": "U\\+000D", "\t": "U\\+0009", "\x00": "U\\+0000", "\x1b": "U\\+001B",
            "\u2028": "U\\+2028", "\u202e": "U\\+202E", "\xa0": "U\\+00A0",
        }
        for character, code in cases.items():
            for key in ("question", "blocks"):
                with self.subTest(character=code, key=key):
                    reservations = json.loads(original)
                    item = dict(reservations["items"][-1])
                    item[key] = item[key][:5] + character + item[key][5:]
                    item["number"], item["ticket"] = "ADR-024", "T-ADR-NEW-13"
                    reservations["items"].append(item)
                    self.write("reservations.json", json.dumps(reservations, indent=2) + "\n")
                    self.assert_fails(f"ADR-024 {key} contains the non-printable character {code}")
                    self.assert_fails("non-printable", lambda root: adr.render(root))
        for forged in ("<!-- SLOT END ADR-024 -->", "x --> y"):
            with self.subTest(forged=forged):
                reservations = json.loads(original)
                reservations["items"].append({
                    "number": "ADR-024", "ticket": "T-ADR-NEW-13", "state": "PENDING",
                    "question": forged, "blocks": "b",
                })
                self.write("reservations.json", json.dumps(reservations, indent=2) + "\n")
                self.assert_fails("ADR-024 question must not contain HTML comment delimiters")
        self.write("reservations.json", original)
        self.assertEqual(adr.check_layout(self.root)["allocations"], 9)

    def test_invalid_json_and_missing_file_fail(self):
        self.write("reservations.json", "{")
        self.assert_fails("reservations.json: invalid JSON")
        (self.adr / "reservations.json").unlink()
        self.assert_fails("reservations.json is missing")


class LegacyManifestTests(ScratchCase):
    def test_duplicate_json_key_fails(self):
        self.edit("legacy-bodies.json", '"bytes": 848', '"bytes": 848, "bytes": 848')
        self.assert_fails("legacy-bodies.json: duplicate JSON key 'bytes'")

    def test_hash_drift_fails(self):
        self.edit("legacy-bodies.json", "56e532e3", "56e532e4")
        self.assert_fails("entry ADR-001 does not match the body derived from the pinned reference")

    def test_length_drift_fails(self):
        self.edit("legacy-bodies.json", '"bytes": 848', '"bytes": 847')
        self.assert_fails("entry ADR-001 does not match")

    def test_manifest_must_stay_byte_exact(self):
        self.write("legacy-bodies.json", json.dumps(json.loads(self.read("legacy-bodies.json")), indent=4) + "\n")
        self.assert_fails("historical inventory must stay byte-exact")

    def test_scalar_types_are_enforced(self):
        self.edit("legacy-bodies.json", '"bytes": 848', '"bytes": "848"')
        self.assert_fails("ADR-001 bytes must be an integer")


class LegacyBodyTests(ScratchCase):
    def test_legacy_body_drift_by_one_byte_fails(self):
        self.edit("ADR-001.md", "**Revisit if:** never, realistically.", "**Revisit if:** never, realistically!")
        self.assert_fails(r"ADR-001\.md: legacy body differs from the pinned pre-split reference")

    def test_missing_final_lf_fails(self):
        self.write("ADR-001.md", self.read("ADR-001.md")[:-1])
        self.assert_fails(r"ADR-001\.md: body must end with exactly one LF \(final LF missing\)")

    def test_extra_final_lf_fails(self):
        self.write("ADR-001.md", self.read("ADR-001.md") + b"\n")
        self.assert_fails(r"ADR-001\.md: body must end with exactly one LF \(extra final LF\)")

    def test_frozen_header_fields(self):
        self.edit("ADR-001.md", "2026-09-01", "2026-09-02", count=2)
        self.assert_fails(r"ADR-001\.md: legacy date is frozen as '2026-09-01'")

    def test_legacy_relationship_fields_stay_null(self):
        self.edit("ADR-004.md", "superseded-by: null", "superseded-by: ADR-018")
        self.assert_fails(r"ADR-004\.md: legacy relationship fields are frozen as null")

    def test_legacy_header_order_is_frozen(self):
        self.edit("ADR-002.md", "status: ACCEPTED\ndate: 2026-09-01\n", "date: 2026-09-01\nstatus: ACCEPTED\n")
        self.assert_fails(r"ADR-002\.md: legacy header differs from the frozen migration header")

    def test_missing_legacy_source_fails(self):
        (self.adr / "ADR-007.md").unlink()
        self.assert_fails(r"missing legacy source adr/ADR-007\.md")

    def test_legacy_set_is_complete_in_the_committed_tree(self):
        self.assertEqual(sorted(adr.validate_sources(ROOT).legacy), [f"ADR-{i:03d}" for i in range(1, 15)])


class SourceFormatTests(ScratchCase):
    def fails(self, pattern, **kwargs):
        self.write(f"{kwargs.get('number', 'ADR-015')}.md", source(**kwargs))
        self.assert_fails(pattern, adr.validate_sources)

    def test_malformed_dates_fail(self):
        self.fails("date '2026-02-30' is not a valid calendar date", date="2026-02-30")
        self.fails("date '2026-9-1' is not a canonical YYYY-MM-DD date", date="2026-9-1")
        self.fails("is not a canonical", date="2026/09/01")
        self.fails("is not a canonical", date="20261001")

    def test_status_and_date_must_match_between_header_and_body(self):
        self.fails("body records ACCEPTED · 2026-10-02 but the header records ACCEPTED · 2026-10-01", body_date="2026-10-02")
        self.fails("body records PENDING · 2026-10-01 but the header records ACCEPTED · 2026-10-01", body_status="PENDING")

    def test_unknown_status_fails(self):
        self.fails("status must be one of PENDING, ACCEPTED, SUPERSEDED, not 'PROPOSED'", status="PROPOSED")

    def test_duplicate_unknown_and_missing_header_fields_fail(self):
        self.fails("duplicate header field 'date'", extra_header=("date: 2026-10-01",))
        self.fails("unknown header field 'author'", extra_header=("author: someone",))
        text = source().replace("supersedes: null\n", "")
        self.write("ADR-015.md", text)
        self.assert_fails(r"missing header field\(s\) supersedes", adr.validate_sources)

    def test_malformed_header_lines_fail(self):
        self.write("ADR-015.md", source().replace("status: ACCEPTED", "status:ACCEPTED"))
        self.assert_fails("malformed header line 'status:ACCEPTED'", adr.validate_sources)
        self.write("ADR-015.md", source().replace("---\nnumber", "---\n\nnumber"))
        self.assert_fails("malformed header line ''", adr.validate_sources)
        self.write("ADR-015.md", "number: ADR-015\n" + source())
        self.assert_fails("header must start with a --- line", adr.validate_sources)
        self.write("ADR-015.md", source().replace("superseded-by: null\n---\n", "superseded-by: null\n"))
        self.assert_fails("header is not closed", adr.validate_sources)

    def test_malformed_references_and_tickets_fail(self):
        self.fails("supersedes must be null or an ADR-### reference, not 'ADR-4'", supersedes="ADR-4")
        self.fails("superseded-by must be null or an ADR-### reference, not ''", superseded_by="")
        self.fails("ticket 'money-01' is malformed", ticket="money-01")

    def test_non_printable_title_is_rejected(self):
        for character, code in (("\t", "U\\+0009"), ("\u202e", "U\\+202E"), ("\u2028", "U\\+2028"), ("\x1b", "U\\+001B")):
            with self.subTest(character=code):
                self.fails(f"ADR-015\\.md: title contains the non-printable character {code}", title=f"Money{character}wire")
        self.fails("title must not contain HTML comment delimiters", title="Money <!-- SLOT END ADR-015 --> wire")
        self.fails("title must be a non-empty trimmed string", title="Money ")

    def test_symlinked_source_is_rejected(self):
        self.write("ADR-015.md", source())
        real = Path.is_symlink
        with mock.patch.object(Path, "is_symlink", lambda path: path.name == "ADR-015.md" or real(path)):
            self.assert_fails(r"adr/ADR-015\.md: sources must be regular files, not symbolic links", adr.validate_sources)
        adr.validate_sources(self.root)

    def test_real_symbolic_link_source_is_rejected(self):
        self.write("ADR-015.md", source())
        target = self.adr / "ADR-015.md"
        link = self.adr / "ADR-016.md"
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"symbolic links are not available here: {error}")
        self.assertTrue(link.is_file(), "is_file() follows the link, which is why is_symlink() is checked first")
        self.assert_fails(r"adr/ADR-016\.md: sources must be regular files, not symbolic links", adr.validate_sources)
        link.unlink()
        os.symlink(target, self.adr / "ADR-015.md.lnk")
        self.assert_fails(r"adr/ADR-015\.md\.lnk: sources must be regular files, not symbolic links", adr.validate_sources)

    def test_body_heading_rules(self):
        self.write("ADR-015.md", source().replace("## ADR-015 — Money", "## ADR-015 - Money"))
        self.assert_fails("body must start with the heading", adr.validate_sources)
        self.write("ADR-015.md", source(title="Money").replace("title: Money\n", "title: Cash\n"))
        self.assert_fails("body must start with the heading '## ADR-015 — Cash'", adr.validate_sources)
        self.fails("exactly one ## ADR-### — Title heading", tail="\n## ADR-015 — Again\n")
        self.fails("exactly one \\*\\*Status:\\*\\* line", tail="\n**Status:** ACCEPTED · 2026-10-01\n")
        self.write("ADR-015.md", source().replace("**Status:** ACCEPTED · 2026-10-01", "**Status:** ACCEPTED 2026-10-01"))
        self.assert_fails("malformed status line", adr.validate_sources)

    def test_historical_annotation_after_the_date_is_accepted(self):
        self.write("ADR-015.md", source().replace("· 2026-10-01\n", "· 2026-10-01 *(founder decision)*\n"))
        self.assertEqual(adr.validate_sources(self.root).sources["ADR-015"].date, "2026-10-01")

    def test_final_lf_rules_for_new_records(self):
        self.fails(r"final LF missing", tail="\n**Decision.** Sample.")
        self.fails(r"extra final LF", tail="\n**Decision.** Sample.\n\n")

    def test_encoding_rules(self):
        self.write("ADR-015.md", b"\xef\xbb\xbf" + source().encode("utf-8"))
        self.assert_fails("UTF-8 BOM is not allowed", adr.validate_sources)
        self.write("ADR-015.md", source().replace("\n", "\r\n"))
        self.assert_fails("CR bytes found", adr.validate_sources)
        self.write("ADR-015.md", source().encode("utf-8")[:-3] + b"\xff\n")
        self.assert_fails("invalid UTF-8", adr.validate_sources)

    def test_file_name_rules(self):
        self.write("ADR-15.md", source())
        self.assert_fails(r"adr/ADR-15\.md: sources are files named exactly ADR-###\.md", adr.validate_sources)
        (self.adr / "ADR-15.md").unlink()
        self.write("ADR-016.md", source())
        self.assert_fails(r"ADR-016\.md: header number 'ADR-015' must match the file name", adr.validate_sources)
        (self.adr / "ADR-016.md").unlink()
        (self.adr / "ADR-017.md").mkdir()
        self.assert_fails(r"adr/ADR-017\.md: sources are files", adr.validate_sources)


class ReplacementTests(ScratchCase):
    def publish(self, number, ticket, **kwargs):
        self.write(f"{number}.md", source(number=number, ticket=ticket, title=f"Sample {number}", **kwargs))

    def test_valid_supersession_derives_predecessor_state_without_editing_it(self):
        legacy = self.read("ADR-004.md")
        self.publish("ADR-018", CRYPTO, supersedes="ADR-004")
        self.assertTrue(adr.render(self.root))
        self.assertEqual(self.read("ADR-004.md"), legacy)
        readme = self.readme()
        predecessor = slot_rows(readme, "ADR-004")[0]
        self.assertEqual((predecessor["Status"], predecessor["Superseded by"]), ("SUPERSEDED", "ADR-018"))
        successor = slot_rows(readme, "ADR-018")
        self.assertEqual((successor[0]["Status"], successor[0]["Supersedes"], successor[0]["Superseded by"]), ("ACCEPTED", "ADR-004", "—"))
        self.assertEqual(successor[1]["State"], "ACCEPTED")
        self.assertEqual(adr.check_layout(self.root)["superseded"], 1)

    def test_chain_marks_every_replaced_member_superseded(self):
        self.publish("ADR-015", MONEY, supersedes="ADR-004")
        self.publish("ADR-016", CAT, supersedes="ADR-015", superseded_by="null")
        adr.render(self.root)
        readme = self.readme()
        self.assertEqual(slot_rows(readme, "ADR-004")[0]["Superseded by"], "ADR-015")
        self.assertEqual(slot_rows(readme, "ADR-015")[0]["Status"], "SUPERSEDED")
        self.assertEqual(slot_rows(readme, "ADR-015")[1]["State"], "SUPERSEDED")
        self.assertEqual(slot_rows(readme, "ADR-016")[0]["Status"], "ACCEPTED")
        self.assertEqual(slot_rows(readme, "ADR-016")[1]["State"], "ACCEPTED")
        # Recorded metadata stays as written; only the effective view changes.
        self.assertEqual(adr.validate_sources(self.root).sources["ADR-015"].status, "ACCEPTED")

    def test_explicit_superseded_by_must_agree_with_a_forward_claim(self):
        self.publish("ADR-015", MONEY, superseded_by="ADR-016")
        self.assert_fails(r"ADR-015\.md: superseded-by ADR-016 does not agree with a successor's forward claim", adr.validate_sources)
        self.publish("ADR-016", CAT, supersedes="ADR-015")
        self.assertEqual(adr.validate_sources(self.root).successors, {"ADR-015": "ADR-016"})

    def test_recorded_superseded_requires_a_valid_successor(self):
        self.publish("ADR-015", MONEY, status="SUPERSEDED")
        self.assert_fails(r"ADR-015\.md: recorded SUPERSEDED without a valid successor", adr.validate_sources)
        self.publish("ADR-016", CAT, supersedes="ADR-015")
        self.assertEqual(adr.validate_sources(self.root).effective_status("ADR-015"), "SUPERSEDED")

    def test_self_link_dangling_link_and_pending_replacements_fail(self):
        self.publish("ADR-015", MONEY, supersedes="ADR-015")
        self.assert_fails("cannot supersede itself", adr.validate_sources)
        self.publish("ADR-015", MONEY, supersedes="ADR-099")
        self.assert_fails("supersedes ADR-099, which has no source record", adr.validate_sources)
        self.publish("ADR-015", MONEY, supersedes="ADR-016")
        self.assert_fails("supersedes ADR-016, which has no source record", adr.validate_sources)
        self.publish("ADR-015", MONEY, status="PENDING", supersedes="ADR-004")
        self.assert_fails(r"ADR-015\.md: a PENDING record cannot supersede ADR-004", adr.validate_sources)
        self.publish("ADR-015", MONEY, status="PENDING")
        self.publish("ADR-016", CAT, supersedes="ADR-015")
        self.assert_fails(r"ADR-016\.md: supersedes ADR-015, which is not a decided record", adr.validate_sources)

    def test_competing_successors_fail(self):
        self.publish("ADR-015", MONEY, supersedes="ADR-004")
        self.publish("ADR-016", CAT, supersedes="ADR-004")
        self.assert_fails(r"adr/ADR-004\.md has competing successors ADR-015 and ADR-016", adr.validate_sources)

    def test_cycle_fails(self):
        self.publish("ADR-015", MONEY, supersedes="ADR-016")
        self.publish("ADR-016", CAT, supersedes="ADR-015")
        self.assert_fails("replacement cycle through", adr.validate_sources)


class ScopedRenderTests(ScratchCase):
    def test_accepted_record_updates_exactly_its_slots_and_pending_row(self):
        self.write("ADR-015.md", source())
        self.assert_fails("generated slot ADR-015 differs")
        self.assertTrue(adr.render(self.root, MONEY))
        before, after = Baseline.readme(), self.readme()
        self.assertNotEqual(before, after)
        self.assertEqual(adr.mask_slots(before, {"ADR-015"}), adr.mask_slots(after, {"ADR-015"}))
        index, pending = slot_rows(after, "ADR-015")
        self.assertEqual(index, {
            "Source": '<a id="adr-015--money-wire-format-time-and-idempotency"></a> [ADR-015.md](ADR-015.md)',
            "Status": "ACCEPTED", "Ticket": MONEY, "Date": "2026-10-01", "Supersedes": "—", "Superseded by": "—",
        })
        self.assertEqual(pending["State"], "ACCEPTED")
        self.assertEqual(pending["Ticket"], f"`{MONEY}`")
        self.assertEqual(adr.check_layout(self.root)["published"], 1)

    def test_render_is_deterministic(self):
        self.write("ADR-015.md", source())
        self.assertTrue(adr.render(self.root, MONEY))
        first = self.read("README.md")
        self.assertFalse(adr.render(self.root, MONEY))
        self.assertFalse(adr.render(self.root))
        self.assertEqual(self.read("README.md"), first)
        layout = adr.validate_sources(self.root)
        self.assertEqual(adr.render_readme(layout), adr.render_readme(adr.validate_sources(self.root)))

    def test_pending_draft_coexists_with_its_reservation(self):
        self.write("ADR-015.md", source(status="PENDING"))
        self.assertTrue(adr.render(self.root, MONEY))
        index, pending = slot_rows(self.readme(), "ADR-015")
        self.assertEqual(index["Source"], '<a id="adr-015--money-wire-format-time-and-idempotency"></a> [ADR-015.md](ADR-015.md)')
        self.assertEqual((index["Status"], index["Date"], index["Ticket"]), ("PENDING", "2026-10-01", MONEY))
        self.assertEqual(pending["State"], "PENDING")
        summary = adr.check_layout(self.root)
        self.assertEqual((summary["published"], summary["pending"]), (1, 9))
        self.assertEqual(json.loads(self.read("reservations.json")), json.loads(Baseline.read("reservations.json")))

    def test_scoped_render_refuses_to_alter_another_tickets_slots(self):
        self.write("ADR-015.md", source())
        before = self.read("README.md")
        self.assert_fails("outside the slots owned by T-ADR-CAT-02: generated slot ADR-015 differs", lambda root: adr.render(root, CAT))
        self.assertEqual(self.read("README.md"), before)

    def test_scoped_render_refuses_unrelated_drift(self):
        self.write("ADR-015.md", source())
        self.edit("README.md", "Short, durable records", "Short durable records")
        before = self.read("README.md")
        self.assert_fails("outside the slots owned by T-ADR-MONEY-01: text outside the generated slots", lambda root: adr.render(root, MONEY))
        self.assertEqual(self.read("README.md"), before)
        self.write("README.md", Baseline.read("README.md"))
        self.edit("README.md", "| Ticket | T-ADR-CAT-02 |\n| Date | — |", "| Ticket | T-ADR-CAT-02 |\n| Date | 2026-10-01 |")
        self.assert_fails("generated slot ADR-016 differs", lambda root: adr.render(root, MONEY))

    def test_scoped_render_requires_the_existing_projection(self):
        self.write("ADR-015.md", source())
        (self.adr / "README.md").unlink()
        self.assert_fails("README.md is missing; a ticket-scoped render never recreates", lambda root: adr.render(root, MONEY))
        self.write("README.md", Baseline.read("README.md").replace(b"<!-- SLOT START ADR-015 -->", b"<!-- SLOT BEGIN ADR-015 -->"))
        self.assert_fails("has no generated slot for ADR-015", lambda root: adr.render(root, MONEY))
        self.assertTrue(adr.render(self.root))
        self.assertEqual(adr.check_layout(self.root)["published"], 1)

    def test_unknown_or_malformed_ticket_fails(self):
        self.assert_fails("ticket T-ADR-NOPE-99 owns no allocation", lambda root: adr.render(root, "T-ADR-NOPE-99"))
        self.assert_fails("ticket 'money' is malformed", lambda root: adr.render(root, "money"))

    def test_scoped_supersession_updates_derived_predecessor_slots(self):
        self.write("ADR-018.md", source(number="ADR-018", ticket=CRYPTO, title="Sample", supersedes="ADR-004"))
        self.assertTrue(adr.render(self.root, CRYPTO))
        after = self.readme()
        self.assertEqual(adr.mask_slots(Baseline.readme(), {"ADR-018", "ADR-004"}), adr.mask_slots(after, {"ADR-018", "ADR-004"}))
        self.assertEqual(slot_rows(after, "ADR-004")[0]["Superseded by"], "ADR-018")
        # Another ticket may not carry that predecessor change.
        self.write("ADR-004.md", Baseline.read("ADR-004.md"))
        self.write("README.md", Baseline.read("README.md"))
        self.assert_fails("outside the slots owned by T-ADR-MONEY-01: generated slot ADR-004", lambda root: adr.render(root, MONEY))

    def test_retargeting_restores_the_previous_predecessor(self):
        self.write("ADR-018.md", source(number="ADR-018", ticket=CRYPTO, title="Sample", supersedes="ADR-004"))
        adr.render(self.root, CRYPTO)
        original_004 = adr.collect_slots(Baseline.readme())["ADR-004"]
        # Retargeting an uncommitted supersession edits a record this branch already registered on
        # the same date: the base registry is restored first (adr/LAYOUT.md, before-merge workflow).
        self.write("ADR-018.md", source(number="ADR-018", ticket=CRYPTO, title="Sample", supersedes="ADR-005"))
        self.assert_fails(r"ADR-018\.md: accepted record edited without a date change", lambda root: adr.render(root, CRYPTO))
        self.write("accepted-records.json", Baseline.read("accepted-records.json"))
        self.assertTrue(adr.render(self.root, CRYPTO))
        after = self.readme()
        self.assertEqual(adr.collect_slots(after)["ADR-004"], original_004)
        self.assertEqual(slot_rows(after, "ADR-005")[0]["Status"], "SUPERSEDED")
        self.assertEqual(slot_rows(after, "ADR-018")[0]["Supersedes"], "ADR-005")
        self.write("ADR-018.md", source(number="ADR-018", ticket=CRYPTO, title="Sample"))
        self.write("accepted-records.json", Baseline.read("accepted-records.json"))
        self.assertTrue(adr.render(self.root, CRYPTO))
        self.assertEqual(adr.mask_slots(Baseline.readme(), {"ADR-018"}), adr.mask_slots(self.readme(), {"ADR-018"}))
        adr.check_layout(self.root)

    def test_inconsistent_prior_projection_is_rejected(self):
        self.write("ADR-018.md", source(number="ADR-018", ticket=CRYPTO, title="Sample", supersedes="ADR-004"))
        adr.render(self.root, CRYPTO)
        # Forward link without the derived reverse link: someone hand-edited the predecessor slot.
        self.edit("README.md", "| Status | SUPERSEDED |\n| Ticket | — |\n| Date | 2026-09-01 |\n| Supersedes | — |\n| Superseded by | ADR-018 |",
                  "| Status | ACCEPTED |\n| Ticket | — |\n| Date | 2026-09-01 |\n| Supersedes | — |\n| Superseded by | — |")
        self.assert_fails("prior projection is inconsistent; ADR-018 claims to supersede ADR-004", lambda root: adr.render(root, CRYPTO))
        # Reverse link without the forward claim.
        self.write("README.md", Baseline.read("README.md"))
        self.edit("README.md", "| Date | 2026-09-01 |\n| Supersedes | — |\n| Superseded by | — |\n<!-- SLOT END ADR-004 -->",
                  "| Date | 2026-09-01 |\n| Supersedes | — |\n| Superseded by | ADR-018 |\n<!-- SLOT END ADR-004 -->")
        self.assert_fails("prior projection is inconsistent; ADR-004 is marked as superseded by a record of T-ADR-CRYPTO-04", lambda root: adr.render(root, CRYPTO))

    def test_effective_state_is_never_written_back(self):
        self.write("ADR-015.md", source())
        adr.render(self.root, MONEY)
        self.assertEqual(self.read("reservations.json"), Baseline.read("reservations.json"))
        self.assertEqual(self.read("legacy-bodies.json"), Baseline.read("legacy-bodies.json"))
        self.assertEqual(self.read("ADR-015.md"), source().encode("utf-8"))


class RegistryTests(ScratchCase):
    """adr/accepted-records.json (E26-F16): decided records are pinned by date and bytes; an undated
    edit, a withdrawal or a stale entry fails ``check`` naming the record, and ``render`` refuses to
    launder any of them. Compliant records pass unchanged."""

    def registry(self):
        return {item["number"]: item for item in json.loads(self.read("accepted-records.json"))["items"]}

    def entry(self, number="ADR-015"):
        data = self.read(f"{number}.md")
        text = data.decode("utf-8")
        date = dict(line.split(": ", 1) for line in text[4:text.index("\n---\n")].split("\n"))["date"]
        return {"number": number, "date": date, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}

    def publish_and_register(self, **kwargs):
        self.write("ADR-015.md", source(**kwargs))
        self.assertEqual(adr.render(self.root, MONEY), ["adr/README.md", "adr/accepted-records.json"])
        self.assertEqual(adr.check_layout(self.root)["published"], 1)

    def assert_render_refuses(self, pattern, ticket=MONEY):
        before = {name: self.read(name) for name in ("README.md", "accepted-records.json")}
        for scope in (ticket, None):
            with self.subTest(scope=scope):
                self.assert_fails(pattern, lambda root, scope=scope: adr.render(root, scope))
        for name, data in before.items():
            self.assertEqual(self.read(name), data, f"{name} must not change when render refuses")
        self.assertEqual([p.name for p in self.adr.glob(".*.tmp")], [])

    def test_baseline_registry_holds_one_null_entry_per_allocation(self):
        registry = self.registry()
        self.assertEqual(list(registry), [f"ADR-{index:03d}" for index in range(15, 24)])
        for number, item in registry.items():
            self.assertEqual(item, {"number": number, "date": None, "sha256": None, "bytes": None})
        self.assertEqual(self.read("accepted-records.json"), adr.render_registry(registry.values()).encode("utf-8"))

    def test_publishing_registers_the_decided_record(self):
        self.publish_and_register()
        self.assertEqual(self.registry()["ADR-015"], self.entry())
        self.assertEqual(self.registry()["ADR-016"], {"number": "ADR-016", "date": None, "sha256": None, "bytes": None})
        self.assertEqual(adr.render(self.root, MONEY), [])
        self.assertEqual(adr.render(self.root), [])

    def test_pending_draft_is_not_registered(self):
        self.write("ADR-015.md", source(status="PENDING"))
        self.assertEqual(adr.render(self.root, MONEY), ["adr/README.md"])
        self.assertEqual(self.read("accepted-records.json"), Baseline.read("accepted-records.json"))
        adr.check_layout(self.root)

    def test_unregistered_decided_record_fails_check_once_the_readme_matches(self):
        self.publish_and_register()
        self.write("accepted-records.json", Baseline.read("accepted-records.json"))
        self.assert_fails(
            r"adr/ADR-015\.md: decided record ADR-015 is not registered in adr/accepted-records\.json; its owner "
            r"registers it with render --ticket T-ADR-MONEY-01"
        )
        self.assertEqual(adr.render(self.root, MONEY), ["adr/accepted-records.json"])
        adr.check_layout(self.root)

    def test_missing_registry_fails_check_and_is_never_regenerated_over_decided_records(self):
        # Without decided records the registry never existed: an unscoped render creates the empty ledger.
        (self.adr / "accepted-records.json").unlink()
        self.assert_fails(r"adr/accepted-records\.json is missing; the layout owner creates it with an unscoped render")
        self.assert_fails(r"accepted-records\.json is missing; a ticket-scoped render never creates the registry",
                          lambda root: adr.render(root, MONEY))
        self.assertEqual(adr.render(self.root), ["adr/accepted-records.json"])
        self.assertEqual(self.read("accepted-records.json"), Baseline.read("accepted-records.json"))
        # With a decided record, a missing registry is restored from the reviewed commit, never rebuilt:
        # deleting the ledger and re-rendering would otherwise launder an undated edit.
        self.publish_and_register()
        (self.adr / "accepted-records.json").unlink()
        self.edit("ADR-015.md", "Sample text.", "Sample text, quietly changed.")
        self.assert_fails(r"adr/accepted-records\.json is missing; the layout owner creates it")
        self.assert_fails(
            r"adr/accepted-records\.json is missing while decided records exist \(ADR-015\); restore it from the "
            r"reviewed commit, it is never regenerated from the current sources",
            adr.render,
        )
        self.assert_fails(r"a ticket-scoped render never creates the registry", lambda root: adr.render(root, MONEY))
        self.assertFalse((self.adr / "accepted-records.json").exists())

    def test_undated_edit_of_a_registered_record_fails_check_and_render_refuses(self):
        self.publish_and_register()
        registered = self.entry()
        # A body edit that leaves the README untouched: only the registry can reveal it.
        self.edit("ADR-015.md", "Sample text.", "Sample text, quietly changed.")
        message = (
            r"adr/ADR-015\.md: accepted record edited without a date change \(registered 2026-10-01 as sha256 "
            + registered["sha256"][:12] + r"…, " + str(registered["bytes"]) + r" bytes; the current bytes differ\); "
            r"amend it with a later date or publish a superseding record"
        )
        self.assert_fails(message)
        self.assert_render_refuses(message)
        # A header edit that also moves README bytes: README drift is reported first, render still refuses.
        self.write("ADR-015.md", source(title="Money wire format, time, idempotency and more"))
        self.assert_fails("does not match the rendered layout: generated slot ADR-015 differs")
        self.assert_render_refuses(r"adr/ADR-015\.md: accepted record edited without a date change")
        self.write("ADR-015.md", source())
        adr.check_layout(self.root)

    def test_dated_amendment_re_registers_and_an_earlier_date_is_refused(self):
        self.publish_and_register()
        self.write("ADR-015.md", source(date="2026-10-02").replace("Sample text.", "Sample text, amended."))
        self.assert_fails("generated slot ADR-015 differs")
        self.assertEqual(adr.render(self.root, MONEY), ["adr/README.md", "adr/accepted-records.json"])
        self.assertEqual(self.registry()["ADR-015"], self.entry())
        self.assertEqual(self.registry()["ADR-015"]["date"], "2026-10-02")
        self.assertEqual(slot_rows(self.readme(), "ADR-015")[0]["Date"], "2026-10-02")
        adr.check_layout(self.root)
        # The amendment of a record whose README bytes do not move is named until it is re-registered.
        self.write("ADR-015.md", source(date="2026-10-02").replace("Sample text.", "Sample text, amended twice."))
        self.assert_fails(r"adr/ADR-015\.md: accepted record edited without a date change")
        self.write("ADR-015.md", source(date="2026-10-03").replace("Sample text.", "Sample text, amended twice."))
        self.assert_fails("generated slot ADR-015 differs")
        self.write("README.md", adr.render_readme(adr.validate_sources(self.root)))
        self.assert_fails(
            r"adr/ADR-015\.md: accepted record amended on 2026-10-03 \(registered 2026-10-02\); its owner "
            r"re-registers it with render --ticket T-ADR-MONEY-01"
        )
        self.assertEqual(adr.render(self.root, MONEY), ["adr/accepted-records.json"])
        adr.check_layout(self.root)
        self.write("ADR-015.md", source(date="2026-09-30"))
        self.assert_fails("generated slot ADR-015 differs")
        self.assert_render_refuses(r"adr/ADR-015\.md: re-dated 2026-09-30, earlier than its registered acceptance date 2026-10-03")

    def test_withdrawing_a_registered_record_fails(self):
        self.publish_and_register()
        self.write("ADR-015.md", source(status="PENDING"))
        self.assert_fails("generated slot ADR-015 differs")
        self.assert_render_refuses(
            r"adr/ADR-015\.md: registered as decided on 2026-10-01 but now records PENDING; a decided record is "
            r"superseded, never withdrawn \(restore it or review a preservation migration\)"
        )
        self.write("README.md", adr.render_readme(adr.validate_sources(self.root)))
        self.assert_fails(r"adr/ADR-015\.md: registered as decided on 2026-10-01 but now records PENDING")
        (self.adr / "ADR-015.md").unlink()
        self.write("README.md", adr.render_readme(adr.validate_sources(self.root)))
        self.assert_fails(r"adr/ADR-015\.md: registered as decided on 2026-10-01 but is missing; a decided record is superseded")
        self.assert_render_refuses(r"adr/ADR-015\.md: registered as decided on 2026-10-01 but is missing")

    def test_supersession_leaves_the_predecessor_entry_unchanged_and_a_predecessor_edit_needs_a_date(self):
        self.publish_and_register()
        predecessor = self.entry()
        self.write("ADR-016.md", source(number="ADR-016", ticket=CAT, title="Sample", supersedes="ADR-015"))
        self.assertEqual(adr.render(self.root, CAT), ["adr/README.md", "adr/accepted-records.json"])
        registry = self.registry()
        self.assertEqual(registry["ADR-015"], predecessor)
        self.assertEqual(registry["ADR-016"], self.entry("ADR-016"))
        summary = adr.check_layout(self.root)
        self.assertEqual((summary["published"], summary["superseded"]), (2, 1))
        # Recording the supersession on the predecessor is itself a change: dated, it re-registers.
        self.write("ADR-015.md", source(status="SUPERSEDED", superseded_by="ADR-016"))
        self.assert_render_refuses(r"adr/ADR-015\.md: accepted record edited without a date change")
        self.write("ADR-015.md", source(status="SUPERSEDED", superseded_by="ADR-016", date="2026-10-05"))
        self.assertEqual(adr.render(self.root, MONEY), ["adr/README.md", "adr/accepted-records.json"])
        self.assertEqual(self.registry()["ADR-015"]["date"], "2026-10-05")
        self.assertEqual(adr.check_layout(self.root)["superseded"], 1)

    def test_scoped_render_changes_only_its_own_entry_and_refuses_foreign_registry_drift(self):
        self.publish_and_register()
        self.write("ADR-016.md", source(number="ADR-016", ticket=CAT, title="Sample"))
        self.assertEqual(adr.render(self.root, CAT), ["adr/README.md", "adr/accepted-records.json"])
        adr.check_layout(self.root)
        # Unregister ADR-016 behind the owner's back; the README still matches, so the registry decides.
        registry = json.loads(self.read("accepted-records.json"))
        for item in registry["items"]:
            if item["number"] == "ADR-016":
                item.update(date=None, sha256=None, bytes=None)
        self.write("accepted-records.json", adr.render_registry(registry["items"]))
        self.assert_fails(r"adr/ADR-016\.md: decided record ADR-016 is not registered")
        self.assert_fails(
            r"adr/accepted-records\.json differs from the source records outside the entries owned by T-ADR-MONEY-01: "
            r"adr/ADR-016\.md: decided record ADR-016 is not registered .*; a ticket-scoped render refuses to alter "
            r"those bytes",
            lambda root: adr.render(root, MONEY),
        )
        self.assertEqual(adr.render(self.root, CAT), ["adr/accepted-records.json"])
        adr.check_layout(self.root)
        # An undated foreign edit is refused the same way and never laundered by another ticket.
        self.edit("ADR-016.md", "Sample text.", "Sample text, changed by someone else.")
        self.assert_fails(r"adr/ADR-016\.md: accepted record edited without a date change")
        self.assert_fails(r"outside the entries owned by T-ADR-MONEY-01: adr/ADR-016\.md: accepted record edited without",
                          lambda root: adr.render(root, MONEY))
        self.assert_fails(r"adr/ADR-016\.md: accepted record edited without a date change", lambda root: adr.render(root, CAT))
        self.assert_fails(r"adr/ADR-016\.md: accepted record edited without a date change", adr.render)

    def test_reviewed_allocation_addition_gets_a_null_entry_from_the_layout_owner(self):
        reservations = json.loads(self.read("reservations.json"))
        reservations["items"].append({
            "number": "ADR-024", "ticket": "T-ADR-NEW-13", "state": "PENDING", "question": "q", "blocks": "b",
        })
        self.write("reservations.json", json.dumps(reservations, indent=2) + "\n")
        self.assert_fails("generated slot ADR-024 differs")
        self.write("README.md", adr.render_readme(adr.validate_sources(self.root)))
        self.assert_fails(r"adr/accepted-records\.json has no entry for ADR-024; the layout owner adds it with an unscoped render")
        self.write("ADR-024.md", source(number="ADR-024", ticket="T-ADR-NEW-13", title="Sample"))
        self.write("README.md", Baseline.read("README.md"))
        self.assert_fails("has no generated slot for ADR-024", lambda root: adr.render(root, "T-ADR-NEW-13"))
        self.assertEqual(self.read("accepted-records.json"), Baseline.read("accepted-records.json"))
        (self.adr / "ADR-024.md").unlink()
        self.assertEqual(adr.render(self.root), ["adr/README.md", "adr/accepted-records.json"])
        self.assertEqual(self.registry()["ADR-024"], {"number": "ADR-024", "date": None, "sha256": None, "bytes": None})
        self.write("ADR-024.md", source(number="ADR-024", ticket="T-ADR-NEW-13", title="Sample"))
        self.assertEqual(adr.render(self.root, "T-ADR-NEW-13"), ["adr/README.md", "adr/accepted-records.json"])
        self.assertEqual(self.registry()["ADR-024"], self.entry("ADR-024"))
        self.assertEqual(adr.check_layout(self.root)["allocations"], 10)

    def test_registry_shape_rules(self):
        self.publish_and_register()
        good = self.read("accepted-records.json")
        cases = (
            (good.replace(b'"schema_version": 1,', b'"schema_version": 1,\n  "schema_version": 1,'), "duplicate JSON key 'schema_version'"),
            (good.replace(b'"schema_version": 1,', b'"schema_version": 2,'), "schema_version must be the integer 1"),
            (good.replace(b'"bytes": null\n    },\n    {\n      "number": "ADR-017"', b'"bytes": null, "x": 1\n    },\n    {\n      "number": "ADR-017"'),
             "each item declares exactly number, date, sha256, bytes"),
            (good.replace(b'"number": "ADR-016"', b'"number": "ADR-099"'), r"ADR-099 has no allocation; a registered decision is never dropped silently"),
            (good.replace(b'"number": "ADR-016"', b'"number": "ADR-017"'), "duplicate number ADR-017"),
            (good.replace(b'"date": null,\n      "sha256": null,\n      "bytes": null\n    },\n    {\n      "number": "ADR-017"',
                          b'"date": "2026-10-01",\n      "sha256": null,\n      "bytes": null\n    },\n    {\n      "number": "ADR-017"'),
             "ADR-016 must record date, sha256 and bytes together or all null"),
            (good.replace(b'"date": "2026-10-01"', b'"date": "2026-13-01"'), "ADR-015: date '2026-13-01' is not a valid calendar date"),
            (good.replace(b'"date": "2026-10-01"', b'"date": 20261001'), "ADR-015 date must be a string"),
            (good.replace(str(self.entry()["bytes"]).encode(), b'"' + str(self.entry()["bytes"]).encode() + b'"'), "ADR-015 bytes must be a positive integer"),
            (good.replace(str(self.entry()["bytes"]).encode(), b"0"), "ADR-015 bytes must be a positive integer"),
            (good.replace(self.entry()["sha256"].encode(), self.entry()["sha256"].upper().encode()), "ADR-015 sha256 must be 64 lowercase hex digits"),
            (json.dumps(json.loads(good), indent=4).encode() + b"\n", r"accepted-records\.json must stay byte-exact to its canonical rendering"),
            (good.replace(str(self.entry()["bytes"]).encode(), str(self.entry()["bytes"] + 1).encode()),
             r"accepted-records\.json: entry ADR-015 is inconsistent with the unchanged registered bytes"),
            (b"{", r"accepted-records\.json: invalid JSON"),
        )
        for data, pattern in cases:
            with self.subTest(pattern=pattern):
                self.assertNotEqual(data, good)
                self.write("accepted-records.json", data)
                self.assert_fails(pattern)
        # Entries out of allocation order are refused too.
        registry = json.loads(good)
        registry["items"].reverse()
        self.write("accepted-records.json", adr.render_registry(registry["items"]))
        self.assert_fails(r"accepted-records\.json: entries must follow allocation order")
        # A missing entry is added only by the layout owner; a corrupt file is never overwritten by render.
        registry = json.loads(good)
        registry["items"] = [item for item in registry["items"] if item["number"] != "ADR-016"]
        self.write("accepted-records.json", adr.render_registry(registry["items"]))
        self.assert_fails(r"accepted-records\.json has no entry for ADR-016; the layout owner adds it with an unscoped render")
        self.assert_fails(r"has no entry for ADR-016; the layout owner adds it", lambda root: adr.render(root, MONEY))
        self.assertEqual(adr.render(self.root), ["adr/accepted-records.json"])
        self.assertEqual(self.read("accepted-records.json"), good)
        self.write("accepted-records.json", b"{")
        self.assert_fails(r"accepted-records\.json: invalid JSON", adr.render)
        self.assertEqual(self.read("accepted-records.json"), b"{")

    def test_render_refuses_before_writing_anything(self):
        self.publish_and_register()
        self.write("ADR-016.md", source(number="ADR-016", ticket=CAT, title="Sample"))
        self.edit("ADR-015.md", "Sample text.", "Sample text, quietly changed.")
        # ADR-016 is legitimately publishable, yet the undated ADR-015 edit stops the whole render.
        self.assert_render_refuses(r"adr/ADR-015\.md: accepted record edited without a date change", ticket=CAT)

    def test_check_docs_reports_registry_failures(self):
        check_docs = load("check_docs")
        for name in ("planning", "product"):
            shutil.copytree(ROOT / name, self.root / name)
        (self.root / "scripts").mkdir()
        for path in SCRIPTS.glob("*.py"):
            shutil.copy(path, self.root / "scripts" / path.name)
        check_docs.ROOT = self.root
        self.publish_and_register()
        self.edit("ADR-015.md", "Sample text.", "Sample text, quietly changed.")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(check_docs.main(), 1)
        self.assertIn("Documentation check failed: adr/ADR-015.md: accepted record edited without a date change", err.getvalue())


class ProvingTestsTests(ScratchCase):
    """A decided record names its proving tests; drafts and the frozen legacy records are exempt."""

    def fails(self, pattern, **kwargs):
        self.write("ADR-015.md", source(**kwargs))
        self.assert_fails(pattern, adr.validate_sources)

    def test_decided_record_without_a_tests_heading_fails(self):
        pattern = (r"adr/ADR-015\.md: a decided record must name its proving tests under a heading containing "
                   r"the word 'tests' \(none found\)")
        self.fails(pattern, tail=DECISION)
        self.fails(pattern, tail=DECISION + "\n### 7. Verification\n\n`sample_test` proves it.\n")
        self.write("ADR-015.md", source(tail=DECISION))
        self.assert_fails(pattern)
        self.assert_fails(pattern, lambda root: adr.render(root, MONEY))

    def test_tests_heading_without_a_named_test_fails(self):
        self.fails(
            r"adr/ADR-015\.md: the tests section '### 1\. Tests implementation tickets must add' names no test "
            r"\(no backticked identifier\); a decided record names its proving tests",
            tail=DECISION + "\n### 1. Tests implementation tickets must add\n\nTests are added by the tickets.\n",
        )

    def test_pending_draft_may_lack_tests_but_a_recorded_supersession_may_not(self):
        self.write("ADR-015.md", source(status="PENDING", tail=DECISION))
        adr.validate_sources(self.root)
        self.write("ADR-015.md", source(status="SUPERSEDED", tail=DECISION))
        self.write("ADR-016.md", source(number="ADR-016", ticket=CAT, title="Sample", supersedes="ADR-015"))
        self.assert_fails(r"adr/ADR-015\.md: a decided record must name its proving tests", adr.validate_sources)
        self.write("ADR-015.md", source(status="SUPERSEDED"))
        self.assertEqual(adr.validate_sources(self.root).successors, {"ADR-015": "ADR-016"})

    def test_heading_variants_and_sub_sections_count(self):
        for heading in ("## Conformance tests", "#### 9.1 Test matrix", "### TESTS the tickets add", "### 7. Tests"):
            with self.subTest(heading=heading):
                self.write("ADR-015.md", source(tail=DECISION + f"\n{heading}\n\n`named_test` proves it.\n"))
                adr.validate_sources(self.root)
        # Names under a deeper sub-heading of the tests section count; the next same-level heading ends it.
        self.write("ADR-015.md", source(tail=DECISION + "\n### 7. Tests\n\nGrouped below.\n\n#### 7.1 Money\n\n`money_test`\n\n### 8. Rollout\n\nText.\n"))
        adr.validate_sources(self.root)
        self.fails(r"the tests section '### 7\. Tests' names no test",
                   tail=DECISION + "\n### 7. Tests\n\nGrouped below.\n\n### 8. Rollout\n\n`not_a_test_name`\n")

    def test_every_tests_heading_is_examined_not_only_the_first(self):
        """PR #158 core F1: an earlier prose section whose heading contains 'test' must not hide a
        later compliant tests section; when none names a test, every section examined is listed."""
        policy = "\n### 0. Test data policy\n\nSynthetic data only; no production records.\n"
        self.write("ADR-015.md", source(tail=DECISION + policy + TESTS_SECTION))
        adr.validate_sources(self.root)
        self.write("ADR-015.md", source(tail=DECISION + TESTS_SECTION + policy))
        adr.validate_sources(self.root)
        self.write("ADR-015.md", source(tail=DECISION + policy + "\n#### 0.1 Tests of the policy\n\n`policy_test`\n"))
        adr.validate_sources(self.root)
        self.fails(
            r"adr/ADR-015\.md: none of the tests sections '### 0\. Test data policy', "
            r"'### 1\. Tests implementation tickets must add' names a test \(no backticked identifier\); "
            r"a decided record names its proving tests",
            tail=DECISION + policy + "\n### 1. Tests implementation tickets must add\n\nTests are added by the tickets.\n",
        )
        self.fails(r"the tests section '### 0\. Test data policy' names no test", tail=DECISION + policy)

    def test_the_record_heading_and_fenced_code_do_not_count(self):
        self.fails(r"a decided record must name its proving tests", title="Testing strategy", tail=DECISION)
        self.fails(r"a decided record must name its proving tests",
                   tail=DECISION + "\n```text\n### Tests\n`inside_a_code_block`\n```\n")
        self.fails(r"the tests section '### 7\. Tests' names no test",
                   tail=DECISION + "\n### 7. Tests\n\n```text\n`only_inside_a_code_block`\n```\n")


class JsonBlockTests(ScratchCase):
    """Every fenced ```json block of a non-legacy record parses strictly, and a top-level object
    declares a version field; arrays, scalars and non-JSON fences are left alone."""

    def record(self, block, status="ACCEPTED", fence="```", info="json"):
        return source(status=status, tail=DECISION + f"\n{fence}{info}\n{block}\n{fence}\n" + TESTS_SECTION)

    def fails(self, pattern, block, **kwargs):
        self.write("ADR-015.md", self.record(block, **kwargs))
        self.assert_fails(pattern, adr.validate_sources)

    def passes(self, block, **kwargs):
        self.write("ADR-015.md", self.record(block, **kwargs))
        adr.validate_sources(self.root)

    def test_version_keys_that_satisfy_the_rule(self):
        for block in ('{"schema_version": 1}', '{"policy_version": "2026-09-30.6"}', '{"parameters_version": "1"}',
                      '{"version": 7}', '{"schema-version": 1}', '{"SCHEMA_VERSION": 2, "x": null}'):
            with self.subTest(block=block):
                self.passes(block)

    def test_arrays_scalars_and_non_json_fences_are_exempt_from_the_version_rule(self):
        self.passes('[{"relation": ["a"], "target": {"namespace": "android_app"}}]')
        self.passes('"just a string"')
        self.passes("42")
        self.passes("{not json at all", info="text")
        self.passes("{not json at all", info="json5")
        self.passes("{not json at all", info="jsonc")

    def test_invalid_json_and_duplicate_keys_fail_naming_the_record_block_and_line(self):
        record = self.record('{"schema_version": 1 "x": 2}')
        fence_line = record.split("\n").index("```json") + 1
        self.fails(
            r"adr/ADR-015\.md: fenced JSON block 1 \(line " + str(fence_line) + r"\): invalid JSON \(Expecting ',' delimiter",
            '{"schema_version": 1 "x": 2}',
        )
        self.fails(r"fenced JSON block 1 \(line \d+\): duplicate JSON key 'schema_version'", '{"schema_version": 1, "schema_version": 1}')
        self.fails(r"fenced JSON block 1 \(line \d+\): invalid JSON", "", status="PENDING")
        self.fails(r"fenced JSON block 1 \(line \d+\): invalid JSON", '{"schema_version": 1,}')

    def test_non_json_literals_and_lone_surrogates_are_rejected_everywhere(self):
        """PR #158 core F2 / security S1: RFC 8259 has no NaN, Infinity or -Infinity, and a lone
        surrogate escape decodes to text no UTF-8 consumer accepts; blocks and documents alike."""
        for literal in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(literal=literal):
                self.fails(r"fenced JSON block 1 \(line \d+\): non-JSON literal " + literal + "$",
                           '{"schema_version": 1, "x": ' + literal + "}")
                self.fails(r"fenced JSON block 1 \(line \d+\): non-JSON literal " + literal + "$",
                           '{"schema_version": 1, "x": [1, {"y": ' + literal + "}]}", status="PENDING")
        self.fails(r"fenced JSON block 1 \(line \d+\): invalid JSON \(lone surrogate escape U\+D83D\)",
                   '{"schema_version": 1, "x": "\\ud83d"}')
        self.fails(r"invalid JSON \(lone surrogate escape U\+DC00\)", '{"schema_version": 1, "\\udc00": 1}')
        self.passes('{"schema_version": 1, "x": "\\ud83d\\ude00 and \\u00e9"}')  # a valid pair and BMP escape
        self.passes('{"schema_version": 1, "x": 1e308, "y": -0.0, "z": "nan"}')
        # Valid syntax that overflows a binary64 is the same rot by another door: it would re-emit as Infinity.
        self.fails(r"fenced JSON block 1 \(line \d+\): number 1e400 overflows to inf; no consumer can round-trip it",
                   '{"schema_version": 1, "x": 1e400}')
        self.fails(r"number -1e999 overflows to -inf", '{"schema_version": 1, "x": [-1e999]}')
        (self.adr / "ADR-015.md").unlink()  # back to the baseline so the documents, not README drift, are reported
        original = self.read("reservations.json")
        for document in ("reservations.json", "legacy-bodies.json", "accepted-records.json"):
            with self.subTest(document=document):
                data = self.read(document)
                self.write(document, data.replace(b'"schema_version": 1,', b'"schema_version": NaN,'))
                self.assert_fails(document.replace(".", r"\.") + ": non-JSON literal NaN$")
                self.write(document, data)
        self.write("reservations.json", original.replace(b'"question": "Money', b'"question": "\\udbff Money'))
        self.assert_fails(r"reservations\.json: invalid JSON \(lone surrogate escape U\+DBFF\)")
        self.write("reservations.json", original)
        adr.check_layout(self.root)

    def test_integer_literals_follow_the_same_finiteness_rule_everywhere(self):
        """PR #158 core F3 / security S2 (docs#161): the overflow rule covers integer literals too.
        `1` followed by 400 zeros is Infinity to every binary64 consumer and is refused naming the
        record, block, line and digit count, never the literal; the rule is finiteness, not exactness,
        so 9007199254740993 (beyond 2^53) passes. Blocks and documents alike."""
        huge = "1" + "0" * 400
        record = self.record('{"schema_version": 1, "x": ' + huge + "}")
        fence_line = record.split("\n").index("```json") + 1
        self.fails(
            r"adr/ADR-015\.md: fenced JSON block 1 \(line " + str(fence_line) + r"\): integer literal of 401 digits "
            r"overflows a binary64 to inf; no consumer can round-trip it$",
            '{"schema_version": 1, "x": ' + huge + "}",
        )
        with self.assertRaises(adr.LayoutError) as caught:
            adr.validate_sources(self.root)
        self.assertNotIn("0" * 20, str(caught.exception))  # described by its length, never echoed
        self.fails(r"fenced JSON block 1 \(line \d+\): integer literal of 401 digits overflows a binary64 to -inf;",
                   '{"schema_version": 1, "x": [1, {"y": -' + huge + "}]}", status="PENDING")
        self.fails(r"integer literal of 401 digits overflows a binary64 to inf", '{"schema_version": ' + huge + "}")
        # The rule is the value, not the digit count: 1e308 written out is finite, 1.8e308 written out is not.
        self.passes('{"schema_version": 1, "x": 1' + "0" * 308 + "}")
        self.fails(r"integer literal of 309 digits overflows a binary64 to inf", '{"schema_version": 1, "x": 18' + "0" * 307 + "}")
        self.passes('{"schema_version": 1, "x": 9007199254740993, "y": -9007199254740993, "z": -0}')
        self.passes('{"schema_version": 9007199254740993}')
        # Leading zeros are a syntax error before any number hook runs.
        self.fails(r"fenced JSON block 1 \(line \d+\): invalid JSON \(Expecting ',' delimiter", '{"schema_version": 1, "x": 0' + huge + "}")
        self.passes('{"schema_version": 1, "x": 1.0e308}')  # the float rule is unchanged
        self.fails(r"number 1e400 overflows to inf", '{"schema_version": 1, "x": 1e400}')
        (self.adr / "ADR-015.md").unlink()  # back to the baseline so the documents, not README drift, are reported
        for document in ("reservations.json", "legacy-bodies.json", "accepted-records.json"):
            with self.subTest(document=document):
                data = self.read(document)
                self.write(document, data.replace(b'"schema_version": 1,', b'"schema_version": ' + huge.encode() + b","))
                self.assert_fails(
                    document.replace(".", r"\.") + r": integer literal of 401 digits overflows a binary64 to inf; "
                    r"no consumer can round-trip it$"
                )
                self.write(document, data)
        adr.check_layout(self.root)

    def test_over_long_integer_literals_fail_closed_naming_the_block_in_the_library_cli_and_check_docs(self):
        """A literal beyond Python's int-string digit limit (sys.get_int_max_str_digits(), 4300 by
        default) used to escape as a bare ValueError: exit 1 without record, block or line. It is now
        the same labelled LayoutError in the library, the CLI and check_docs, and the interpreter's
        limit is left in force rather than raised."""
        limit = sys.get_int_max_str_digits()  # 0 when the interpreter runs with the limit disabled
        digits = max(limit, 4300) + 1
        message = rf"adr/ADR-015\.md: fenced JSON block 1 \(line \d+\): integer literal of {digits} digits "
        if limit:
            message += rf"exceeds the interpreter's {limit}-digit conversion limit and "
        message += "overflows a binary64 to inf; no consumer can round-trip it"
        block = '{"schema_version": 1, "x": ' + "9" * digits + "}"
        self.fails(message + "$", block)
        self.fails(message.replace("to inf", "to -inf") + "$", '{"schema_version": 1, "x": [-' + "9" * digits + "]}", status="PENDING")
        self.assertEqual(sys.get_int_max_str_digits(), limit)
        self.write("ADR-015.md", self.record(block))
        for command in (["check"], ["render", "--ticket", MONEY]):
            with self.subTest(command=command[0]):
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = adr.main([*command, "--root", str(self.root)])
                self.assertEqual((code, out.getvalue()), (1, ""))
                self.assertRegex(err.getvalue(), "^ERROR: " + message + "\n")
                self.assertNotIn("Traceback", err.getvalue())
        self.assertEqual(self.read("README.md"), Baseline.read("README.md"))  # render refused before writing
        self.assertEqual(self.read("accepted-records.json"), Baseline.read("accepted-records.json"))
        check_docs = load("check_docs")
        for name in ("planning", "product"):
            shutil.copytree(ROOT / name, self.root / name)
        (self.root / "scripts").mkdir()
        for path in SCRIPTS.glob("*.py"):
            shutil.copy(path, self.root / "scripts" / path.name)
        check_docs.ROOT = self.root
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(check_docs.main(), 1)
        self.assertRegex(err.getvalue(), "^Documentation check failed: " + message + "\n$")
        self.assertEqual(sys.get_int_max_str_digits(), limit)

    def test_missing_or_unusable_version_fails(self):
        message = (r"adr/ADR-015\.md: fenced JSON block 1 \(line \d+\) declares no version field \(schema_version, "
                   r"policy_version, parameters_version or another \*_version key holding a non-empty string or positive integer\)")
        self.fails(message + "$", '{"adr": "ADR-015", "roles": []}')
        self.fails(message + r"; 'schema_version' is None", '{"schema_version": null}')
        self.fails(message + r"; 'schema_version' is ''", '{"schema_version": ""}')
        self.fails(message + r"; 'schema_version' is 0", '{"schema_version": 0}')
        self.fails(message + r"; 'schema_version' is True", '{"schema_version": true}')
        self.fails(message + r"; 'schema_version' is -1", '{"schema_version": -1}')
        self.fails(message + r"; 'schema_version' is 1\.0", '{"schema_version": 1.0}')
        self.fails(message + "$", '{"schemaVersion": 1}')
        self.fails(message + "$", '{"nested": {"schema_version": 1}}')
        self.fails(message, '{"adr": "ADR-015"}', status="PENDING")

    def test_second_block_is_numbered_and_uppercase_or_attributed_info_strings_count(self):
        self.write("ADR-015.md", source(tail=DECISION + '\n```json\n{"schema_version": 1}\n```\n\nText.\n\n```JSON title="x"\n{"adr": 1}\n```\n' + TESTS_SECTION))
        self.assert_fails(r"fenced JSON block 2 \(line \d+\) declares no version field", adr.validate_sources)

    def test_tilde_fences_longer_fences_and_unclosed_fences(self):
        self.passes('{"schema_version": 1}', fence="~~~")
        self.fails(r"fenced JSON block 1 .* declares no version field", '{"x": 1}', fence="~~~")
        self.passes('{"schema_version": 1, "note": "```"}', fence="````")
        self.passes('{"schema_version": 1}\n')  # a blank line inside the block is still a closed block
        self.write("ADR-015.md", source(tail=DECISION + '\n```json\n{"schema_version": 1}\n' + TESTS_SECTION))
        self.assert_fails(r"fenced JSON block 1 \(line \d+\) is never closed", adr.validate_sources)

    def test_legacy_records_are_not_scanned(self):
        layout = adr.validate_sources(self.root)
        for number in layout.legacy:
            self.assertNotIn("```json", layout.sources[number].body)

    def test_grandfather_pin_admits_exactly_the_pinned_bytes_of_the_pinned_record(self):
        block = '{\n  "adr": "ADR-015",\n  "roles": ["a"]\n}'
        digest = hashlib.sha256((block + "\n").encode("utf-8")).hexdigest()
        self.fails(r"fenced JSON block 1 .* declares no version field", block)
        with mock.patch.dict(adr.UNVERSIONED_JSON_BLOCKS, {("ADR-015", digest): "ADR-015 sample pin"}, clear=True):
            self.passes(block)
            self.fails(r"fenced JSON block 1 .* declares no version field", block.replace('"a"', '"b"'))
            self.write("ADR-016.md", source(number="ADR-016", ticket=CAT, title="Sample", tail=DECISION + f"\n```json\n{block}\n```\n" + TESTS_SECTION))
            self.write("ADR-015.md", source())
            self.assert_fails(r"adr/ADR-016\.md: fenced JSON block 1 .* declares no version field", adr.validate_sources)

    def test_fenced_block_scanner(self):
        lines = ["text", "```json", "{", "```", "  ~~~", "inner ``` not a close", "  ~~~~", "````", "```", "````", "``` not `a fence", "~~~x", "tail"]
        blocks = [(info, first, last, content) for info, first, last, content in adr.fenced_blocks(lines)]
        self.assertEqual(blocks, [
            ("json", 1, 3, ["{"]),
            ("", 4, 6, ["inner ``` not a close"]),
            ("", 7, 9, ["```"]),
            ("x", 11, None, ["tail"]),
        ])
        self.assertEqual(adr.outside_fences(lines), [0, 10])
        self.assertEqual(list(adr.fenced_blocks(["    ```json", "{", "    ```"])), [])


class WriterTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.dir = Path(directory.name)
        self.addCleanup(self.cleanup, directory)
        self.target = self.dir / "out.md"

    def cleanup(self, directory):
        make_writable(self.dir)
        directory.cleanup()

    def leftovers(self):
        return [path.name for path in self.dir.iterdir() if path.name != "out.md"]

    def test_writes_exact_utf8_bytes_without_bom_or_newline_translation(self):
        adr.write_output(self.target, "## ADR-015 — Title\n**Status:** ACCEPTED · 2026-10-01\n")
        self.assertEqual(self.target.read_bytes(), "## ADR-015 — Title\n**Status:** ACCEPTED · 2026-10-01\n".encode("utf-8"))
        adr.write_output(self.target, b"second\n")
        self.assertEqual(self.target.read_bytes(), b"second\n")
        self.assertEqual(self.leftovers(), [])

    def test_failed_replacement_keeps_the_old_output_and_removes_the_temporary(self):
        self.target.write_bytes(b"old\n")
        with mock.patch.object(adr, "_replace", side_effect=OSError("disk gone")):
            with self.assertRaisesRegex(OSError, "disk gone"):
                adr.write_output(self.target, b"new\n")
        self.assertEqual(self.target.read_bytes(), b"old\n")
        self.assertEqual(self.leftovers(), [])

    def test_failed_write_keeps_the_old_output(self):
        self.target.write_bytes(b"old\n")
        with mock.patch.object(adr.os, "open", side_effect=PermissionError("denied")):
            with self.assertRaises(PermissionError):
                adr.write_output(self.target, b"new\n")
        self.assertEqual(self.target.read_bytes(), b"old\n")
        self.assertEqual(self.leftovers(), [])

    def test_read_only_temporary_is_cleaned_up(self):
        self.target.write_bytes(b"old\n")
        os.chmod(self.target, stat.S_IREAD)
        try:
            with mock.patch.object(adr, "_replace", side_effect=OSError("injected")):
                with self.assertRaisesRegex(OSError, "injected"):
                    adr.write_output(self.target, b"new\n")
            self.assertEqual(self.target.read_bytes(), b"old\n")
            self.assertEqual(self.leftovers(), [])
        finally:
            os.chmod(self.target, stat.S_IREAD | stat.S_IWRITE)

    def test_cleanup_failure_reports_both_errors(self):
        self.target.write_bytes(b"old\n")
        with mock.patch.object(adr, "_replace", side_effect=OSError("replace failed")), \
                mock.patch.object(adr, "_unlink", side_effect=OSError("unlink failed")):
            with self.assertRaises(adr.CleanupError) as caught:
                adr.write_output(self.target, b"new\n")
        self.assertIn("unlink failed", str(caught.exception))
        self.assertEqual(str(caught.exception.__cause__), "replace failed")
        self.assertEqual(self.target.read_bytes(), b"old\n")
        make_writable(self.dir)
        for name in self.leftovers():
            (self.dir / name).unlink()

    @unittest.skipIf(os.name == "nt", "POSIX permission bits")
    def test_existing_mode_is_retained_and_new_files_use_ordinary_permissions(self):
        self.target.write_bytes(b"old\n")
        os.chmod(self.target, 0o640)
        adr.write_output(self.target, b"new\n")
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o640)
        fresh = self.dir / "fresh.md"
        mask = os.umask(0o022)
        try:
            adr.write_output(fresh, b"x\n")
        finally:
            os.umask(mask)
        self.assertEqual(stat.S_IMODE(fresh.stat().st_mode), 0o644)


class CliTests(ScratchCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = adr.main([*args, "--root", str(self.root)])
        return code, out.getvalue(), err.getvalue()

    def test_failures_exit_one_with_an_error_line(self):
        self.write("ADR-015.md", source(ticket=CAT))
        code, out, err = self.run_cli("check")
        self.assertEqual((code, out), (1, ""))
        self.assertTrue(err.startswith("ERROR: adr/ADR-015.md: ticket T-ADR-CAT-02 does not own ADR-015"))

    def test_help_states_that_ticket_is_a_scope_guard_not_identity(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as caught:
            adr.main(["render", "--help"])
        self.assertEqual(caught.exception.code, 0)
        text = " ".join(out.getvalue().split())
        self.assertIn("a declared scope guard", text)
        self.assertIn("not authenticated identity", text)
        self.assertIn("not authenticated identity", " ".join(adr.__doc__.split()))

    def test_render_reports_updates_and_no_ops(self):
        self.write("ADR-015.md", source())
        code, out, _ = self.run_cli("render", "--ticket", MONEY)
        self.assertEqual((code, out), (0, "adr/README.md and adr/accepted-records.json updated for T-ADR-MONEY-01.\n"))
        code, out, _ = self.run_cli("render", "--ticket", MONEY)
        self.assertEqual(
            (code, out),
            (0, "adr/README.md and adr/accepted-records.json already match the rendered layout for T-ADR-MONEY-01.\n"),
        )
        code, out, _ = self.run_cli("check")
        self.assertEqual(code, 0)
        self.assertIn("1 published reserved records, 8 pending", out)
        # A PENDING draft changes only the README; the registry stays untouched.
        self.write("ADR-016.md", source(number="ADR-016", ticket=CAT, title="Sample", status="PENDING"))
        code, out, _ = self.run_cli("render", "--ticket", CAT)
        self.assertEqual((code, out), (0, "adr/README.md updated for T-ADR-CAT-02.\n"))

    def test_filesystem_failures_report_the_causal_chain(self):
        self.write("ADR-015.md", source())
        with mock.patch.object(adr, "_replace", side_effect=OSError("replace failed")), \
                mock.patch.object(adr, "_unlink", side_effect=OSError("unlink failed")):
            code, _, err = self.run_cli("render", "--ticket", MONEY)
        self.assertEqual(code, 1)
        self.assertIn("ERROR: write of", err)
        self.assertIn("unlink failed", err)
        self.assertIn("caused by: OSError('replace failed')", err)
        self.assertEqual(self.read("README.md"), Baseline.read("README.md"))
        self.assertEqual(self.read("accepted-records.json"), Baseline.read("accepted-records.json"))
        make_writable(self.adr)
        for path in self.adr.glob(".*.tmp"):
            path.unlink()


GIT = shutil.which("git")


class GitScratchCase(ScratchCase):
    """A scratch layout committed as ``main`` of a local git repository: isolated HOME and config,
    no hooks, no signing, LF checkouts, no fsync (test-only speed). Local repositories only."""

    INIT_REPO = True  # subclasses that only work on copies of a template repository skip the init

    def setUp(self):
        super().setUp()
        self.home = self.root / "home"
        self.home.mkdir()
        (self.home / "gitconfig").write_text("", encoding="utf-8")
        self.env = {
            **os.environ, "HOME": str(self.home), "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": str(self.home / "gitconfig"), "GIT_CONFIG_PARAMETERS": "",
            "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "GIT_AUTHOR_DATE": "2026-10-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-10-01T00:00:00Z",
        }
        if self.INIT_REPO:
            self.init_repo()

    def init_repo(self):
        self.git("init", "-q", "-b", "main")
        self.commit("baseline")

    def git(self, *args, cwd=None, check=True):
        return subprocess.run(
            [GIT, "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", "-c", "core.fsync=none",
             "-c", "gc.auto=0", "-c", f"core.hooksPath={self.home / 'nohooks'}", *args],
            cwd=cwd or self.root, env=self.env, capture_output=True, text=True, encoding="utf-8", check=check,
        )

    def commit(self, message):
        self.git("add", "-A", "adr")
        self.git("commit", "-q", "-m", message)

    def land(self, branch, number, ticket, **kwargs):
        """Publish one synthetic record on its own branch from main with a ticket-scoped render."""
        self.git("checkout", "-q", "-b", branch, "main")
        self.write(f"{number}.md", source(number=number, ticket=ticket, title=f"Sample {number}", **kwargs))
        self.assertTrue(adr.render(self.root, ticket))
        self.commit(f"land {number}")

    def squash(self, branch):
        self.git("merge", "-q", "--squash", branch)
        self.git("commit", "-q", "-m", f"squash {branch}")


@unittest.skipUnless(GIT, "git is not available")
class GitIntegrationTests(GitScratchCase):
    """Independent ordinary tickets land in either order without conflict; same-predecessor
    supersessions conflict textually and are rejected semantically. Local repositories only."""

    def test_independent_tickets_squash_merge_cleanly_in_both_orders(self):
        self.land("money", "ADR-015", MONEY)
        self.land("cat", "ADR-016", CAT)
        self.git("checkout", "-q", "money")
        self.squash("cat")
        self.assertEqual(adr.check_layout(self.root)["published"], 2)
        merged = self.read("README.md")
        self.git("checkout", "-q", "cat")
        self.squash("money")
        self.assertEqual(self.read("README.md"), merged)
        self.assertEqual(adr.check_layout(self.root)["published"], 2)
        self.assertEqual(self.git("status", "--porcelain", "--", "adr").stdout, "")

    def test_same_predecessor_supersessions_conflict_and_are_rejected(self):
        self.land("money", "ADR-015", MONEY, supersedes="ADR-004")
        self.land("cat", "ADR-016", CAT, supersedes="ADR-004")
        self.git("checkout", "-q", "money")
        result = self.git("merge", "--squash", "cat", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UU adr/README.md", self.git("status", "--porcelain").stdout)
        self.git("checkout", "-q", "--theirs", "adr/README.md")
        self.assert_fails(r"adr/ADR-004\.md has competing successors ADR-015 and ADR-016", adr.validate_sources)


if __name__ == "__main__":
    unittest.main()
