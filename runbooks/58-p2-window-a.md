---
status: current
summary: Spec 58 AC15 — download sentinel-1-rtc over Window A (s2grid=4772924, 1 Jun–1 Jul 2018, one orbit track) with PC_SDK_SUBSCRIPTION_KEY unset, build S1 and S2 cubes for the same cell/window, and run create_training_data on each with identical verb signatures.
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

**Window A** (spec 58 D18): `s2grid=4772924`, **2018-06-01 → 2018-07-01** — the labelled Austria
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

- ⚠️ **Spec 58 P2 is NOT merged into `main`.** Its code lives only on the branch
  `worktree-spec58-p2`, checked out at `fsd/.claude/worktrees/spec58-p2`. **Step 0 below is
  what points the run at it** — skip Step 0 and step 1 dies at preflight with
  `source='mpc' does not serve collection='sentinel-1-rtc'`, because the main checkout's
  `SERVED_COLLECTIONS` is still S2-only.
- The fsd venv with `[mpc,local,grid]`, in the **main** checkout (Step 0 uses it by absolute
  path — do NOT `activate` it, and do not create a second venv in the worktree):
  ```bash
  cd ~/NASA-Harvest/project/fetch_satdata_claude/fsd
  .venv/bin/pip install -e ".[dev,local,mpc,grid]"
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
- `$FSD_MAIN/tests/outputs/demo_e2e/imagery/catalog.parquet` exists — the S2 archive, in the
  **main** checkout (`tests/outputs/` is gitignored, so it is NOT in the worktree; that is
  why step 4 reaches for it by absolute path). If it does not exist, stop — that is a
  different, larger problem than this run-book.
- ⚠️ **Disk: ~22–26 GB for this run, and the FULL window would have been 387.7 GB.** A download
  is a **whole-asset byte copy**, so a ~6 km cell still pulls entire ~250 km Sentinel-1 scenes:
  **~3.7 GB per scene** (VV+VH), measured 2026-09-12. An earlier draft guessed "a few GB" for the
  whole window; it was wrong by ~100×. That is why this run is scoped to **one orbit track over
  one month** (step 1b) plus a **6-day slice of the other orbit state** (step 1c). **Step 1a
  re-measures before anything transfers** — do not skip it, and never simply raise `max_tiles`
  to get past the cap.

## Steps

Run every command from **the P2 worktree**, not from the main `fsd/` checkout — spec 58 P2
is **not merged into `main`**, so the main checkout's `mpc.SERVED_COLLECTIONS` is still
S2-only and step 1 fails preflight with
`source='mpc' does not serve collection='sentinel-1-rtc'`.

### Step 0 — set up the shell (do this once, in the terminal you will use)

```bash
cd ~/NASA-Harvest/project/fetch_satdata_claude/fsd/.claude/worktrees/spec58-p2

export PYTHONPATH=src                                    # import P2's fsd, not main's
export FSD_MAIN="$(cd "$(git rev-parse --git-common-dir)/.." && pwd)"
export PY="$FSD_MAIN/.venv/bin/python"                   # the venv lives in the main checkout
export OUT="$FSD_MAIN/tests/outputs/p58_p2"              # outputs OUTLIVE this worktree
unset PC_SDK_SUBSCRIPTION_KEY

"$PY" -c "
import fsd
from fsd.sources import mpc
from fsd import collections as c
print('fsd from   :', fsd.__file__)
print('collections:', c.known())
print('mpc serves :', mpc.SERVED_COLLECTIONS)
assert 'spec58-p2' in fsd.__file__, 'PYTHONPATH=src not picked up -- you are running main'
assert 'sentinel-1-rtc' in mpc.SERVED_COLLECTIONS, 'P2 code not loaded'
print('OK')
"
echo "FSD_MAIN=$FSD_MAIN"; echo "OUT=$OUT"
```

- **Expect:** `fsd from` ends in `.claude/worktrees/spec58-p2/src/fsd/__init__.py`,
  `collections: ['sentinel-1-rtc', 'sentinel-2-l2a']`, and `OK`.
- **PASS if:** it prints `OK`. If either assert fires, **stop** — every later step will fail in
  a confusing way. `PYTHONPATH=src` is what makes the worktree's code win over the editable
  install that points at the main checkout.
- ⚠️ **Every step below assumes this shell.** A new terminal needs Step 0 again — `$PY`, `$OUT`
  and `$FSD_MAIN` unset would silently write to `/imagery_s1` and friends.
- Outputs go to the **main checkout's** `tests/outputs/p58_p2/` on purpose: this worktree
  is deleted when P2 merges, and the downloaded S1 archive should survive that.


### Step 1a — probe the window BEFORE downloading anything

⚠️ **Why this step exists.** A download is a **whole-asset byte copy** — a ~6 km cell still
fetches entire ~250 km Sentinel-1 scenes. The first attempt matched **104 tiles**, i.e. 208
whole COGs (VV+VH). **Do not just raise `max_tiles`** until this step says what the bytes are.

**Measured 2026-09-12** over `s2grid=4772924`, 2018-04-01 → 2018-09-30 — re-run it, but this is
what it said, and it is why the later steps are scoped the way they are:

| `(sat:orbit_state, sat:relative_orbit)` | scenes | GB | GB/scene | cadence |
|---|---|---|---|---|
| `('ascending', 146)` | 31 | 114.0 | 3.68 | 5.9 d |
| `('ascending', 73)` | 30 | 110.6 | 3.69 | 6.1 d |
| `('descending', 22)` | 44 | 163.1 | 3.71 | 4.1 d |
| **total** | **105** | **387.7** | | |

Free disk at the time: **44.6 GB**. Every asset carried `file:size`, so those totals are exact,
not estimates. **Even the smallest single track is 2.5× the free space**, which is what forces
rule 3 below — the window shrinks, it is not a matter of picking a better orbit.

```bash
"$PY" -c "
import json, shutil
import geopandas as gpd
from fsd.sources import mpc

roi = gpd.read_file('notebooks/shapefiles/s2grid=4772924.geojson')
items = mpc._search_items_unsigned(
    roi, '2018-04-01', '2018-09-30', collection='sentinel-1-rtc',
)
groups, sized, unsized, total_bytes = {}, 0, 0, 0
for it in items:
    key = (it.properties.get('sat:orbit_state'), it.properties.get('sat:relative_orbit'))
    g = groups.setdefault(str(key), {'n': 0, 'bytes': 0})
    g['n'] += 1
    for b in ('vv', 'vh'):
        asset = it.assets.get(b)
        size = (asset.extra_fields or {}).get('file:size') if asset is not None else None
        if size:
            sized += 1; total_bytes += size; g['bytes'] += size
        else:
            unsized += 1
free = shutil.disk_usage('.').free
result = {'step': 'probe_window', 'status': 'ok', 'pass': True,
          'metrics': {'n_items': len(items),
                      'by_orbit_state_relorbit': groups,
                      'assets_with_file_size': sized, 'assets_without': unsized,
                      'total_GB': round(total_bytes / 1e9, 1),
                      'free_disk_GB': round(free / 1e9, 1)},
          'expected': {}, 'error': None}
import os; os.makedirs('$OUT', exist_ok=True)
with open('$OUT/_result_probe_window.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
```

- **Expect:** `n_items` around 104, split across one or more
  `(sat:orbit_state, sat:relative_orbit)` groups, each with its own byte total.
- **PASS if:** it prints without error. This step is a **decision input, not a gate**.
- **If `assets_without` is non-zero**, MPC did not publish `file:size` for those assets and
  `total_GB` is an undercount — treat it as a floor, not an estimate.
- **Record:** the group table and `total_GB` vs `free_disk_GB`. Step 1b is chosen from it.

#### Choosing what to download (the rule, in order)

1. **Pick ONE `sat:orbit_state`** — the build can only ever use one (D9 enforcement), so the
   other's bytes are pure waste. Prefer the group with the most acquisitions.
2. **If that is still too big, also pin `sat:relative_orbit`** to the busiest track within the
   chosen orbit state. Fewer acquisitions, but they are the ones that actually co-register.
3. **If it is STILL too big, shorten the window** — e.g. `2018-06-01 → 2018-07-31`. The 2018
   EuroCrops labels are season-level (`GEOM_DATE_` = 2018-07-31), so a mid-season window keeps
   them valid. **Use the same window for step 4's S2 build** so the two stay comparable.
4. Keep **at least ~5 acquisitions** so `mosaic_days=20` has something to composite.

**Leave yourself headroom:** do not start a download whose `total_GB` is within ~20 GB of
`free_disk_GB`.

### Step 1b — download the chosen partition

**Pre-filled from the 2026-09-12 probe** — all three narrowing rules had to be applied, because
the full window was 387.7 GB against 44.6 GB free. Re-derive these from *your* step 1a output if
it differs. `MAX_TILES` is the expected scene count plus slack, deliberately left tight so a
wrong window trips the cap instead of the disk.

> `REL_ORBIT = 146` is an **integer**, as `sat:relative_orbit` is in the STAC `sat` extension.
> That works because the P2 review fixed `properties_filter` to accept non-string scalars — it
> previously raised `TypeError` on the int and silently matched **zero rows** on the string
> `"146"`. This step is the first real use of that fix.

```bash
"$PY" -c "
import json, os
from fsd import api

assert os.environ.get('PC_SDK_SUBSCRIPTION_KEY') is None, 'unset PC_SDK_SUBSCRIPTION_KEY first'

ORBIT     = 'ascending'      # measured 2026-09-12, step 1a
REL_ORBIT = 146              # pin the track: 31 scenes over the full window, 3.68 GB each
START, END = '2018-06-01', '2018-07-01'   # ~5 scenes ~= 18.4 GB of 44.6 GB free
MAX_TILES = 8

pf = {'sat:orbit_state': ORBIT}
if REL_ORBIT is not None:
    pf['sat:relative_orbit'] = REL_ORBIT

catalog_fp = api.download(
    roi='notebooks/shapefiles/s2grid=4772924.geojson',
    startdate=START, enddate=END,
    bands=['vv', 'vh'],
    dst_folderpath='$OUT/imagery_s1',
    source='mpc', collection='sentinel-1-rtc',
    properties_filter=pf,
    max_tiles=MAX_TILES, progress=True,
)
result = {'step': 'download_s1', 'status': 'ok', 'pass': True,
          'metrics': {'catalog_filepath': catalog_fp, 'properties_filter': pf,
                      'window': [START, END]},
          'expected': {}, 'error': None}
os.makedirs('$OUT', exist_ok=True)
with open('$OUT/_result_download_s1.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
```

- **Expect:** anonymous discovery + download (no key prompt, no 401/403/404), only the chosen
  partition's scenes, `pass: True`.
- **PASS if:** `_result_download_s1.json` has `pass: true` and
  `$OUT/imagery_s1/catalog.parquet` exists.
- **If it fails with a 401/403/404 or a key prompt:** that contradicts D10 (retracted) —
  paste the exact error; do not set the key to work around it, that would hide the finding.
- **If `max_tiles` is still exceeded:** the error now reports how many tiles survived the
  filter and that it already narrowed — go back to rule 2 or 3, do not just raise the cap.
- **If it fails / hangs:** Ctrl-C is safe; `mpc.download` skips files already on disk, so
  re-running resumes.

### Step 1c — add a small slice of the OTHER orbit state (only if step 1a found two)

AC11 needs a catalog that genuinely spans two orbit states, or step 3a has nothing to raise
about. This adds **one repeat cycle** (~12 days) of the orbit state you did *not* choose —
a handful of scenes, not a second full archive — into the **same** folder and catalog.

```bash
"$PY" -c "
import json, os
from fsd import api

OTHER = 'descending'          # the orbit state NOT chosen in step 1b
SLICE_START, SLICE_END = '2018-06-01', '2018-06-07'   # 6 d ~= 1-2 scenes ~= 3.7-7.4 GB

catalog_fp = api.download(
    roi='notebooks/shapefiles/s2grid=4772924.geojson',
    startdate=SLICE_START, enddate=SLICE_END,
    bands=['vv', 'vh'],
    dst_folderpath='$OUT/imagery_s1',
    source='mpc', collection='sentinel-1-rtc',
    properties_filter={'sat:orbit_state': OTHER},
    max_tiles=10, progress=True,
)
result = {'step': 'download_s1_other_orbit_slice', 'status': 'ok', 'pass': True,
          'metrics': {'catalog_filepath': catalog_fp, 'orbit_state': OTHER,
                      'window': [SLICE_START, SLICE_END]},
          'expected': {}, 'error': None}
with open('$OUT/_result_download_s1_other_slice.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
```

- **Skip this step entirely if step 1a found only ONE orbit state** — then step 3a is expected
  to succeed, and AC11's raise is covered by the unit tests alone. Say so in your write-up.
- **PASS if:** `pass: true`. Expect **1-2 scenes, ~3.7-7.4 GB** — enough to make the
  catalog span two orbit states, which is all AC11 needs.

### Step 2 — verify what actually landed in the catalog

```bash
"$PY" -c "
import json
from fsd.catalog.catalog import TileCatalog

gdf = TileCatalog('$OUT/imagery_s1/catalog.parquet').read()
orbits = {}
for p in gdf['properties']:
    props = json.loads(p) if p else {}
    key = (props.get('sat:orbit_state'), props.get('sat:relative_orbit'))
    orbits[key] = orbits.get(key, 0) + 1
result = {'step': 'inspect_orbits', 'status': 'ok', 'pass': True,
          'metrics': {'n_rows': int(len(gdf)),
                      'orbit_relative_orbit_counts': {str(k): v for k, v in orbits.items()}},
          'expected': {}, 'error': None}
with open('$OUT/_result_inspect_orbits.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
```

- **Expect:** exactly the partition(s) step 1b/1c downloaded — nothing else. This is the
  check that `properties_filter` did what it claimed at DOWNLOAD time, not just at build time.
- **PASS if:** the `(orbit_state, relative_orbit)` keys here are a subset of what step 1a
  reported, and contain the orbit state chosen in step 1b. If step 1c ran, **two** orbit states
  must appear — that is what makes step 3a's AC11 raise a real result rather than a hypothetical.
- **PASS if:** `n_rows > 0`. **This step's OUTPUT decides step 3's `properties_filter`** — it is
  not a pass/fail gate on its own.
- **Record** which `sat:orbit_state` value(s) appear, and how many `relative_orbit` values share
  the dominant one — you need this for step 3.

### Step 3a — build the S1 cube (first attempt, no `properties_filter`)

```bash
"$PY" -c "
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
        catalog_filepath='$OUT/imagery_s1/catalog.parquet',
        startdate='2018-06-01', enddate='2018-07-01', mosaic_days=10,
        bands=['vv', 'vh'], id_col='fid', label_col='crop',
        export_folderpath='$OUT/training_s1',
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
with open('$OUT/_result_build_s1_no_filter.json', 'w') as f:
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
  stopped.

**Observed 2026-09-12 — this step PASSED, and here is exactly what it looked like**, so the next
reader is not misled by the result file:

```
ValueError: build_datacube: rows span multiple values of ('sat:orbit_state',) (spec 58 D9) ...
  (sat:orbit_state='ascending',  sat:relative_orbit=146): 5 acquisition(s), ROI coverage 100.0%
  (sat:orbit_state='descending', sat:relative_orbit=22):  2 acquisition(s), ROI coverage 100.0%
```

⚠️ **The `_result.json` for that run recorded something completely different:**
`FileNotFoundError: ... /845512/metadata.pickle.npy`. That is NOT a second bug in the build —
it is the verb-level symptom of the gap noted above. The D9 `ValueError` is raised inside the
Snakemake **subprocess**; `run_create_datacube` does not check the runner's return code, so
`create_training_data` carries on to the flatten phase and dies looking for a cube that was
never written. **The FileNotFoundError names a cell id and a missing `.npy` and says nothing
about orbits** — it is actively misleading on its own. Always read the terminal, not just the
result file, when this step fails. (Reported for decision; not fixed in P2.)
- **PASS if:** the outcome matches what step 2 predicted. A raise when step 2 saw one orbit
  state (or a silent success when it saw two) is the actual failure to report.

### Step 3b — build the S1 cube with `properties_filter` (only if step 3a raised)

Pre-filled with `'ascending'` — the group step 3a's enumeration showed with the most
acquisitions (5 vs 2), run 2026-09-12. Use whatever *your* step 3a enumerated if it differs.

Note this writes to a **different** window folder than step 3a did: `properties_filter` is part
of `params_key`'s digest (D9.3), so a differently-filtered re-run can never collide with, or
silently resume, another selection's cubes. Step 3a's partial folder is left behind on purpose.

```bash
"$PY" -c "
import geopandas as gpd
import json
from fsd import api

cell = gpd.read_file('notebooks/shapefiles/s2grid=4772924.geojson')
gdf = gpd.read_file('notebooks/shapefiles/AT_2018_TRAIN.geojson').to_crs(cell.crs)
gdf = gdf[gdf.intersects(cell.geometry.iloc[0])]  # the 43 fields inside the cell
td = api.create_training_data(
    label_polygons=gdf,
    catalog_filepath='$OUT/imagery_s1/catalog.parquet',
    startdate='2018-06-01', enddate='2018-07-01', mosaic_days=10,
    bands=['vv', 'vh'], id_col='fid', label_col='crop',
    export_folderpath='$OUT/training_s1',
    collection='sentinel-1-rtc',
    properties_filter={'sat:orbit_state': 'ascending'},
)
result = {'step': 'build_s1_with_filter', 'status': 'ok', 'pass': True,
          'metrics': {'n_pixels': td.n_pixels, 'n_timestamps': td.n_timestamps,
                      'bands': td.bands},
          'expected': {}, 'error': None}
with open('$OUT/_result_build_s1_with_filter.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
```

- **Expect:** succeeds this time — no orbit-state raise, since `properties_filter` narrowed the
  catalog to one value before the build. The 5 ascending/146 scenes fall in 3 calendar windows.
- **PASS if:** `pass: true`, `td.bands == ['vv', 'vh']`, and `td.n_timestamps == 3`.

### Step 4 — build the S2 cube for the SAME cell/window (identical verb shape)

```bash
"$PY" -c "
import geopandas as gpd
import json
from fsd import api

cell = gpd.read_file('notebooks/shapefiles/s2grid=4772924.geojson')
gdf = gpd.read_file('notebooks/shapefiles/AT_2018_TRAIN.geojson').to_crs(cell.crs)
gdf = gdf[gdf.intersects(cell.geometry.iloc[0])]  # the 43 fields inside the cell
td = api.create_training_data(
    label_polygons=gdf,
    catalog_filepath='$FSD_MAIN/tests/outputs/demo_e2e/imagery/catalog.parquet',
    startdate='2018-06-01', enddate='2018-07-01', mosaic_days=10,
    bands=['B04', 'B08', 'SCL'], id_col='fid', label_col='crop',
    export_folderpath='$OUT/training_s2',
    collection='sentinel-2-l2a',
)
result = {'step': 'build_s2', 'status': 'ok', 'pass': True,
          'metrics': {'n_pixels': td.n_pixels, 'n_timestamps': td.n_timestamps,
                      'bands': td.bands},
          'expected': {}, 'error': None}
with open('$OUT/_result_build_s2.json', 'w') as f:
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
- **`td.n_timestamps` should match between the S1 and S2 runs, and should be 3** — the window is
  2018-06-01 → 2018-07-01 with `mosaic_days=10`, so `T = ceil(30/10) = 3` for both, by
  construction (same `startdate`/`enddate`/`mosaic_days` → the same calendar-interval mosaic
  axis, ADR 0010), even though the two cubes come from unrelated acquisitions. A mismatch here
  is a real finding, not a data quirk.
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
build ONE grid cell's cube directly and export it as a GeoTIFF.

`ORBIT` is pre-filled to match step 3b. **It is required here**: this step builds from the raw
catalog, which spans both orbit states, so leaving it unset raises the same D9 error step 3a
did. That `build_datacube` accepts `properties_filter` at all is a P2-review fix — before it,
this step could only be told it was wrong, never narrowed.

The export picks the mosaic window with the most valid pixels rather than blindly taking the
first, which can legitimately be empty (5 acquisitions spread over 3 calendar windows).

```bash
"$PY" -c "
import geopandas as gpd, os, json, numpy as np, rasterio
from fsd.catalog.catalog import TileCatalog, filter_gdf
from fsd.datacube import builder

ORBIT = 'ascending'   # must match step 3b

cat = TileCatalog('$OUT/imagery_s1/catalog.parquet').read()
shapes = gpd.read_file('notebooks/shapefiles/s2grid=4772924.geojson')
subset = filter_gdf(cat, shapes, '2018-06-01', '2018-07-01')
flat = builder.flatten_catalog(subset)
out = '$OUT/s1_eyeball'
builder.build_datacube(
    catalog_subset=flat, shape_gdf=shapes,
    startdate='2018-06-01', enddate='2018-07-01', bands=['vv', 'vh'], mosaic_days=10,
    export_folderpath=out, if_missing_files='warn',
    properties_filter={'sat:orbit_state': ORBIT},
)
dc = np.load(os.path.join(out, 'datacube.npy'))
md = np.load(os.path.join(out, 'metadata.pickle.npy'), allow_pickle=True)[()]

valid = [int(np.count_nonzero(dc[t, :, :, 0])) for t in range(dc.shape[0])]
best = int(np.argmax(valid))
npx = dc.shape[1] * dc.shape[2]
vv = dc[best, :, :, 0]
vv_valid = vv[np.nonzero(vv)]

profile = dict(md['geotiff_metadata'])
profile.update(count=2, dtype='float32')
tif = os.path.join(out, 'vv_vh_t%d.tif' % best)
with rasterio.open(tif, 'w', **profile) as dst:
    dst.write(dc[best, :, :, 0].astype('float32'), 1)
    dst.write(dc[best, :, :, 1].astype('float32'), 2)

result = {'step': 'qgis_eyeball', 'status': 'ok', 'pass': bool(valid[best] > 0),
          'metrics': {'cube_shape': list(dc.shape), 'bands': md['bands'],
                      'dtype': str(dc.dtype),
                      'timestamps': [str(t) for t in md['timestamps']],
                      'valid_px_per_timestamp': valid, 'px_per_timestamp': npx,
                      'exported_timestamp_index': best, 'geotiff': tif,
                      'vv_min': float(vv_valid.min()) if vv_valid.size else None,
                      'vv_max': float(vv_valid.max()) if vv_valid.size else None,
                      'vv_mean': float(vv_valid.mean()) if vv_valid.size else None},
          'expected': {'n_timestamps': 3, 'bands': ['vv', 'vh']}, 'error': None}
with open('$OUT/_result_qgis_eyeball.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
```

- **Expect:** `cube_shape` = `[3, H, W, 2]`, `dtype` `float32`, `bands` `['vv', 'vh']`, and at
  least one timestamp with `valid_px` near `px_per_timestamp`.
- **Sanity-check the values, not just the shape:** RTC gamma naught is **linear power, not dB**
  (D17: `scale=1.0`, already calibrated). Land backscatter should land roughly in **0.01–1.0**,
  i.e. about −20 to 0 dB. `vv_mean` far outside that, or negative, means something is wrong —
  negative values in particular would mean source nodata (`-32768`) leaked in as data.
- **Then open the exported GeoTIFF in QGIS.** Load band 1 (VV) alone first: real SAR backscatter
  should show field-scale texture, not a flat value or structureless noise. This is not optional
  (`CLAUDE.md`: raster ops get eyeballed).
- **PASS if:** `pass: true`, the raster opens, is not entirely nodata, and shows plausible
  backscatter texture over the Austria cell.
- **If it raises the D9 orbit error:** `ORBIT` is unset or does not match a value in the
  catalog — that is this step's own guard working, not a build failure.

## Success criteria (`_result.json`)

Files under `$OUT/` (i.e. the **main** checkout's `fsd/tests/outputs/p58_p2/`):

```
_result_probe_window.json              _result_download_s1.json
_result_download_s1_other_slice.json   _result_inspect_orbits.json
_result_build_s1_no_filter.json        _result_build_s1_with_filter.json
_result_build_s2.json                  _result_qgis_eyeball.json
```

**The run passes when:**
1. Every result file's `pass` is `true` (or, for `build_s1_no_filter`, its outcome matched what
   step 2 predicted).
2. Step 4's note on verb-signature identity is filled in and confirms only the expected keywords
   differ.
3. You have looked at the QGIS raster and it shows real backscatter, not a blank/flat image,
   and `_result_qgis_eyeball.json`'s `vv_mean` sits in the physically plausible 0.01–1.0 range
   for linear-power gamma naught.

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
- This window's S1 archive (`$OUT/imagery_s1/`) is scoped to one grid cell — it is
  a proof archive, not a replacement for a full-ROI S1 download. A full-ROI S1 pass (if ever
  wanted) is a separate, larger run-book, modelled on `runbooks/58-redownload-austria-mpc.md`.
- THE ORDER's next item after P2 lands is spec 58 **P3** (`hls2-s30`/`hls2-l30`, Window B) — see
  `PROGRESS.md`.
