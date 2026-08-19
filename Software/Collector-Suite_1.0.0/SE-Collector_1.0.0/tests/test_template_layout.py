from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
STYLE = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
FO = "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"


def page_properties(filename: str) -> ET.Element:
    with zipfile.ZipFile(ROOT / "templates" / filename) as package:
        root = ET.fromstring(package.read("styles.xml"))
    properties = root.find(f".//{{{STYLE}}}page-layout-properties")
    assert properties is not None
    return properties


def test_portrait_templates_have_18_mm_left_binding_margin():
    for filename in ("IB_Selbstbewertung1.odt",):
        properties = page_properties(filename)
        assert properties.get(f"{{{FO}}}margin-left") == "0.7087in"
