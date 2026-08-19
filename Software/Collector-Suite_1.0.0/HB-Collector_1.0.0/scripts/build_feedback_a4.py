"""Build the HB feedback sheet from the published SE A4 evaluation layout."""
from __future__ import annotations

import copy
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "scripts" / "assets" / "Evaluation_SE1.odt"
FEEDBACK_SOURCE = ROOT / "scripts" / "assets" / "Rueckmeldung_HB_A5_Quer.odt"
OUTPUT = ROOT / "templates" / "IB_Hefterbewertung.odt"

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)

def q(prefix: str, name: str) -> str:
    return f"{{{NS[prefix]}}}{name}"

def text_of(node: ET.Element) -> str:
    return "".join(node.itertext()).strip()

def replace_text(root: ET.Element, old: str, new: str) -> None:
    for item in root.iter():
        if old in (item.text or ""):
            item.text = item.text.replace(old, new)
        if old in (item.tail or ""):
            item.tail = item.tail.replace(old, new)

def entries(path: Path):
    with zipfile.ZipFile(path) as source:
        return [(info, source.read(info.filename)) for info in source.infolist()]

base_entries = entries(BASE)
source_entries = entries(FEEDBACK_SOURCE)
base_root = ET.fromstring(next(data for info, data in base_entries if info.filename == "content.xml"))
source_root = ET.fromstring(next(data for info, data in source_entries if info.filename == "content.xml"))

replace_text(base_root, "PHYSIK", "FACH")
replace_text(base_root, "Mitarbeit im Unterricht", "Hefterbewertung")
replace_text(base_root, "Auswertung der Selbstevaluation · Q1 2026/27", "Rückmeldung · ZEITRAUM")

base_auto = next(base_root.iter(q("office", "automatic-styles")))
source_auto = next(source_root.iter(q("office", "automatic-styles")))
existing_names = {item.get(q("style", "name")) for item in base_auto.findall(q("style", "style"))}
for style in source_auto.findall(q("style", "style")):
    name = style.get(q("style", "name")) or ""
    if name.startswith("HB") and name not in existing_names:
        base_auto.append(copy.deepcopy(style))

base_body = next(base_root.iter(q("office", "text")))
kept = []
for child in list(base_body):
    if child.tag == q("text", "sequence-decls"):
        kept.append(child)
    elif child.tag == q("table", "table") and child.get(q("table", "name")) in {"Table2", "SEFields"}:
        kept.append(child)
for child in list(base_body):
    base_body.remove(child)
for child in kept:
    base_body.append(child)

source_body = next(source_root.iter(q("office", "text")))
intro = next(p for p in source_body.findall(q("text", "p")) if p.get(q("text", "style-name")) == "HBIntro")
table = next(t for t in source_body.findall(q("table", "table")) if t.get(q("table", "name")) == "HBFeedback")
summary = next(p for p in source_body.findall(q("text", "p")) if p.get(q("text", "style-name")) == "HBSummary")
table = copy.deepcopy(table)
last_row = table.findall(q("table", "table-row"))[-1]
ninth = copy.deepcopy(last_row)
replace_text(ninth, "_8", "_9")
table.append(ninth)
base_body.extend((copy.deepcopy(intro), table, copy.deepcopy(summary)))

content = ET.tostring(base_root, encoding="utf-8", xml_declaration=True)
manifest_data = next(data for info, data in base_entries if info.filename == "META-INF/manifest.xml")
manifest_root = ET.fromstring(manifest_data)
for item in manifest_root.iter(q("manifest", "file-entry")):
    if item.get(q("manifest", "full-path")) == "/":
        item.set(q("manifest", "media-type"), "application/vnd.oasis.opendocument.text")
manifest = ET.tostring(manifest_root, encoding="utf-8", xml_declaration=True)

with tempfile.NamedTemporaryFile(dir=OUTPUT.parent, suffix=".odt", delete=False) as stream:
    temporary = Path(stream.name)
with zipfile.ZipFile(temporary, "w") as target:
    for info, data in base_entries:
        if info.filename == "mimetype":
            payload = b"application/vnd.oasis.opendocument.text"
        elif info.filename == "content.xml":
            payload = content
        elif info.filename == "META-INF/manifest.xml":
            payload = manifest
        else:
            payload = data
        compression = zipfile.ZIP_STORED if info.filename == "mimetype" else info.compress_type
        target.writestr(info, payload, compress_type=compression)
temporary.replace(OUTPUT)
