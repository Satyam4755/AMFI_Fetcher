import csv
import glob
import logging
import os
import re
from typing import Any

import json
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

AMFI_BASE_URL = "https://www.amfiindia.com"
AUM_API_PATH = "/api/sif-average-aum-schemewise"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


def _http_get_json(url: str, timeout: int = 15) -> Any:
    """Helper to fetch JSON from URL using requests if available, or urllib.request."""
    try:
        import requests
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"requests failed for {url}: {e}, trying urllib...")

    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def clean_numeric_aum(val: Any) -> float | None:
    """
    Cleans and converts raw AUM value to a standard float.
    Handles numeric types, strings with commas (e.g. '6,138.22'), spaces, None, NaN, currency text.
    Returns float or None if invalid/missing.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        import math
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("nan", "null", "none", "-", "na", "n/a"):
        return None
    
    # Match the first floating-point or integer number in the string
    match = re.search(r"[-+]?\d[\d,]*\.?\d*", val_str)
    if not match:
        return None
        
    num_str = match.group(0).replace(",", "")
    try:
        return float(num_str)
    except (ValueError, TypeError):
        return None


def fetch_financial_years(
    base_url: str = AMFI_BASE_URL,
    str_type: str = "Categorywise",
    sif_id: int = 0,
    timeout: int = 15
) -> list[dict]:
    """
    Fetches available financial years from AMFI SIF Average AUM endpoint.
    """
    url = f"{base_url}{AUM_API_PATH}?strType={str_type}&SIF_Id={sif_id}"
    logger.info(f"Fetching SIF AUM Financial Years from: {url}")
    try:
        data = _http_get_json(url, timeout=timeout)
        if isinstance(data, dict):
            return data.get("data", [])
        elif isinstance(data, list):
            return data
    except Exception as e:
        logger.error(f"Error fetching financial years: {e}")
    return []


def fetch_periods(
    fy_id: int,
    base_url: str = AMFI_BASE_URL,
    str_type: str = "Categorywise",
    sif_id: int = 0,
    timeout: int = 15
) -> list[dict]:
    """
    Fetches available periods for a financial year from AMFI SIF Average AUM endpoint.
    """
    url = f"{base_url}{AUM_API_PATH}?fyId={fy_id}&strType={str_type}&SIF_Id={sif_id}"
    logger.info(f"Fetching SIF AUM Periods for fyId={fy_id} from: {url}")
    try:
        data = _http_get_json(url, timeout=timeout)
        if isinstance(data, dict):
            d = data.get("data", {})
            if isinstance(d, dict):
                return d.get("periods", [])
            elif isinstance(d, list):
                return d
        elif isinstance(data, list):
            return data
    except Exception as e:
        logger.error(f"Error fetching periods for fyId={fy_id}: {e}")
    return []


def fetch_schemewise_aum_raw(
    fy_id: int,
    period_id: int,
    base_url: str = AMFI_BASE_URL,
    str_type: str = "Categorywise",
    sif_id: int = 0,
    timeout: int = 20
) -> list[dict]:
    """
    Fetches raw Schemewise Categorywise SIF AUM table data from AMFI.
    """
    url = f"{base_url}{AUM_API_PATH}?strType={str_type}&fyId={fy_id}&periodId={period_id}&SIF_Id={sif_id}"
    logger.info(f"Fetching SIF AUM data for fyId={fy_id}, periodId={period_id} from: {url}")
    try:
        data = _http_get_json(url, timeout=timeout)
        if isinstance(data, dict):
            return data.get("data", [])
        elif isinstance(data, list):
            return data
    except Exception as e:
        logger.error(f"Error fetching AUM data for fyId={fy_id}, periodId={period_id}: {e}")
    return []


def parse_aum_records(records: list[dict]) -> dict[str, float]:
    """
    Parses AMFI raw AUM response records into a mapping of sif_code -> aum (float).
    Extracts AMFI_Code (e.g. SIF-122) and AverageAumForTheMonth.
    """
    sif_aum_map: dict[str, float] = {}
    if not records:
        return sif_aum_map

    for group in records:
        schemes = group.get("schemes", [])
        if not schemes or not isinstance(schemes, list):
            continue

        for scheme in schemes:
            if not isinstance(scheme, dict):
                continue
            
            amfi_code = scheme.get("AMFI_Code") or scheme.get("amfi_code") or scheme.get("sif_code")
            if not amfi_code:
                continue

            amfi_code_str = str(amfi_code).strip()
            # Normalize SIF code if needed (e.g. sif-122 -> SIF-122)
            if amfi_code_str.lower().startswith("sif-"):
                sif_num = amfi_code_str.split("-")[-1]
                amfi_code_str = f"SIF-{sif_num}"

            raw_aum = scheme.get("AverageAumForTheMonth")
            if raw_aum is None:
                raw_aum = scheme.get("averageAUM") or scheme.get("AverageAum")

            cleaned_aum = clean_numeric_aum(raw_aum)
            if cleaned_aum is not None:
                sif_aum_map[amfi_code_str] = cleaned_aum
            else:
                logger.warning(f"Could not parse valid numeric AUM for {amfi_code_str}: raw_value={raw_aum}")

    logger.info(f"Successfully extracted {len(sif_aum_map)} SIF codes with AUM values.")
    return sif_aum_map


def fetch_latest_sif_aum(
    base_url: str = AMFI_BASE_URL,
    str_type: str = "Categorywise",
    sif_id: int = 0,
    timeout: int = 20
) -> tuple[dict[str, float], dict[str, Any]]:
    """
    Dynamically discovers the latest Financial Year and latest Period,
    and fetches the corresponding SIF AUM dataset.
    Returns (sif_aum_map, metadata_dict).
    """
    metadata: dict[str, Any] = {
        "financial_year": None,
        "fy_id": None,
        "period": None,
        "period_id": None,
        "count": 0,
    }

    # Step 1: Discover Financial Years
    fys = fetch_financial_years(base_url=base_url, str_type=str_type, sif_id=sif_id, timeout=timeout)
    if not fys:
        logger.error("No financial years found from AMFI.")
        return {}, metadata

    latest_fy = fys[0]
    fy_id = latest_fy.get("id")
    metadata["financial_year"] = latest_fy.get("financial_year")
    metadata["fy_id"] = fy_id

    if fy_id is None:
        logger.error("Latest financial year object missing 'id'.")
        return {}, metadata

    # Step 2: Discover Periods for the latest FY
    periods = fetch_periods(fy_id=fy_id, base_url=base_url, str_type=str_type, sif_id=sif_id, timeout=timeout)
    if not periods:
        logger.error(f"No periods found for fy_id={fy_id}.")
        return {}, metadata

    latest_period = periods[0]
    period_id = latest_period.get("id")
    metadata["period"] = latest_period.get("period")
    metadata["period_id"] = period_id

    if period_id is None:
        logger.error("Latest period object missing 'id'.")
        return {}, metadata

    # Step 3: Fetch Schemewise Table Data
    records = fetch_schemewise_aum_raw(
        fy_id=fy_id,
        period_id=period_id,
        base_url=base_url,
        str_type=str_type,
        sif_id=sif_id,
        timeout=timeout
    )
    if not records:
        logger.error("No AUM records returned from AMFI table data endpoint.")
        return {}, metadata

    sif_aum_map = parse_aum_records(records)
    metadata["count"] = len(sif_aum_map)

    logger.info(
        f"Fetched latest SIF AUM ({metadata['financial_year']} / {metadata['period']}): "
        f"{len(sif_aum_map)} schemes parsed."
    )
    return sif_aum_map, metadata


def merge_aum_into_schemes(schemes: list[dict], sif_aum_map: dict[str, float]) -> list[dict]:
    """
    Attaches or updates the 'AUM' key on each scheme dictionary.
    Formats AUM as a clean decimal string (or None/empty string if missing).
    """
    if not schemes:
        return []

    for scheme in schemes:
        sif_code = scheme.get("sif_code")
        if sif_code and sif_code in sif_aum_map:
            aum_val = sif_aum_map[sif_code]
            # Format float nicely without trailing unnecessary decimals if integer, but preserving precision
            scheme["AUM"] = f"{aum_val:.2f}" if isinstance(aum_val, float) else str(aum_val)
        else:
            # If not in AUM map, preserve existing AUM if present, else empty string
            if "AUM" not in scheme:
                scheme["AUM"] = ""

    return schemes


def update_single_daily_csv(file_path: str, sif_aum_map: dict[str, float]) -> bool:
    """
    Reads a single daily CSV file, updates/adds the AUM column, and writes it back.
    Ensures columns: sif_code,nav_date,nav,AUM
    """
    if not os.path.exists(file_path):
        return False

    rows = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sif_code = row.get("sif_code", "").strip()
            nav_date = row.get("nav_date", "").strip()
            nav = row.get("nav", "").strip()
            
            existing_aum = row.get("AUM", "").strip()
            if sif_code in sif_aum_map:
                aum_val = sif_aum_map[sif_code]
                aum_str = f"{aum_val:.2f}" if isinstance(aum_val, float) else str(aum_val)
            else:
                aum_str = existing_aum

            rows.append({
                "sif_code": sif_code,
                "nav_date": nav_date,
                "nav": nav,
                "AUM": aum_str
            })

    if not rows:
        return False

    with open(file_path, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["sif_code", "nav_date", "nav", "AUM"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return True


def update_daily_csv_files(
    daily_dir: str = "data/sif/scheme/nav/daily",
    sif_aum_map: dict[str, float] | None = None
) -> int:
    """
    Updates all daily CSV files in daily_dir with AUM data.
    If sif_aum_map is None, fetches the latest from AMFI.
    Returns count of updated files.
    """
    if sif_aum_map is None:
        sif_aum_map, _ = fetch_latest_sif_aum()

    if not sif_aum_map:
        logger.error("No SIF AUM data available to update CSV files.")
        return 0

    files = glob.glob(os.path.join(daily_dir, "*.csv"))
    if not files:
        logger.warning(f"No CSV files found in {daily_dir}.")
        return 0

    updated_count = 0
    for fpath in sorted(files):
        if update_single_daily_csv(fpath, sif_aum_map):
            updated_count += 1

    logger.info(f"Updated {updated_count}/{len(files)} daily CSV files with AUM.")
    return updated_count
