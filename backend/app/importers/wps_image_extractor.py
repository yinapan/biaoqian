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


def extract_wps_images(xlsx_path: str) -> dict[str, dict[int, str]]:
    """Extract WPS DISPIMG image mappings.

    Returns ``{sheet_name: {row_number: media_path}}`` nested dict.
    """
    result: dict[str, dict[int, str]] = {}
    try:
        with zipfile.ZipFile(xlsx_path) as zf:
            if "xl/cellimages.xml" not in zf.namelist():
                return result

            # Step 1: Parse cellimages.xml to get image name -> rId mapping
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

            # Step 2: Parse rels to get rId -> media file path mapping
            rels_path = "xl/_rels/cellimages.xml.rels"
            if rels_path not in zf.namelist():
                return result

            rels_xml = zf.read(rels_path).decode("utf-8")
            rels_root = ET.fromstring(rels_xml)
            rid_to_path: dict[str, str] = {}
            for rel in rels_root.iter():
                if rel.tag.endswith("Relationship"):
                    rid_to_path[rel.get("Id")] = rel.get("Target")

            # Step 3: Scan worksheet XML for DISPIMG formulas
            for fname in zf.namelist():
                if not fname.startswith("xl/worksheets/sheet") or not fname.endswith(".xml"):
                    continue
                sheet_xml = zf.read(fname).decode("utf-8")
                matches = re.findall(
                    r'<c r="([A-Z]+)(\d+)"[^>]*>.*?<f[^>]*>.*?DISPIMG\("([^"]+)"',
                    sheet_xml,
                    re.DOTALL,
                )
                if not matches:
                    continue
                sheet_name = fname.split("/")[-1].replace(".xml", "")
                sheet_map: dict[int, str] = {}
                for _col, row_str, img_name in matches:
                    row_num = int(row_str)
                    rid = name_to_rid.get(img_name)
                    if rid:
                        media_path = rid_to_path.get(rid)
                        if media_path:
                            sheet_map[row_num] = f"xl/{media_path}"
                result[sheet_name] = sheet_map

    except Exception:
        # Gracefully handle corrupt or non-WPS files
        pass

    return result
