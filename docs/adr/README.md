# Architecture Decision Records

Each ADR captures one significant, lasting decision: its context, the decision, the options
rejected, and the consequences. Numbers are immutable; supersede a decision with a new ADR that
references the old one rather than editing history.

Most ADRs `0003`–`0019` were back-filled from the specs, the old DROPPED file, `ROADMAP.md`, and the
runbooks — the decision was already made and recorded there; the ADR gives it a single canonical
home. The cited spec/date is the source of record.

## The index is this folder's file listing

There is no table here any more. Each file name is `NNNN-<the decision as a sentence>.md`, so the
folder listing reads as the index: open [`docs/adr/`](./) on GitHub, or run `ls docs/adr/`. Each
ADR's own **Status** line says whether it is accepted or superseded, and by what.

The table this file used to hold was frozen and removed in spec 102 P3b (ADR
[0033](0033-index-tables-freeze-status-lives-in-the-tracking-issue.md)): every new ADR appended a
row at the same place, so two PRs adding an ADR always conflicted, and nothing kept it current. The
last version (ADRs 0001–0032) is `git show d4c05a0:docs/adr/README.md`.

## Adding an ADR

Copy [`TEMPLATE.md`](TEMPLATE.md) to the next free number. If two PRs take the same number, the
one that merges second renumbers; CI fails on a duplicate.
