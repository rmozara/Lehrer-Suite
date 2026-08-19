import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "IB_QR-Karten.odt"
FO = "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
STYLE = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"


class TemplateTests(unittest.TestCase):
    def test_template_is_a5_landscape_with_18_mm_binding_margin(self):
        with zipfile.ZipFile(TEMPLATE) as package:
            root = ET.fromstring(package.read("styles.xml"))
        properties = root.find(f".//{{{STYLE}}}page-layout-properties")
        self.assertIsNotNone(properties)
        self.assertEqual(properties.get(f"{{{FO}}}page-width"), "8.2677in")
        self.assertEqual(properties.get(f"{{{FO}}}page-height"), "5.8465in")
        self.assertEqual(properties.get(f"{{{STYLE}}}print-orientation"), "landscape")
        self.assertAlmostEqual(
            float(properties.get(f"{{{FO}}}margin-left").removesuffix("in")),
            18 / 25.4,
            delta=0.01,
        )

    def test_body_starts_one_blank_line_below_unchanged_header(self):
        with zipfile.ZipFile(TEMPLATE) as package:
            root = ET.fromstring(package.read("content.xml"))
        body = root.find(f".//{{{OFFICE}}}text")
        self.assertIsNotNone(body)
        children = list(body)
        table_index = next(
            index
            for index, child in enumerate(children)
            if child.tag == f"{{{TABLE}}}table"
            and child.get(f"{{{TABLE}}}name") == "Table2"
        )
        self.assertGreater(table_index, 0)
        self.assertNotEqual(children[table_index - 1].tag, f"{{{TEXT}}}p")
        self.assertEqual(children[table_index + 1].tag, f"{{{TEXT}}}p")
        self.assertEqual("".join(children[table_index + 1].itertext()).strip(), "")


if __name__ == "__main__":
    unittest.main()
