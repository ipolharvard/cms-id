from __future__ import annotations

import io
import json
from datetime import date
from typing import TYPE_CHECKING
from zipfile import ZipFile

from cms_icd.models import Release
from cms_icd.sources import CMSProvider, parse_catalog

if TYPE_CHECKING:
    from pathlib import Path

CATALOG_HTML = """
<html><body>
  <a href="/files/zip/2026-code-tables-tabular-and-index.zip">
    2026 Code Tables, Tabular and Index (ZIP)
  </a>
  <a href="/files/zip/april-1-2026-code-tables-tabular-index.zip">
    April 1, 2026 Code Tables, Tabular and Index (ZIP)
  </a>
  <a href="/files/zip/2026-pcs-tables-index.zip">
    2026 ICD-10-PCS Code Tables and Index (ZIP)
  </a>
  <a href="/files/document/fy-2026-icd-10-cm-coding-guidelines.pdf">
    FY 2026 ICD-10-CM Coding Guidelines (PDF)
  </a>
  <a href="/files/zip/2026-conversion-table.zip">2026 Conversion Table</a>
</body></html>
"""


def test_parse_catalog_distinguishes_initial_and_april_revisions() -> None:
    entries = parse_catalog(CATALOG_HTML)
    cm_tabular = [
        entry
        for entry in entries
        if entry.system == "cm" and entry.material == "tabular"
    ]
    assert [entry.release_date for entry in cm_tabular] == [
        date(2025, 10, 1),
        date(2026, 4, 1),
    ]
    assert {entry.material for entry in entries} == {"tabular", "index", "guidelines"}


class FakeResponse:
    def __init__(self, *, text: str = "", content: bytes = b"") -> None:
        self.text = text
        self.content = content

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int):
        del chunk_size
        yield self.content


class FakeSession:
    def __init__(self, archive: bytes) -> None:
        self.archive = archive
        self.downloads = 0

    def get(self, url: str, **kwargs):
        del kwargs
        if "coding-billing/icd-10-codes" in url:
            return FakeResponse(text=CATALOG_HTML)
        self.downloads += 1
        return FakeResponse(content=self.archive)


def _cm_archive() -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("icd10cm_tabular_2026.xml", "<ICD10CM.tabular/>")
        archive.writestr("icd10cm_index_2026.xml", "<ICD10CM.index/>")
        archive.writestr("icd10cm_neoplasm_2026.xml", "<ICD10CM.index/>")
        archive.writestr("icd10cm_eindex_2026.xml", "<ICD10CM.index/>")
        archive.writestr("icd10cm_drug_2026.xml", "<ICD10CM.index/>")
    return buffer.getvalue()


def test_one_archive_download_supplies_tabular_and_index(tmp_path: Path) -> None:
    session = FakeSession(_cm_archive())
    provider = CMSProvider(
        Release(2026, date(2025, 10, 1)),
        cache_dir=tmp_path,
        session=session,  # type: ignore[arg-type]
    )

    tabular = provider.paths("cm", "tabular")
    index = provider.paths("cm", "index")

    assert session.downloads == 1
    assert [path.name for path in tabular] == ["icd10cm_tabular_2026.xml"]
    assert len(index) == 4
    manifest = json.loads(
        (
            tmp_path / "fy2026" / "2025-10-01" / "cm" / "tabular" / "manifest.json"
        ).read_text()
    )
    assert manifest["release_date"] == "2025-10-01"
    assert len(manifest["sha256"]) == 64
