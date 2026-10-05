# AGENTS.md — fsd

Instructions for AI coding agents working in this repo. Humans: start with `CONTRIBUTING.md`; this
file adds the code conventions and the optional agent method.

## What this is

`fsd` downloads Sentinel-2 L2A imagery, builds datacubes and flattens them to training data, with a
verb API (`fsd.download`, `fsd.create_training_data`, `run_inference`, `deploy`). It runs locally or
scales onto Azure ML without cloud lock-in. Model *training* stays on the user's side. Plan:
`ROADMAP.md`. Design: `ARCHITECTURE.md`. Vocabulary: `CONTEXT.md`.

## Setup and checks

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,local]"            # CI installs every extra; add what your change touches
.venv/bin/python -m pytest -q            # fast, synthetic, deterministic (network marker is off)
.venv/bin/ruff check src/ tests/
.venv/bin/python scripts/docs_kwarg_sweep.py   # notebook/doc calls still match verb signatures
```

In a git worktree there is no `.venv`: run
`PYTHONPATH=src <main-checkout>/.venv/bin/python -m pytest -q -p no:cacheprovider`.

## The four gates (every PR; details in `CONTRIBUTING.md`)

1. CI green. 2. Linked issue; a change to a convention, an on-disk format or the public API also needs
a signed-off short spec (`specs/TEMPLATE.md`). 3. Reviewed by someone other than the author (for an
agent: a different session from the one that wrote the change); every finding is fixed in the PR or
filed as an issue. 4. Real-run evidence pasted in the PR when real data, the cloud or pixels are touched.

Every change reaches `main` through a pull request. Work on a branch, push it and open a draft PR; the
maintainer merges. Never push to `main`. The PR description holds the work's state (done, next, review
findings). The PR title becomes the release-note line.

## Rules for all agents

1. **Hand risky runs to a human.** Run fast local checks yourself (pytest, ruff, grep, reading files).
   Anything that touches the network, the cloud or credentials, or runs longer than a few minutes, goes
   to the human, who pastes back the result.
2. **Prior-art check.** Before proposing a mechanism (a design, process or test pattern), say whether
   it is homemade. If it is, look for the established practice documented **before 2022-11-30** and
   prefer it. Cite it so a reviewer can verify it (a link, plus what it contributed), or say what you
   searched and that nothing fit. Never invent a precedent to satisfy this rule.
3. **Privacy.** Describe an identifier; never spell it out in anything committed (GUIDs, resource
   names, personal paths). Blob paths (storage account, container, `abfss://`) may be committed.
4. **Ask before changing a contract.** If a request contradicts a rule here, say so before proceeding.

## Code conventions

- **All file I/O goes through `fsd.storage`** (fsspec), so local, Azure Blob and S3 are config, not
  code. The one exception is raster pixel reads, which use rasterio/GDAL VSI. S3 transport is generic
  (`s3fs`, any `endpoint_url`); no direct `boto3`.
- **Raster ops take and return `(data, profile)`**, so they chain as `sequence=[(func, kwargs), ...]`.
- **Band math uses the 5-D contract** `(samples, timestamps, height, width, bands)` plus a
  `band_indices` dict `{band_name: index}`.
- **Catalog = GeoParquet** (`TileCatalog`); STAC is an additive export view. Datacube artifacts are
  `datacube.npy` + `metadata.pickle.npy`. Nodata = 0.
- **Calendar-interval mosaic is the default**: cubes over the same start/end/`mosaic_days` share an
  identical `timestamps` axis, which `flatten` requires.
- **No back-compat shims for the archive layout.** Old artifacts raise an error that names the fix.
  On-disk format versions keep their supported lists.
- **Geospatial principles.** Resample *to* a real reference image of known resolution (B08 = 10 m);
  never trust the resampler to align to an abstract grid. `rasterio.merge` needs one CRS, so collapse
  MGRS tiles into the max-mean-`area_contribution` zone before merging. Eyeball raster output in QGIS;
  unit tests alone do not validate pixels.
- **Terminology: never write a bare "tile".** An **MGRS tile** is the ~110 km source granule
  (`T36PZT`, catalog column `mgrs_tile`); it is what we download and what the builder merges across.
  A **grid cell** is the ~5 km S2-geometry subdivision of an ROI (`fsd.grid.roi_to_s2_grids`, id like
  `165b09c`, column `id`); one grid cell = one inference datacube = one per-cell task.
- **Docs:** keep the living docs true in the same PR as the code (`README.md`, `CONTRIBUTING.md`,
  `ARCHITECTURE.md`, `CONTEXT.md`, `LIMITATIONS.md`, `ROADMAP.md`, `docs/`). Specs, ADRs and run-books
  are point-in-time: never edit them after sign-off except by amendment (specs) or a superseding ADR.
  `TODO #NN` in old text means GitHub issue #NN.

## Optional agent method (not enforced; nobody can check how the work was produced)

- **Spec flow.** Open the tracking issue; its number is the spec's number (`specs/NNN-<slug>.md`,
  header `issue: "#NNN"` required from 102). Grill the design before writing it. An ADR lands in the
  same PR as its spec, with the next sequential `docs/adr/NNNN-` number.
- **Model split.** A stronger model for design, debugging and review; a cheaper one to implement
  against a signed-off spec. Do not spawn subagents just to write code.
- **Handoffs.** At a session boundary, write the state into the draft PR description (or the tracking
  issue before a PR exists), then start a fresh session pointed at it. Do not rely on a compacted
  context.
- **Run-books.** A credentialed or visual check is handed over as a notebook (`runbooks/TEMPLATE.ipynb`):
  Markdown says what each step does and what PASS means, plain `assert`s, no environment variables, a
  Settings cell for every input, outputs cleared before commit (`tests/test_notebooks.py` enforces it).
- **Session start.** Read `gh pr list` (work in flight) and the pinned "Order of work" issue. The tests
  must be green before you start; do not pin expected test counts anywhere.
