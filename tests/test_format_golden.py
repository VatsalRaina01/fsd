"""Golden files for the two on-disk format versions (spec 102 D11, AC7).

`FSD_DECLARATION_VERSION` (collection declaration, in every catalog's Parquet footer) and
`BUNDLE_VERSION` (`bundle.json`) each have `tests/data/formats/<kind>.v<N>.json`.

* **Test A** writes a *fixed synthetic* example with today's code and compares it to the golden
  file for the current version. The example is pinned here, not read from S2 defaults, so a changed
  S2 default is not mistaken for a format change. Nothing in either manifest is volatile (no
  timestamps, digests, fsd version or paths), so no normalization is needed.
* **Test B** loads every supported version from its golden file. The bundle's list is
  `SUPPORTED_BUNDLE_VERSIONS`; the declaration has no such list (`from_json` accepts any version
  <= current), so its equivalent is `range(1, FSD_DECLARATION_VERSION + 1)`.

To change a format: bump the constant, add `<kind>.v<N+1>.json` (copy the failing test's "got"
output), keep the old files.

Provenance: `declaration.v1.json` was produced by running the v1 `to_json` from git history
(`2398c13^`); `bundle.v1.json` is `bundle.v2.json` minus `code`/`code_origin` with the version set to 1
(a v1 bundle has no `code` block; same recipe as `test_bundle_code.test_version_1_bundle_still_loads`).
"""

from __future__ import annotations

import json
import os
import sys

import pytest

from fsd.catalog import declaration as declaration_module
from fsd.catalog.declaration import CollectionDeclaration, MaskSpec
from fsd.model import bundle

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "data", "formats")


def _golden_path(kind: str, version: int) -> str:
    return os.path.join(GOLDEN_DIR, f"{kind}.v{version}.json")


def _read_golden(kind: str, version: int) -> dict:
    with open(_golden_path(kind, version)) as f:
        return json.load(f)


def _assert_matches_golden(kind: str, const: str, version: int, got: dict) -> None:
    path = _golden_path(kind, version)
    rel = os.path.relpath(path, os.path.dirname(GOLDEN_DIR))
    assert os.path.exists(path), (
        f"{const} is {version} but {rel} does not exist. Add it with this content:\n"
        f"{json.dumps(got, indent=2)}"
    )
    with open(path) as f:
        want = json.load(f)
    assert got == want, (
        f"The {kind} format written by today's code differs from {rel}. If the change is "
        f"intended, bump {const} to {version + 1} and add {kind}.v{version + 1}.json with:\n"
        f"{json.dumps(got, indent=2)}"
    )


# --- declaration -----------------------------------------------------------------------------

# Every field set explicitly, to values unlike any default.
_DECLARATION = CollectionDeclaration(
    reference_band="B08",
    native_grid=False,
    mask_spec=MaskSpec(band="SCL", mask_type="categorical_classes", classes=(3, 8), bits=(1, 2)),
    mask_keep=True,
    nodata=7,
    mosaic_method="median",
    scale=0.5,
    radiometry_bands=("B04", "B08"),
    band_aliases=(("red", "B04"), ("nir", "B08")),
    requires_subscription_key=True,
    supports_cloud_cover=False,
    mosaic_partition=("sat:orbit_state",),
    partition_policy="raise",
)


def test_declaration_format_matches_golden():
    version = declaration_module.FSD_DECLARATION_VERSION
    _assert_matches_golden(
        "declaration", "FSD_DECLARATION_VERSION", version, declaration_module.to_json(_DECLARATION)
    )


@pytest.mark.parametrize("version", range(1, declaration_module.FSD_DECLARATION_VERSION + 1))
def test_declaration_golden_files_still_load(version):
    decl = declaration_module.from_json(_read_golden("declaration", version))
    assert isinstance(decl, CollectionDeclaration)
    if version == declaration_module.FSD_DECLARATION_VERSION:
        assert decl == _DECLARATION


# --- bundle ----------------------------------------------------------------------------------

_ADAPTER_SRC = '''
from fsd.model.adapter import BaseModelAdapter


class GoldenAdapter(BaseModelAdapter):
    required_bands = ["B04", "B08"]
    n_timestamps = 3
    output_dtype = "uint8"
    output_nodata = 255
    output_band_names = ["klass"]

    def load(self):
        self.loaded = True

    def predict(self, X):
        return X
'''


@pytest.fixture
def golden_adapter(tmp_path, monkeypatch):
    src_dir = tmp_path / "srcroot"
    src_dir.mkdir()
    (src_dir / "golden_adapter.py").write_text(_ADAPTER_SRC)
    monkeypatch.syspath_prepend(str(src_dir))
    import golden_adapter as mod

    yield mod.GoldenAdapter
    sys.modules.pop("golden_adapter", None)


def test_bundle_format_matches_golden(tmp_path, golden_adapter):
    model = tmp_path / "model.bin"
    model.write_bytes(b"x")
    bdir = bundle.save(
        golden_adapter(), {"model": str(model)}, str(tmp_path / "b"),
        requirements=["scikit-learn>=1.3"], verbose=False,
    )
    _assert_matches_golden(
        "bundle", "BUNDLE_VERSION", bundle.BUNDLE_VERSION, bundle.read_spec(bdir)
    )


@pytest.mark.parametrize("version", bundle.SUPPORTED_BUNDLE_VERSIONS)
def test_bundle_golden_files_still_load(tmp_path, golden_adapter, version):
    manifest = _read_golden("bundle", version)
    bdir = tmp_path / "b"
    bdir.mkdir()
    (bdir / "bundle.json").write_text(json.dumps(manifest))
    (bdir / "model.bin").write_bytes(b"x")
    if manifest.get("code"):  # v2 bundled: ship the adapter source, as `save` would
        code_dir = bdir / manifest["code"]["root"]
        code_dir.mkdir()
        (code_dir / "golden_adapter.py").write_text(_ADAPTER_SRC)
        sys.modules.pop("golden_adapter", None)  # force a fresh import from code/, not the fixture's copy
        sys.path[:] = [p for p in sys.path if not p.endswith("srcroot")]
    adapter = bundle.load(str(bdir))
    assert type(adapter).__name__ == "GoldenAdapter"
    assert adapter.loaded
