"""Material discovery, download, and local-directory providers."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from fnmatch import fnmatch
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse
from zipfile import BadZipFile, ZipFile

import requests
from bs4 import BeautifulSoup

from .exceptions import (
    AmbiguousReleaseError,
    DownloadError,
    MaterialUnavailableError,
    ReleaseUnavailableError,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .models import Release

logger = logging.getLogger(__name__)

CMS_CATALOG_URL = "https://www.cms.gov/medicare/coding-billing/icd-10-codes"
CMS_ARCHIVE_URL = "https://www.cms.gov/medicare/coding-billing/icd-10-codes/icd-10-cm-icd-10-pcs-gem-archive"

_PATTERNS: dict[tuple[str, str], tuple[str, ...]] = {
    ("cm", "tabular"): ("icd10cm_tabular*.xml",),
    ("cm", "index"): (
        "*icd10cm_index*.xml",
        "*icd10cm_neoplasm*.xml",
        "*icd10cm_eindex*.xml",
        "*icd10cm_drug*.xml",
    ),
    ("cm", "guidelines"): ("*cm*guidelines*.pdf",),
    ("pcs", "tabular"): ("*icd10pcs_tables*.xml",),
    ("pcs", "index"): ("*icd10pcs_index*.xml",),
    ("pcs", "guidelines"): ("*pcs*guidelines*.pdf",),
}


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """One downloadable material advertised by CMS."""

    system: str
    material: str
    fiscal_year: int
    release_date: date
    label: str
    url: str
    page_url: str


def fiscal_year_for(value: date) -> int:
    """Return the CMS fiscal year containing a date.

    Examples:
        >>> fiscal_year_for(date(2025, 9, 30))
        2025
        >>> fiscal_year_for(date(2025, 10, 1))
        2026
    """
    return value.year + 1 if (value.month, value.day) >= (10, 1) else value.year


def _infer_system(label: str, href: str) -> str | None:
    text = f"{label} {href}".lower()
    if "pcs" in text:
        return "pcs"
    if "cm" in text or "code tables, tabular and index" in text:
        return "cm"
    return None


def _infer_material(label: str, href: str) -> str | None:
    text = f"{label} {href}".lower()
    if "guideline" in text:
        return "guidelines"
    if "table" in text and "index" in text:
        return "bundle"
    return None


def _infer_year(label: str, href: str) -> int | None:
    years = re.findall(r"20\d{2}", f"{label} {href}")
    return int(years[0]) if years else None


def _infer_release_date(label: str, fiscal_year: int) -> date:
    lowered = label.lower()
    if "april" in lowered or re.search(r"\b04[-/ ]0?1\b", lowered):
        return date(fiscal_year, 4, 1)
    if "january" in lowered:
        return date(fiscal_year, 1, 1)
    return date(fiscal_year - 1, 10, 1)


def parse_catalog(
    html: str, page_url: str = CMS_CATALOG_URL
) -> tuple[CatalogEntry, ...]:
    """Parse supported ICD artifacts from a CMS catalog page.

    The parser deliberately ignores unrelated code-description, conversion, and addendum
    files.
    """
    soup = BeautifulSoup(html, "html.parser")
    entries: list[CatalogEntry] = []
    for anchor in soup.find_all("a", href=True):
        label = " ".join(anchor.get_text(" ", strip=True).split())
        href = str(anchor["href"])
        system = _infer_system(label, href)
        material = _infer_material(label, href)
        fiscal_year = _infer_year(label, href)
        if system is None or material is None or fiscal_year is None:
            continue
        url = urljoin(page_url, href)
        release_date = _infer_release_date(label, fiscal_year)
        materials = ("tabular", "index") if material == "bundle" else (material,)
        entries.extend(
            CatalogEntry(
                system=system,
                material=item,
                fiscal_year=fiscal_year,
                release_date=release_date,
                label=label,
                url=url,
                page_url=page_url,
            )
            for item in materials
        )
    return tuple(entries)


class MaterialProvider(ABC):
    """Abstract provider of local paths for individual ICD materials."""

    release: Release

    @abstractmethod
    def paths(self, system: str, material: str) -> tuple[Path, ...]:
        """Return local files needed for a system/material pair."""


class DirectoryProvider(MaterialProvider):
    """Discover CMS-format files in an existing directory."""

    def __init__(self, directory: str | Path, release: Release) -> None:
        self.directory = Path(directory)
        if not self.directory.is_dir():
            raise FileNotFoundError(
                f"ICD material directory does not exist: {self.directory}"
            )
        self.release = release

    def paths(self, system: str, material: str) -> tuple[Path, ...]:
        patterns = _PATTERNS[(system, material)]
        matches = tuple(
            sorted(
                (
                    path
                    for path in self.directory.iterdir()
                    if path.is_file()
                    and any(
                        fnmatch(path.name.lower(), pattern.lower())
                        for pattern in patterns
                    )
                ),
                key=lambda path: path.name,
            )
        )
        if not matches:
            raise MaterialUnavailableError(
                f"No {system.upper()} {material} material found in {self.directory}"
            )
        if material != "index" and len(matches) != 1:
            raise AmbiguousReleaseError(
                f"Expected one {system.upper()} {material} file in {self.directory}, "
                f"found {[path.name for path in matches]}"
            )
        return matches


def default_cache_dir() -> Path:
    """Return the platform-appropriate default cache directory."""
    base = os.environ.get("XDG_CACHE_HOME")
    return Path(base) / "cms-icd" if base else Path.home() / ".cache" / "cms-icd"


@contextmanager
def _directory_lock(path: Path, timeout: float = 30.0) -> Iterable[None]:
    lock = path.with_suffix(path.suffix + ".lock")
    deadline = time.monotonic() + timeout
    while True:
        try:
            lock.mkdir(parents=True)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise DownloadError(
                    f"Timed out waiting for cache lock: {lock}"
                ) from None
            time.sleep(0.05)
    try:
        yield
    finally:
        lock.rmdir()


class CMSProvider(MaterialProvider):
    """Lazily resolve and cache materials from official CMS catalog pages."""

    def __init__(
        self,
        release: Release,
        *,
        service_date: date | None = None,
        cache_dir: str | Path | None = None,
        fallback: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.release = release
        self.service_date = service_date
        self.cache_dir = (
            Path(cache_dir) if cache_dir is not None else default_cache_dir()
        )
        self.fallback = fallback
        self._session = session or requests.Session()
        self._catalog: tuple[CatalogEntry, ...] | None = None

    def _load_catalog(self) -> tuple[CatalogEntry, ...]:
        if self._catalog is None:
            entries: list[CatalogEntry] = []
            for url in (CMS_CATALOG_URL, CMS_ARCHIVE_URL):
                try:
                    response = self._session.get(url, timeout=30)
                    response.raise_for_status()
                except requests.RequestException as exc:
                    raise DownloadError(
                        f"Unable to read CMS ICD catalog {url}: {exc}"
                    ) from exc
                entries.extend(parse_catalog(response.text, url))
            self._catalog = tuple(dict.fromkeys(entries))
        return self._catalog

    def _select(self, system: str, material: str) -> CatalogEntry:
        candidates = [
            entry
            for entry in self._load_catalog()
            if entry.system == system
            and entry.material == material
            and entry.fiscal_year == self.release.fiscal_year
        ]
        if self.service_date is not None:
            candidates = [
                item for item in candidates if item.release_date <= self.service_date
            ]
            if candidates:
                selected_date = max(item.release_date for item in candidates)
                candidates = [
                    item for item in candidates if item.release_date == selected_date
                ]
        else:
            candidates = [
                item
                for item in candidates
                if item.release_date == self.release.release_date
            ]

        unique = {(item.url, item.release_date): item for item in candidates}
        candidates = list(unique.values())
        if not candidates and self.fallback == "latest_for_fy":
            all_for_year = [
                entry
                for entry in self._load_catalog()
                if entry.system == system
                and entry.material == material
                and entry.fiscal_year == self.release.fiscal_year
            ]
            if all_for_year:
                selected_date = max(item.release_date for item in all_for_year)
                candidates = [
                    item for item in all_for_year if item.release_date == selected_date
                ]
        if not candidates:
            raise ReleaseUnavailableError(
                f"No CMS {system.upper()} {material} material is available for "
                f"FY {self.release.fiscal_year}, release {self.release.release_date}"
            )
        if len(candidates) != 1:
            raise AmbiguousReleaseError(
                f"Multiple CMS {system.upper()} {material} artifacts match: "
                f"{[item.label for item in candidates]}"
            )
        return candidates[0]

    def _artifact_dir(self, entry: CatalogEntry) -> Path:
        return (
            self.cache_dir
            / f"fy{entry.fiscal_year}"
            / entry.release_date.isoformat()
            / entry.system
            / entry.material
        )

    def paths(self, system: str, material: str) -> tuple[Path, ...]:
        entry = self._select(system, material)
        destination = self._artifact_dir(entry)
        manifest_path = destination / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = tuple(destination / name for name in manifest["files"])
            if files and all(path.is_file() for path in files):
                return files

        destination.parent.mkdir(parents=True, exist_ok=True)
        with _directory_lock(destination):
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                files = tuple(destination / name for name in manifest["files"])
                if files and all(path.is_file() for path in files):
                    return files
            staging = destination.with_name(destination.name + ".tmp")
            if staging.exists():
                shutil.rmtree(staging)
            staging.mkdir()
            try:
                files, digest = self._download_and_extract(
                    entry, staging, system, material
                )
                manifest = {
                    "fiscal_year": entry.fiscal_year,
                    "release_date": entry.release_date.isoformat(),
                    "system": system,
                    "material": material,
                    "label": entry.label,
                    "url": entry.url,
                    "page_url": entry.page_url,
                    "sha256": digest,
                    "files": [path.name for path in files],
                }
                (staging / "manifest.json").write_text(
                    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                if destination.exists():
                    shutil.rmtree(destination)
                staging.replace(destination)
            except Exception:
                shutil.rmtree(staging, ignore_errors=True)
                raise
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return tuple(destination / name for name in manifest["files"])

    def _download_and_extract(
        self,
        entry: CatalogEntry,
        staging: Path,
        system: str,
        material: str,
    ) -> tuple[tuple[Path, ...], str]:
        artifact, digest = self._cached_artifact(entry)

        patterns = _PATTERNS[(system, material)]
        extracted: list[Path] = []
        try:
            if artifact.suffix.lower() == ".pdf":
                target = staging / Path(entry.url).name
                shutil.copy2(artifact, target)
                extracted.append(target)
            else:
                with ZipFile(artifact) as archive:
                    for member in archive.infolist():
                        filename = Path(member.filename).name
                        if not filename or not any(
                            fnmatch(filename.lower(), pattern.lower())
                            for pattern in patterns
                        ):
                            continue
                        target = staging / filename
                        target.write_bytes(archive.read(member))
                        extracted.append(target)
        except BadZipFile as exc:
            raise DownloadError(
                f"CMS artifact is not a valid ZIP file: {entry.url}"
            ) from exc
        if not extracted:
            expected = f"{system.upper()} {material}"
            raise MaterialUnavailableError(
                f"{entry.label!r} did not contain expected {expected} files"
            )
        return tuple(sorted(extracted, key=lambda path: path.name)), digest

    def _cached_artifact(self, entry: CatalogEntry) -> tuple[Path, str]:
        """Download a CMS URL once, even when it supplies several lazy stores."""
        url_key = hashlib.sha256(entry.url.encode()).hexdigest()
        suffix = Path(urlparse(entry.url).path).suffix or ".bin"
        artifact_dir = self.cache_dir / "_artifacts" / url_key
        artifact = artifact_dir / f"artifact{suffix}"
        checksum = artifact_dir / "sha256"
        if artifact.is_file() and checksum.is_file():
            return artifact, checksum.read_text(encoding="ascii").strip()

        artifact_dir.parent.mkdir(parents=True, exist_ok=True)
        with _directory_lock(artifact_dir):
            if artifact.is_file() and checksum.is_file():
                return artifact, checksum.read_text(encoding="ascii").strip()
            try:
                response = self._session.get(entry.url, timeout=60, stream=True)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise DownloadError(f"Unable to download {entry.url}: {exc}") from exc

            digest = hashlib.sha256()
            with NamedTemporaryFile(
                dir=artifact_dir.parent,
                suffix=suffix,
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
                        digest.update(chunk)
            staging = artifact_dir.with_name(artifact_dir.name + ".tmp")
            shutil.rmtree(staging, ignore_errors=True)
            staging.mkdir()
            temporary.replace(staging / artifact.name)
            (staging / checksum.name).write_text(
                digest.hexdigest() + "\n", encoding="ascii"
            )
            if artifact_dir.exists():
                shutil.rmtree(artifact_dir)
            staging.replace(artifact_dir)
        return artifact, checksum.read_text(encoding="ascii").strip()
