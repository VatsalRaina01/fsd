# PROGRESS — fsd

**Resume anchor.** Read this, then `specs/00-overview.md`. This file is the *current state* plus the
most recent entry — **not the log.** Older entries are moved verbatim to
[`docs/progress-archive.md`](docs/progress-archive.md) (spec 41 D12; split re-run 2026-09-03 for
[#94](https://github.com/nikhilsrajan/fsd/issues/94)). For the narrative — why the code looks like
this — read [`docs/history.md`](docs/history.md).

## Resuming after a break — start here

**Spec 58 P1 is landed and its re-download has run green. The next action is spec 58 P2.**
P1 merged to `main` 2026-09-05 (review found one real bug and two untested ACs); the
re-download run-book ran **2026-09-07**, all steps green including the QGIS eyeball, and found
**three more real bugs** that two review passes had missed — see "Most recent entry". `main` is
clean, no unmerged branches except `spike/rslearn` (intentional). **`v0.1.0` is cut and pushed.**
⚠️ **`main` is ~12 commits AHEAD of `origin/main` — everything since P1 is unpushed.**

1. Read this file top to bottom. It is ~2k words by design; it is the whole picture.
2. **Push `main`**, then start spec 58 **P2** (`sentinel-1-rtc`) — unblocked, since the schema
   change is landed and there is real data behind it.
3. ⚠️ **The test archive changed shape**: it is **184 granules / 67.2 GB / `B04,B08,SCL`** from
   **MPC** (not the old 207-granule, 74 GB, four-band CDSE one). **B8A is gone** — full fidelity
   measured ~117 GB against ~110 GB of headroom. `demos/e2e_austria.py` still requests B8A and
   would fetch ~28 GB more; spec 58 **P3's AC17 needs it** (`nir08` **is** B8A), so that pass is
   deferred, not avoided. The radiometry is now **correct** (baseline 02.12 → offset 0, verified).
4. `gh issue list` — the open work. Nothing here is blocked on a decision you have to remember.
5. Otherwise pick from **THE ORDER** below, which is still sequenced.

**Before trusting anything below, re-verify rather than assume.** Every dated claim was true when
written. Cheap checks (on `main`, spec 58 P1 + the re-download's three fixes merged):
`.venv/bin/python -m pytest -q` (expect **~1109 passed / 103 skipped**; a worktree run with
`PYTHONPATH=src` collects a few fewer `test_docs.py` params -- same passes either way),
`.venv/bin/ruff check src tests demos examples`, `git log --oneline -5`, `gh issue list`.
A quiet stretch in the git log is a break, not a stall — do not read it as a problem to diagnose.

### ⚠️ Three obligations OUTSIDE this repo, still open

These will not fail loudly until something real runs, so they are recorded here rather than in an
entry that gets archived:

1. **The consumer repo `rise/` will break on its next cluster run.** It installs
   `fsd[azure,aml,mpc,grid]` and builds its image with `extras=("azure","mpc")`. Since **#80**,
   **both need `local` added** — the AML in-job entrypoints run the same Snakemake orchestration a
   laptop does, so without it the image builds fine and the dispatch fails ~30 min in. The image
   digest changes, so **the images must be rebuilt**, not just re-tagged.
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
| **Current work** | **spec 58** — P1 landed and its re-download ran green 2026-09-07; **P2 `sentinel-1-rtc` is next and unblocked**. See THE ORDER below |
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
| **8** | **[spec 58](specs/58-collection-agnostic-verbs.md)** — **CURRENT.** Collection-agnostic verbs: P1 contract → P2 `sentinel-1-rtc` → P3 HLS | **P1 IMPLEMENTED + REVIEWED + MERGED 2026-09-05** (`--no-ff` onto `main`, worktree pruned; **local, unpushed**). Review fixed one real bug + two untested ACs; pytest **1100 passed / 102 skipped**, ruff clean. Re-download run-book **DONE 2026-09-07** (184 granules / 552 files / 67.2 GB, `B04,B08,SCL` @ cc50, **B8A deferred**; 3 real bugs found by running it). Next: **P2 `sentinel-1-rtc`** | → **9** |
| **9** | **[#93](https://github.com/nikhilsrajan/fsd/issues/93)** — Front door: README → tutorial → how-tos | **wants its own spec** (touches spec 41 D1's audience table + ADR 0026) | → `v0.2.0` is cut after spec 58 P3 |

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

_Last updated: 2026-09-07 (**THE AUSTRIA ARCHIVE IS RE-INGESTED — run-book 58 ran green, and
three real bugs came out of it that no amount of review had found.** `runbooks/58-redownload-
austria-mpc.md` steps 0–5 done, QGIS eyeball passed. The archive is **184 granules / 552 files /
67.2 GB** at `tests/outputs/demo_e2e/imagery/`, `B04,B08,SCL` @ `max_cloudcover=50`, MPC. Spec 58
**P2 (`sentinel-1-rtc`) is now unblocked** — the schema change is landed and the data behind it is
real. `main` is 10+ commits ahead of `origin/main`.)_

_**The archive changed shape, and nothing fails loudly if you assume otherwise.** It is **not** the
old 207-granule / 74 GB / four-band CDSE archive: **B8A is gone** (full fidelity measured ~117 GB
against ~110 GB of headroom, so it was dropped to fit) and cloud cover is capped at 50, not 70.
Consequences: `demos/e2e_austria.py` still requests B8A and would fetch ~28 GB more; spec 58 **P3's
AC17 needs B8A** (`nir08` **is** B8A), so a supplementary pass is deferred, not avoided. The
workspace `CLAUDE.md` still describes the OLD archive — see the out-of-repo obligations above._

_**The radiometry debt is retired, and the proof is in the artifact rather than in a constant:**
`verify` reports `baselines_seen: ["02.12"]` — every granule declares processing baseline 02.12,
below 04.00, so ESA's offset genuinely is 0. MPC serves the **original 2018 processing**; CDSE
served the **2023 reprocessing** (N0500 ≥ 04.00, offset −1000) while recording 0, which is exactly
what made the old cubes ~1000 DN high. An earlier draft of `verify` asserted a flat `-1000` and the
`discover` step falsified it in seconds; it now derives the expected offset per row from the
baseline in the item's own `properties` (spec 58 D12's new column), which is right for either
provider._

_**Three bugs, all found by running it, none by review:**
(1) **`mpc.download` signed every href at STAC discovery.** An MPC SAS token lives ~45 min and a
whole-archive run takes longer, so 393 of 552 files failed at once when it aged out — a contiguous
newest-first tail, with the part-downloaded granules exactly at its boundary. Both MPC paths now
sign **inside the transfer worker, once per attempt**; `discover_shard_rows` had documented this
hazard for the AML fan-out all along, and `download()` was the path that still signed up front.
(2) **`api.download` never forwarded `max_concurrent`**, pinning every download to
`config.MPC_MAX_CONCURRENT` = 4 — a value whose own comment says it was picked for "a single
tile/band runbook". (3) **Failure reasons were collected and thrown away**: `DownloadResult.
failures` always carried `(src_url, reason)`, but nothing printed it, so a run could lose 71 % of
its files and say only `fail=393`. Failures now print grouped by exception **type** — the first
version of that summary grouped on the whole message, which for `FileNotFoundError(url)` is unique
per file, so it printed 74 failures as 74 useless one-off lines._

_**A methodological note worth keeping** ([[real-run-beats-review]] again): the first diagnosis of
the download failure was wrong. "Success rate was steady for 44 minutes, so it is not expiry" is
invalid reasoning — successes necessarily stop when a token dies, so a flat rate right up to the
end is consistent with sudden death, not evidence against it. The date distribution of what landed
is what settled it. Two review passes over this code found none of these three bugs; one real run
found all three._
