from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cms_icd.exceptions import ParseError
from cms_icd.parsers import parse_cm_tabular, parse_index, parse_pcs_tabular

if TYPE_CHECKING:
    from pathlib import Path

CM_XML = """\
<ICD10CM.tabular>
  <chapter>
    <name>9</name>
    <desc>Diseases of the circulatory system</desc>
    <notes><note>chapter instruction</note></notes>
    <section id="I10-I16">
      <desc>Hypertensive diseases</desc>
      <diag>
        <name>I10</name>
        <desc>Essential hypertension</desc>
        <includes><note>high blood pressure</note></includes>
      </diag>
    </section>
  </chapter>
</ICD10CM.tabular>
"""


PCS_XML = """\
<ICD10PCS>
  <pcsTable>
    <axis pos="1"><title>Section</title><label code="0">Medical</label></axis>
    <axis pos="2"><title>Body System</title><label code="A">Nervous</label></axis>
    <axis pos="3"><title>Operation</title><label code="B">Excision</label></axis>
    <pcsRow codes="2">
      <axis pos="4" values="2">
        <title>Body Part</title>
        <label code="0">Brain</label>
        <label code="1">Meninges</label>
      </axis>
    </pcsRow>
  </pcsTable>
</ICD10PCS>
"""


INDEX_XML = """\
<ICD10CM.index>
  <letter>
    <title>H</title>
    <mainTerm>
      <title>Hypertension (arterial)</title>
      <code>I10</code>
      <term><title>secondary</title><code>I15.9</code></term>
    </mainTerm>
  </letter>
</ICD10CM.index>
"""


def test_cm_parser_builds_direct_hierarchy_and_notes(tmp_path: Path) -> None:
    path = tmp_path / "icd10cm_tabular.xml"
    path.write_text(CM_XML)

    store = parse_cm_tabular(path)

    assert [node.id for node in store.children("cm")] == ["cm_9"]
    assert [node.id for node in store.children("cm_9")] == ["cm_9_I10-I16"]
    assert [node.name for node in store.leaves("cm")] == ["I10"]
    assert store["cm_9"].notes == ("chapter instruction",)
    assert store.by_code("I10").includes == ("high blood pressure",)


def test_pcs_parser_validates_and_generates_combinations(tmp_path: Path) -> None:
    path = tmp_path / "icd10pcs_tables.xml"
    path.write_text(PCS_XML)
    store = parse_pcs_tabular(path)
    assert [node.name for node in store.leaves("pcs")] == ["0AB0", "0AB1"]

    bad_path = tmp_path / "bad_icd10pcs_tables.xml"
    bad_path.write_text(PCS_XML.replace('codes="2"', 'codes="3"'))
    with pytest.raises(ParseError, match="declares 3 codes but defines 2 combinations"):
        parse_pcs_tabular(bad_path)


def test_index_parser_preserves_direct_children_and_modifiers(tmp_path: Path) -> None:
    path = tmp_path / "icd10cm_index.xml"
    path.write_text(INDEX_XML)
    store = parse_index((path,), system="cm")

    main = store.main_terms()[0]
    child = store.children(main.id)[0]
    assert main.title == "Hypertension"
    assert main.optional_modifiers == ("arterial",)
    assert child.path == "Hypertension, secondary"
