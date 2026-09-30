# PROGRESS — fsd

**Resume anchor.** Read this, then `specs/00-overview.md`. This file is the *current state* plus the
most recent entry — **not the log.** Older entries are moved verbatim to
[`docs/progress-archive.md`](docs/progress-archive.md) (spec 41 D12; split re-run 2026-09-03 for
[#94](https://github.com/nikhilsrajan/fsd/issues/94)). For the narrative — why the code looks like
this — read [`docs/history.md`](docs/history.md).

## Resuming after a break — start here

**Spec 58 P1 + P2 are merged, and P2 is now proven on AML too** — `notebooks/e2e_austria_aml.ipynb`
ran green end to end for `sentinel-1-rtc` on 2026-09-29 (see "Most recent entry": two real bugs,
one fixed in `src/`, one in the notebooks' image extras). The P2 detail that used to sit here (the
AC15 run-book outcome, the Opus review's findings, the S1 notebook prep, D18's wrong Window A) is
archived verbatim as *"2026-09-12 — resume-block snapshot"* in
[`docs/progress-archive.md`](docs/progress-archive.md).

**THE NEXT ACTIONS, in order:**

1. **Commit the main checkout's notebooks** (user). They carry the
   `extras=("local", "azure", "mpc")` fix and now pass `tests/test_notebooks.py` (cleared, and
   blob paths are allowed since `2a70ada` — see "Most recent entry").
2. **Push `main`** (the user's call) — 6 commits ahead of `origin/main` as of 2026-09-29 (the
   bug-1 fix, this `PROGRESS.md` update, the notebook-guard change, and their merges). Until then
   `EnterWorktree` (which branches from `origin/main`) misses them, so make worktrees by hand:
   `git worktree add -b <branch> .claude/worktrees/<name> main`.
3. **Review + merge [spec 59](specs/59-imagery-archive-layout.md) P1** (Opus, `/effort high`) —
   **IMPLEMENTED 2026-09-30 on branch `spec59-p1`** (worktree `.claude/worktrees/spec59-p1`),
   network-free: D2-D11, AC 1-17 covered by `tests/test_spec59_p1.py` (44 tests) plus the existing
   suites migrated to the new contract. `pytest -q` **1214 passed / 105 skipped** (baseline
   1174/105), `ruff check src tests demos examples` clean. Review against spec 59 + repo
   standards, then merge `--no-ff`, close #74 with the merge hash, prune the worktree.
   **Then P2:** the re-download run-book + D12's notebook/doc repointing (Austria S2 + the S1
   blob imagery). Next spec after 59: **#101** (train-vs-inference processing guard).
   What P1 left for P2 on purpose: `docs/tutorial.md` and the committed
   `tests/data/tutorial/` fixture still use the pre-59 catalog (flat folders, no acquisition
   columns) -- `tests/test_tutorial_fixture.py` converts a per-test copy into
   `{root}/sentinel-2-l2a/catalog.parquet`; the tutorial's `catalog_filepath=` line will fail D5's
   preflight until D12 repoints it. Notebooks untouched. Also unverified (spec §5 AC 20): whether a
   blob mid-put kill leaves a partial blob visible under the final name -- the run-book checks it.
   Implementation notes worth knowing: one shared selector `fsd/catalog/processing.py` serves
   `download` (D7) and the builds (D6); granule parsers live in `fsd/collections/{s2_l2a,s1_rtc,hls}.py`
   behind `collections/naming.py` (HLS has parsers but no declaration yet); the venv's editable
   install points at the MAIN checkout, so run tests from a worktree with
   `-o pythonpath=src`.

Standing open items from P2 (not blocking): **D18 needs amending** (Window A is `s2grid=4772924`,
not `476da24`, which has no labels within 47.7 km); D17's `nodata=-32768` is decorative (the build
uses the catalog column's 0 — harmless, pinned by a test); AC11's raise is not catchable through
`create_training_data(runner="local")` (it happens in a Snakemake subprocess). A windowed-read
ingest would cut S1's whole-scene download cost (~3.7 GB/scene) by ~3 orders — not filed.

Test archive: **184 granules / 67.2 GB / `B04,B08,SCL` from MPC**, radiometry correct, **B8A gone**
(P3's AC17 needs it).

**Before trusting anything below, re-verify rather than assume.** Cheap checks:
`.venv/bin/python -m pytest -q` (expect **1173 passed / 104 skipped** on `main` @ `1ba1199` with a
clean notebook — measured 1172 + the one notebook-outputs failure), `.venv/bin/ruff check src tests`, `git log --oneline -5`, `gh issue list`.
A quiet stretch in the git log is a break, not a stall — do not read it as a problem to diagnose.

### ⚠️ Three obligations OUTSIDE this repo, still open

These will not fail loudly until something real runs, so they are recorded here rather than in an
entry that gets archived:

1. **The consumer repo `rise/` will break on its next cluster run.** It installs
   `fsd[azure,aml,mpc,grid]` and builds its image with `extras=("azure","mpc")`. Since **#80**,
   **both need `local` added** — the AML in-job entrypoints run the same Snakemake orchestration a
   laptop does, so without it the image builds fine and the dispatch fails ~30 min in. The image
   digest changes, so **the images must be rebuilt**, not just re-tagged. **Proven 2026-09-29:**
   fsd's OWN notebooks had the same gap and the S1 build died exactly this way (0.05 s per shard,
   not ~30 min in, because the cluster was already warm). `rise/` is still unfixed.
2. **The workspace `CLAUDE.md` dev line still reads `pip install -e ".[dev]"`.** `pytest` passes on
   that, but `docs/tutorial.md` and any `runner="local"` work now need `.[dev,local]`. That file is
   outside the repo, so no commit here can fix it.
3. **The workspace `CLAUDE.md` describes the OLD test archive** — "207 granules, 74 GB, bands
   B04/B08/B8A/SCL", and the radiometry warning that cubes are ~1000 DN high. All of that is stale
   as of **2026-09-07**: the archive is **184 granules, 67.2 GB, `B04,B08,SCL` (no B8A), from MPC**,
   and its radiometry is **correct** (baseline 02.12, offset 0, verified). Also outside the repo.

> **Keep this file small.** D12's target is **~2k words**. It has now blown past that twice, both
> times by accreting `_Previously:_` blocks that nobody deleted. When you add an entry, move the one
> below it into the archive. Entries are **moved, never rewritten** ([ADR 0022](docs/adr/0022-documents-are-point-in-time-or-continuously-true.md));
> the two sections above and below the entry are continuously-true and *are* rewritten.

## Where things stand

**What fsd does today, proven on real infrastructure:** download → datacube → training data →
inference → per-output COGs + STAC, run on a laptop and fanned out across an Azure ML cluster —
and, since **2026-09-02**, driven from a *separate consumer repository* with fsd installed as a
dependency rather than checked out. That run was the goal stated on day one, and it is met.

| | state |
|---|---|
| **Pipeline** | v1 core complete (**Sentinel-2 L2A only**, CDSE + MPC), proven local and on AML. Local test archive re-ingested from MPC 2026-09-07 under P1's schema: **184 granules, `B04,B08,SCL`, no B8A** |
| **Scale-out** | AML runner seam; download, build, flatten and inference all fan out. Reference run `20260729T132222Z`: 18.8 min, 8/8 steps, 97 jobs, 213 granules, 300 grid cells → 300 COGs + STAC + a merged map |
| **Serving** | tier-1 (pre-styled XYZ) and tier-2 (pgSTAC + titiler-pgstac) both validated |
| **Docs** | spec 41 P1–P7 done; `docs/history.md` written and approved 2026-09-02; `src/` changelog comments swept (#85, refs 1,187 → 92) |
| **Current work** | **Imagery archive layout — spec 59 signed off 2026-09-30, P1 implementation next** (THE ORDER step 9). Spec 58 P1 + P2 merged; P2 proven on AML 2026-09-29 (S1 notebook green end to end). P3 (HLS) waits behind the layout spec |
| **Release** | **`v0.1.0` cut 2026-09-04.** SemVer 0.y.z on purpose — the `Source` abstraction does not exist and S1 is coming, so the API will break |
| **Deferred work** | **GitHub Issues**, number-aligned with the old `TODO.md` rows (`gh issue list`) |
| **rslearn** | **decision CLOSED 2026-07-31** — no rslearn for download; rslearn-on-Azure is a separate, unstarted project. `spike/rslearn` stays unmerged |

**What is not met, stated plainly:** the pipeline is **S2 L2A only** (the `Source` abstraction is
implied but does not exist); the **radiometry debt** is fixed in code but still live in the Austria
test archive (cubes ~1000 DN high — fine for infrastructure, not for science); the cluster's
dominant cost is **warm-up, not work** (36 % of the demo run) and nothing has been done about it;
and the pipeline still **dispatches on a hardcoded pair of source names**. The tag is no longer
outstanding: `v0.1.0` was cut 2026-09-04 once both things a tag pins — the dependency set and
the asset layout — had stopped moving.

**Where to look:**

| you want | read |
|---|---|
| how the code is laid out | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| how we got here | [`docs/history.md`](docs/history.md) |
| where fsd is going | [`ROADMAP.md`](ROADMAP.md) |
| what a term means | [`CONTEXT.md`](CONTEXT.md) |
| why a decision was made | [`docs/adr/`](docs/adr/) |
| a measured result | [`docs/findings/`](docs/findings/) |
| an env variable | [`docs/reference/environment.md`](docs/reference/environment.md) |
| open work | `gh issue list` |
| what happened on a given day | [`docs/progress-archive.md`](docs/progress-archive.md) |

## THE ORDER — four tasks, and what follows each (user, 2026-08-28)

The user's standing instruction: **record what comes after finishing a task, so it is not
forgotten at the boundary.** Do not reorder without saying so.

| # | task | done when | → then |
|---|---|---|---|
| ~~**1**~~ | ~~**[#92](https://github.com/nikhilsrajan/fsd/issues/92)** — AZ_ROOT cleanup~~ | **DONE 2026-08-28** — `3a968dc` / `ee7277b`, issue closed + pushed | → **2**, now current |
| ~~**2**~~ | ~~**The consumer-repo run**~~ | **MEASUREMENT DONE 2026-09-02** — `[collect]` 26 s / `[stac]` 10 s vs the 616 s / 161 s baseline; spec 57 §9 step 5 discharged. Spec 56 §9 step 10 discharged by a live `environment_exists` probe | → **3**, now current; **#80 + #82 unblocked** |
| ~~**3**~~ | ~~**[#55](https://github.com/nikhilsrajan/fsd/issues/55)** — spec 43 → `docs/history.md`~~ | **DONE + CLOSED 2026-09-02** — approved, merged, `ARCHITECTURE.md` refreshed alongside | → **4** |
| ~~**4**~~ | ~~**[#85](https://github.com/nikhilsrajan/fsd/issues/85)** — trim the changelog out of `src/` comments~~ | **DONE + CLOSED + PUSHED 2026-09-03** — refs **1,187 → 92 (−92%)**, `816823c` + `c68adba`; swept in one pass, not one package per session, and **extended** to `image/`/`aml/`/`registry/`/`config.py`/`cli.py` | → #93 per this table; **the user chose #94 instead** |

**⚠️ The order changed after step 4 (user, 2026-09-03).** This table said #93 next; the user picked
**#94** (the `PROGRESS.md` split). #93 is not dropped — it keeps the notebook-front-door proposal
and is still the front-door work. Recorded here rather than silently re-sequenced, per the standing
instruction above.

| # | task | done when | → then |
|---|---|---|---|
| ~~**5**~~ | ~~**[#94](https://github.com/nikhilsrajan/fsd/issues/94)** — re-run the `PROGRESS.md` split~~ | **DONE 2026-09-03** — 1,737 lines moved verbatim to the archive; this file **19,970 → 1,762 words**; four defects retired, one of them a test that never ran | → **6**, now current |
| ~~**6**~~ | ~~**[#80](https://github.com/nikhilsrajan/fsd/issues/80)** — snakemake/s3fs → extras~~ | **DONE 2026-09-04** — core 689 → 578 MB; **AML node images need `local` and must be rebuilt** | → **7** |
| ~~**7**~~ | ~~**[#82](https://github.com/nikhilsrajan/fsd/issues/82)** — cut + push `v0.1.0`~~ | **DONE 2026-09-04** — the tag is cut | → **8** |
| **8** | **[spec 58](specs/58-collection-agnostic-verbs.md)** — **CURRENT.** Collection-agnostic verbs: P1 contract → P2 `sentinel-1-rtc` → P3 HLS | **P1 IMPLEMENTED + REVIEWED + MERGED 2026-09-05** (`--no-ff` onto `main`, worktree pruned; **local, unpushed**). Review fixed one real bug + two untested ACs; pytest **1100 passed / 102 skipped**, ruff clean. Re-download run-book **DONE 2026-09-07** (184 granules / 552 files / 67.2 GB, `B04,B08,SCL` @ cc50, **B8A deferred**; 3 real bugs found by running it). **P2 spec amended + SIGNED OFF 2026-09-11** (`6220256`). **P2 DONE + MERGED 2026-09-12** (`795b117`, `--no-ff`, worktree pruned) — 2 real bugs found while implementing (S1 offset derivation, `reference_band=None` never actually built) + 2 more by review (`properties_filter` could not filter an int property; `build_datacube` enforced but never applied it), run-book **green incl. QGIS**, pytest **1169 passed / 104 skipped**, ruff clean. `demos/` + notebook updated for P2; **S1 notebook ran green on AML 2026-09-29** (2 real bugs, see "Most recent entry"). **P3 (HLS) now waits behind step 9** | → **9** |
| **9** | **Imagery archive layout — [spec 59](specs/59-imagery-archive-layout.md)** — **CURRENT (user, 2026-09-29).** `{root}/{collection}/YYYY/MM/DD/{canonical granule name}/`; lossless (ADR 0032): two processings coexist, a build over both raises, `processing=` selects per acquisition; `acquisition_key`/`processing_version`/`processing_datetime`/`source` columns; closes #74 | **spec SIGNED OFF 2026-09-30**; P1 implemented + reviewed, then the P2 re-download run-book | → **#101** spec (processing guard), then **10** |
| **10** | **Contributor readiness** — CI, in-repo `AGENTS.md`/`CONTRIBUTING.md`, branch-safe spec/ADR numbering, conflict-free changelog/progress files, a fresh-clone contributor dry run | **wants its own spec + a clean session** (user, 2026-09-29). Start from memory note `contributor-readiness-kickoff` | → spec 58 **P3 (HLS)** — order vs. step 10 not yet confirmed; P3 could be the first "real contribution" under the new process |
| **11** | **[#93](https://github.com/nikhilsrajan/fsd/issues/93)** — Front door: README → tutorial → how-tos | **wants its own spec** (touches spec 41 D1's audience table + ADR 0026) | → `v0.2.0` is cut after spec 58 P3 |

**⚠️ The order changed again (user, 2026-09-29).** After the S1 AML run the user chose the **archive
layout** as the next task, ahead of P3 and of contributor readiness. Reasons (agreed in-session):
it changes the on-disk format, cheapest while there is one user (no-back-compat policy = every
archive re-downloads); contributor docs would otherwise teach a layout about to break; and P3/HLS
hits the same one-catalog-per-collection wall. Recorded rather than silently re-sequenced.

**⚠️ The order changed again (user, 2026-09-04).** #93 was step 8 and CURRENT; the user promoted
**spec 58** ahead of it after the grilling session. Reason: spec 58 rewrites four verb signatures,
the README and the tutorial, so writing the front door first would document an API about to break
twice. Recorded rather than silently re-sequenced, per the standing instruction.

**Rider on step 2 — DISCHARGED 2026-09-04.** #80 and #82 both landed **inside** `v0.1.0`, as
the rule required. The rule itself (user, 2026-08-26): a tag pins the dependency set *and* the
asset layout, so it waits until both stop moving. **Layout** stopped on 2026-09-02 (the
consumer-repo run); **dependencies** stopped with #80. **#93 was dropped from the tag's
prerequisites** — it is documentation, and docs pin nothing.
**One correction to the rider's own text:** it said #80 *"cannot alter runtime behaviour"*. It
does — an AML node image without `[local]` now fails mid-dispatch. The rider was written from
the issue's "never imported by `src/fsd/`", which is true and still misleads, because the in-job
entrypoints call the local runner. **#79** is wanted-not-blocking; **#81 must not block**.

**Why #92 goes first, not after the run:** it edits `notebooks/e2e_austria_aml.ipynb`'s prose and
`docs/howto/run-at-scale.md`'s config example — cheaper to fix before the run than to re-touch a
notebook that has just been validated.

## Most recent entry

_Last updated: 2026-09-29 (**THE S1 NOTEBOOK RAN GREEN ON AML, end to end — the first AML run of
any kind since ~08-27.** `notebooks/e2e_austria_aml.ipynb` with `COLLECTION="sentinel-1-rtc"`
(cell `s2grid=4772924`, 2018-06-01 → 07-01, ascending, T=3, 43 fields) ran download → datacube →
training data → RF → verify_adapter → bundle → verify_image → deploy → inference, and
`build_images.ipynb` ran alongside it. Run folder `demo-20260928T142634Z`. Getting there took **two
real bugs, both invisible to the green suite**. Next task chosen: **the imagery archive layout
spec** — see THE ORDER.)_

_**Bug 1 — the AML download leg ignored `collection` and `properties_filter`** (fixed `19b5ad8`,
merged `1ba1199`). `api.download`'s `runner="aml"` branch forwarded neither to
`run_aml_download`, which had no such parameters, so driver-side MPC discovery
(`discover_shard_rows`) fell back to its `sentinel-2-l2a` default and raised *"band 'vv' is not
available on item S2B_MSIL2A_…"*. `create_training_data` also dropped `properties_filter` on its way
to the download, which would have fetched BOTH orbits (~2× the bytes). P2's run-book proved S1 on
the **local** runner only; the local branch forwarded both. Fix: forwarded at all three hops,
`discover_shard_rows` applies the filter before rows exist (so `max_tiles` counts post-filter), four
forwarding tests in `tests/test_spec58_p2.py`. The same class as 09-07's `max_concurrent` bug: **a
kwarg added to a verb is only as real as its least-tested runner branch.** Checked in code: the
build / verify_adapter / inference AML legs are NOT affected — all three go through
`create_datacube.setup` on the driver, which filters and writes `declaration.json` for the nodes._

_**Bug 2 — the notebooks' node images had no Snakemake.** Every build shard died 0.05 s in:
*"the Snakemake runner needs the optional '[local]' extra"*. #80 (09-04) moved `snakemake` to
`[local]` and updated `docs/howto/build-the-images.md`, and THE ORDER row 6 below even says **"AML
node images need `local` and must be rebuilt"** — but both notebooks' `ImageDefinition` still read
`extras=("azure", "mpc")`, and no AML build had run since to notice. Fixed to
`("local", "azure", "mpc")` in `build_images.ipynb` and `e2e_austria_aml.ipynb` (**uncommitted in
the main checkout** — see below) and the images rebuilt. Downloads had worked only because download
jobs never touch Snakemake. Also found: a failed shard's `_status/<k>.json` said only `"snakemake
exited 1"` for the first diagnosis attempt — the real error needed the AML job log. Not filed yet._

_**Pinning the old images was sound, and is a reusable trick:** a fix that changes only driver-side
code (`api.py`, `run_aml_download`, `discover_shard_rows`) leaves node behaviour identical, so the
run can pin the previously-built AML env versions instead of `ensure_environment` (which STARTS an
ACR build on any `src/` change) and rebuild once at the end. It did not help here only because those
images lacked `[local]` anyway._

_**Policy change (user, 2026-09-29): blob paths may be committed.** The S1 notebook hardcodes
`AZ_ROOT` as a literal `abfss://…` path; the user ruled that storage account / container / blob
paths are safe to expose (no access without a credential) and that environment variables for them
are clunky — **no `AZ_ROOT` env var going forward**. `tests/test_notebooks.py` was changed to match
(`2a70ada`): the storage-URL pattern is gone and the email pattern no longer mistakes
`abfss://container@account…` for an address; GUIDs, emails, home dirs and rg/workspace/cluster
names stay forbidden. ⚠️ This **contradicts the workspace `CLAUDE.md`** ("never copy [concrete
infra] values into anything under `fsd/`") — that file is outside the repo and needs amending.
Also learned: VS Code's "Clear All Outputs" keeps `execution_count`, which the guard rejects —
RECIPES.md has the one-liner that clears both._

_**Two directions assessed and parked in memory for their own sessions** (not in-repo yet):
(a) **download path layout** — `imagery/` is flat per run, MPC and CDSE use different layouts and
ids for the same granule, one catalog file = one collection. Prior art (Landsat product-id split,
Earth Search replace-on-same-id, ODC archive-not-overwrite, EODAG provider priority, STAC
`processing:*`) supports `{archive}/{collection}/{acquisition_key}/`, whole-granule
replace-or-refuse, latest processing wins, first-class `source` + `processing_version` columns.
⚠️ Same acquisition ≠ same bytes (MPC's 2018 S2 is the 2020 reprocessing), so a naive collision
would union bands from two processings under one row's `offset`. **(b) contributor readiness** —
no CI, no in-repo `AGENTS.md`/`CONTRIBUTING.md`, spec/ADR numbering and `PROGRESS.md`/`CHANGES.md`
are branch-conflict magnets. **A YAML collection registry was assessed and rejected for now**: a
collection is already a ~40-line pure-data Python declaration; verifiability is the bottleneck._
