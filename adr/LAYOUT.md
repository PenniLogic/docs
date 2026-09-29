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

## Generator ownership and commands

Decision authors edit only their own source, then run, for their allocated ticket:

```text
python -B scripts/validate_adr_layout.py render --ticket T-ADR-MONEY-01
python -B scripts/validate_adr_layout.py check
```

Ticket-scoped generation refuses to alter bytes outside that ticket's slots and
the derived slots of its previous and current predecessors. Before restoring an
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
source/header/schema consistency, owner claims and the complete replacement graph.
It does not establish that all later published records are present. Stop if this
check fails, the inventory differs unexpectedly, accepted source/header bytes or
modes have changed, or any retained work lacks an agreed owner. Restore missing
inputs only from reviewed/retained evidence with the affected owners; never guess,
rewrite pins, drop an allocation or rebuild the historical manifest to match drift.

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
retained initial source, allocation file and manifest against this reconstruction,
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
injected mid-split failure and this isolated reconstruction, not real process death.

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

The stdlib-only suite uses the real pinned migration bodies and original owners,
not candidate manifests as expected values. Nine independent ordinary branches
are committed from one split baseline. Forward, reverse, alternating, and both
orders of every adjacent pair are serially squash-merged and committed, checking
strict validation, exact rendering, owner retention and cumulative source sets
after every merge. No custom/union merge driver or discarded first squash is used.
A separate same-predecessor test expects textual conflict and semantic rejection.
Depth-1 clones use local `file://` transport and exercise a committed candidate,
including a negative candidate, with no parent history or network.
