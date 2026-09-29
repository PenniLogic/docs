# September 29 public-organization migration

The original organization is `PenniLogic-old` (ID `323571547`).
The new public Free organization is `PenniLogic` (ID `335295566`).
The old repositories, Git histories, private discussions, workflow runs and
unmerged work remain there unchanged. No source repository was transferred.

Each new repository contains `migration-source.json`, recording the pinned old
main commit and exported files. Only the API had accepted executable application
code on old main: the Kotlin/Ktor health scaffold. AI-service, Android, Web,
Admin and Contracts still require their product/scaffold delivery. Old unmerged
scaffolds were deliberately not declared accepted by copying them here.

The imported product documents and ADRs retain their original dates and
limitations. Historical GitHub issue, PR and project URLs point to the old
organization. Bare issue numbers in historical planning documents are old
identities, not new public issues. The current public operating policy is
[governance/DELIVERY.md](governance/DELIVERY.md) and generated repository guidance.
Older planning gate descriptions are historical evidence, not activation of
the retired check-publishing or self-hosted system in this organization.

## Backlog

`planning/backlog.json` preserves all 427 old board-card identities, titles,
repositories, statuses and sizing metadata without copying issue discussions.
`planning/source` preserves the accepted product backlog specification and
schemas. The new delivery project imports unfinished cards as drafts with source
provenance; historical Done cards stay in the complete snapshot. A draft is not
a duplicate GitHub issue or an implementation.
Convert a selected card to an issue in its owning public repository when work
starts, retaining its stable source identity. Historical Done statuses are not
new release acceptance; use the original evidence and the migrated source.

No old generated governance artifacts, self-hosted runner controller, credential
transport helpers, private check-publishing scripts or archived execution logs
are part of the new baseline. The native hosted `CI` job reports actual checks;
non-executable repositories explicitly report foundation checks only.

## Local checkouts

New repositories are in the `public` subdirectory of the existing local
collection. Existing checkouts and old sessions are retained. Before any future
push from an old checkout, verify its remote repository's numeric identity:
the old URL now names a different organization. Never use an old session's stale
`PenniLogic/...` app association as proof that it targets the new public code.

No open-source license was chosen during this migration. Publication of owned
source does not authorize copying third-party material without its license.
