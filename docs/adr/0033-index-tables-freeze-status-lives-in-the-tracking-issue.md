# Index tables freeze; implementation status lives in the spec's tracking issue

**Status:** accepted (spec 102 D7, grilled + agreed 2026-10-05). **Supersedes in part** ADR 0023: its
"process state lives in a regenerated index" half. Its three-value `status:` header half still stands.

**Context.** ADR 0023 moved implementation status out of each document's header and into
`specs/README.md` and `runbooks/README.md`, which it described as **regenerated**. No generator was
ever written. The tables were maintained by hand, and `specs/README.md` stops at spec 47 while specs go up to 59.
Once more than one branch is in flight there is a second problem. Every PR that adds a spec or an ADR appends a row at
the same place (the end of the table), and two such appends are a git conflict. Spec 102 designs fsd for a
future maintainer who works without an agent, so a table that someone has to remember to update is the wrong
place for process state.

**Decision.** **Freeze both index tables, and keep implementation status in the spec's tracking issue.**

- `specs/README.md` gets one last update to spec 59 and is marked "frozen snapshot; for newer specs see
  their tracking issue". Nobody adds rows after that.
- From spec 102 on, every spec has its own tracking issue, and its number *is* that issue's number (spec 102
  D5). The issue's state is the implementation status: open means not done, closed means done.
- `docs/adr/README.md` keeps its introduction and points readers at the directory listing. ADR slugs are
  decision sentences, so the listing is the index.
- New ADRs keep Nygard's sequential `NNNN-` numbering. A CI check fails on a duplicate ADR or spec number
  (spec 102 D6).

**Considered options.** **Write the generator and have CI check that the committed index is fresh.** Rejected:
it is a script to maintain, the generated rows still conflict between two PRs, and "implemented?" would still
need a hand-kept field to generate from. **A generator that prints on demand and commits nothing.** Rejected:
nobody browsing the repo on the web would ever see the index. **Keep hand-editing the tables.** Rejected: that is
the failure this ADR records.

**Consequences.** There is no single table spanning old and new specs. Specs 00–59 are listed in the frozen
snapshot, and newer specs are listed by their tracking issues (Kubernetes KEPs use the same pattern: the
tracking issue is "where the current state of the KEP is being updated"). Nothing can go stale, because
nothing has to be updated by hand. `runbooks/README.md` is covered by spec 102 D8's run-book triage.
