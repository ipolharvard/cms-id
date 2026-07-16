from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

import pytest

from cms_icd import ICD10KnowledgeBase

if TYPE_CHECKING:
    from pathlib import Path

EXPECTED_SHA256 = {
    ("fy2017", "2016-10-01", "cm", "tabular"): (
        "245a4e286ee43c41ca5e47a359cc9777b6f7d809a3da2c760b8ae39a0d1ac3cd"
    ),
    ("fy2017", "2016-10-01", "pcs", "tabular"): (
        "622ba1504ec29b74ea31187a49742573fed32cc3647cd0960a0cdfffba50d306"
    ),
    ("fy2022", "2021-10-01", "cm", "tabular"): (
        "5496e64d9c7b60427e9d0cff35adf1d5ec7ebfcf47df84d4a6ff8af8e3a9b4ab"
    ),
    ("fy2025", "2024-10-01", "pcs", "tabular"): (
        "f4b6d12ef621f8cf6a485c347993d3bfbd0914e7fa2280b7f6254f2da308f01f"
    ),
    ("fy2025", "2025-04-01", "pcs", "tabular"): (
        "515198d2fc5caff19d6e29b68a276174157c9e53a486c1a0bdf239f1ecb1f2cd"
    ),
}


def _assert_fingerprint(
    cache: Path,
    key: tuple[str, str, str, str],
) -> None:
    manifest = json.loads((cache.joinpath(*key) / "manifest.json").read_text())
    assert manifest["sha256"] == EXPECTED_SHA256[key], (
        f"CMS changed historical artifact {manifest['url']}; review and update "
        "the expected fingerprint deliberately"
    )


@pytest.mark.live_cms
@pytest.mark.live_historical
def test_archived_fy2017_cm_and_pcs_tabular_materials_parse(
    historical_cache: Path,
) -> None:
    kb = ICD10KnowledgeBase.from_cms(
        fiscal_year=2017,
        release_date=date(2016, 10, 1),
        cache_dir=historical_cache,
    )

    assert kb.cm["I10"].assignable
    assert len(kb.pcs.tabular) > 1_000
    _assert_fingerprint(
        historical_cache,
        ("fy2017", "2016-10-01", "cm", "tabular"),
    )
    _assert_fingerprint(
        historical_cache,
        ("fy2017", "2016-10-01", "pcs", "tabular"),
    )


@pytest.mark.live_cms
@pytest.mark.live_historical
def test_fy2019_direct_and_zipped_guidelines_parse(
    historical_cache: Path,
) -> None:
    kb = ICD10KnowledgeBase.from_cms(
        fiscal_year=2019,
        release_date=date(2018, 10, 1),
        cache_dir=historical_cache,
    )

    assert len(kb.cm.guidelines) > 10
    assert len(kb.pcs.guidelines["document"].content) > 10_000


@pytest.mark.live_cms
@pytest.mark.live_historical
def test_fy2022_updated_names_and_four_part_cm_index_parse(
    historical_cache: Path,
) -> None:
    kb = ICD10KnowledgeBase.from_cms(
        fiscal_year=2022,
        release_date=date(2021, 10, 1),
        cache_dir=historical_cache,
    )

    assert kb.cm["I10"].assignable
    assert len(kb.cm.index) > 1_000
    assert {term.source for term in kb.cm.index.values()} >= {
        "",
        "Drug",
        "External Cause",
        "Neoplasm",
    }
    assert len(kb.pcs.tabular) > 1_000
    _assert_fingerprint(
        historical_cache,
        ("fy2022", "2021-10-01", "cm", "tabular"),
    )


@pytest.mark.live_cms
@pytest.mark.live_historical
def test_fy2025_initial_and_april_revisions_parse_distinct_pcs_codes(
    historical_cache: Path,
) -> None:
    initial = ICD10KnowledgeBase.from_cms(
        fiscal_year=2025,
        release_date=date(2024, 10, 1),
        cache_dir=historical_cache,
    )
    april = ICD10KnowledgeBase.from_cms(
        fiscal_year=2025,
        release_date=date(2025, 4, 1),
        cache_dir=historical_cache,
    )
    assert "0B118D6" not in initial.pcs
    assert april.pcs["0B118D6"].assignable

    manifests = []
    for effective in ("2024-10-01", "2025-04-01"):
        path = (
            historical_cache
            / "fy2025"
            / effective
            / "pcs"
            / "tabular"
            / "manifest.json"
        )
        manifests.append(json.loads(path.read_text()))
    assert manifests[0]["sha256"] != manifests[1]["sha256"]
    assert "april" not in manifests[0]["url"].lower()
    assert "april" in manifests[1]["url"].lower()
    _assert_fingerprint(
        historical_cache,
        ("fy2025", "2024-10-01", "pcs", "tabular"),
    )
    _assert_fingerprint(
        historical_cache,
        ("fy2025", "2025-04-01", "pcs", "tabular"),
    )


@pytest.mark.live_cms
@pytest.mark.live_historical
def test_service_date_switches_to_april_revision(
    historical_cache: Path,
) -> None:
    before = ICD10KnowledgeBase.for_date(
        date(2025, 3, 31),
        cache_dir=historical_cache,
    )
    after = ICD10KnowledgeBase.for_date(
        date(2025, 4, 1),
        cache_dir=historical_cache,
    )

    assert "0B118D6" not in before.pcs
    assert "0B118D6" in after.pcs


@pytest.mark.live_cms
@pytest.mark.live_historical
def test_april_snapshot_inherits_and_replaces_materials_per_system(
    historical_cache: Path,
) -> None:
    april = ICD10KnowledgeBase.from_cms(
        fiscal_year=2026,
        release_date=date(2026, 4, 1),
        cache_dir=historical_cache,
    )

    assert len(april.cm.guidelines) > 10
    assert len(april.pcs.guidelines["document"].content) > 10_000
    cm_manifest = json.loads(
        (
            historical_cache
            / "fy2026"
            / "2025-10-01"
            / "cm"
            / "guidelines"
            / "manifest.json"
        ).read_text()
    )
    pcs_manifest = json.loads(
        (
            historical_cache
            / "fy2026"
            / "2026-04-01"
            / "pcs"
            / "guidelines"
            / "manifest.json"
        ).read_text()
    )
    assert cm_manifest["release_date"] == "2025-10-01"
    assert pcs_manifest["release_date"] == "2026-04-01"
