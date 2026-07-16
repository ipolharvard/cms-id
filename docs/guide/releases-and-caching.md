# Releases and caching

## Fiscal years and effective dates

CMS fiscal years begin on October 1. `for_date()` calculates the fiscal year and
selects the latest advertised revision effective on or before the service date.

```pycon
>>> from datetime import date
>>> from cms_icd.sources import fiscal_year_for
>>> fiscal_year_for(date(2025, 9, 30))
2025
>>> fiscal_year_for(date(2025, 10, 1))
2026

```

`from_cms()` instead requests an exact fiscal year and release date. If
`release_date` is omitted, October 1 before the fiscal year is used.

## Strict selection and fallback

Release selection is strict by default. If CMS does not advertise the requested
revision, accessing its first material raises
[`ReleaseUnavailableError`](../reference/exceptions.md).

An application may explicitly permit the latest available material in the same
fiscal year:

```python
icd = ICD10KnowledgeBase.from_cms(
    fiscal_year=2026,
    release_date=date(2026, 4, 1),
    fallback="latest_for_fy",
)
```

!!! warning

```
A fallback can change cohort labels or coding behavior. Record the resolved
release and use fallback only when that scientific or operational tradeoff
is acceptable.
```

## Cache behavior

By default, files are cached under:

```text
${XDG_CACHE_HOME}/cms-icd
```

or `~/.cache/cms-icd` when `XDG_CACHE_HOME` is not set. Set `cache_dir` to keep
artifacts with a project or shared application cache:

```python
icd = ICD10KnowledgeBase.for_date(
    date(2026, 5, 1),
    cache_dir="data/cms_icd",
)
```

Downloaded artifacts are keyed by URL, checksummed with SHA-256, and reused when
one CMS bundle supplies multiple lazy stores. Extraction uses a directory lock
and an atomic staging rename so concurrent readers do not observe partial
materials.

Each extracted material directory contains `manifest.json` with the source URL,
release metadata, checksum, and extracted filenames.
