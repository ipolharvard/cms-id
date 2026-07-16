# CMS ICD

`cms-icd` provides version-aware, structured access to official CMS ICD-10-CM
and ICD-10-PCS materials. Downloads and parsing are lazy: using diagnosis codes
does not download PCS files, and reading a tabular list does not parse indexes
or guideline PDFs.

Python 3.12 or newer is required. The package is tested on Python 3.12–3.14.

## Installation

Install an internal Git checkout with `uv`:

```bash
uv pip install -e /path/to/cms-icd
```

## Choosing a release

Select the release applicable to a service date:

```python
from datetime import date

from cms_icd import ICD10KnowledgeBase

icd = ICD10KnowledgeBase.for_date(
    date(2026, 5, 1),
    cache_dir="data/cms_icd",
)
cm = icd.cm
code = cm["I10"]  # downloads and parses CM tabular material on first use
```

For reproducible research, select an exact effective revision:

```python
icd = ICD10KnowledgeBase.from_cms(
    fiscal_year=2026,
    release_date=date(2026, 4, 1),
    cache_dir="data/cms_icd",
)
```

CMS does not always retain every historical intra-year revision. Selection is
strict by default. Pass `fallback="latest_for_fy"` only when using the closest
available fiscal-year material is scientifically acceptable.

## Offline and custom stores

An existing directory is not inspected until a material is requested:

```pycon
>>> from datetime import date
>>> from pathlib import Path
>>> from tempfile import TemporaryDirectory
>>> from cms_icd import ICD10KnowledgeBase
>>> with TemporaryDirectory() as directory:
...     kb = ICD10KnowledgeBase.from_directory(
...         directory,
...         fiscal_year=2026,
...         release_date=date(2025, 10, 1),
...     )
...     repr(kb)
'ICD10KnowledgeBase(release=Release(fiscal_year=2026, release_date=datetime.date(2025, 10, 1)), loaded=[])'

```

Small custom or synthetic stores can be supplied directly:

```pycon
>>> from cms_icd import Code, ICD10CMKnowledgeBase
>>> from cms_icd.models import Node
>>> from cms_icd.stores import TabularStore
>>> root = Node("cm", "cm", children_ids=("I10",))
>>> code = Code("I10", "I10", "Essential hypertension", parent_id="cm")
>>> tabular = TabularStore({"cm": root, "I10": code}, {"I10": "I10"}, ("cm",))
>>> cm = ICD10CMKnowledgeBase.from_stores(tabular=tabular)
>>> cm["I10"].description
'Essential hypertension'
>>> cm.get_leaves("cm")
['I10']

```

## Development

```bash
make install-dev
make test
```

Normal tests are offline. `make test-live` accesses CMS and must be run only
when live integration testing is explicitly intended.

The package depends on PyMuPDF for guideline extraction. Confirm PyMuPDF's
licensing is suitable for the intended distribution before publishing this
library outside the organization.
