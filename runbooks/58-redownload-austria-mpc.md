---
status: current
summary: Re-download the Austria test archive from MPC under spec 58 P1's catalog schema — settled on B04/B08/SCL at cloudcover 50 (~89 GB, 184 granules) because full fidelity did not fit; re-stamps radiometry from each item's own declared baseline.
---

# Run-book: 58 — re-download the Austria archive (MPC, new catalog schema)

> Spec-24 run-book for **spec 58 §10**. **You** run this; paste back each step's
> `_result_<step>.json` from `tests/outputs/p58_redownload/`. Claude diffs them against the
> success criteria below and never reads your logs.
>
> Script: [`runbooks/scripts/58_redownload_austria.py`](scripts/58_redownload_austria.py).
> Every step is one invocation and writes its own `_result_*.json` even when it fails.

## Purpose

Spec 58 P1 renamed the catalog's `satellite` column to `collection` and added `scale` and
`properties`, **with no read-time back-compat shim** (D12) — so every catalog written before P1
is invalidated. The Austria archive is further behind than that: it carries **no `offset` or
`nodata` column at all**, which is the live half of the radiometry debt. Every granule in the
window was served by CDSE as the **2023 reprocessing** (baseline `N0500` ≥ 04.00, ESA offset
−1000) and recorded as nothing, so cubes built from it are **~1000 DN high** — fine for
infrastructure tests, wrong for science.

⚠️ **MPC does not carry the same processing, and that is fine.** MPC serves the **original
2018 processing** of the same acquisitions — baseline < 04.00, so ESA's offset genuinely *is*
0 and `offsets_declared: [0]` from step 1 is the truthful stamp, not a repeat of the bug. The
old archive was wrong because it stamped 0 onto *reprocessed* bytes that needed −1000, not
because the number was 0. Step 4 therefore checks each row's offset against **the baseline
that row's own item declares**, which is right for either provider; an earlier draft of this
run-book asserted a flat `-1000` and step 1 falsified it in seconds.

Re-ingesting under post-spec-34 code stamps the real per-item offset and the new schema in one
pass. That is the whole job: **this run-book does not change any code**, it replaces data.

## Two decisions already made (user, 2026-09-05)

- **Source is MPC, not the CDSE the old archive came from.** Spec 58 D1 made MPC the default:
  anonymous (no creds leg at all) and its assets are already COG, so there is no jp2→COG
  conversion pass over 207 granules. **Consequence:** item ids and the on-disk layout change —
  flat `<root>/<item_id>/` instead of CDSE's `Sentinel-2/MSI/L2A_N0500/YYYY/MM/DD/<id>/`.
  Nothing reads those paths except the catalog being rewritten anyway.
- **The old archive is deleted first, and the new one lands in the same place.** There is no
  room to do otherwise: the archive was ~79 GB and the disk had ~25 GB free (98 % full).
  Step 2 is the only destructive step in this run-book and it refuses to run without an
  explicit flag.

## ⚠️ Sizing: measured on the first real run (2026-09-05)

**MPC's COGs are bigger than the CDSE-converted ones — 0.549 GB/granule vs 0.384.** For 213
granules × B04+B08+B8A+SCL that is **~117 GB**, against ~104 GB of headroom after deleting the
old archive. **The full-fidelity run does not fit on this disk**, and step 1 correctly returns
`pass: false` when it does not.

Step 0 (`reclaim`) buys ~10 GB. That is necessary and, on its own, still not enough — so
price a scope lever with `discover` before committing, e.g.:

```bash
# cheapest lever: a tighter cloud-cover ceiling (fewer granules, better data)
.venv/bin/python runbooks/scripts/58_redownload_austria.py discover --max-cloudcover 50

# or drop the 20 m B8A (~12 GB) -- but note spec 58 P3's AC17 compares `nir08` (= B8A)
# between S2 and HLS, so that band comes back later
.venv/bin/python runbooks/scripts/58_redownload_austria.py discover --bands B04,B08,SCL
```

Each is a STAC query plus three HEADs — seconds, no bytes. **Whatever you settle on, pass the
same `--bands` / `--max-cloudcover` to `download`.** (`verify` and `build-cube` need no flags:
they read the band set back off the catalog's own `files` column, so they cannot disagree with
what was actually downloaded.)

### What this archive actually is (settled 2026-09-05)

| | value | vs the run-book default |
|---|---|---|
| bands | **`B04,B08,SCL`** | **B8A dropped** |
| `max_cloudcover` | **50** | was 70 |
| granules | **184** | 213 at cc70; the old CDSE archive had 207 |
| size | **~89 GB** (0.483 GB/granule) | ~117 GB at full fidelity |

**Two consequences, neither of which fails loudly:**

1. **`demos/e2e_austria.py` requests `B04,B08,B8A,SCL`.** Run it against this archive and it
   will go and fetch B8A — another ~28 GB, which will not fit. Change its `BANDS` to match, or
   accept the download.
2. **Spec 58 P3's AC17 compares `red` and `nir08` between `sentinel-2-l2a` and `hls2-s30`, and
   `nir08` *is* B8A.** P3 will need a supplementary B8A pass over this window. Dropping it here
   deferred that cost; it did not remove it.

The cloud-cover change is not a loss: 50 is a stricter filter than 70, so the granules that
remain are better, just fewer.

## Prerequisites

- `main` at or after `3217db7` (spec 58 P1 merged). Check: `git log --oneline -1`.
- The fsd venv with the `[mpc]` and `[local]` extras — `[local]` because step 5 runs the
  Snakemake local runner, which left the core install in #80:
  ```bash
  cd fsd && source .venv/bin/activate && pip install -e ".[dev,local,mpc,grid]"
  ```
- **No credentials.** MPC discovery and download are anonymous for `sentinel-2-l2a`; if anything
  asks you for a key, stop and paste the error — that is a bug, not a prerequisite.
- Network for ~1–3 hours on the download step, and the machine awake for it.
- Nothing else writing to `tests/outputs/demo_e2e/`.

## What gets deleted, and what does not

| path | size | step 2 deletes it? |
|---|---|---|
| `tests/outputs/demo_e2e/imagery/` | ~79 GB | **yes** — this is the archive being replaced |
| `tests/outputs/demo_e2e/training_run/` | 60 MB | no — stale, but see below |
| `tests/outputs/demo_e2e/model_outputs/`, `bundle/`, `rf.joblib` | ~7 GB | no |

`training_run/`'s cubes are stale, but they **cannot be silently reused**: spec 58 D4 made the
cube-path digest key on `collection` + the declaration hash, so anything built after this
run-book lands at a *different* window segment. Deleting them is hygiene, not correctness — do
it yourself if you want the 60 MB back:
`rm -rf fsd/tests/outputs/demo_e2e/training_run`.

## Steps

Run every command from `fsd/`, with the venv active.

### Step 0 — reclaim stale derived artifacts

```bash
.venv/bin/python runbooks/scripts/58_redownload_austria.py reclaim            # dry run
.venv/bin/python runbooks/scripts/58_redownload_austria.py reclaim --yes-delete
```

Removes what the *old* archive fed and nothing else: `demo_e2e/`'s `model_outputs`, `bundle`,
`rf.joblib`, `training_data`, `training_run`, plus `spec34_mixed_baseline`. All of it is
derived from an archive that is being replaced, so it is stale by construction. It does **not**
touch `imagery/` (that is step 2, with its own confirmation) or `mpc_baseline/` — 1.6 GiB, kept
because it is the reference cube this run-book's GeoTIFF writer was validated against.

- **Expect:** `would_reclaim_gb` ≈ 10 on the dry run; `free_gb_after` ≈ `free_gb_before` + 10.
- **PASS if:** `all_removed: true`.

### Step 1 — discover (no bytes, nothing deleted)

```bash
.venv/bin/python runbooks/scripts/58_redownload_austria.py discover
```

Queries MPC for the archive's own window (`2018-04-01` → `2018-09-30`, `AT_ROI.geojson`,
`max_cloudcover=70`), and sizes the download by HEAD-ing the band assets of three real items —
a measured number, not a constant, because the delete in step 2 is justified by it.

**This runs before anything is destroyed on purpose:** a wrong ROI, window, or collection costs
one STAC query here and nothing else.

- **Expect:** `granules` near **207** (MPC's dedup and cloud-cover differ from CDSE's, so an
  exact match is not expected), `mgrs_tiles` exactly `["T33UVP","T33UVQ","T33UWP","T33UWQ"]`,
  `offsets_declared` `[-1000]`, `scales_declared` `[0.0001]`, and
  `free_gb_after_delete` comfortably above `estimated_download_gb`.
- **PASS if:** `pass: true` in `_result_discover.json`.
- **If it fails:** paste `_result_discover.json`. A granule count far from 207, or a missing
  MGRS tile, means the ROI or window is wrong — **do not proceed to step 2**, because step 2 is
  what makes this expensive to undo.

### Step 2 — free the disk ⚠️ DESTRUCTIVE

```bash
.venv/bin/python runbooks/scripts/58_redownload_austria.py free-disk --yes-delete-the-archive
```

Deletes `tests/outputs/demo_e2e/imagery/` (~79 GB). Without the flag the script reports what it
*would* delete and exits non-zero, which is a safe way to see the numbers first:

```bash
.venv/bin/python runbooks/scripts/58_redownload_austria.py free-disk   # dry, refuses
```

- **Expect:** `deleted_gb` ≈ 79, `free_gb_after` ≈ 104.
- **PASS if:** `archive_removed: true` and `free_gb_after` > step 1's `estimated_download_gb`
  × 1.25.
- **Before you run it:** step 1 passed, and you accept that the only copy of this archive is
  gone until step 3 finishes. It is re-downloadable — that is the entire point — but it is
  hours.

### Step 3 — download (the long leg, ~1–3 h)

```bash
.venv/bin/python runbooks/scripts/58_redownload_austria.py download \
    --bands B04,B08,SCL --max-cloudcover 50 --max-concurrent 16
```

`api.download(source="mpc", collection="sentinel-2-l2a", ...)` with `progress=True`, so it
prints a live rate + ETA line rather than going quiet.

**`--max-concurrent` is why the first attempt crawled.** `sources.mpc.download` defaults to
`config.MPC_MAX_CONCURRENT` = **4** — a value whose own comment says it was chosen for *"a
single tile/band runbook"* — and `api.download` did not forward the parameter at all until
this run-book needed it (fixed in the same commit; `tests/test_spec58_p1.py::
test_download_forwards_max_concurrent_to_both_sources` pins it). 200+ granules × 4 bands over
4 threads is latency-bound, not bandwidth-bound. 16 is a sane default against MPC, a public
Azure endpoint; raise it further if the rate line is still flat.

**Pass the same `--bands` / `--max-cloudcover` you priced in step 1**, or you will download a
different archive from the one you sized the disk for.

- **Expect:** a progress line that advances; on completion `granules` near 207 and
  `archive_gb` close to step 1's `estimated_download_gb`.
- **PASS if:** `pass: true` and `catalog.parquet` exists under `imagery/`.
- **If it fails / hangs / you need the machine:** **Ctrl-C is safe.** `mpc.download` skips any
  file already on disk, so re-running the same command resumes and costs only the transfers
  that were in flight. Run it as many times as needed until `pass: true`.
- **If the disk fills anyway:** stop, paste `_result_download.json`, and do not delete anything
  else — the numbers say what over-ran the estimate.

### Step 4 — verify the new archive

```bash
.venv/bin/python runbooks/scripts/58_redownload_austria.py verify
```

This is the step that proves the re-download did its job. It checks, on the real files:

| check | why it is here |
|---|---|
| `columns_match_catalog_COLUMNS` | D12's new schema, in the documented order |
| `declaration_stamp_is_s2_l2a` + `declaration_version_is_2` | the footer carries a v2 `CollectionDeclaration` |
| `offset_matches_declared_baseline` | **the radiometry debt is retired** — every row's offset is re-derived from the baseline in its own `properties` (ESA: −1000 for ≥ 04.00, else 0) and must agree. Provider-agnostic, so it stays correct for MPC's original-2018 items *and* CDSE's reprocessed ones |
| `scale == 1e-4` | D5.1's declared scale reached the catalog |
| `properties_non_empty` | D12's `properties` column is populated, not `{}` |
| `scl_never_offset` | SCL's COG carries scale 1 / offset 0 while B04's carries 1e-4 — the on-disk counterpart of the `radiometry_bands=None` bug P1's review re-derived |
| `every_granule_has_the_same_bands` | the archive's own band set (read from `files`, reported as `archive_bands`) is present on every row. Checks **internal consistency**, not a hardcoded list — which bands were downloaded is your choice; a granule short of one the others have is the bug |

- **PASS if:** every entry of `checks` is `true`.
- **If `offset_matches_declared_baseline` fails:** read `offset_mismatches` in the metrics —
  it names the granule, the baseline it declares, and both offsets. A row with **no** baseline
  is a mismatch too, never a silent pass (`offset_for_item` raises for the same reason, spec 34
  §3a A1). Paste the result and stop; do not build cubes from it.
- **`offsets_seen: [0]` on its own is not a failure here** — see the radiometry note above.

### Step 5 — build two cubes and eyeball them in QGIS

```bash
.venv/bin/python runbooks/scripts/58_redownload_austria.py build-cube
```

Builds one cube from `s2grid=476da24` (**100 % inside T33UWP** — the single-tile control) and
one from the AT_ROI grid cell spanning the most MGRS tiles (**the multi-CRS seam**). Since
`satellite_benchmark/` was deleted, AT_ROI is the *only* real-data cover left for that seam —
the Ethiopia ROI has no imagery behind it any more.

Builds with the bands the **archive** holds (read off `files`, printed as `bands`), not a
hardcoded list — so no flags, and no way for this step to disagree with what step 3 fetched.
Each writes `first_timestamp_rgb.tif` under `tests/outputs/p58_redownload/cubes/<case>/`:
B08/B04/B8A where present, so on this archive it is a **two-band** B08/B04 file, not three.

- **Expect:** both `built: true`, a 4-D `shape` `(timestamps, height, width, bands)`,
  `nodata_fraction` well under 0.9, and `seam_cell_mgrs_tile_count` ≥ 2.
- **PASS if:** `pass: true`.
- **Then open both GeoTIFFs in QGIS.** This is not optional and it is not something the
  `_result.json` can tell you (`CLAUDE.md`: raster ops get eyeballed, not just unit-tested).
  Look for: no seam line across the multi-tile cube, no black/wrapped tile (the ~1000 DN
  symptom), and the cube landing on the right part of Austria rather than at the origin.

## Success criteria (`_result.json`)

Six files under `fsd/tests/outputs/p58_redownload/`:

```
_result_reclaim.json   _result_discover.json  _result_free-disk.json
_result_download.json  _result_verify.json    _result_build-cube.json
```

Each has the spec-24 shape:

```json
{ "step": "verify", "status": "ok", "pass": true,
  "metrics": { "...": 0 }, "expected": { "...": 0 }, "error": null }
```

**The run passes when all six have `pass: true` AND you have looked at both GeoTIFFs.**
Paste the six files back, plus one line on what QGIS showed.

## Stop / observe

- **Progress:** step 3 prints a live rate + ETA line (`progress=True`).
- **Dry-run:** step 1 *is* the dry run — it transfers nothing and deletes nothing, and
  `--bands`/`--max-cloudcover` let you price a smaller run in seconds. Steps 0 and 2 without
  their confirmation flags report what they would delete and refuse.
- **Abort:** **Ctrl-C at any point.** Only steps 0 and 2 are destructive, and neither is
  interruptible in a harmful way (a `shutil.rmtree` cut short just leaves less to delete on
  the re-run). Step 3 is resume-safe by construction.
- **Resume:** re-run the same step command. Steps 1, 3, 4 and 5 are all idempotent.

## After this run-book

- `demos/e2e_austria.py` still calls `sources.cdse` directly **and requests B8A**, so running it
  against this archive re-downloads from CDSE and fetches a band this archive does not have.
  It is **not** updated by this run-book — the demo's source and band choices are a separate
  change, tracked with spec 58's follow-ups. See "What this archive actually is" above.
- THE ORDER's next item is **spec 58 P2** (`sentinel-1-rtc`), which needs this archive's window
  as the S2 half of AC15's Window A comparison.
