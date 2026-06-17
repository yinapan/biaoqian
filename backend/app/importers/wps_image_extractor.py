# backend/app/importers/wps_image_extractor.py
"""Extract WPS DISPIMG image mappings from .xlsx files.

WPS Office embeds cell images via a proprietary DISPIMG formula mechanism.
This module parses the underlying XML to map (sheet, row) -> media file path.

Uses defusedxml to prevent XXE attacks when parsing untrusted Excel files.
"""
from __future__ import annotations

import re
import zipfile

import defusedxml.ElementTree as ET

_SSML_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_DISPIMG_RE = re.compile(r'DISPIMG\("([^"]+)"')


def _build_sheet_name_map(zf: zipfile.ZipFile) -> dict[str, str]:
    """Map worksheet XML filenames (e.g. 'sheet3') to display names (e.g. 'P080【完成】')."""
    wb_xml = zf.read("xl/workbook.xml").decode("utf-8")
    wb_root = ET.fromstring(wb_xml)

    rid_to_display: dict[str, str] = {}
    for elem in wb_root.iter():
        if elem.tag.endswith("}sheet"):
            name = elem.get("name")
            rid = None
            for attr, val in elem.attrib.items():
                if attr.endswith("}id"):
                    rid = val
            if name and rid:
                rid_to_display[rid] = name

    rels_path = "xl/_rels/workbook.xml.rels"
    if rels_path not in zf.namelist():
        return {}

    rels_xml = zf.read(rels_path).decode("utf-8")
    rels_root = ET.fromstring(rels_xml)

    xml_to_display: dict[str, str] = {}
    for rel in rels_root.iter():
        if rel.tag.endswith("Relationship"):
            target = rel.get("Target")
            rid = rel.get("Id")
            if target and rid and "worksheets/" in target:
                xml_name = target.split("/")[-1].replace(".xml", "")
                display = rid_to_display.get(rid)
                if display:
                    xml_to_display[xml_name] = display

    return xml_to_display


def _scan_sheet_for_dispimg(zf: zipfile.ZipFile, fname: str) -> dict[int, str]:
    """Parse a worksheet XML and return {row_num: image_name} for DISPIMG formulas."""
    sheet_xml = zf.read(fname).decode("utf-8")
    root = ET.fromstring(sheet_xml)

    row_to_img: dict[int, str] = {}
    f_tag = f"{{{_SSML_NS}}}f"
    c_tag = f"{{{_SSML_NS}}}c"

    for cell in root.iter(c_tag):
        formula_elem = cell.find(f_tag)
        if formula_elem is None or formula_elem.text is None:
            continue
        m = _DISPIMG_RE.search(formula_elem.text)
        if not m:
            continue
        ref = cell.get("r", "")
        row_str = re.sub(r"[A-Z]+", "", ref)
        if row_str:
            row_to_img[int(row_str)] = m.group(1)

    return row_to_img


def extract_wps_images(xlsx_path: str) -> dict[str, dict[int, str]]:
    """Extract WPS DISPIMG image mappings.

    Returns ``{display_sheet_name: {row_number: media_path}}`` nested dict.
    Keys are actual sheet display names (e.g. "P080【完成】"), not XML filenames.
    """
    result: dict[str, dict[int, str]] = {}
    try:
        with zipfile.ZipFile(xlsx_path) as zf:
            if "xl/cellimages.xml" not in zf.namelist():
                return result

            sheet_name_map = _build_sheet_name_map(zf)

            ci_xml = zf.read("xl/cellimages.xml").decode("utf-8")
            name_to_rid: dict[str, str] = {}
            ci_root = ET.fromstring(ci_xml)
            for elem in ci_root.iter():
                if elem.tag.endswith("cellImage"):
                    name: str | None = None
                    rid: str | None = None
                    for child in elem.iter():
                        if child.tag.endswith("cNvPr"):
                            name = child.get("name")
                        if child.tag.endswith("blip"):
                            for attr_name, attr_val in child.attrib.items():
                                if attr_name.endswith("}embed"):
                                    rid = attr_val
                    if name and rid:
                        name_to_rid[name] = rid

            rels_path = "xl/_rels/cellimages.xml.rels"
            if rels_path not in zf.namelist():
                return result

            rels_xml = zf.read(rels_path).decode("utf-8")
            rels_root = ET.fromstring(rels_xml)
            rid_to_path: dict[str, str] = {}
            for rel in rels_root.iter():
                if rel.tag.endswith("Relationship"):
                    rid_to_path[rel.get("Id")] = rel.get("Target")

            for fname in zf.namelist():
                if not fname.startswith("xl/worksheets/sheet") or not fname.endswith(".xml"):
                    continue

                row_to_img = _scan_sheet_for_dispimg(zf, fname)
                if not row_to_img:
                    continue

                xml_name = fname.split("/")[-1].replace(".xml", "")
                display_name = sheet_name_map.get(xml_name, xml_name)
                sheet_map: dict[int, str] = {}
                for row_num, img_name in row_to_img.items():
                    rid = name_to_rid.get(img_name)
                    if rid:
                        media_path = rid_to_path.get(rid)
                        if media_path:
                            sheet_map[row_num] = f"xl/{media_path}"
                if sheet_map:
                    result[display_name] = sheet_map

    except Exception:
        pass

    return result


def extract_image_bytes(xlsx_path: str, media_path: str) -> bytes | None:
    """Extract a single image's bytes from the xlsx zip archive."""
    try:
        with zipfile.ZipFile(xlsx_path) as zf:
            return zf.read(media_path)
    except (KeyError, zipfile.BadZipFile):
        return None
