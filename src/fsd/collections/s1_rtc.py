"""The `sentinel-1-rtc` collection declaration -- spec 58 P2.

Spec: specs/58-collection-agnostic-verbs.md D17. ADR 0028 (why RTC, not GRD).

Values verified against the live MPC `sentinel-1-rtc` collection + item JSONs,
2026-09-07 (spec 58 D17's table + "Window A coverage is confirmed, anonymously").
"""

from __future__ import annotations

from fsd.catalog.declaration import CollectionDeclaration

COLLECTION_ID = "sentinel-1-rtc"

DECLARATION = CollectionDeclaration(
    # VV and VH are both 10 m -- nothing to resample (D11).
    reference_band=None,
    # Scene-based, like S2, not one native global grid.
    native_grid=False,
    # SAR has no cloud/QA band; mask + drop steps are skipped (#35).
    mask_spec=None,
    mask_keep=False,
    # Declared in every RTC `raster:bands`.
    nodata=-32768,
    mosaic_method="median",
    # Gamma naught is already calibrated linear power, not scaled DN.
    scale=1.0,
    # Empty, not None -- None means "every band carries radiometry"; no S1 band does.
    radiometry_bands=(),
    # EO common_names are optical; SAR polarizations have no canonical alias (D8 N/A).
    band_aliases=(),
    # D10, retracted: MPC dropped the RTC key requirement in 2024.
    requires_subscription_key=False,
    # Gated by D6; AC14 -- SAR has no cloud-cover concept at all.
    supports_cloud_cover=False,
    # D9: ascending/descending backscatter must never be medianed together.
    mosaic_partition=("sat:orbit_state",),
    partition_policy="raise",
)
