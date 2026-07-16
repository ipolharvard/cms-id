from __future__ import annotations

from datetime import date

import pytest

from cms_icd import ICD10KnowledgeBase


@pytest.mark.live_cms
def test_fy2022_cm_and_pcs_materials_are_available(tmp_path) -> None:
    kb = ICD10KnowledgeBase.from_cms(
        fiscal_year=2022,
        release_date=date(2021, 10, 1),
        cache_dir=tmp_path,
        fallback="latest_for_fy",
    )
    assert kb.cm["I10"].assignable
    assert len(kb.cm.index) > 1_000
    assert len(kb.pcs.tabular) > 1_000


@pytest.mark.live_cms
def test_fy2026_initial_and_april_revisions_use_distinct_cache_entries(
    tmp_path,
) -> None:
    initial = ICD10KnowledgeBase.from_cms(
        fiscal_year=2026,
        release_date=date(2025, 10, 1),
        cache_dir=tmp_path,
    )
    april = ICD10KnowledgeBase.from_cms(
        fiscal_year=2026,
        release_date=date(2026, 4, 1),
        cache_dir=tmp_path,
    )
    assert initial.cm["I10"].assignable
    assert april.cm["I10"].assignable
    assert initial.release != april.release
