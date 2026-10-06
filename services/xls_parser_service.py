import os
import io
import re
import html
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

def parse_summary_xls(xls_path: str) -> dict:
    """
    Reads an AMFI Summary document (XML spreadsheet 2003, AMFI XML, HTML table, or binary Excel)
    and returns its rows as a dictionary mapping sheet_name to a list of dictionaries.
    Strips extra whitespace from strings and converts empty values to None.
    """
    if not xls_path or not os.path.exists(xls_path):
        logger.error(f"Invalid or non-existent file path provided: {xls_path}")
        return {}

    with open(xls_path, "rb") as f:
        content = f.read()

    if not content or b"404 - File" in content:
        logger.error(f"File {xls_path} is empty or contains 404 error.")
        return {}

    # 1. XML Spreadsheet 2003 (<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet">)
    if b"urn:schemas-microsoft-com:office:spreadsheet" in content or b"<Workbook" in content[:300]:
        try:
            root = ET.fromstring(content)
            ns = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}
            sheets = {}
            for ws in root.findall(".//ss:Worksheet", ns):
                sheet_name = ws.attrib.get(f"{{{ns['ss']}}}Name", "Sheet1")
                rows = []
                for r in ws.findall(".//ss:Row", ns):
                    cells = []
                    for c in r.findall("./ss:Cell", ns):
                        idx_attr = c.attrib.get(f"{{{ns['ss']}}}Index")
                        if idx_attr:
                            target_idx = int(idx_attr) - 1
                            while len(cells) < target_idx:
                                cells.append("")
                        d = c.find("./ss:Data", ns)
                        text = d.text.strip() if (d is not None and d.text) else ""
                        cells.append(text)
                    if any(cells):
                        if len(cells) >= 3 and (re.match(r"^\d+$", cells[0]) or cells[0] == "Fields"):
                            row_dict = {cells[0]: cells[1], cells[1]: cells[2], "val": cells[2]}
                            if re.match(r"^\d+$", cells[0]):
                                row_dict[f"field_{cells[0]}"] = cells[2]
                            rows.append(row_dict)
                        elif len(cells) >= 2:
                            row_dict = {cells[0]: cells[1], "val": cells[1]}
                            if re.match(r"^\d+$", cells[0]):
                                row_dict[f"field_{cells[0]}"] = cells[1]
                            rows.append(row_dict)
                        elif len(cells) == 1:
                            rows.append({"col0": cells[0]})
                if rows:
                    sheets[sheet_name] = rows
            if sheets:
                logger.info(f"Successfully parsed XML Spreadsheet with {len(sheets)} sheets from {xls_path}.")
                return sheets
        except Exception as e:
            logger.warning(f"XML Spreadsheet parsing failed for {xls_path}: {e}")

    # 2. Pure AMFI XML (<SchemeSummaryDocument> or <root type="object">)
    if b"<SchemeSummaryDocument" in content[:300] or b"<root" in content[:300] or b"<SchemeSummary" in content[:300]:
        try:
            root = ET.fromstring(content)
            summary_elem = root.find(".//SchemeSummary")
            if summary_elem is None:
                summary_elem = root
            xml_dict = {}
            for child in summary_elem:
                items = child.findall("./item")
                if items:
                    arr = []
                    for it in items:
                        it_dict = {sub.tag: (sub.text.strip() if sub.text else "") for sub in it}
                        arr.append(it_dict)
                    xml_dict[child.tag] = arr
                elif child.text and child.text.strip():
                    xml_dict[child.tag] = child.text.strip()
            rows = [{k: v} for k, v in xml_dict.items()]
            logger.info(f"Successfully parsed AMFI XML with {len(rows)} attributes from {xls_path}.")
            return {"Sheet1": rows}
        except Exception as e:
            logger.warning(f"AMFI XML parsing failed for {xls_path}: {e}")

    # 3. HTML Table (as often served in .xls files)
    if b"<html" in content[:300].lower() or b"<table" in content[:300].lower():
        try:
            text_html = content.decode("utf-8", errors="ignore")
            rows = []
            for tr_match in re.finditer(r"<tr[^>]*>(.*?)</tr>", text_html, flags=re.DOTALL | re.IGNORECASE):
                tr_content = tr_match.group(1)
                cells = []
                for td_match in re.finditer(r"<t[dh][^>]*>(.*?)</t[dh]>", tr_content, flags=re.DOTALL | re.IGNORECASE):
                    td_raw = td_match.group(1)
                    td_clean = re.sub(r"<[^>]+>", " ", td_raw, flags=re.DOTALL | re.IGNORECASE)
                    td_clean = html.unescape(td_clean).strip()
                    cells.append(td_clean)
                if len(cells) >= 2:
                    rows.append({cells[0]: cells[1], "val": cells[1]})
                elif len(cells) == 1:
                    rows.append({"col0": cells[0]})
            if rows:
                logger.info(f"Successfully parsed HTML table with {len(rows)} rows from {xls_path}.")
                return {"Sheet1": rows}
        except Exception as e:
            logger.warning(f"HTML table parsing failed for {xls_path}: {e}")

    return {}


