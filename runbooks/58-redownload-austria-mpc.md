---
status: current
summary: Re-download the 74 GiB Austria test archive from MPC under spec 58 P1's catalog schema — deletes the old archive first (only ~23 GiB free), and retires the ~1000 DN radiometry debt.
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
window is baseline `N0500` (ESA offset −1000) recorded as nothing, so cubes built from it are
**~1000 DN high** — fine for infrastructure tests, wrong for science.

Re-ingesting under post-spec-34 code stamps the real per-item offset and the new schema in one
pass. That is the whole job: **this run-book does not change any code**, it replaces data.

## Two decisions already made (user, 2026-09-05)

- **Source is MPC, not the CDSE the old archive came from.** Spec 58 D1 made MPC the default:
  anonymous (no creds leg at all) and its assets are already COG, so there is no jp2→COG
  conversion pass over 207 granules. **Consequence:** item ids and the on-disk layout change —
  flat `<root>/<item_id>/` instead of CDSE's `Sentinel-2/MSI/L2A_N0500/YYYY/MM/DD/<id>/`.
  Nothing reads those paths except the catalog being rewritten anyway.
- **The old archive is deleted first, and the new one lands in the same place.** There is no
  room to do otherwise: the archive is ~79 GB and the disk has ~25 GB free (98 % full). Step 2
  is the only destructive step in this run-book and it refuses to run without an explicit flag.

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
.venv/bin/python runbooks/scripts/58_redownload_austria.py download
```

`api.download(source="mpc", collection="sentinel-2-l2a", ...)` with `progress=True`, so it
prints a live rate + ETA line rather than going quiet.

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
| `reflectance_offset == -1000` | **the radiometry debt is retired** — the old archive had no offset at all |
| `scale == 1e-4` | D5.1's declared scale reached the catalog |
| `properties_non_empty` | D12's `properties` column is populated, not `{}` |
| `scl_never_offset` | SCL's COG carries scale 1 / offset 0 while B04's carries 1e-4 — the on-disk counterpart of the `radiometry_bands=None` bug P1's review re-derived |
| `all_bands_present_per_granule` | B04/B08/B8A/SCL on every row |

- **PASS if:** every entry of `checks` is `true`.
- **If `reflectance_offset` is `[0]`:** the archive was ingested by pre-spec-34 code — wrong
  venv or a stale checkout. Paste the result and stop; do not build cubes from it.

### Step 5 — build two cubes and eyeball them in QGIS

```bash
.venv/bin/python runbooks/scripts/58_redownload_austria.py build-cube
```

Builds one cube from `s2grid=476da24` (**100 % inside T33UWP** — the single-tile control) and
one from the AT_ROI grid cell spanning the most MGRS tiles (**the multi-CRS seam**). Since
`satellite_benchmark/` was deleted, AT_ROI is the *only* real-data cover left for that seam —
the Ethiopia ROI has no imagery behind it any more.

Each writes `first_timestamp_rgb.tif` (B08/B04/B8A) under
`tests/outputs/p58_redownload/cubes/<case>/`.

- **Expect:** both `built: true`, a 4-D `shape` `(timestamps, height, width, bands)`,
  `nodata_fraction` well under 0.9, and `seam_cell_mgrs_tile_count` ≥ 2.
- **PASS if:** `pass: true`.
- **Then open both GeoTIFFs in QGIS.** This is not optional and it is not something the
  `_result.json` can tell you (`CLAUDE.md`: raster ops get eyeballed, not just unit-tested).
  Look for: no seam line across the multi-tile cube, no black/wrapped tile (the ~1000 DN
  symptom), and the cube landing on the right part of Austria rather than at the origin.

## Success criteria (`_result.json`)

Five files under `fsd/tests/outputs/p58_redownload/`:

```
_result_discover.json  _result_free-disk.json  _result_download.json
_result_verify.json    _result_build-cube.json
```

Each has the spec-24 shape:

```json
{ "step": "verify", "status": "ok", "pass": true,
  "metrics": { "...": 0 }, "expected": { "...": 0 }, "error": null }
```

**The run passes when all five have `pass: true` AND you have looked at both GeoTIFFs.**
Paste the five files back, plus one line on what QGIS showed.

## Stop / observe

- **Progress:** step 3 prints a live rate + ETA line (`progress=True`).
- **Dry-run:** step 1 *is* the dry run — it transfers nothing and deletes nothing. Step 2
  without `--yes-delete-the-archive` reports what it would delete and refuses.
- **Abort:** **Ctrl-C at any point.** Only step 2 is destructive, and it is not interruptible in
  a harmful way (a `shutil.rmtree` that is cut short just leaves less to delete on the re-run).
  Step 3 is resume-safe by construction.
- **Resume:** re-run the same step command. Steps 1, 3, 4 and 5 are all idempotent.

## After this run-book

- `demos/e2e_austria.py` still calls `sources.cdse` directly and will re-download from CDSE if
  you run it. It is **not** updated by this run-book — the demo's own source choice is a
  separate change, tracked with spec 58's follow-ups.
- THE ORDER's next item is **spec 58 P2** (`sentinel-1-rtc`), which needs this archive's window
  as the S2 half of AC15's Window A comparison.
