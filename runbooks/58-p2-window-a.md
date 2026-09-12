---
status: current
summary: Spec 58 AC15 — download sentinel-1-rtc over Window A (s2grid=4772924, Apr-Sep 2018) with PC_SDK_SUBSCRIPTION_KEY unset, build S1 and S2 cubes for the same cell/window, and run create_training_data on each with identical verb signatures.
---

# Run-book 58-P2 — Window A: `sentinel-1-rtc` vs `sentinel-2-l2a`

> Spec 24: Claude does not run downloads or networked scripts. You run these; paste back each
> step's `_result.json` and Claude diffs it against the success criteria below. **Do not paste
> logs** — paste the result blocks.

## Purpose

Prove spec 58 P2's AC15 for real: `sentinel-1-rtc` and `sentinel-2-l2a` build over the **same**
grid cell and calendar window through the **same** `create_training_data` call shape, with no
verb-signature difference between them — and that the S1 half needs **no** MPC subscription key
(D10, retracted 2026-09-07) and correctly enforces the orbit-state partition (D9) if the window
turns up more than one.

**Window A** (spec 58 D18): `s2grid=4772924`, 2018-04-01 → 2018-09-30 — the labelled Austria
window, so this run-book exercises `create_training_data` with real crop labels for S1, not just
an unlabelled probe. The cell sits **100% inside T33UWP** (single MGRS tile, single CRS — verified
2026-09-12 against the archive: 21 granules cover it and the cell is fully within their union),
and **43 labelled `AT_2018_TRAIN` fields fall inside it** (7 crop classes, mostly
`grain_maize_corn_popcorn` and `hemp_cannabis`).

> ⚠️ **This cell is NOT the one spec 58 D18 names, and the change is deliberate** (review,
> 2026-09-12 — pending sign-off to amend D18). D18 pairs `s2grid=476da24` with "the EuroCrops
> labels", but those two do not intersect:
> `austria_eurocrops_sampled_ethiopia_translated.geojson` is, despite the `austria_` prefix,
> **translated to Ethiopia** (36.1–36.9 °E, 11.4–12.0 °N), while `s2grid=476da24` is in Austria
> (16.034–16.116 °E, 48.106–48.156 °N, just south-east of Vienna). The Ethiopia file cannot be
> used at all anyway — its imagery (`satellite_benchmark/`) was deleted (see `CLAUDE.md`).
>
> **And the Austrian labels do not rescue that cell either.** Measured 2026-09-12:
> `476da24` lies **47.7 km outside `AT_ROI`** (no intersection), and the nearest
> `AT_2018_TRAIN` field is **50.2 km** away — **0 of 900** fall inside it. Its *imagery* is
> fine (entirely within MGRS **T33UWP**, 21 archive granules cover it fully), which is exactly
> what it was authored for; it simply has no labels. So D18's Window A as written could not
> prove the "labelled" half of AC15. `s2grid=4772924` keeps every property D18 wanted — one
> cell, one MGRS tile (T33UWP again), inside the existing S2 archive, Apr–Sep 2018 — and adds
> the 43 labelled fields.

**The S2 half is already on disk** — the Austria archive at `tests/outputs/demo_e2e/imagery/`
(184 granules, `B04,B08,SCL`, MPC, re-ingested 2026-09-07; see `PROGRESS.md`). Step 5 builds
against it directly; nothing here re-downloads S2.

## Prerequisites

- `main` (or this branch, merged) at or after the commit implementing spec 58 P2. Check:
  `git log --oneline -1` and confirm `fsd/collections/s1_rtc.py` exists.
- The fsd venv with `[mpc,local,grid]`:
  ```bash
  cd fsd && source .venv/bin/activate && pip install -e ".[dev,local,mpc,grid]"
  ```
- **`PC_SDK_SUBSCRIPTION_KEY` must be UNSET for this run** — its absence is part of what step 1
  proves (D10: MPC dropped the RTC key requirement in 2024). Check and unset:
  ```bash
  echo "PC_SDK_SUBSCRIPTION_KEY is: ${PC_SDK_SUBSCRIPTION_KEY:-<unset>}"
  unset PC_SDK_SUBSCRIPTION_KEY
  ```
- `notebooks/shapefiles/s2grid=4772924.geojson` — committed to the repo (added 2026-09-12, from
  `fsd.grid.roi_to_s2_grids(AT_ROI, grid_size_km=5)`; see that folder's `NOTICE` for why this
  cell and not `476da24`). Being in-repo, it resolves from the main checkout **and** from any
  `.claude/worktrees/` copy — unlike the workspace-root `../shapefiles/`, which does not.
- `notebooks/shapefiles/AT_2018_TRAIN.geojson` — 900 Austria 2018 crop fields, EPSG:31287;
  `id_col="fid"`, `label_col="crop"` (the same pair `demos/e2e_austria.py` uses). The steps below
  reproject it and clip it to the cell themselves. ⚠️ It carries **EuroCrops' terms, not fsd's
  MIT** (`notebooks/shapefiles/NOTICE`) — fine to read locally here; do not redistribute its
  contents or paste field rows into a result block.
- `tests/outputs/demo_e2e/imagery/catalog.parquet` exists (the S2 archive). If it does not,
  stop — that is a different, larger problem than this run-book.
- A few GB of disk and network for step 1 (one grid cell, ~6 months of S1 acquisitions — far
  smaller than a full-ROI S2 download).

## Steps

Run every command from `fsd/`, with the venv active and `PC_SDK_SUBSCRIPTION_KEY` unset.

### Step 1 — download `sentinel-1-rtc` over Window A, anonymously

```bash
.venv/bin/python -c "
import json, os
from fsd import api

assert os.environ.get('PC_SDK_SUBSCRIPTION_KEY') is None, 'unset PC_SDK_SUBSCRIPTION_KEY first'

dst = 'tests/outputs/p58_p2/imagery_s1'
catalog_fp = api.download(
    roi='notebooks/shapefiles/s2grid=4772924.geojson',
    startdate='2018-04-01', enddate='2018-09-30',
    bands=['vv', 'vh'],
    dst_folderpath=dst,
    source='mpc', collection='sentinel-1-rtc',
    max_tiles=50, progress=True,
)
result = {'step': 'download_s1', 'status': 'ok', 'pass': True,
          'metrics': {'catalog_filepath': catalog_fp}, 'expected': {}, 'error': None}
os.makedirs('tests/outputs/p58_p2', exist_ok=True)
with open('tests/outputs/p58_p2/_result_download_s1.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
```

- **Expect:** anonymous discovery + download (no key prompt, no 401/403/404), a handful of
  granules (a single ~5 km cell over 6 months, not a whole-ROI archive), `pass: True`.
- **PASS if:** `_result_download_s1.json` has `pass: true` and
  `tests/outputs/p58_p2/imagery_s1/catalog.parquet` exists.
- **If it fails with a 401/403/404 or a key prompt:** that contradicts D10 (retracted) —
  paste the exact error; do not set the key to work around it, that would hide the finding.
- **If it fails / hangs:** Ctrl-C is safe; `mpc.download` skips files already on disk, so
  re-running resumes.

### Step 2 — inspect the orbit states this window actually has

```bash
.venv/bin/python -c "
import json
from fsd.catalog.catalog import TileCatalog

gdf = TileCatalog('tests/outputs/p58_p2/imagery_s1/catalog.parquet').read()
orbits = {}
for p in gdf['properties']:
    props = json.loads(p) if p else {}
    key = (props.get('sat:orbit_state'), props.get('sat:relative_orbit'))
    orbits[key] = orbits.get(key, 0) + 1
result = {'step': 'inspect_orbits', 'status': 'ok', 'pass': True,
          'metrics': {'n_rows': int(len(gdf)),
                      'orbit_relative_orbit_counts': {str(k): v for k, v in orbits.items()}},
          'expected': {}, 'error': None}
with open('tests/outputs/p58_p2/_result_inspect_orbits.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
```

- **Expect:** one or more `(orbit_state, relative_orbit)` keys with counts. spec 58 D17's own
  probe (2026-09-07) saw `sat:orbit_state: 'ascending'`, `sat:relative_orbit: 146` — but that
  probe was a single item over the *`476da24`* bbox (the cell D18 named; see the Purpose note).
  **Make no prediction here**: a different cell over 6 months may well turn up both orbit states,
  which is the more interesting case for AC11. Whatever this step reports is the ground truth
  step 3 is checked against.
- **PASS if:** `n_rows > 0`. **This step's OUTPUT decides step 3's `properties_filter`** — it is
  not a pass/fail gate on its own.
- **Record** which `sat:orbit_state` value(s) appear, and how many `relative_orbit` values share
  the dominant one — you need this for step 3.

### Step 3a — build the S1 cube (first attempt, no `properties_filter`)

```bash
.venv/bin/python -c "
import geopandas as gpd
import json
from fsd import api

cell = gpd.read_file('notebooks/shapefiles/s2grid=4772924.geojson')
gdf = gpd.read_file('notebooks/shapefiles/AT_2018_TRAIN.geojson').to_crs(cell.crs)
gdf = gdf[gdf.intersects(cell.geometry.iloc[0])]  # the 43 fields inside the cell
result = {'step': 'build_s1_no_filter', 'expected': {'raises_or_succeeds': 'depends on step 2'}}
try:
    td = api.create_training_data(
        label_polygons=gdf,
        catalog_filepath='tests/outputs/p58_p2/imagery_s1/catalog.parquet',
        startdate='2018-04-01', enddate='2018-09-30', mosaic_days=20,
        bands=['vv', 'vh'], id_col='fid', label_col='crop',
        export_folderpath='tests/outputs/p58_p2/training_s1',
        collection='sentinel-1-rtc',
    )
    result.update(status='ok', pass_=True,
                   metrics={'n_pixels': td.n_pixels, 'n_timestamps': td.n_timestamps,
                            'bands': td.bands, 'raised': False})
except Exception as exc:
    result.update(status='raised', pass_=None,
                   metrics={'raised': True, 'exc_type': type(exc).__name__,
                            'message': str(exc)})
result['pass'] = result.pop('pass_')
with open('tests/outputs/p58_p2/_result_build_s1_no_filter.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
```

- **If step 2 found exactly ONE `sat:orbit_state` value:** **Expect** this to SUCCEED
  (`raised: False`) — go straight to step 4 and skip step 3b.
- **If step 2 found MORE than one `sat:orbit_state` value:** **Expect** this to FAIL (spec 58
  AC11). ⚠️ **Where the message appears:** with `runner="local"` the per-cell build runs inside
  a **Snakemake subprocess**, so the D9 `ValueError` and its enumeration of
  `(orbit_state, relative_orbit)` pairs with acquisition counts and ROI coverage print to your
  **terminal**, and the exception this snippet catches is whatever the failed dispatch raises
  afterwards (not the `ValueError` itself). **This failure is the correct, intended behaviour**,
  not a bug — proceed to step 3b using the enumeration to pick one.
- **Paste the enumeration block from the terminal** alongside this step's `_result.json`. It is
  the actual AC11 evidence; `_result_build_s1_no_filter.json` only records that the build
  stopped. (That the verb-level exception is not itself the D9 `ValueError` is a known,
  reported gap, not something this run-book is testing.)
- **PASS if:** the outcome matches what step 2 predicted. A raise when step 2 saw one orbit
  state (or a silent success when it saw two) is the actual failure to report.

### Step 3b — build the S1 cube with `properties_filter` (only if step 3a raised)

Replace `<ORBIT_STATE>` with the value step 3a's error enumerated (e.g. `"ascending"`):

```bash
.venv/bin/python -c "
import geopandas as gpd
import json
from fsd import api

cell = gpd.read_file('notebooks/shapefiles/s2grid=4772924.geojson')
gdf = gpd.read_file('notebooks/shapefiles/AT_2018_TRAIN.geojson').to_crs(cell.crs)
gdf = gdf[gdf.intersects(cell.geometry.iloc[0])]  # the 43 fields inside the cell
td = api.create_training_data(
    label_polygons=gdf,
    catalog_filepath='tests/outputs/p58_p2/imagery_s1/catalog.parquet',
    startdate='2018-04-01', enddate='2018-09-30', mosaic_days=20,
    bands=['vv', 'vh'], id_col='fid', label_col='crop',
    export_folderpath='tests/outputs/p58_p2/training_s1',
    collection='sentinel-1-rtc',
    properties_filter={'sat:orbit_state': '<ORBIT_STATE>'},
)
result = {'step': 'build_s1_with_filter', 'status': 'ok', 'pass': True,
          'metrics': {'n_pixels': td.n_pixels, 'n_timestamps': td.n_timestamps,
                      'bands': td.bands},
          'expected': {}, 'error': None}
with open('tests/outputs/p58_p2/_result_build_s1_with_filter.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
```

- **Expect:** succeeds this time — no orbit-state raise, since `properties_filter` narrowed the
  catalog to one value before the build.
- **PASS if:** `pass: true` and `td.bands == ['vv', 'vh']`.

### Step 4 — build the S2 cube for the SAME cell/window (identical verb shape)

```bash
.venv/bin/python -c "
import geopandas as gpd
import json
from fsd import api

cell = gpd.read_file('notebooks/shapefiles/s2grid=4772924.geojson')
gdf = gpd.read_file('notebooks/shapefiles/AT_2018_TRAIN.geojson').to_crs(cell.crs)
gdf = gdf[gdf.intersects(cell.geometry.iloc[0])]  # the 43 fields inside the cell
td = api.create_training_data(
    label_polygons=gdf,
    catalog_filepath='tests/outputs/demo_e2e/imagery/catalog.parquet',
    startdate='2018-04-01', enddate='2018-09-30', mosaic_days=20,
    bands=['B04', 'B08', 'SCL'], id_col='fid', label_col='crop',
    export_folderpath='tests/outputs/p58_p2/training_s2',
    collection='sentinel-2-l2a',
)
result = {'step': 'build_s2', 'status': 'ok', 'pass': True,
          'metrics': {'n_pixels': td.n_pixels, 'n_timestamps': td.n_timestamps,
                      'bands': td.bands},
          'expected': {}, 'error': None}
with open('tests/outputs/p58_p2/_result_build_s2.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
```

- **Expect:** succeeds (this archive and window are already proven, run-book 58 D5-9-2026-09-07).
- **PASS if:** `pass: true`. **Compare this call's keyword arguments against step 3a/3b's**: only
  `catalog_filepath`, `bands`, `export_folderpath`, `collection`, and (for S1) `properties_filter`
  differ — every other keyword (`label_polygons`, `startdate`, `enddate`, `mosaic_days`, `id_col`,
  `label_col`) is byte-identical. **That identity of shape is AC15's actual claim** — write down
  whether it held.
- **`td.n_timestamps` should match between the S1 and S2 runs** (same `startdate`/`enddate`/
  `mosaic_days` → the same calendar-interval mosaic axis, ADR 0010) even though the two cubes
  come from unrelated acquisitions.
- **`td.bands` should be `['B04', 'B08']` here — SCL is consumed, not returned.** Nothing in this
  call applies the cloud mask; the verb has no mask parameter at all (D3). `build_datacube` reads
  `mask_spec` off the `sentinel-2-l2a` declaration and, because `SCL` is among the requested
  `bands`, runs `apply_cloud_mask_scl` (setting B04/B08 to nodata wherever SCL ∈ {0, 1, 3, 7, 8,
  9, 10}) → `drop_bands(['SCL'])` → `median_mosaic`, **in that order**, so cloudy pixels are
  excluded from the temporal median rather than averaged into it. Step 3's S1 call runs neither
  op: `sentinel-1-rtc` declares `mask_spec=None`. **That is the AC15 claim in one line — same verb
  signature, different declared behaviour.**
  ⚠️ **Keep `SCL` in `bands`.** `mask_active` is literally `mask_spec.band in bands`, so removing
  SCL disables masking **silently** — no error, no warning, just an unmasked cube.

### Step 5 — QGIS eyeball of one S1 cube

The array `create_training_data` lands is flattened pixels, not a raster — for a visual check,
build ONE grid cell's cube directly and export it as a GeoTIFF:

**If step 3b was needed** (the window has more than one orbit state), set `ORBIT` below to
the same value you used there; otherwise leave it `None`. `build_datacube` applies
`properties_filter` itself, so this step does not have to pre-filter the catalog.

```bash
.venv/bin/python -c "
import geopandas as gpd, os, numpy as np, rasterio
from fsd.catalog.catalog import TileCatalog, filter_gdf
from fsd.datacube import builder
from fsd import collections as _collections

ORBIT = None  # e.g. 'ascending' -- must match step 3b if step 3b ran

cat = TileCatalog('tests/outputs/p58_p2/imagery_s1/catalog.parquet').read()
shapes = gpd.read_file('notebooks/shapefiles/s2grid=4772924.geojson')
subset = filter_gdf(cat, shapes, '2018-04-01', '2018-09-30')
flat = builder.flatten_catalog(subset)
out = 'tests/outputs/p58_p2/s1_eyeball'
builder.build_datacube(
    catalog_subset=flat, shape_gdf=shapes,
    startdate='2018-04-01', enddate='2018-09-30', bands=['vv', 'vh'], mosaic_days=20,
    export_folderpath=out, if_missing_files='warn',
    properties_filter=({'sat:orbit_state': ORBIT} if ORBIT else None),
)
dc = np.load(os.path.join(out, 'datacube.npy'))
md = np.load(os.path.join(out, 'metadata.pickle.npy'), allow_pickle=True)[()]
profile = dict(md['geotiff_metadata'])
profile.update(count=2, dtype='float32')
with rasterio.open(os.path.join(out, 'vv_vh_first_timestamp.tif'), 'w', **profile) as dst:
    dst.write(dc[0, :, :, 0], 1)
    dst.write(dc[0, :, :, 1], 2)
print('wrote', os.path.join(out, 'vv_vh_first_timestamp.tif'))
"
```

- **Then open `tests/outputs/p58_p2/s1_eyeball/vv_vh_first_timestamp.tif` in QGIS.** Load band 1
  (VV) alone first: real SAR backscatter should show field-scale texture, not a flat value or
  noise with no structure. This is not optional (`CLAUDE.md`: raster ops get eyeballed).
- **PASS if:** the raster opens, is not entirely nodata, and shows plausible backscatter texture
  over the Austria cell.

## Success criteria (`_result.json`)

Files under `fsd/tests/outputs/p58_p2/`:

```
_result_download_s1.json  _result_inspect_orbits.json  _result_build_s1_no_filter.json
_result_build_s1_with_filter.json (if step 3b ran)     _result_build_s2.json
```

**The run passes when:**
1. Every result file's `pass` is `true` (or, for `build_s1_no_filter`, its outcome matched what
   step 2 predicted).
2. Step 4's note on verb-signature identity is filled in and confirms only the expected keywords
   differ.
3. You have looked at the QGIS raster and it shows real backscatter, not a blank/flat image.

Paste all result files, the verb-signature comparison note, and one line on what QGIS showed.

## Stop / observe

- **Progress:** step 1 prints a live rate line (`progress=True`) — one grid cell over 6 months is
  small; expect seconds to low minutes, not hours.
- **Abort:** Ctrl-C at any point. Nothing here is destructive; step 1 resumes on re-run.
- **Resume:** re-run any step's command; `create_training_data`'s stamp-based skip means step 3/4
  re-runs with identical arguments do nothing after the first success.

## After this run-book

- If step 2 found more than one orbit state, record which one you picked in step 3b (and why —
  larger coverage, more acquisitions) in `PROGRESS.md`'s next entry, since a different reader
  re-running this later needs the same answer to reproduce the same cube path.
- This window's S1 archive (`tests/outputs/p58_p2/imagery_s1/`) is scoped to one grid cell — it is
  a proof archive, not a replacement for a full-ROI S1 download. A full-ROI S1 pass (if ever
  wanted) is a separate, larger run-book, modelled on `runbooks/58-redownload-austria-mpc.md`.
- THE ORDER's next item after P2 lands is spec 58 **P3** (`hls2-s30`/`hls2-l30`, Window B) — see
  `PROGRESS.md`.
