# Contributing to fsd

Code is MIT; by opening a PR you license your contribution under the repo's terms (GitHub ToS §D.6,
inbound = outbound). No CLA, no sign-off line. Agents: also read `AGENTS.md`.

## Setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev,local]"
.venv/bin/python -m pytest -q && .venv/bin/ruff check src/ tests/
```

## Every change is a pull request that passes four gates

`main` is protected: no direct pushes. Work on a branch and open a PR from the template.

1. **CI green**: ruff, the fast pytest suite, the guard tests, `scripts/docs_kwarg_sweep.py`.
2. **Linked issue.** Changing a convention, an on-disk format or the public API also needs a signed-off
   short spec (`specs/TEMPLATE.md`; its number is its tracking issue's number). Bug fixes, refactors, docs and
   a new collection that follows `docs/adding-a-source.md` need only the issue.
3. **Reviewed by someone other than the author**, as a PR comment. Every finding is fixed in the PR or
   filed as an issue.
4. **Real-run evidence** when you touch real data, the cloud or pixels: paste the output or a screenshot
   (QGIS). No archive or Azure access? Say so; the reviewer runs it.

The PR title becomes the release-note line. The maintainer labels and merges (merge commit).

## Conventions

- Specs and ADRs: copy `specs/TEMPLATE.md` / `docs/adr/TEMPLATE.md`. ADR numbers are sequential; if two
  PRs pick the same number, the one that merges second renumbers (CI fails on duplicates).
- Keep the living docs true in the same PR (`README.md`, `ARCHITECTURE.md`, `CONTEXT.md`,
  `LIMITATIONS.md`, `ROADMAP.md`, `docs/`). Specs, ADRs and run-books are point-in-time.
- `TODO #NN` in old text = GitHub issue #NN. File deferred work as an issue.
- Call a MGRS tile (the ~110 km source granule) and a grid cell (the ~5 km ROI subdivision) by those
  names; never a bare "tile". See `CONTEXT.md`.

## Review checklist

Each line points at the incident that taught it.

- [ ] **Real run, not just green tests.** Synthetic fixtures encode today's assumptions (spec 50: a real run
  found stale `input.csv` rows adopted and a ~3600-call serial blob sweep after two clean reviews).
- [ ] **Verify the primitive a spec cites.** A docstring or our own issue is not evidence (#74: "no `.part`
  here" missed that `fs.transfer` was already atomic).
- [ ] **Test the serialization boundary.** Shard CSVs and `input.csv` retype values (`"05.00"` becomes `5.0`);
  test the round trip, not the in-memory rows.
- [ ] **Address per unit path.** Never hash a set; watch control files written once per run (spec 58 D13).
- [ ] **Doc call sites rot silently.** pytest never runs a notebook cell; `scripts/docs_kwarg_sweep.py` does
  (four dead `scl_mask_classes=` call sites after spec 58 P1).
- [ ] **Prior art.** If the mechanism is homemade, does the PR say what standard practice it replaced?
- [ ] **Spec vs. code.** Was the spec checked against fsd's own code, not only against its sources?
- [ ] **A lesson becomes a check.** If review caught a class of bug, did the PR add a test or guard for the class?

## Maintainer tasks

- **Merge** with a merge commit once the four gates hold; apply one label (`breaking`, `feature`, `fix`,
  `docs`, `internal`). After merging, fast-forward local `main` and delete the branch and worktree.
- **Branch protection** (Settings → Branches → `main`): require a pull request, require the `test` status
  check, **no required approvals** (authors cannot approve their own PRs), merge commits only, no direct pushes.
- **Release.** Tag `v0.y.z` when there is something worth shipping; `breaking` bumps `y`, everything else bumps `z`.
  Create the release with "Generate release notes" (`.github/release.yml` groups by label). Only the maintainer
  edits the `pyproject.toml` version.
- **Weekly CI run** (Mondays, on `main`): a failure opens an issue. Fix it by pinning a range in `pyproject.toml`
  with a comment saying why. GitHub disables scheduled runs after 60 days without repository activity.
- **Shared cloud aliases** (`current`, `champion`, `demo-*`) move only from `main`, and only the maintainer
  moves them. Teammates with Azure access use a personal namespace (`dev-<user>`).
- **Orders of work:** milestones plus one pinned "Order of work" issue replace the old progress log.

## Maintainer handover

1. Transfer the repo to the `nasaharvest` org (needs repo-create permission there; old links redirect, and the
   redirect is lost if a repo is ever created at the old name).
2. Branch protection and CI move with the repo; check the weekly failure still opens an issue.
3. The successor gets their own `rise` access through the platform admin; shared aliases and blob roots are
   in `AZURE_INFRA.md`.
4. Hand private values (resource group, workspace names) over privately; never commit them.
5. Dry run: a fresh agent session or the successor takes a `good first issue` to a green PR using only these docs.
   Every question it has to ask becomes a doc fix.
