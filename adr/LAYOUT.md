# ADR layout and migration contract

This is the file-format and generator specification for `T-ADR-INDEX-10`, not an
architecture decision or a change to repository review/merge policy.

## Preserved migration reference

`presplit-reference.md` is the raw `adr/README.md` blob from source commit
`3daa2d7a2ab3ac3f17eecbfff9e9ae8c485b5ccf`.

- Original Git blob OID: `99707073a05034863522763c18bb38d2ad5fc81f`
- Original raw SHA-256: `995641e20e49dc13c2074f15fff4515c9f4ca78a5b2b2beced39fcb2c62314fd`

The migration checker pins both identifiers, verifies the reference bytes, and
derives all fourteen original bodies and the nine original allocations from those
bytes. It requires complete ADR-001 through ADR-014 and ADR-015 through ADR-023 sets.
`legacy-bodies.json` is an independently checked manifest, not the baseline.
Neither candidate HEAD manifests nor parent history are trusted as baselines.
There is no fallback or network fetch.

The unchanged reference blob is part of the current tree, so a normal depth-1
checkout contains it. Validation reads and hashes the local file; it does not need
the original commit object or `HEAD^`. Reviewers with the original source can
verify `git show 3daa2d7a2ab3ac3f17eecbfff9e9ae8c485b5ccf:adr/README.md`
against these pins. `git rev-parse HEAD:adr/presplit-reference.md` in a committed
candidate yields the original blob OID.

This is a bounded migration-integrity check under ordinary code review trust.
An operator who rewrites the checker and its pins can bypass it. It is not
cryptographic reviewer identity, independent approval, or proof of authorship.

## Sources and schema

Each source is UTF-8 with LF line endings, named exactly `ADR-###.md`. Its header
requires `number`, `title`, `status`, `date`, `supersedes`, and `superseded-by`.
New (nonlegacy) records also require `ticket`, matching their explicit allocation.
For example, ADR-015 must claim `ticket: T-ADR-MONEY-01`. Missing, malformed and
wrong-owner claims fail. The legacy fourteen must not acquire invented ticket data.

The body starts with its one matching `## ADR-### — Title` heading. Its one
`**Status:** STATUS · YYYY-MM-DD` line must match the header's recorded status/date.
Existing historical annotations after the date are preserved. The date must be a
canonical valid calendar date. Status is `PENDING`, `ACCEPTED`, or `SUPERSEDED`.
Duplicate/unknown header fields and malformed references fail.

Both JSON documents support only integer `schema_version: 1`, their declared item
fields and correct scalar types; duplicate JSON keys and duplicate numbers fail.
Allocation `state` remains `PENDING`; effective state is derived, not stored back.
An explicit reviewed addition to `reservations.json` may allocate a number above
023. It may not remove/reassign/change the original nine allocations or allocate
a legacy number. A new record with no allocation always fails.

Text that reaches the generated README — a source `title` and an allocation's
`question` and `blocks` cells — must be one trimmed line of printable code points
(`str.isprintable()`): control characters including CR, LF and TAB, the no-break
space, Unicode line and paragraph separators, bidirectional overrides and every
other non-printable code point are rejected, as are the HTML comment delimiters
`<!--` and `-->` that could forge slot markers; a cell may not contain `|`. The
check applies before any write, so `render` never emits such text and `check`
rejects it in an existing file.

Legacy source title, recorded status/date, null relationship fields and decision
bytes remain frozen. The owner-approved file-boundary exception replaces only the
terminal run of LF separator bytes with exactly one LF, matching the existing
pre-commit EOF rule. Interior whitespace, line endings, punctuation and content
are not normalized. The complete pre-split reference and its historical body
hash/length inventory remain byte-exact; validation derives the expected split
body from that pinned reference and rejects any other change, including a missing
or extra final LF. `split` accepts only the original README and verified reference;
it refuses to overwrite an already split layout.

## Replacement relationships

The new record's `supersedes` link is the authoritative replacement claim. A valid
successor must be decided, not PENDING, and must name an existing decided source.
The predecessor needs no edit. Reverse links and effective `SUPERSEDED` status are
derived for both generated index and pending-table slots. Its recorded status/date
and original body stay unchanged.

Each predecessor has at most one direct successor. Self-links, dangling links,
cycles, PENDING replacements, and competing successors fail. An explicit
`superseded-by` is an optional assertion (otherwise `null`); if supplied it must
agree with a successor's forward claim. Recorded `SUPERSEDED` without a valid
successor fails. Chains are allowed; every replaced member is effectively
SUPERSEDED, and only the terminal accepted member is currently ACCEPTED.

## Accepted-record integrity

An accepted record is the authority every downstream ticket implements, so a
change to it that is not visible in the index is tampering with the plan (STRIDE
finding E26-F16, `governance/threat-model/records/E26.json`). A *decided* record
is a non-legacy source whose recorded status is `ACCEPTED` or `SUPERSEDED`. The
legacy fourteen are frozen by the pinned reference and need none of this.

Every decided record carries its `**Status:** STATUS · YYYY-MM-DD` line (above) and
names its proving tests: some heading (`##` to `####`, not the record heading) whose
text contains the word `test` or `tests`, with at least one backticked test or
fixture name in that section's prose (a sub-heading of the section counts; text
inside fenced code does not). Every such heading is examined and the first
section that names a test satisfies the rule; the error lists the sections that
were examined. A draft with `status: PENDING` may still lack the section.

Every fenced ```` ```json ```` block of a non-legacy record, draft or decided,
must parse as RFC 8259 JSON — no duplicate keys, no `NaN`/`Infinity`/`-Infinity`
literals, no number that overflows a binary64 to infinity, no lone-surrogate
`\uD800`–`\uDFFF` escapes — and a block whose top
level is an
object must declare a version field — `version` or any `*_version`/`*-version` key
holding a non-empty string or a positive integer (`schema_version`,
`policy_version`, `parameters_version`) — so the machine-readable artefacts that
dependent tickets consume cannot rot silently. The same parser reads the layout's
JSON documents. Arrays and scalars (templates of
externally specified files, value lists) are exempt from the version rule. One
block decided before this rule, ADR-020 §10, is admitted by an explicit pin on its
record and content digest in `scripts/validate_adr_layout.py`; the pin dies the
moment the block changes, and the dated amendment then declares `schema_version`.
Errors name the record, the block ordinal and its line.

`accepted-records.json` is the acceptance registry: `schema_version: 1` and one
item per allocation, in allocation order, `{number, date, sha256, bytes}`; the
three values are the record's date and the SHA-256 and length of its complete
source bytes, or all `null` while the number has no decided record. Entries are
fixed like README slots, so concurrent landings change disjoint lines. `check`
requires the file to be canonical and every decided record to be registered with
its current bytes, and fails naming the record when: a decided record is not
registered (its owner runs `render --ticket`); the bytes changed with the same
date (*accepted record edited without a date change*); the bytes changed with a
later date but the entry is stale (*amended on …; re-registers with render*); the
date moved earlier; or a registered record now records `PENDING` or is missing
(*a decided record is superseded, never withdrawn*). `render` writes only a first
registration or an amendment dated strictly later than the registered date; it
refuses every other change before writing a byte, and `--ticket` restricts the
entries it may change to the ticket's numbers while every other entry must
already agree with its source.

A superseding record leaves the predecessor's bytes, and therefore its entry,
unchanged. Recording the supersession on the predecessor (`status: SUPERSEDED`,
`superseded-by`) is itself a change and carries a later date. Before a pull
request merges, the registry entry of its record is a proposal: after editing a
decided record the branch already registered, restore `accepted-records.json`
from the base branch and render again, or keep the draft `PENDING` until its
final round. After the merge the registered bytes are the accepted decision.
The registry is a ledger, not a projection: when it is damaged or missing while
decided records exist, restore it from the reviewed commit; `render` refuses to
overwrite a damaged registry or to recreate a missing one over decided records,
and creates it only for a layout with no decided record (the initial split). A
scoped render never creates it. The one-time bootstrap of this rule registered
the six records accepted before it as they stood on `main`.

This is a content-hash pin under ordinary code-review trust, like the migration
pins: a change to the registry is visible in review, and an operator who rewrites
the checker or the registry bypasses it. It does not identify who decided.
Recommended for records decided after 2026-09-30, not yet enforced: a line
`**Decided by:** PenniLogic/docs#<PR>, reviewed commit <sha>` naming the pull
request whose independent reviews accepted the record. Enforcement is a later
dated change once the six records accepted before this rule carry the line.

## Generator ownership and commands

Decision authors edit only their own source, then run, for their allocated ticket:

```text
python -B scripts/validate_adr_layout.py render --ticket T-ADR-MONEY-01
python -B scripts/validate_adr_layout.py check
```

Ticket-scoped generation refuses to alter bytes outside that ticket's slots and
the derived slots of its previous and current predecessors, and outside that
ticket's registry entries. Before restoring an
earlier supersession effect, the generator reconstructs the prior owned-record
links from the existing index and validates the whole unowned projection against
the unchanged source records. Malformed relationships or unrelated index drift
remain errors; retargeting or removing an uncommitted supersession does not require
unscoped generation. It validates sources before writing. This prior projection
is a consistency check, not independently authenticated edit history.
The `--ticket` argument is a declared scope guard, not authenticated
identity. The layout owner uses unscoped `render` for migration/layout maintenance.
No one edits generated bytes manually. Exact-output validation detects drift;
it cannot infer whether identical generated bytes were produced by a human.

### Per-file replacement and failure boundary

`T-ADR-REC-01` hardens the shared output writer, not the source format. Each write
exclusively creates a unique sibling temporary file. For an existing destination,
the temporary's creation permissions are no broader than the destination's access
bits, and its mode is applied before any content is written. Failure to prepare
that mode refuses the write. The writer writes UTF-8 without a BOM and without
newline translation, closes the file, restores the final destination mode (writes
can clear special permission bits), then uses `os.replace` to replace that one
destination. Generated text remains LF. New files retain ordinary text-file
creation permissions (0666 filtered by umask on POSIX, platform defaults on Windows),
not a new 0600
convention. Other metadata, ACLs, ownership, timestamps and hard-link identity are
not preserved by this replacement contract; use ordinary repository files.

Before replacement succeeds, write/encoding/close/mode failures leave the old
output intact. A replacement failure that leaves the destination untouched also
retains it. Errors propagate; the CLI reports filesystem failures as `ERROR` with
exit 1. Cleanup removes only the operation's own temporary path, including a
read-only temporary on Windows. Cleanup failure is also an error, not success.
When an operation and cleanup both fail, the CLI includes the causal exception
chain as well as the final error; retain both diagnostics and inspect only the
owned path, never sweep temporary patterns.

This is single-file atomic replacement, not a multi-file transaction. `split`
still writes several files in sequence and can leave a partial layout. There is
no fsync/power-loss durability guarantee, automatic recovery after process death,
or guarantee for arbitrary simultaneous writers or other same-user processes.
Stop competing writers during recovery. Serial Git integration of disjoint
branches is not concurrent writing to one worktree.

Ordinary additions affect only their own preallocated slots. Supersession also
affects derived predecessor slots: declare these effects, coordinate ownership,
and serialize any overlap. Two branches superseding the same predecessor are
not conflict-free; neither a union merge nor regeneration resolves competing
decision semantics. Do not change the predecessor source to satisfy the checker.

## Bounded recovery and rollback

### Missing or truncated generated README

The layout owner, not an individual ticket author bypassing the scope guard,
performs recovery. Stop writers and affected workstreams; retain a separate copy
and byte/mode inventory of the entire current `adr` directory, including damaged
output and unrelated uncommitted work. Compare the retained sources and allocation
extensions against the reviewed commit and any recorded in-progress work. Do not
assume that a missing nonlegacy decision can be detected by the original fourteen
body pins; confirm the complete expected source inventory with its owners.

Validate retained inputs without relying on the damaged index, from the repository
root (stdlib only):

```text
python -B -c "import sys; from pathlib import Path; sys.path.insert(0, 'scripts'); import validate_adr_layout as adr; adr.validate_sources(Path.cwd())"
```

This checks the pinned raw reference, original body inventory and allocations,
source/header/schema consistency, owner claims, the proving-tests and fenced-JSON
rules and the complete replacement graph.
It does not establish that all later published records are present, and it does
not read the acceptance registry. Stop if this
check fails, the inventory differs unexpectedly, accepted source/header bytes or
modes have changed, or any retained work lacks an agreed owner. Restore missing
inputs only from reviewed/retained evidence with the affected owners; never guess,
rewrite pins, drop an allocation or rebuild the historical manifest to match drift.
Restore a damaged or missing `accepted-records.json` from the reviewed commit in
the same way; regenerating it from the current sources would launder an undated
edit, so `render` refuses to overwrite a damaged registry or to recreate a
missing one while decided records exist.

Once preservation and input checks succeed, the layout owner may regenerate only
the derived README without consulting its damaged prior projection:

```text
python -B scripts/validate_adr_layout.py render
python -B scripts/validate_adr_layout.py check
pwsh -NoProfile -File planning-automation/validate-backlog-v2.ps1 -Quiet
```

Compare every retained non-README file byte-for-byte and mode-for-mode afterward;
none should change. Verify existing README mode is retained (a missing file uses
normal creation permissions). A second render must produce identical README bytes.
Retain the recovery diff and validation evidence for review before resuming work.
Do not manually repair generated slots or force a ticket-scoped render through a
missing/truncated prior projection. A failed recovery remains stopped.

### Partial initial split

Do not restore the raw monolith over the working README and rerun `split` in place:
its original-README guard is not an inventory check for later work. Preserve the
partial directory first. If all source inputs already exist and validate, use the
README-only recovery above, even if the current README is still the raw monolith.

If inputs are missing, reconstruct the initial layout in a **separate empty scratch
repository directory** using the same reviewed script and only the verified raw
reference as both `adr/presplit-reference.md` and the initial `adr/README.md`. Run
`split --root <scratch-root>` and `check --root <scratch-root>` there. Compare every
retained initial source, allocation file, manifest and the empty acceptance
registry against this reconstruction,
including headers and bodies. Existing files must not be replaced just because a
reconstruction is available. Stop on any differing retained source, downstream
record, allocation extension or uncertain inventory; coordinate preservation with
its owner instead of treating it as disposable initial-split output.

Only for a confirmed initial-only partial split with matching retained files may
the layout owner copy individually identified missing initial files from the
validated reconstruction, preserving their modes. Do not copy its README over the
working directory. Validate the now-complete working inputs, then use unscoped
README regeneration and the preservation checks above. The pinned reference and
historical manifest never become repairable candidate baselines. Tests exercise an
injected mid-split failure and this isolated reconstruction, not real process death
(`scripts/tests/test_adr_layout_exercises.py`, `SplitRecoveryTests`).

### Reverting the migration

Before dependent decisions exist, rollback of the split is a separately reviewed
**protected revert** through the repository's normal gates, followed by validation
before resuming work. After dependent decisions exist, stop affected workstreams
and review a **preservation migration** instead. Never use a simplistic revert
that loses accepted decisions, their source headers/bodies, original allocations,
the raw reference or historical body-hash manifest. Review duration is not a fixed
recovery-time guarantee. Reverting this writer hardening alone restores in-place
writes; it neither repairs damaged output nor rolls the ADR layout back.

## Validation

```text
python -B scripts/validate_adr_layout.py test
pwsh -NoProfile -File planning-automation/validate-backlog-v2.ps1 -Quiet
```

The stdlib-only suite (`scripts/tests/test_adr_layout.py` and
`scripts/tests/test_adr_layout_exercises.py`) uses the real pinned migration
bodies and original owners,
not candidate manifests as expected values. Nine independent ordinary branches
are committed from one split baseline. Forward, reverse, alternating, and both
orders of every adjacent pair are serially squash-merged and committed, checking
strict validation, exact rendering, owner retention and cumulative source sets
after every merge (`SquashMergeMatrixTests`), and again onto a main that already
holds two published records and one supersession
(`SquashMergeMatrixOnPublishedFixtureTests`). No custom/union merge driver or
discarded first squash is used.
A separate same-predecessor test expects textual conflict and semantic rejection.
Depth-1 clones use local `file://` transport and exercise a committed candidate,
including a negative candidate, with no parent history or network
(`ShallowCloneTests`): the positive candidates are the baseline and the two-record
fixture; the negatives are a hand-edited generated slot and an undated edit of an
accepted record, which the committed registry alone reveals in a one-commit clone.
Planted negatives for the accepted-record rules (`RegistryTests`,
`ProvingTestsTests`, `JsonBlockTests`) live in scratch fixtures, never in a
committed record. The git exercises spawn about three hundred git processes; they
run in seconds on a Linux runner and are bound by process creation on Windows.
