import csv
import glob
import json
import logging
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

AMFI_BASE_URL = "https://www.amfiindia.com"
SIF_NAV_HISTORY_API = f"{AMFI_BASE_URL}/api/sif-nav-history"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


def _http_get_json(url: str, timeout: int = 15) -> Any:
    """Helper to fetch JSON from URL with timeout and standard headers."""
    try:
        import requests
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"HTTP GET failed ({resp.status_code}) for {url}")
        return None
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"requests failed for {url}: {e}, falling back to urllib...")

    try:
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning(f"urllib failed for {url}: {e}")
    return None


def parse_nav_date(val: Any) -> tuple[datetime | None, str | None]:
    """
    Parses various date representations into a datetime object and standard 'dd-MMM-yyyy' string.
    Supports ISO formats ('2026-08-19', '2026-08-19T00:00:00.000Z') and AMFI formats ('19-Aug-2026').
    """
    if not val:
        return None, None
    s = str(val).strip()
    if not s:
        return None, None

    # Handle ISO with timestamp (e.g. 2026-08-19T00:00:00.000Z)
    if "T" in s:
        s = s.split("T")[0]
    elif " " in s:
        s = s.split()[0]

    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt, dt.strftime("%d-%b-%Y")
        except ValueError:
            pass

    return None, None


def clean_nav_value(val: Any) -> float | None:
    """
    Validates and cleans NAV value. Returns float or None.
    Rejects strings like 'GROWTH', 'Direct Plan', negative numbers, or non-numeric tokens.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        import math
        if math.isnan(val) or math.isinf(val) or val <= 0:
            return None
        return float(val)

    s = str(val).replace(",", "").strip()
    if not s or s.lower() in ("nan", "null", "none", "-", "na", "n/a"):
        return None

    try:
        f = float(s)
        return f if f > 0 else None
    except (ValueError, TypeError):
        return None


def fetch_historical_nav_from_amfi(
    sif_code: str,
    from_date: str = "2024-01-01",
    to_date: str | None = None
) -> list[dict]:
    """
    Fetches historical NAV observations for a given SIF code from AMFI SIF NAV History API.
    Returns list of dicts: [{'sif_code': 'SIF-122', 'nav_date': '10-Jun-2026', 'nav': '9.9678', 'dt': datetime_obj, 'plan': '...'}]
    """
    if not sif_code:
        return []

    if not to_date:
        to_date = datetime.utcnow().strftime("%Y-%m-%d")

    # Format from_date if in dd-MMM-yyyy format
    from_dt, _ = parse_nav_date(from_date)
    if from_dt:
        from_date_iso = from_dt.strftime("%Y-%m-%d")
    else:
        from_date_iso = "2024-01-01"

    to_dt, _ = parse_nav_date(to_date)
    to_date_iso = to_dt.strftime("%Y-%m-%d") if to_dt else datetime.utcnow().strftime("%Y-%m-%d")

    url = f"{SIF_NAV_HISTORY_API}?query_type=historical_period&sd_id={sif_code}&from_date={from_date_iso}&to_date={to_date_iso}"
    data = _http_get_json(url)

    if not data or not isinstance(data, dict):
        return []

    resp_data = data.get("data", {})
    nav_groups = resp_data.get("nav_groups", [])
    if not nav_groups and isinstance(resp_data, list):
        nav_groups = resp_data

    results = []
    for grp in nav_groups:
        records = grp.get("historical_records", [])
        for r in records:
            raw_date = r.get("date") or r.get("hNAV_Date")
            raw_nav = r.get("nav") or r.get("hNAV_Amt")
            plan = r.get("Plan") or ""

            # Check if this record is a Direct Plan
            if "direct" in plan.lower():
                continue

            dt, date_str = parse_nav_date(raw_date)
            nav_val = clean_nav_value(raw_nav)

            if dt and date_str and nav_val is not None:
                # Format NAV to match original precision (e.g. 4 decimals or exact string)
                nav_str = f"{nav_val:.4f}" if isinstance(nav_val, float) and len(str(nav_val).split(".")[-1]) <= 4 else str(nav_val)
                # If exact raw_nav string had decimals, preserve precision
                if isinstance(raw_nav, str) and "." in raw_nav:
                    nav_str = raw_nav.strip()
                elif isinstance(raw_val_float := clean_nav_value(raw_nav), float):
                    # Strip unnecessary trailing zeros if whole or keep clean float format
                    nav_str = f"{raw_val_float:.4f}".rstrip("0").rstrip(".") if f"{raw_val_float:.4f}".endswith(".0000") else f"{raw_val_float:.4f}"

                results.append({
                    "sif_code": sif_code,
                    "nav_date": date_str,
                    "nav": str(nav_val),
                    "dt": dt,
                    "plan": plan
                })

    return results


def fetch_daily_sif_nav_from_amfi(date_str: str) -> list[dict]:
    """
    Fetches all SIF NAV records for a specific calendar date from AMFI.
    date_str can be YYYY-MM-DD or dd-MMM-yyyy.
    """
    dt, date_formatted = parse_nav_date(date_str)
    if not dt or not date_formatted:
        return []

    date_iso = dt.strftime("%Y-%m-%d")
    url = f"{SIF_NAV_HISTORY_API}?query_type=all_for_date&from_date={date_iso}"
    data = _http_get_json(url)

    if not data or not isinstance(data, dict):
        return []

    results = []
    for mf in data.get("data", []):
        for s in mf.get("schemes", []):
            for n in s.get("navs", []):
                sd_id = n.get("SD_ID")
                h_nav = clean_nav_value(n.get("hNAV_Amt"))
                h_date_raw = n.get("hNAV_Date")
                h_dt, h_date_str = parse_nav_date(h_date_raw)

                if sd_id and h_nav is not None and (h_dt or dt):
                    target_date_str = h_date_str if h_date_str else date_formatted
                    target_dt = h_dt if h_dt else dt
                    results.append({
                        "sif_code": sd_id,
                        "nav_date": target_date_str,
                        "nav": str(h_nav),
                        "dt": target_dt,
                        "plan": n.get("Plan", ""),
                        "option": n.get("Option", "")
                    })

    return results


def read_existing_historical_csv(filepath: str) -> list[dict]:
    """Reads an existing historical NAV CSV file and returns cleaned rows."""
    if not os.path.exists(filepath):
        return []

    rows = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                sif_code = r.get("sif_code")
                nav_date_raw = r.get("nav_date")
                nav_raw = r.get("nav")

                dt, date_str = parse_nav_date(nav_date_raw)
                nav_val = clean_nav_value(nav_raw)

                # Ignore corrupted rows (e.g. Plan name in nav column)
                if sif_code and dt and date_str and nav_val is not None:
                    rows.append({
                        "sif_code": sif_code.strip(),
                        "nav_date": date_str,
                        "nav": str(nav_raw).strip(),
                        "dt": dt
                    })
    except Exception as e:
        logger.warning(f"Error reading historical CSV {filepath}: {e}")
    return rows


def merge_historical_records(existing_rows: list[dict], new_rows: list[dict]) -> list[dict]:
    """
    Merges existing and newly fetched records:
    - Deduplicates by date.
    - Preserves existing valid NAV records without unnecessary overwriting.
    - Seamlessly inserts missing historical dates (earlier, internal, or later).
    - Filters invalid NAV values.
    - Sorts chronologically in ascending order.
    """
    date_map: dict[datetime, dict] = {}

    for r in existing_rows:
        dt = r.get("dt")
        if dt and clean_nav_value(r.get("nav")) is not None:
            date_map[dt] = r

    for r in new_rows:
        dt = r.get("dt")
        if dt and clean_nav_value(r.get("nav")) is not None:
            if dt not in date_map:
                date_map[dt] = r

    # Sort chronologically
    sorted_dts = sorted(date_map.keys())
    merged = []
    for dt in sorted_dts:
        item = date_map[dt]
        merged.append({
            "sif_code": item["sif_code"],
            "nav_date": item["nav_date"],
            "nav": str(item["nav"])
        })

    return merged



def write_historical_nav_csv(sif_code: str, rows: list[dict], base_dir: str = "data/sif/scheme/nav/historical") -> str:
    """Writes the merged records to data/sif/scheme/nav/historical/sif_x.csv."""
    os.makedirs(base_dir, exist_ok=True)
    safe_name = sif_code.lower().replace("-", "_")
    filepath = os.path.join(base_dir, f"{safe_name}.csv")

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["sif_code", "nav_date", "nav"])
        writer.writeheader()
        writer.writerows(rows)

    return filepath


def update_historical_nav(schemes: list[dict], base_dir: str = "data/sif/scheme/nav/historical"):
    """
    Appends or updates historical NAV CSV files from a list of scheme dicts.
    Preserves backward compatibility with daily NAV pipeline.
    """
    if not schemes:
        return

    os.makedirs(base_dir, exist_ok=True)

    for scheme in schemes:
        sif_code = scheme.get("sif_code")
        nav_date_raw = scheme.get("nav_date")
        nav_raw = scheme.get("nav")

        if not sif_code or not nav_date_raw:
            continue

        dt, date_str = parse_nav_date(nav_date_raw)
        nav_val = clean_nav_value(nav_raw)
        if not dt or not date_str or nav_val is None:
            continue

        safe_name = sif_code.lower().replace("-", "_")
        filepath = os.path.join(base_dir, f"{safe_name}.csv")

        existing_rows = read_existing_historical_csv(filepath)
        new_row = {"sif_code": sif_code, "nav_date": date_str, "nav": str(nav_raw).strip(), "dt": dt}
        merged = merge_historical_records(existing_rows, [new_row])
        write_historical_nav_csv(sif_code, merged, base_dir=base_dir)


def discover_eligible_non_direct_sifs(
    details_dir: str = "data/sif/scheme/details",
    navall_path_or_url: str | None = None
) -> list[dict]:
    """
    Discovers all eligible SIF schemes/plans that are NOT Direct plans.
    Combines scheme detail JSON metadata and AMFI SIF_NAVAll feed.
    """
    sif_dict: dict[str, dict] = {}
    direct_codes: set[str] = set()

    # 1. Parse details directory
    if os.path.exists(details_dir):
        for f in glob.glob(os.path.join(details_dir, "*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
            except Exception:
                continue

            fund_name = data.get("fund_name", "")
            inception = data.get("allotment_date") or data.get("nfo_allotment_date") or data.get("nfo_open_date") or data.get("reopen_date")

            plans = data.get("plans", {})
            for p_type, p_obj in plans.items():
                if not isinstance(p_obj, dict):
                    continue
                for opt, opt_obj in p_obj.items():
                    objs = opt_obj if isinstance(opt_obj, list) else []
                    if isinstance(opt_obj, dict):
                        for k, v in opt_obj.items():
                            if isinstance(v, list):
                                objs.extend(v)
                    for item in objs:
                        if not isinstance(item, dict):
                            continue
                        amfi_code = item.get("amfi_code")
                        name = item.get("name") or ""
                        is_direct = (p_type == "direct") or ("direct" in name.lower())

                        if amfi_code and str(amfi_code).startswith("SIF-"):
                            if is_direct:
                                direct_codes.add(amfi_code)
                            else:
                                if amfi_code not in sif_dict:
                                    sif_dict[amfi_code] = {
                                        "sif_code": amfi_code,
                                        "isin": item.get("isin_code"),
                                        "name": name,
                                        "fund_name": fund_name,
                                        "inception": str(inception).split()[0] if inception else None,
                                        "is_direct": False
                                    }

    # 2. Parse AMFI SIF_NAVAll.txt
    lines = []
    if navall_path_or_url and os.path.exists(navall_path_or_url):
        with open(navall_path_or_url, "r", encoding="utf-8") as fp:
            lines = fp.read().splitlines()
    else:
        try:
            url = navall_path_or_url or "https://portal.amfiindia.com/spages/SIF_NAVAll.txt"
            req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                lines = resp.read().decode("utf-8", errors="ignore").splitlines()
        except Exception as e:
            logger.warning(f"Could not fetch SIF_NAVAll.txt for plan discovery: {e}")

    code_idx = 0
    plan_idx = 4
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("Scheme Code"):
            headers = [h.strip() for h in line.split(";")]
            try:
                code_idx = headers.index("Scheme Code")
                plan_idx = headers.index("Plan")
            except ValueError:
                pass
            continue
        if ";" not in line:
            continue
        parts = [p.strip() for p in line.split(";")]
        if len(parts) > max(code_idx, plan_idx):
            code = parts[code_idx]
            plan = parts[plan_idx]
            is_direct = "direct" in plan.lower()

            if is_direct:
                direct_codes.add(code)
                if code in sif_dict:
                    del sif_dict[code]
            else:
                if code not in direct_codes and code not in sif_dict:
                    sif_dict[code] = {
                        "sif_code": code,
                        "isin": None,
                        "name": parts[3] if len(parts) > 3 else "",
                        "fund_name": None,
                        "inception": None,
                        "is_direct": False
                    }

    # Remove any direct plans
    eligible = [v for k, v in sif_dict.items() if k not in direct_codes]

    # Sort by numeric SIF code
    def sort_key(item):
        code = item["sif_code"]
        match = re.search(r"\d+", code)
        return int(match.group(0)) if match else 999999

    return sorted(eligible, key=sort_key)
