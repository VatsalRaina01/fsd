"""Shared by the MPC and CDSE sources: where a granule lives, and the catalog columns that
describe it.

Spec: specs/59-imagery-archive-layout.md D2/D3/D8. Both sources write the same layout,
`{root}/{collection}/YYYY/MM/DD/{canonical granule name}/`, so the same granule from either
source lands in the same folder (and the same catalog row).
"""

from __future__ import annotations

import os

from fsd.collections.naming import GranuleInfo, granule_info

__all__ = ["item_granule", "granule_folderpath", "granule_columns", "collection_root"]


def item_granule(collection: str, item) -> GranuleInfo:
    """`granule_info` for a (duck-typed) STAC item."""
    return granule_info(collection, item.id, item.properties, item.datetime)


def collection_root(root_folderpath: str, collection: str) -> str:
    """`{root}/{collection}` -- the directory one catalog.parquet lives in (D2/D5)."""
    return os.path.join(root_folderpath, collection)


def granule_folderpath(root_folderpath: str, collection: str, info: GranuleInfo) -> str:
    d = info.acquisition_date
    return os.path.join(
        collection_root(root_folderpath, collection),
        f"{d.year:04d}", f"{d.month:02d}", f"{d.day:02d}", info.canonical_name,
    )


def granule_columns(info: GranuleInfo, *, source: str) -> dict:
    """The D8 catalog columns for one discovered granule."""
    return {
        "id": info.canonical_name,
        "acquisition_key": info.acquisition_key,
        "processing_version": info.processing_version,
        "processing_datetime": info.processing_datetime,
        "source": source,
    }
