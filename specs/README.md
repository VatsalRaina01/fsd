# Specs — index

> **Frozen snapshot (spec 102 D7, ADR 0033, 2026-10-06).** This table lists specs 00–59 and gets no
> more rows. **For a newer spec, read its tracking issue:** from spec 102 on, a spec's number is its
> tracking issue's number, and the issue's state is its implementation status (open = not done).
> The "implemented?" column was re-checked against merge commits on 2026-10-06 and will not be
> updated again. Each spec's own `status:` header (`current` / `superseded-by-NN` / `historical`,
> ADR 0023) still holds.

| # | spec | status | implemented? | evidence |
|---|------|--------|---------------|----------|
| 00 | [overview.md](00-overview.md) | current | across `src/fsd/` | the package itself |
| 01 | [sources.md](01-sources.md) | current | yes | `tests/test_cdse.py`, `tests/test_mpc.py` |
| 02 | [catalog.md](02-catalog.md) | current | yes | `tests/test_catalog.py`; ADR 0006 |
| 03 | [datacube.md](03-datacube.md) | current | yes | `tests/test_datacube_builder.py`; ADR 0007 |
| 04 | [datacube-ops.md](04-datacube-ops.md) | current | yes | `tests/test_datacube_ops.py` |
| 05 | [flatten.md](05-flatten.md) | current | yes | `tests/test_datacube_flatten.py` |
| 06 | [bands.md](06-bands.md) | current | yes | `tests/test_bands.py` |
| 07 | [raster.md](07-raster.md) | current | yes | `tests/test_raster.py` |
| 08 | [workflows.md](08-workflows.md) | current | yes | `tests/test_workflows.py`, `tests/test_scaffold.py`; ADR 0004 |
| 09 | [notebooks.md](09-notebooks.md) | current | yes | `pyproject.toml` (src-layout, extras) |
| 10 | [storage-and-scale.md](10-storage-and-scale.md) | current | yes | `tests/test_azure_seam.py`; ADR 0003 |
| 11 | [benchmark-throughput-sweep.md](11-benchmark-throughput-sweep.md) | current | yes | `tests/test_benchmark_throughput.py`, `benchmarks/datacube_throughput_report.md` |
| 12 | [benchmark-read-instrumentation.md](12-benchmark-read-instrumentation.md) | current | yes | same harness as spec 11 |
| 13 | [cog-vs-jp2-experiment.md](13-cog-vs-jp2-experiment.md) | current | yes | `tests/test_prep_cog.py`, `benchmarks/cog_vs_jp2_report.md` |
| 14 | [cog-on-download.md](14-cog-on-download.md) | current | yes | `src/fsd/raster/cog.py`; ADR 0001, ADR 0014 |
| 15 | [calendar-mosaic.md](15-calendar-mosaic.md) | current | yes | ADR 0010 |
| 16 | [packaging-and-api.md](16-packaging-and-api.md) | current | yes | `tests/test_api.py` |
| 17 | [stac-catalog.md](17-stac-catalog.md) | current | yes | `tests/test_catalog_stac.py`; ADR 0016 |
| 18 | [model-adapter.md](18-model-adapter.md) | current | yes | `tests/test_model.py`; ADR 0018 |
| 18 | [model-bundle-explainer.md](18-model-bundle-explainer.md) | current | n/a (companion explainer) | see spec 18 evidence |
| 19 | [e2e-demo.md](19-e2e-demo.md) | superseded-by-23 | superseded | `demos/e2e_austria.py` replaced `demos/e2e_ethiopia.py` |
| 20 | [datacube-tile-merge-bug.md](20-datacube-tile-merge-bug.md) | current | yes | `tests/test_datacube_builder.py` (merge fix) |
| 21 | [roi-inference-verb.md](21-roi-inference-verb.md) | current | yes | `tests/test_api_roi.py` |
| 22 | [unify-inference-runner.md](22-unify-inference-runner.md) | current | yes | `tests/test_runners.py`; ADR 0015 |
| 23 | [e2e-austria-local-gate.md](23-e2e-austria-local-gate.md) | current | yes | `demos/e2e_austria.py`, `demos/E2E_AUSTRIA.md` |
| 24 | [working-contract.md](24-working-contract.md) | current | yes | `CLAUDE.md`, `runbooks/TEMPLATE.md` |
| 25 | [download-convert-redesign.md](25-download-convert-redesign.md) | current | yes | `tests/test_download_cli.py`; ADR 0019 |
| 25b | [pipeline-exception-safety.md](25b-pipeline-exception-safety.md) | current | yes | `tests/test_download_cli.py` |
| 26 | [safe-download-runner.md](26-safe-download-runner.md) | current | yes | `tests/test_download_cli.py`; `runbooks/26-download-confirm-run.md` |
| 27 | [titiler-leaflet-stac-verify.md](27-titiler-leaflet-stac-verify.md) | historical | not implemented (rejected at sign-off) | replacement plan: `demos/TITILER_LEAFLET.md`, TODO #26-#29 |
| 28 | [stac-output-geometry-fix.md](28-stac-output-geometry-fix.md) | current | yes | `tests/test_catalog_stac.py` |
| 29 | [tier1-prestyled-xyz-validation.md](29-tier1-prestyled-xyz-validation.md) | current | yes | `tests/test_titiler_serve.py`, `demos/titiler_serve.py` |
| 30 | [tier2-mini-mpc-validation.md](30-tier2-mini-mpc-validation.md) | current | yes | `demos/mini_mpc/`; `runbooks/30-tier2-mini-mpc.md` |
| 31 | [p1-azure-storage-seam.md](31-p1-azure-storage-seam.md) | current | yes | `tests/test_azure_seam.py`; ADR 0003 |
| 32 | [mpc-source-baseline-harmonization.md](32-mpc-source-baseline-harmonization.md) | current | yes | `tests/test_mpc.py`, `tests/test_declaration.py` |
| 33 | [mpc-reprocessing-dedup.md](33-mpc-reprocessing-dedup.md) | current | yes | `tests/test_mpc.py`; `runbooks/33-mpc-dedup-live.md` |
| 34 | [ingest-normalization-contract.md](34-ingest-normalization-contract.md) | current | yes | `tests/test_declaration.py`; ADR 0011, ADR 0012 |
| 35 | [declaration-persistence.md](35-declaration-persistence.md) | current | yes | `tests/test_declaration.py`; ADR 0013 |
| 36 | [scale-runner.md](36-scale-runner.md) | current | yes | `tests/test_scale_runner.py`; ADR 0005, ADR 0017 |
| 37 | [download-on-aml.md](37-download-on-aml.md) | current | yes | `tests/test_download_aml.py` |
| 38 | [inference-on-aml.md](38-inference-on-aml.md) | current | yes; cluster-validated 2026-07-28 | `tests/test_infer_aml.py`; `runbooks/38-inference-on-aml.md`; merge `4be331b` |
| 39 | [training-data-on-aml.md](39-training-data-on-aml.md) | current | yes | `tests/test_training_data_aml.py` |
| 40 | [e2e-aml-demo-script.md](40-e2e-aml-demo-script.md) | current | yes | `tests/test_e2e_aml_demo_helpers.py`, `tests/test_plot_aml_timings.py`, `tests/test_restamp_cli.py`; ADR 0021 |
| 41 | [docs-refactor.md](41-docs-refactor.md) | current | yes (P1–P7; P6 = spec 42, P8 = spec 43) | `tests/test_docs.py`; ADRs 0022–0026; merge `e144d27` (P7) |
| 42 | [tutorial-fixture.md](42-tutorial-fixture.md) | current | yes | `tests/data/tutorial/`, `tests/test_tutorial_fixture.py`, `tests/test_build_fixture.py`; merge `2bdc4c6` |
| 43 | [history.md](43-history.md) | current | yes | `docs/history.md`; ADR 0027; merge `675a1c7` (closes #55) |
| 44 | [bundle-carried-adapter-code.md](44-bundle-carried-adapter-code.md) | current | phase 1 yes; phase 2 (D7/D8) superseded by spec 51 | `tests/test_bundle_code.py`; merge `9881c1e` |
| 45 | [bundle-transparency-and-image-verification.md](45-bundle-transparency-and-image-verification.md) | current | yes | `tests/test_bundle_transparency.py`, `src/fsd/model/verify_image.py`; merge `20b6009` |
| 46 | [run-addressability-and-grid-dedup.md](46-run-addressability-and-grid-dedup.md) | current | yes | `tests/test_grid.py`, `tests/test_workflows.py`; merge `20b6009` |
| 47 | [driver-side-honesty.md](47-driver-side-honesty.md) | current | yes, except D9 (deferred: #75) | `tests/test_download_aml.py`, `tests/test_progress.py`; merge `2e5b3b3` |
| 48 | [verify-adapter.md](48-verify-adapter.md) | current | yes | `tests/test_verify_adapter.py`; merge `c0d9d17` |
| 49 | [skip-work-already-done.md](49-skip-work-already-done.md) | current | yes | `tests/test_build_skip.py`, `tests/test_flatten_skip.py`; merge `c0d9d17` |
| 50 | [backward-walk.md](50-backward-walk.md) | current | steps 0/1/2/4 yes; step 3 (D9) waits on #84 | `tests/test_backward_walk.py`; merge `1876c16` |
| 51 | [deploy-model-registry.md](51-deploy-model-registry.md) | current | yes (§9 steps 0–3) | `tests/test_registry.py`, `tests/test_deploy.py`; merge `2b5ae4b` and follow-ups |
| 52 | [registry-on-blob.md](52-registry-on-blob.md) | current | yes; verified on Azure 2026-08-25 | `tests/test_registry.py`; `runbooks/52-registry-on-blob.md`; merge `f2fe6bf` |
| 53 | [blob-registry-on-the-local-run-path.md](53-blob-registry-on-the-local-run-path.md) | current | yes | `tests/test_local_bundle_staging.py`; merge `38a2d09` |
| 54 | [user-level-config.md](54-user-level-config.md) | current | yes | `tests/test_config.py`, `tests/test_cli.py`; merge `9a00f2b` (closes #78) |
| 55 | [root-leaves-the-config.md](55-root-leaves-the-config.md) | current | yes | `tests/test_config.py`, `tests/test_cli.py`; merge `7e809cd` |
| 56 | [image-definitions-and-registry.md](56-image-definitions-and-registry.md) | current | yes | `tests/test_image_definition.py`, `tests/test_image_registry.py`; merge `b6ba610` |
| 57 | [collect-and-stac-round-trips.md](57-collect-and-stac-round-trips.md) | current | yes | `tests/test_catalog_stac.py`, `tests/test_api_roi.py`; merge `52f7b2b` |
| 58 | [collection-agnostic-verbs.md](58-collection-agnostic-verbs.md) | current | P1 + P2 (S1 RTC) yes; P3 (HLS) not started | `tests/test_spec58_p1.py`, `tests/test_spec58_p2.py`; ADRs 0028–0031; merges `38954a4`, `795b117` |
| 59 | [imagery-archive-layout.md](59-imagery-archive-layout.md) | current | P1, P2 Window A, D12 yes; full Austria re-download not done | `tests/test_spec59_p1.py`; ADR 0032; merges `d8aa8dd`, `7c5493e` |
| — | [research-s2-reprocessing-dedup.md](research-s2-reprocessing-dedup.md) | current | n/a (research notes) | cited by spec 33 |

## Conventions
- **Numbers are never reused or renumbered.** A superseded spec keeps its number; read the one
  named in `superseded_by` instead.
- **`25b` and `research-s2-reprocessing-dedup`** are non-numeric-suffix filenames; `superseded_by`
  (when used) names the file's stem exactly as it appears in `specs/`, not a bare two-digit number.
- Status header format and rules: spec 41 D4 / ADR 0023. Why this table is frozen: ADR 0033.
