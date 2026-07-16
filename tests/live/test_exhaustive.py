from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from conftest import (
    catalog_entries,
    latest_complete_release,
    release_dates,
    write_diagnostic,
)

if TYPE_CHECKING:
    from pathlib import Path

from cms_icd import ICD10KnowledgeBase


@pytest.mark.live_cms
@pytest.mark.live_exhaustive
def test_every_advertised_snapshot_and_material_parses(
    historical_cache: Path,
) -> None:
    entries = catalog_entries()
    latest_complete = latest_complete_release(entries)
    results: list[dict[str, object]] = []
    for year, dates in sorted(release_dates(entries).items()):
        for effective in dates:
            kb = ICD10KnowledgeBase.from_cms(
                fiscal_year=year,
                release_date=effective,
                cache_dir=historical_cache,
            )
            snapshot = {
                "fiscal_year": year,
                "release_date": effective,
                "materials": {},
            }
            for system, material in (
                ("cm", "tabular"),
                ("cm", "index"),
                ("cm", "guidelines"),
                ("pcs", "tabular"),
                ("pcs", "index"),
                ("pcs", "guidelines"),
            ):
                name = f"{system}/{material}"
                try:
                    value = getattr(getattr(kb, system), material)
                except Exception as exc:
                    snapshot["materials"][name] = type(exc).__name__
                else:
                    snapshot["materials"][name] = len(value)
            results.append(snapshot)
    write_diagnostic("exhaustive-results.json", results)

    supported = [
        item
        for item in results
        if int(item["fiscal_year"]) <= latest_complete.fiscal_year
    ]
    failures = [
        item
        for item in supported
        if not all(isinstance(value, int) for value in dict(item["materials"]).values())
    ]
    assert not failures, failures
