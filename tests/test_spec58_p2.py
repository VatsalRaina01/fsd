"""Spec 58 P2 acceptance criteria — `sentinel-1-rtc` + `properties_filter` (D9/D17).

AC numbering follows specs/58-collection-agnostic-verbs.md §5 (the amended P2 section).
AC15 is a run-book (`runbooks/58-p2-window-a.md`), not a pytest AC -- see it for the
"S1 and S2 build/create_training_data with no verb-signature difference" proof.
"""

from __future__ import annotations

import datetime
import json
import pathlib

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import rasterio
import shapely
from rasterio.transform import from_origin

from fsd import api, config
from fsd import collections as _collections
from fsd.catalog import catalog
from fsd.catalog import declaration as declaration_module
from fsd.datacube import builder
from fsd.sources import mpc
from fsd.storage import fs
from fsd.workflows import create_datacube


def _s1_flattened_gdf(rows: list[tuple[str, str, "shapely.geometry.base.BaseGeometry"]]):
    """A band-flattened (`flatten_catalog`-shaped) GeoDataFrame for one requested band
    (`vv`), given `(id, orbit_state, geometry)` triples -- just enough columns for
    `builder._enforce_mosaic_partition` (and, transitively, `build_datacube`'s
    pre-image-load checks) to run without any real raster file."""
    data = {
        "id": [r[0] for r in rows],
        "filepath": ["" for _ in rows],
        "band": ["vv" for _ in rows],
        "timestamp": [pd.Timestamp("2018-04-01", tz="UTC") for _ in rows],
        "geometry": [r[2] for r in rows],
        "area_contribution": [1.0 for _ in rows],
        "offset": [0 for _ in rows],
        "nodata": [-32768 for _ in rows],
        "properties": [json.dumps({"sat:orbit_state": r[1]}) for r in rows],
    }
    return gpd.GeoDataFrame(data, crs="EPSG:4326")


# --- D17: the sentinel-1-rtc declaration ---------------------------------------------

def test_s1_rtc_declaration_matches_spec_table():
    decl = _collections.get("sentinel-1-rtc")
    assert decl.reference_band is None
    assert decl.native_grid is False
    assert decl.mask_spec is None
    assert decl.nodata == -32768
    assert decl.scale == 1.0
    assert decl.radiometry_bands == ()  # empty, not None (D17)
    assert decl.band_aliases == ()
    assert decl.supports_cloud_cover is False
    assert decl.requires_subscription_key is False
    assert decl.mosaic_partition == ("sat:orbit_state",)
    assert decl.partition_policy == "raise"


def test_s1_rtc_declaration_round_trips_through_json():
    decl = _collections.get("sentinel-1-rtc")
    assert declaration_module.from_json(declaration_module.to_json(decl)) == decl


def test_mpc_serves_sentinel_1_rtc():
    assert "sentinel-1-rtc" in mpc.SERVED_COLLECTIONS


# --- bug found while wiring S1 ingest: offset_for_item raised for non-S2 items --------

def test_mpc_items_to_gdf_does_not_derive_offset_for_a_non_radiometric_collection():
    """`_items_to_gdf` used to call `_s2_radiometry.offset_for_item` unconditionally,
    which raises `ValueError` for any item lacking S2's processing-baseline properties
    -- every sentinel-1-rtc item. A collection declaring `radiometry_bands=()` has
    nothing to derive, so ingest must not even try."""
    class _Item:
        id = "S1B_..._rtc"
        datetime = pd.Timestamp("2018-04-01", tz="UTC")
        properties = {"sat:orbit_state": "ascending"}  # no s2:processing_baseline
        geometry = shapely.geometry.mapping(shapely.geometry.box(0, 0, 1, 1))

        def get_self_href(self):
            return "https://example/x"

    decl = _collections.get("sentinel-1-rtc")
    gdf = mpc._items_to_gdf([_Item()], collection="sentinel-1-rtc", declaration=decl)
    assert gdf["offset"].iloc[0] == 0


# --- bug found while drafting the AC15 run-book: reference_band=None never built ----

def test_reference_band_none_builds_a_real_cube_not_just_declaration_shape(tmp_path):
    """D11 says `reference_band=None` (S1 RTC, HLS: bands are already grid-uniform)
    means "use the first requested band for the merge geometry, run no resample step" --
    but `build_datacube` compared `catalog_gdf["band"] == reference_band` where
    `reference_band` was still `None`, which matches NOTHING, leaving `ref_indices`
    empty and the merge failing on zero images. No P1 test built a real cube with
    `reference_band=None`; every P1 AC checked the declaration/preflight shape, not a
    pixel. This is the missing real-run proof, for the collection that actually needs it."""
    crs = "EPSG:32633"
    transform = from_origin(500000, 5000000, 10, 10)
    tile_box = shapely.geometry.box(500000, 4999960, 500040, 5000000)

    def _write(path, value):
        with rasterio.open(
            path, "w", driver="GTiff", height=4, width=4, count=1,
            dtype="float32", crs=crs, transform=transform, nodata=-32768,
        ) as dst:
            dst.write(np.full((1, 4, 4), value, dtype=np.float32))

    ts = pd.Timestamp("2018-06-01", tz="UTC")
    rows = []
    for band, val in [("vv", 0.1), ("vh", 0.05)]:
        p = tmp_path / f"{band}.tif"
        _write(p, val)
        rows.append({
            "id": "s1_item", "filepath": str(p), "band": band, "timestamp": ts,
            "geometry": tile_box, "area_contribution": 100.0,
            "properties": json.dumps({"sat:orbit_state": "ascending"}),
        })
    catalog_subset = gpd.GeoDataFrame(rows, crs=crs)
    shape_gdf = gpd.GeoDataFrame({"geometry": [tile_box]}, crs=crs)
    decl = _collections.get("sentinel-1-rtc")
    assert decl.reference_band is None  # the case under test

    out = tmp_path / "cube"
    builder.build_datacube(
        catalog_subset=catalog_subset, shape_gdf=shape_gdf,
        startdate=datetime.datetime(2018, 5, 31), enddate=datetime.datetime(2018, 6, 20),
        bands=["vv", "vh"], mosaic_days=20, declaration=decl,
        export_folderpath=str(out), if_missing_files=None,
    )
    dc = fs.load_npy(str(out / "datacube.npy"))
    md = fs.load_npy(str(out / "metadata.pickle.npy"), allow_pickle=True)[()]
    assert dc.shape == (1, 4, 4, 2)
    assert md["bands"] == ["vv", "vh"]
    assert dc[0, 0, 0, 0] == pytest.approx(0.1)
    assert dc[0, 0, 0, 1] == pytest.approx(0.05)


# --- AC11: rows spanning both orbit states raise, enumerating pairs + counts ---------

def test_ac11_mixed_orbit_states_raises_enumerating_counts_and_coverage():
    decl = _collections.get("sentinel-1-rtc")
    box1 = shapely.geometry.box(0, 0, 10, 10)
    catalog_subset = _s1_flattened_gdf([
        ("a1", "ascending", box1), ("a2", "ascending", box1),
        ("d1", "descending", box1),
    ])
    shape_gdf = gpd.GeoDataFrame({"geometry": [box1]}, crs="EPSG:4326")

    with pytest.raises(ValueError) as exc_info:
        builder.build_datacube(
            catalog_subset=catalog_subset, shape_gdf=shape_gdf,
            startdate=datetime.datetime(2018, 4, 1), enddate=datetime.datetime(2018, 9, 30),
            bands=["vv"], declaration=decl, export_folderpath="/tmp/unused-ac11",
            if_missing_files=None,
        )
    msg = str(exc_info.value)
    assert "sat:orbit_state" in msg
    assert "ascending" in msg and "descending" in msg
    assert "2 acquisition" in msg
    assert "1 acquisition" in msg
    assert "coverage" in msg.lower()


def test_ac11_single_orbit_state_does_not_raise():
    decl = _collections.get("sentinel-1-rtc")
    box1 = shapely.geometry.box(0, 0, 10, 10)
    catalog_subset = _s1_flattened_gdf([("a1", "ascending", box1), ("a2", "ascending", box1)])
    shape_gdf = gpd.GeoDataFrame({"geometry": [box1]}, crs="EPSG:4326")
    builder._enforce_mosaic_partition(catalog_subset, shape_gdf, decl)  # must not raise


def test_ac11_s2_never_enforces_partition():
    """`sentinel-2-l2a` declares `mosaic_partition=()` -- rows carrying any (or no)
    properties never trigger enforcement; P1's behaviour is unchanged."""
    decl = _collections.get(config.SATELLITE_S2L2A)
    box1 = shapely.geometry.box(0, 0, 10, 10)
    catalog_subset = _s1_flattened_gdf([("a1", "ascending", box1), ("d1", "descending", box1)])
    shape_gdf = gpd.GeoDataFrame({"geometry": [box1]}, crs="EPSG:4326")
    builder._enforce_mosaic_partition(catalog_subset, shape_gdf, decl)  # no-op, no raise


# --- AC12: properties_filter given succeeds; an uncarried key raises -----------------

def test_ac12_properties_filter_narrows_to_one_orbit_then_enforcement_succeeds():
    decl = _collections.get("sentinel-1-rtc")
    box1 = shapely.geometry.box(0, 0, 10, 10)
    catalog_subset = _s1_flattened_gdf([
        ("a1", "ascending", box1), ("a2", "ascending", box1),
        ("d1", "descending", box1),
    ])
    filtered = catalog.filter_by_properties(catalog_subset, {"sat:orbit_state": "descending"})
    assert sorted(filtered["id"]) == ["d1"]
    shape_gdf = gpd.GeoDataFrame({"geometry": [box1]}, crs="EPSG:4326")
    builder._enforce_mosaic_partition(filtered, shape_gdf, decl)  # must not raise


def test_ac12_properties_filter_uncarried_key_raises_naming_carried_keys():
    gdf = gpd.GeoDataFrame(
        {"properties": ['{"sat:orbit_state": "ascending"}', '{"sat:orbit_state": "descending"}']}
    )
    with pytest.raises(ValueError) as exc_info:
        catalog.filter_by_properties(gdf, {"sat:relative_orbit": 146})
    msg = str(exc_info.value)
    assert "sat:relative_orbit" in msg
    assert "sat:orbit_state" in msg


def test_ac12_properties_filter_value_matching_zero_rows_is_not_an_error():
    """A KNOWN key whose requested value matches nothing is an ordinary empty result,
    not the "uncarried key" error -- only a key absent from every row raises."""
    gdf = gpd.GeoDataFrame({"properties": ['{"sat:orbit_state": "ascending"}']})
    out = catalog.filter_by_properties(gdf, {"sat:orbit_state": "descending"})
    assert len(out) == 0


def test_ac12_empty_or_none_properties_filter_is_a_no_op():
    gdf = gpd.GeoDataFrame({"properties": ['{"sat:orbit_state": "ascending"}']})
    assert len(catalog.filter_by_properties(gdf, None)) == 1
    assert len(catalog.filter_by_properties(gdf, {})) == 1


# --- AC13: properties_filter selection changes the digest; empty selection doesn't ---

def test_ac13_empty_properties_filter_does_not_perturb_the_s2_digest():
    """Reimplements the PRE-P2 `params_key` formula independently (not by calling the
    SUT with a different code path) and checks the SUT's default (`properties_filter`
    omitted) still produces exactly that digest -- catching a regression where an empty
    selection sneaks in an extra `|` or empty component."""
    import hashlib

    decl = _collections.get(config.SATELLITE_S2L2A)
    bands = ["B04", "B08"]
    raw = "|".join([
        ",".join(bands), config.MOSAIC_SCHEME, config.SATELLITE_S2L2A,
        declaration_module.digest(decl),
    ])
    expected = hashlib.sha1(raw.encode()).hexdigest()[:8]

    assert create_datacube.params_key(
        bands, config.MOSAIC_SCHEME, collection=config.SATELLITE_S2L2A, declaration=decl,
    ) == expected
    assert create_datacube.params_key(
        bands, config.MOSAIC_SCHEME, collection=config.SATELLITE_S2L2A, declaration=decl,
        properties_filter=None,
    ) == expected
    assert create_datacube.params_key(
        bands, config.MOSAIC_SCHEME, collection=config.SATELLITE_S2L2A, declaration=decl,
        properties_filter={},
    ) == expected


def test_ac13_differing_properties_filter_selection_changes_the_digest():
    decl = _collections.get("sentinel-1-rtc")
    bands = ["vv", "vh"]
    none_key = create_datacube.params_key(
        bands, config.MOSAIC_SCHEME, collection="sentinel-1-rtc", declaration=decl,
    )
    asc = create_datacube.params_key(
        bands, config.MOSAIC_SCHEME, collection="sentinel-1-rtc", declaration=decl,
        properties_filter={"sat:orbit_state": "ascending"},
    )
    desc = create_datacube.params_key(
        bands, config.MOSAIC_SCHEME, collection="sentinel-1-rtc", declaration=decl,
        properties_filter={"sat:orbit_state": "descending"},
    )
    assert len({none_key, asc, desc}) == 3


def test_ac13_properties_filter_canonicalization_is_order_independent():
    """Key order and per-key value-list order must not change the digest -- one
    selection is one stable string (D9.3)."""
    decl = _collections.get("sentinel-1-rtc")
    bands = ["vv"]
    a = create_datacube.params_key(
        bands, config.MOSAIC_SCHEME, collection="sentinel-1-rtc", declaration=decl,
        properties_filter={"sat:orbit_state": "ascending", "z": ["b", "a"]},
    )
    b = create_datacube.params_key(
        bands, config.MOSAIC_SCHEME, collection="sentinel-1-rtc", declaration=decl,
        properties_filter={"z": ["a", "b"], "sat:orbit_state": "ascending"},
    )
    assert a == b


# --- AC14: max_cloudcover against sentinel-1-rtc raises; no S1 key plumbing ----------

def test_ac14_max_cloudcover_against_s1_raises_naming_collection():
    errs = api._check_cloudcover_capability("sentinel-1-rtc", 50.0)
    assert errs and "sentinel-1-rtc" in errs[0]


def test_ac14_download_preflight_raises_for_s1_max_cloudcover():
    with pytest.raises(api.PreflightError, match="sentinel-1-rtc"):
        api.download(
            roi=None, startdate=datetime.datetime(2018, 4, 1),
            enddate=datetime.datetime(2018, 9, 30), bands=["vv"],
            dst_folderpath="/tmp/unused-ac14", source="mpc", collection="sentinel-1-rtc",
            max_tiles=1, max_cloudcover=50.0,
        )


def test_ac14_no_fsd_code_reads_pc_sdk_subscription_key():
    """D10 (retracted): sentinel-1-rtc needs no key, and P2 builds no preflight for
    one. `planetary_computer` (the third-party package) reads the env var itself; fsd
    is free to MENTION it in comments/docstrings (it does, documenting that the
    package reads it) but no fsd code may itself read `os.environ`/`os.getenv` for it
    -- that would be a second source of truth for the same secret (D10's own text)."""
    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "fsd"
    read_patterns = (
        'os.environ["PC_SDK_SUBSCRIPTION_KEY"]', "os.environ['PC_SDK_SUBSCRIPTION_KEY']",
        'os.environ.get("PC_SDK_SUBSCRIPTION_KEY"', "os.environ.get('PC_SDK_SUBSCRIPTION_KEY'",
        'os.getenv("PC_SDK_SUBSCRIPTION_KEY"', "os.getenv('PC_SDK_SUBSCRIPTION_KEY'",
    )
    hits = [
        str(p) for p in root.rglob("*.py")
        if any(pat in p.read_text() for pat in read_patterns)
    ]
    assert hits == []
