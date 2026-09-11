---
status: current
summary: Spec 58 AC15 — download sentinel-1-rtc over Window A (s2grid=476da24, Apr-Sep 2018) with PC_SDK_SUBSCRIPTION_KEY unset, build S1 and S2 cubes for the same cell/window, and run create_training_data on each with identical verb signatures.
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

**Window A** (spec 58 D18): `s2grid=476da24` (single-tile, 100% inside T33UWP, verified
2026-07-17), 2018-04-01 → 2018-09-30 — the labelled Austria window, so this run-book also
exercises `create_training_data` with real EuroCrops labels for S1, not just an unlabelled probe.

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
- `../shapefiles/s2grid=476da24.geojson` exists (workspace-root `shapefiles/`, sibling of the
  `fsd` checkout — works from the main checkout or a `.claude/worktrees/` copy).
- `../shapefiles/austria_eurocrops_sampled_ethiopia_translated.geojson` exists (the EuroCrops
  labels; `id_col="fid"`, `label_col="EC_hcat_n"`, per `CLAUDE.md`).
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
    roi='../shapefiles/s2grid=476da24.geojson',
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
  probe (2026-09-07) saw `sat:orbit_state: 'ascending'`, `sat:relative_orbit: 146` for this
  bbox/window — but 6 months of coverage may turn up more than the single item that probe found.
- **PASS if:** `n_rows > 0`. **This step's OUTPUT decides step 3's `properties_filter`** — it is
  not a pass/fail gate on its own.
- **Record** which `sat:orbit_state` value(s) appear, and how many `relative_orbit` values share
  the dominant one — you need this for step 3.

### Step 3a — build the S1 cube (first attempt, no `properties_filter`)

```bash
.venv/bin/python -c "
import geopandas as gpd
import json
from shapely.geometry import box
from fsd import api

gdf = gpd.read_file('../shapefiles/austria_eurocrops_sampled_ethiopia_translated.geojson')
result = {'step': 'build_s1_no_filter', 'expected': {'raises_or_succeeds': 'depends on step 2'}}
try:
    td = api.create_training_data(
        label_polygons=gdf,
        catalog_filepath='tests/outputs/p58_p2/imagery_s1/catalog.parquet',
        startdate='2018-04-01', enddate='2018-09-30', mosaic_days=20,
        bands=['vv', 'vh'], id_col='fid', label_col='EC_hcat_n',
        export_folderpath='tests/outputs/p58_p2/training_s1',
        collection='sentinel-1-rtc',
    )
    result.update(status='ok', pass_=True,
                   metrics={'n_pixels': td.n_pixels, 'n_timestamps': td.n_timestamps,
                            'bands': td.bands, 'raised': False})
except ValueError as exc:
    result.update(status='raised', pass_=None,
                   metrics={'raised': True, 'message': str(exc)})
result['pass'] = result.pop('pass_')
with open('tests/outputs/p58_p2/_result_build_s1_no_filter.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
```

- **If step 2 found exactly ONE `sat:orbit_state` value:** **Expect** this to SUCCEED
  (`raised: False`) — go straight to step 4 and skip step 3b.
- **If step 2 found MORE than one `sat:orbit_state` value:** **Expect** this to RAISE
  (`ValueError`, spec 58 AC11) — the message enumerates `(orbit_state, relative_orbit)` pairs
  with acquisition counts and ROI coverage. **This raise is the correct, intended behaviour**,
  not a bug — proceed to step 3b using the enumeration to pick one.
- **PASS if:** the outcome matches what step 2 predicted. A raise when step 2 saw one orbit
  state (or a silent success when it saw two) is the actual failure to report.

### Step 3b — build the S1 cube with `properties_filter` (only if step 3a raised)

Replace `<ORBIT_STATE>` with the value step 3a's error enumerated (e.g. `"ascending"`):

```bash
.venv/bin/python -c "
import geopandas as gpd
import json
from fsd import api

gdf = gpd.read_file('../shapefiles/austria_eurocrops_sampled_ethiopia_translated.geojson')
td = api.create_training_data(
    label_polygons=gdf,
    catalog_filepath='tests/outputs/p58_p2/imagery_s1/catalog.parquet',
    startdate='2018-04-01', enddate='2018-09-30', mosaic_days=20,
    bands=['vv', 'vh'], id_col='fid', label_col='EC_hcat_n',
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

gdf = gpd.read_file('../shapefiles/austria_eurocrops_sampled_ethiopia_translated.geojson')
td = api.create_training_data(
    label_polygons=gdf,
    catalog_filepath='tests/outputs/demo_e2e/imagery/catalog.parquet',
    startdate='2018-04-01', enddate='2018-09-30', mosaic_days=20,
    bands=['B04', 'B08', 'SCL'], id_col='fid', label_col='EC_hcat_n',
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

### Step 5 — QGIS eyeball of one S1 cube

The array `create_training_data` lands is flattened pixels, not a raster — for a visual check,
build ONE grid cell's cube directly and export it as a GeoTIFF:

```bash
.venv/bin/python -c "
import geopandas as gpd, os, numpy as np, rasterio
from fsd.catalog.catalog import TileCatalog, filter_gdf
from fsd.datacube import builder
from fsd import collections as _collections

cat = TileCatalog('tests/outputs/p58_p2/imagery_s1/catalog.parquet').read()
shapes = gpd.read_file('../shapefiles/s2grid=476da24.geojson')
subset = filter_gdf(cat, shapes, '2018-04-01', '2018-09-30')
flat = builder.flatten_catalog(subset)
out = 'tests/outputs/p58_p2/s1_eyeball'
builder.build_datacube(
    catalog_subset=flat, shape_gdf=shapes,
    startdate='2018-04-01', enddate='2018-09-30', bands=['vv', 'vh'], mosaic_days=20,
    export_folderpath=out, if_missing_files='warn',
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
