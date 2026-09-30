"""Generate and validate the ADR layout specified in adr/LAYOUT.md (owned by T-ADR-INDEX-10).

Commands, run from the repository root (every subcommand accepts ``--root``):

    python -B scripts/validate_adr_layout.py check
    python -B scripts/validate_adr_layout.py render [--ticket T-ADR-...]
    python -B scripts/validate_adr_layout.py split [--root <scratch-root>]
    python -B scripts/validate_adr_layout.py test

``check`` pins adr/presplit-reference.md to its recorded Git blob OID and SHA-256, derives the
fourteen original bodies and the nine original allocations from those verified bytes, checks the
historical manifest and the reservation file against them, validates every adr/ADR-###.md header
and body, owner claims and the replacement graph, and finally requires adr/README.md to equal the
rendered projection byte for byte. ``render`` writes that projection; with ``--ticket`` it refuses
to alter bytes outside the slots of that ticket's allocated number and the derived slots of the
record's previous and current predecessors. The ``--ticket`` argument is a declared scope guard,
not authenticated identity: it limits which bytes one render may change and proves nothing about
who ran it. ``split`` performs the one-time migration from the original monolithic README and
refuses to overwrite an already split layout. ``test`` runs the stdlib unittest suite in
scripts/tests/test_adr_layout*.py.

Text that reaches the generated README (source titles, allocation tickets, questions and blocks)
must be printable: control characters, CR/LF/TAB, Unicode line/paragraph separators, bidirectional
overrides and other non-printable code points are rejected, as are HTML comment delimiters that
could forge slot markers. Sources must be regular files, not symbolic links.

Effective state is derived and never stored back. An allocated number without a source, or whose
source records ``status: PENDING``, renders as PENDING; a source with a valid successor renders as
SUPERSEDED with the reverse link. A PENDING draft therefore coexists with its allocation: the file
may be published early, its index slot links the file and shows the recorded PENDING status and
date, and its pending-gate row stays PENDING until the recorded status is ACCEPTED. The allocation
in reservations.json is never rewritten. scripts/check_docs.py runs ``check`` so CI enforces the
layout with the standard library only.
"""

import argparse
import dataclasses
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]

# Migration pins (adr/LAYOUT.md, "Preserved migration reference"). The reference is the raw
# adr/README.md blob of source commit REFERENCE_SOURCE_COMMIT; nothing else is a baseline.
REFERENCE_SOURCE_COMMIT = "3daa2d7a2ab3ac3f17eecbfff9e9ae8c485b5ccf"
REFERENCE_BLOB_OID = "99707073a05034863522763c18bb38d2ad5fc81f"
REFERENCE_SHA256 = "995641e20e49dc13c2074f15fff4515c9f4ca78a5b2b2beced39fcb2c62314fd"

ADR_DIR = "adr"
README_NAME = "README.md"
REFERENCE_NAME = "presplit-reference.md"
MANIFEST_NAME = "legacy-bodies.json"
RESERVATIONS_NAME = "reservations.json"

STATUSES = ("PENDING", "ACCEPTED", "SUPERSEDED")
REQUIRED_FIELDS = ("number", "title", "status", "date", "supersedes", "superseded-by")
TICKET_FIELD = "ticket"
MANIFEST_FIELDS = ("number", "title", "sha256", "bytes")
RESERVATION_FIELDS = ("number", "ticket", "state", "question", "blocks")
EMPTY = "—"

NUMBER_PATTERN = re.compile(r"ADR-\d{3}")
SOURCE_NAME_PATTERN = re.compile(r"ADR-\d{3}\.md")
TICKET_PATTERN = re.compile(r"T-[A-Z0-9]+(?:-[A-Z0-9]+)+")
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
HEX_PATTERN = re.compile(r"[0-9a-f]{64}")
HEADER_LINE = re.compile(r"([a-z][a-z-]*): (.*)")
HEADING_LINE = re.compile(r"^## (ADR-\d{3}) — (.+)$", re.MULTILINE)
STATUS_LINE = re.compile(r"\*\*Status:\*\* (\S+) · (\S+)(?: (.*))?")
ALLOCATION_ROW = re.compile(r"^\| (ADR-\d{3}) \| `([^`]+)` \| (.+?) \| (.+?) \|$", re.MULTILINE)
PENDING_HEADING = "## Pending execution-gate ADRs\n"
SLOT_PATTERN = re.compile(r"<!-- SLOT START (ADR-\d{3}) -->\n(.*?)<!-- SLOT END \1 -->\n", re.DOTALL)
CELL_PATTERN = re.compile(r"^\| ([^|]+?) \| (.*) \|$", re.MULTILINE)

BEGIN_INDEX = "<!-- BEGIN GENERATED ACCEPTED INDEX -->\n"
END_INDEX = "<!-- END GENERATED ACCEPTED INDEX -->\n"
BEGIN_PENDING = "<!-- BEGIN GENERATED PENDING GATE ADRS -->\n"
END_PENDING = "<!-- END GENERATED PENDING GATE ADRS -->\n"

# Fixed README text around the two generated regions. The whole README is generator-owned.
INTRO = """# Architecture Decision Records

Short, durable records of decisions that are expensive to reverse. Each accepted decision lives in its own numbered file under `adr/ADR-###.md`, while this README is generator-owned and keeps the index, reservation map and pending gate table in fixed slots.

**Status key:** `ACCEPTED` = decided · `SUPERSEDED` = replaced by a later ADR · `RESERVED` = slot held for an open ticket · `PENDING` = the ticket is still open and the file is not yet accepted.

**Slot rule:** allocated ADR numbers have fixed slots. Landing an ordinary decision updates only its slots, without inserting or deleting another number's slots. A supersession also updates the derived predecessor index/state slots, not the predecessor source.

The layout and generator are owned by `T-ADR-INDEX-10`. Decision authors edit only their own ADR source and run `python -B scripts/validate_adr_layout.py render --ticket T-ADR-...` to update authorized affected slots; they never hand-edit generated bytes. Supersession effects on shared predecessor slots must be declared and serialized. Two branches superseding the same predecessor are not conflict-free.

Source status/date remain the recorded decision metadata. The index derives effective `SUPERSEDED` status and reverse links from valid successor records. Migration pins, header/schema rules and the bounded shallow-checkout trust model are specified in [LAYOUT.md](LAYOUT.md).

"""
MIDDLE = """
Slots ADR-015 to ADR-023 retain their original ticket allocations. Source, recorded date and effective replacement state are generated from the records; allocation metadata is not rewritten when a decision lands.

## Pending execution-gate ADRs

"""
TAIL = """
T-ADR-INDEX-10 owns the per-file layout, the reservation file and the generator for the two generated regions above. A record claiming a reserved number owned by a different ticket fails validation, and a hand edit inside a generated region fails validation too.

Two additional decisions are deliberately `Future` and do not block the MVP tranche: `T-ADR-BUREAU-11` decides whether credit-bureau integration is viable without violating the no-lending business model, and `T-ADR-EMBED-12` decides whether any user-derived embedding may be persisted. Until the latter is accepted, vector database extensions and durable user-derived embeddings are prohibited.

Context and the full gate list: [`../product/04-execution-readiness-review.md`](../product/04-execution-readiness-review.md).
Ticket source: [`../planning-automation/backlog-v2/README.md`](../planning-automation/backlog-v2/README.md).
"""

# Indirections so the failure-boundary tests can inject filesystem faults into one writer call.
_replace = os.replace
_unlink = os.unlink


class LayoutError(ValueError):
    """The layout, a source, a JSON document or the generated README violates adr/LAYOUT.md."""


class CleanupError(OSError):
    """An output write failed and its own temporary file could not be removed either."""


def number_value(number):
    return int(number[4:])


def sort_numbers(numbers):
    return sorted(numbers, key=number_value)


def blob_oid(data):
    """Git's object identifier for a blob: SHA-1 over the ``blob <size>\\0`` header and content."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def canonical_date(value, label):
    if not DATE_PATTERN.fullmatch(value):
        raise LayoutError(f"{label}: date {value!r} is not a canonical YYYY-MM-DD date")
    year, month, day = (int(part) for part in value.split("-"))
    try:
        datetime.date(year, month, day)
    except ValueError:
        raise LayoutError(f"{label}: date {value!r} is not a valid calendar date") from None
    return value


def anchor(number, title):
    """GitHub-style heading slug of ``## ADR-### — Title`` for the index source cell."""
    text = re.sub(r"[^\w\- ]", "", f"{number} — {title}".lower())
    return text.replace(" ", "-")


def check_rendered_text(value, label):
    """Text that reaches the README: one trimmed line of printable code points, no marker forgery."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise LayoutError(f"{label} must be a non-empty trimmed string")
    if not value.isprintable():
        offending = next(character for character in value if not character.isprintable())
        raise LayoutError(f"{label} contains the non-printable character U+{ord(offending):04X}")
    if "<!--" in value or "-->" in value:
        raise LayoutError(f"{label} must not contain HTML comment delimiters")
    return value


@dataclasses.dataclass(frozen=True)
class LegacyRecord:
    """One of the fourteen original decisions, derived from the pinned reference bytes."""

    number: str
    title: str
    status: str
    date: str
    segment: str  # raw reference bytes from the heading to the next section; the manifest hashes it

    @property
    def body(self):
        # Owner-approved file-boundary exception: only the terminal run of LF separator bytes is
        # replaced by exactly one LF; nothing interior is normalized.
        return self.segment.rstrip("\n") + "\n"


@dataclasses.dataclass(frozen=True)
class Allocation:
    number: str
    ticket: str
    question: str
    blocks: str


@dataclasses.dataclass(frozen=True)
class Source:
    number: str
    title: str
    status: str
    date: str
    supersedes: object
    superseded_by: object
    ticket: object
    header: str
    body: str


@dataclasses.dataclass
class Layout:
    legacy: dict
    allocations: dict
    sources: dict
    successors: dict

    def numbers(self):
        return sort_numbers(set(self.sources) | set(self.allocations))

    def effective_status(self, number):
        if number in self.successors:
            return "SUPERSEDED"
        return self.sources[number].status

    def effective_state(self, number):
        """Pending-gate state of an allocated number: PENDING until an ACCEPTED source exists."""
        if number not in self.sources or self.sources[number].status == "PENDING":
            return "PENDING"
        return self.effective_status(number)

    def summary(self):
        published = [number for number in self.sources if number not in self.legacy]
        pending = [n for n in self.allocations if self.effective_state(n) == "PENDING"]
        return {
            "legacy": len(self.legacy), "allocations": len(self.allocations),
            "published": len(published), "pending": len(pending), "superseded": len(self.successors),
        }


def verify_reference(data, label=f"{ADR_DIR}/{REFERENCE_NAME}"):
    """Pin the raw pre-split reference to both recorded identifiers; return its text."""
    digest = hashlib.sha256(data).hexdigest()
    if digest != REFERENCE_SHA256:
        raise LayoutError(f"{label}: SHA-256 {digest} does not match the pinned {REFERENCE_SHA256}")
    oid = blob_oid(data)
    if oid != REFERENCE_BLOB_OID:
        raise LayoutError(f"{label}: Git blob OID {oid} does not match the pinned {REFERENCE_BLOB_OID}")
    return data.decode("utf-8")


def _pending_boundary(reference):
    boundary = reference.find(PENDING_HEADING)
    if boundary <= 0 or reference[boundary - 1] != "\n":
        raise LayoutError("reference lacks the pending execution-gate section")
    return boundary


def derive_legacy(reference):
    """Derive the fourteen original records from the verified reference text."""
    boundary = _pending_boundary(reference)
    headings = list(HEADING_LINE.finditer(reference, 0, boundary))
    records = {}
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else boundary
        segment = reference[match.start():end]
        lines = segment.split("\n")
        status = STATUS_LINE.fullmatch(lines[1]) if len(lines) > 1 else None
        if status is None or status.group(1) not in STATUSES:
            raise LayoutError(f"reference {match.group(1)} has no recognizable status line")
        canonical_date(status.group(2), f"reference {match.group(1)}")
        records[match.group(1)] = LegacyRecord(
            match.group(1), match.group(2), status.group(1), status.group(2), segment
        )
    if list(records) != [f"ADR-{index:03d}" for index in range(1, 15)]:
        raise LayoutError("reference does not contain exactly the original bodies ADR-001 to ADR-014")
    return records


def derive_allocations(reference):
    """Derive the nine original allocations from the reference's pending table."""
    allocations = {}
    for match in ALLOCATION_ROW.finditer(reference, _pending_boundary(reference)):
        number, ticket, question, blocks = match.groups()
        if number in allocations:
            raise LayoutError(f"reference allocates {number} twice")
        allocations[number] = Allocation(number, ticket, question, blocks)
    if list(allocations) != [f"ADR-{index:03d}" for index in range(15, 24)]:
        raise LayoutError("reference does not contain exactly the original allocations ADR-015 to ADR-023")
    return allocations


def render_header(fields):
    return "---\n" + "".join(f"{key}: {value}\n" for key, value in fields) + "---\n"


def legacy_header(record):
    return render_header((
        ("number", record.number), ("title", record.title), ("status", record.status),
        ("date", record.date), ("supersedes", "null"), ("superseded-by", "null"),
    ))


def legacy_source(record):
    return legacy_header(record) + record.body


def render_json(items):
    return json.dumps({"schema_version": 1, "items": items}, indent=2) + "\n"


def render_manifest(legacy):
    return render_json([
        {
            "number": record.number, "title": record.title,
            "sha256": hashlib.sha256(record.segment.encode("utf-8")).hexdigest(),
            "bytes": len(record.segment.encode("utf-8")),
        }
        for record in legacy.values()
    ])


def render_reservations(allocations):
    return render_json([
        {
            "number": item.number, "ticket": item.ticket, "state": "PENDING",
            "question": item.question, "blocks": item.blocks,
        }
        for item in allocations.values()
    ])


def load_json_document(path):
    label = f"{ADR_DIR}/{path.name}"

    def reject_duplicates(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise LayoutError(f"{label}: duplicate JSON key {key!r}")
            value[key] = item
        return value

    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise LayoutError(f"{label} is missing") from None
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LayoutError(f"{label}: invalid JSON ({error})") from None


def parse_items(document, label, fields):
    """Enforce the ``schema_version: 1`` envelope, declared item fields and unique numbers."""
    if not isinstance(document, dict) or set(document) != {"schema_version", "items"}:
        raise LayoutError(f"{label}: document must contain exactly schema_version and items")
    version = document["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise LayoutError(f"{label}: schema_version must be the integer 1")
    if not isinstance(document["items"], list):
        raise LayoutError(f"{label}: items must be a list")
    seen = set()
    for item in document["items"]:
        if not isinstance(item, dict) or set(item) != set(fields):
            raise LayoutError(f"{label}: each item declares exactly {', '.join(fields)}")
        number = item["number"]
        if not isinstance(number, str) or not NUMBER_PATTERN.fullmatch(number):
            raise LayoutError(f"{label}: item number {number!r} is not ADR-###")
        if number in seen:
            raise LayoutError(f"{label}: duplicate number {number}")
        seen.add(number)
    return document["items"]


def validate_manifest(root, legacy):
    path = root / ADR_DIR / MANIFEST_NAME
    label = f"{ADR_DIR}/{MANIFEST_NAME}"
    items = parse_items(load_json_document(path), label, MANIFEST_FIELDS)
    for item in items:
        if not isinstance(item["title"], str) or not isinstance(item["sha256"], str):
            raise LayoutError(f"{label}: {item['number']} title and sha256 must be strings")
        if not HEX_PATTERN.fullmatch(item["sha256"]):
            raise LayoutError(f"{label}: {item['number']} sha256 must be 64 lowercase hex digits")
        if isinstance(item["bytes"], bool) or not isinstance(item["bytes"], int):
            raise LayoutError(f"{label}: {item['number']} bytes must be an integer")
    if path.read_bytes() != render_manifest(legacy).encode("utf-8"):
        expected = {entry["number"]: entry for entry in json.loads(render_manifest(legacy))["items"]}
        for item in items:
            if item != expected.get(item["number"]):
                raise LayoutError(
                    f"{label}: entry {item['number']} does not match the body derived from the pinned reference"
                )
        raise LayoutError(f"{label}: the historical inventory must stay byte-exact to the derived manifest")


def validate_reservations(root, original):
    path = root / ADR_DIR / RESERVATIONS_NAME
    label = f"{ADR_DIR}/{RESERVATIONS_NAME}"
    items = parse_items(load_json_document(path), label, RESERVATION_FIELDS)
    allocations = {}
    tickets = {}
    for item in items:
        number = item["number"]
        for key in RESERVATION_FIELDS[1:]:
            if not isinstance(item[key], str):
                raise LayoutError(f"{label}: {number} {key} must be a string")
        if item["state"] != "PENDING":
            raise LayoutError(f"{label}: {number} state must remain PENDING; effective state is derived")
        if not TICKET_PATTERN.fullmatch(item["ticket"]):
            raise LayoutError(f"{label}: {number} ticket {item['ticket']!r} is malformed")
        for key in ("question", "blocks"):
            value = check_rendered_text(item[key], f"{label}: {number} {key}")
            if "|" in value:
                raise LayoutError(f"{label}: {number} {key} must be one table cell without '|'")
        if item["ticket"] in tickets:
            raise LayoutError(f"{label}: ticket {item['ticket']} is allocated twice")
        tickets[item["ticket"]] = number
        allocations[number] = Allocation(number, item["ticket"], item["question"], item["blocks"])
    for number, expected in original.items():
        if number not in allocations:
            raise LayoutError(f"{label}: original allocation {number} ({expected.ticket}) was removed")
        if allocations[number] != expected:
            raise LayoutError(f"{label}: original allocation {number} was changed or reassigned")
    ceiling = max(number_value(number) for number in original)
    for number in allocations:
        if number not in original and number_value(number) <= ceiling:
            raise LayoutError(
                f"{label}: {number} cannot be allocated; reviewed additions use numbers above ADR-{ceiling:03d}"
            )
    return {number: allocations[number] for number in sort_numbers(allocations)}


def parse_reference(value, label, field):
    if value == "null":
        return None
    if not NUMBER_PATTERN.fullmatch(value):
        raise LayoutError(f"{label}: {field} must be null or an ADR-### reference, not {value!r}")
    return value


def parse_source(name, data):
    """Parse and validate one ``ADR-###.md`` source; the header is ``---`` fenced ``key: value``."""
    label = f"{ADR_DIR}/{name}"
    if data.startswith(b"\xef\xbb\xbf"):
        raise LayoutError(f"{label}: UTF-8 BOM is not allowed")
    if b"\r" in data:
        raise LayoutError(f"{label}: CR bytes found; sources use LF line endings")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise LayoutError(f"{label}: invalid UTF-8") from None
    if not text.startswith("---\n"):
        raise LayoutError(f"{label}: header must start with a --- line")
    close = text.find("\n---\n", 3)
    if close < 0:
        raise LayoutError(f"{label}: header is not closed by a --- line")
    header, body = text[:close + 5], text[close + 5:]
    fields = {}
    for line in header[4:close + 1].split("\n")[:-1]:
        match = HEADER_LINE.fullmatch(line)
        if match is None:
            raise LayoutError(f"{label}: malformed header line {line!r}")
        key, value = match.groups()
        if key in fields:
            raise LayoutError(f"{label}: duplicate header field {key!r}")
        if key not in REQUIRED_FIELDS and key != TICKET_FIELD:
            raise LayoutError(f"{label}: unknown header field {key!r}")
        fields[key] = value
    missing = [key for key in REQUIRED_FIELDS if key not in fields]
    if missing:
        raise LayoutError(f"{label}: missing header field(s) {', '.join(missing)}")
    number = fields["number"]
    if not NUMBER_PATTERN.fullmatch(number) or f"{number}.md" != name:
        raise LayoutError(f"{label}: header number {number!r} must match the file name")
    title = check_rendered_text(fields["title"], f"{label}: title")
    status = fields["status"]
    if status not in STATUSES:
        raise LayoutError(f"{label}: status must be one of {', '.join(STATUSES)}, not {status!r}")
    date = canonical_date(fields["date"], label)
    supersedes = parse_reference(fields["supersedes"], label, "supersedes")
    superseded_by = parse_reference(fields["superseded-by"], label, "superseded-by")
    ticket = fields.get(TICKET_FIELD)
    if ticket is not None and not TICKET_PATTERN.fullmatch(ticket):
        raise LayoutError(f"{label}: ticket {ticket!r} is malformed")
    if not body.endswith("\n"):
        raise LayoutError(f"{label}: body must end with exactly one LF (final LF missing)")
    if body.endswith("\n\n"):
        raise LayoutError(f"{label}: body must end with exactly one LF (extra final LF)")
    lines = body.split("\n")
    heading = f"## {number} — {title}"
    if lines[0] != heading:
        raise LayoutError(f"{label}: body must start with the heading {heading!r}")
    if sum(1 for line in lines if HEADING_LINE.fullmatch(line)) != 1:
        raise LayoutError(f"{label}: body must contain exactly one ## ADR-### — Title heading")
    status_lines = [line for line in lines if line.startswith("**Status:** ")]
    if len(status_lines) != 1:
        raise LayoutError(f"{label}: body must contain exactly one **Status:** line")
    recorded = STATUS_LINE.fullmatch(status_lines[0])
    if recorded is None:
        raise LayoutError(f"{label}: malformed status line; expected **Status:** STATUS · YYYY-MM-DD")
    if (recorded.group(1), recorded.group(2)) != (status, date):
        raise LayoutError(
            f"{label}: body records {recorded.group(1)} · {recorded.group(2)} but the header records "
            f"{status} · {date}"
        )
    return Source(number, title, status, date, supersedes, superseded_by, ticket, header, body)


def read_sources(root):
    sources = {}
    for path in sorted((root / ADR_DIR).iterdir()):
        if not path.name.lower().startswith("adr-"):
            continue
        if path.is_symlink():
            raise LayoutError(f"{ADR_DIR}/{path.name}: sources must be regular files, not symbolic links")
        if not SOURCE_NAME_PATTERN.fullmatch(path.name) or not path.is_file():
            raise LayoutError(f"{ADR_DIR}/{path.name}: sources are files named exactly ADR-###.md")
        source = parse_source(path.name, path.read_bytes())
        sources[source.number] = source
    return sources


def check_legacy(source, record):
    """The legacy fourteen stay frozen: title, status/date, null links, no ticket, exact bytes."""
    label = f"{ADR_DIR}/{record.number}.md"
    if source.ticket is not None:
        raise LayoutError(f"{label}: legacy records must not acquire ticket data")
    for field in ("title", "status", "date"):
        if getattr(source, field) != getattr(record, field):
            raise LayoutError(f"{label}: legacy {field} is frozen as {getattr(record, field)!r}")
    if source.supersedes is not None or source.superseded_by is not None:
        raise LayoutError(f"{label}: legacy relationship fields are frozen as null")
    if source.body != record.body:
        raise LayoutError(f"{label}: legacy body differs from the pinned pre-split reference")
    if source.header != legacy_header(record):
        raise LayoutError(f"{label}: legacy header differs from the frozen migration header")


def resolve_replacements(sources):
    """Validate the replacement graph; return predecessor -> successor for every valid claim."""
    successors = {}
    for source in sources.values():
        target = source.supersedes
        if target is None:
            continue
        label = f"{ADR_DIR}/{source.number}.md"
        if target == source.number:
            raise LayoutError(f"{label}: a record cannot supersede itself")
        if target not in sources:
            raise LayoutError(f"{label}: supersedes {target}, which has no source record")
        if source.status == "PENDING":
            raise LayoutError(f"{label}: a PENDING record cannot supersede {target}")
        if sources[target].status == "PENDING":
            raise LayoutError(f"{label}: supersedes {target}, which is not a decided record")
        if target in successors:
            raise LayoutError(
                f"{ADR_DIR}/{target}.md has competing successors {successors[target]} and {source.number}"
            )
        successors[target] = source.number
    for start in successors:
        seen, current = {start}, start
        while current in successors:
            current = successors[current]
            if current in seen:
                raise LayoutError(f"replacement cycle through {ADR_DIR}/{current}.md")
            seen.add(current)
    for source in sources.values():
        label = f"{ADR_DIR}/{source.number}.md"
        if source.superseded_by is not None and successors.get(source.number) != source.superseded_by:
            raise LayoutError(
                f"{label}: superseded-by {source.superseded_by} does not agree with a successor's forward claim"
            )
        if source.status == "SUPERSEDED" and source.number not in successors:
            raise LayoutError(f"{label}: recorded SUPERSEDED without a valid successor")
    return successors


def validate_sources(root):
    """Validate pins, manifests, allocations, every source and the replacement graph."""
    root = Path(root)
    reference_path = root / ADR_DIR / REFERENCE_NAME
    try:
        reference = verify_reference(reference_path.read_bytes())
    except FileNotFoundError:
        raise LayoutError(f"{ADR_DIR}/{REFERENCE_NAME} is missing; there is no fallback baseline") from None
    legacy = derive_legacy(reference)
    original = derive_allocations(reference)
    validate_manifest(root, legacy)
    allocations = validate_reservations(root, original)
    sources = read_sources(root)
    for number, record in legacy.items():
        if number not in sources:
            raise LayoutError(f"missing legacy source {ADR_DIR}/{number}.md")
        check_legacy(sources[number], record)
    for number, source in sources.items():
        if number in legacy:
            continue
        label = f"{ADR_DIR}/{number}.md"
        allocation = allocations.get(number)
        if allocation is None:
            raise LayoutError(f"{label}: {number} has no allocation in {RESERVATIONS_NAME}")
        if source.ticket is None:
            raise LayoutError(f"{label}: new records must claim their allocation with ticket: {allocation.ticket}")
        if source.ticket != allocation.ticket:
            raise LayoutError(
                f"{label}: ticket {source.ticket} does not own {number}, which is allocated to {allocation.ticket}"
            )
    return Layout(legacy, allocations, sources, resolve_replacements(sources))


def render_slot(number, rows):
    lines = [f"<!-- SLOT START {number} -->", f"### {number}", "| Field | Value |", "|---|---|"]
    lines += [f"| {field} | {value} |" for field, value in rows]
    lines.append(f"<!-- SLOT END {number} -->")
    return "\n".join(lines) + "\n"


def render_index_slot(layout, number):
    allocation = layout.allocations.get(number)
    source = layout.sources.get(number)
    if source is not None:
        cell = f'<a id="{anchor(number, source.title)}"></a> [{number}.md]({number}.md)'
        values = (
            cell, layout.effective_status(number), source.date,
            source.supersedes or EMPTY, layout.successors.get(number, EMPTY),
        )
    else:
        values = (f"reserved for `{allocation.ticket}`", "PENDING", EMPTY, EMPTY, EMPTY)
    return render_slot(number, (
        ("Source", values[0]), ("Status", values[1]),
        ("Ticket", allocation.ticket if allocation else EMPTY), ("Date", values[2]),
        ("Supersedes", values[3]), ("Superseded by", values[4]),
    ))


def render_pending_slot(layout, number):
    allocation = layout.allocations[number]
    return render_slot(number, (
        ("Ticket", f"`{allocation.ticket}`"), ("State", layout.effective_state(number)),
        ("Question the record must settle", allocation.question), ("Blocks", allocation.blocks),
    ))


def render_readme(layout):
    """Render the whole generator-owned README deterministically from the validated layout."""
    index = "".join(render_index_slot(layout, number) + "\n" for number in layout.numbers())
    pending = "".join(render_pending_slot(layout, number) + "\n" for number in layout.allocations)
    return INTRO + BEGIN_INDEX + index + END_INDEX + MIDDLE + BEGIN_PENDING + pending + END_PENDING + TAIL


def collect_slots(text):
    """Map each slot number to its occurrences (index region first, then pending region)."""
    slots = {}
    for match in SLOT_PATTERN.finditer(text):
        slots.setdefault(match.group(1), []).append(match.group(2))
    return slots


def describe_drift(actual, expected):
    try:
        text = actual.decode("utf-8")
    except UnicodeDecodeError:
        return "the file is not valid UTF-8"
    if "\r" in text:
        return "CR bytes are present; generated text is LF"
    actual_slots, expected_slots = collect_slots(text), collect_slots(expected.decode("utf-8"))
    for number in sort_numbers(set(actual_slots) | set(expected_slots)):
        if actual_slots.get(number) != expected_slots.get(number):
            return f"generated slot {number} differs from the rendered projection (hand edit or stale render)"
    return "text outside the generated slots differs from the rendered projection"


def mask_slots(text, numbers):
    return SLOT_PATTERN.sub(
        lambda match: (
            f"<!-- SLOT START {match.group(1)} -->\n<!-- SLOT END {match.group(1)} -->\n"
            if match.group(1) in numbers else match.group(0)
        ),
        text,
    )


def scoped_numbers(layout, ticket, existing):
    """Slots a ticket-scoped render may change: its own plus previous and current predecessors.

    The previous predecessor is reconstructed from the existing index, which must be internally
    consistent (forward and reverse links agree); it is a consistency check, not edit history.
    """
    owned = [number for number, item in layout.allocations.items() if item.ticket == ticket]
    if not owned:
        raise LayoutError(f"ticket {ticket} owns no allocation in {ADR_DIR}/{RESERVATIONS_NAME}")
    slots = {}
    for match in SLOT_PATTERN.finditer(existing):
        slots.setdefault(match.group(1), []).append(dict(CELL_PATTERN.findall(match.group(2))))
    label = f"{ADR_DIR}/{README_NAME}"
    allowed, forward = set(owned), set()
    for number in owned:
        if number not in slots:
            raise LayoutError(
                f"{label} has no generated slot for {number}; a ticket-scoped render needs the existing "
                "projection (the layout owner regenerates it with an unscoped render)"
            )
        previous = slots[number][0].get("Supersedes", EMPTY)
        if NUMBER_PATTERN.fullmatch(previous):
            if not any(row.get("Superseded by") == number for row in slots.get(previous, [])):
                raise LayoutError(
                    f"{label}: prior projection is inconsistent; {number} claims to supersede {previous} "
                    f"but {previous} is not marked as superseded by it"
                )
            forward.add(previous)
        source = layout.sources.get(number)
        if source is not None and source.supersedes is not None:
            allowed.add(source.supersedes)
    for number, rows in slots.items():
        if any(row.get("Superseded by") in owned for row in rows) and number not in forward:
            raise LayoutError(
                f"{label}: prior projection is inconsistent; {number} is marked as superseded by a record of "
                f"{ticket} that does not claim it"
            )
    return owned, allowed | forward


def check_scope(existing, rendered, allowed, ticket):
    masked_existing, masked_rendered = mask_slots(existing, allowed), mask_slots(rendered, allowed)
    if masked_existing == masked_rendered:
        return
    reason = describe_drift(masked_existing.encode("utf-8"), masked_rendered.encode("utf-8"))
    raise LayoutError(
        f"{ADR_DIR}/{README_NAME} differs from the source records outside the slots owned by {ticket}: "
        f"{reason}; a ticket-scoped render refuses to alter those bytes"
    )


def _remove_temporary(temporary):
    try:
        _unlink(temporary)
    except FileNotFoundError:
        return
    except PermissionError:
        # A temporary that inherited a read-only destination mode cannot be unlinked on Windows
        # until the read-only attribute is cleared.
        os.chmod(temporary, stat.S_IREAD | stat.S_IWRITE)
        _unlink(temporary)


def _cleanup_after_failure(temporary, error):
    try:
        _remove_temporary(temporary)
    except OSError as cleanup_error:
        raise CleanupError(
            f"write of {temporary.name} failed and its temporary file could not be removed: {cleanup_error}"
        ) from error


def write_output(destination, data):
    """Replace one destination atomically via an exclusive sibling temporary (adr/LAYOUT.md)."""
    destination = Path(destination)
    if isinstance(data, str):
        data = data.encode("utf-8")
    try:
        mode = stat.S_IMODE(os.stat(destination).st_mode)
    except FileNotFoundError:
        mode = None
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    for _ in range(64):
        temporary = destination.with_name(f".{destination.name}.{secrets.token_hex(8)}.tmp")
        try:
            descriptor = os.open(temporary, flags, 0o666 if mode is None else mode)
            break
        except FileExistsError:
            continue
    else:
        raise OSError(f"could not create a unique temporary file beside {destination}")
    try:
        if mode is not None:
            os.chmod(temporary, mode)
    except BaseException as error:
        os.close(descriptor)
        _cleanup_after_failure(temporary, error)
        raise
    try:
        with open(descriptor, "wb") as handle:
            handle.write(data)
        if mode is not None:
            os.chmod(temporary, mode)
        _replace(temporary, destination)
    except BaseException as error:
        _cleanup_after_failure(temporary, error)
        raise


def check_layout(root):
    """Validate sources and require adr/README.md to equal the rendered projection exactly."""
    root = Path(root)
    layout = validate_sources(root)
    expected = render_readme(layout).encode("utf-8")
    try:
        actual = (root / ADR_DIR / README_NAME).read_bytes()
    except FileNotFoundError:
        raise LayoutError(
            f"{ADR_DIR}/{README_NAME} is missing; the layout owner regenerates it with an unscoped render"
        ) from None
    if actual != expected:
        raise LayoutError(
            f"{ADR_DIR}/{README_NAME} does not match the rendered layout: {describe_drift(actual, expected)}"
        )
    return layout.summary()


def render(root, ticket=None):
    """Write the rendered README (ticket-scoped when requested); return whether bytes changed."""
    root = Path(root)
    if ticket is not None and not TICKET_PATTERN.fullmatch(ticket):
        raise LayoutError(f"ticket {ticket!r} is malformed")
    layout = validate_sources(root)
    rendered = render_readme(layout).encode("utf-8")
    path = root / ADR_DIR / README_NAME
    try:
        existing = path.read_bytes()
    except FileNotFoundError:
        existing = None
    if ticket is not None:
        if existing is None:
            raise LayoutError(
                f"{ADR_DIR}/{README_NAME} is missing; a ticket-scoped render never recreates the projection"
            )
        try:
            existing_text = existing.decode("utf-8")
        except UnicodeDecodeError:
            raise LayoutError(f"{ADR_DIR}/{README_NAME} is not valid UTF-8") from None
        _, allowed = scoped_numbers(layout, ticket, existing_text)
        check_scope(existing_text, rendered.decode("utf-8"), allowed, ticket)
    if existing == rendered:
        return False
    write_output(path, rendered)
    return True


def split(root):
    """One-time migration of the original monolithic README into the per-file layout."""
    root = Path(root)
    adr = root / ADR_DIR
    try:
        readme = (adr / README_NAME).read_bytes()
        reference = verify_reference((adr / REFERENCE_NAME).read_bytes())
    except FileNotFoundError as error:
        raise LayoutError(f"split requires {ADR_DIR}/{README_NAME} and {ADR_DIR}/{REFERENCE_NAME}: {error}") from None
    legacy = derive_legacy(reference)
    allocations = derive_allocations(reference)
    outputs = [adr / f"{number}.md" for number in legacy] + [adr / MANIFEST_NAME, adr / RESERVATIONS_NAME]
    present = {path.name for path in outputs if path.exists()}
    present |= {path.name for path in adr.iterdir() if path.name.lower().startswith("adr-")}
    if present:
        raise LayoutError(f"refusing to overwrite an already split layout: {', '.join(sorted(present))}")
    if readme != reference.encode("utf-8"):
        raise LayoutError(f"split accepts only the original {ADR_DIR}/{README_NAME} (it must equal the verified reference)")
    for record in legacy.values():
        write_output(adr / f"{record.number}.md", legacy_source(record))
    write_output(adr / MANIFEST_NAME, render_manifest(legacy))
    write_output(adr / RESERVATIONS_NAME, render_reservations(allocations))
    write_output(adr / README_NAME, render_readme(validate_sources(root)))
    return check_layout(root)


def run_tests():
    suite = unittest.TestLoader().discover(str(Path(__file__).resolve().parent / "tests"), "test_adr_layout*.py")
    return 0 if unittest.TextTestRunner().run(suite).wasSuccessful() else 1


def describe_summary(summary):
    return (
        f"{summary['legacy']} legacy records, {summary['allocations']} allocations, "
        f"{summary['published']} published reserved records, {summary['pending']} pending, "
        f"{summary['superseded']} superseded"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="ADR layout generator and validator (adr/LAYOUT.md).")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (
        ("check", "validate sources and require the README to match the rendered projection"),
        ("render", "write the rendered README, optionally scoped to one ticket's slots"),
        ("split", "migrate the original monolithic README into the per-file layout"),
        ("test", "run the stdlib unittest suite for this generator"),
    ):
        command = commands.add_parser(name, help=text)
        command.add_argument("--root", type=Path, default=ROOT, help="repository root containing adr/")
        if name == "render":
            command.add_argument(
                "--ticket",
                help="allocated ticket whose slots may change, e.g. T-ADR-MONEY-01; a declared scope "
                "guard that limits which bytes this render may alter, not authenticated identity",
            )
    args = parser.parse_args(argv)
    if args.command == "test":
        return run_tests()
    try:
        if args.command == "check":
            print(f"ADR layout valid: {describe_summary(check_layout(args.root))}; {ADR_DIR}/{README_NAME} matches.")
        elif args.command == "render":
            changed = render(args.root, args.ticket)
            scope = f" for {args.ticket}" if args.ticket else ""
            state = "updated" if changed else "already matches the rendered layout"
            print(f"{ADR_DIR}/{README_NAME} {state}{scope}.")
        else:
            print(f"Split complete: {describe_summary(split(args.root))}.")
    except (LayoutError, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        cause = error.__cause__ or error.__context__
        while cause is not None:
            print(f"  caused by: {cause!r}", file=sys.stderr)
            cause = cause.__cause__ or cause.__context__
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
