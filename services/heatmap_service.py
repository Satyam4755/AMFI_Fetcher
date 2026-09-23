import logging
import re
import pandas as pd

from services.performance_service import calculate_monthly_returns

logger = logging.getLogger("HeatmapService")

MONTH_COLUMNS = [
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec"
]

HEADER = ["sif_code", "year"] + MONTH_COLUMNS


def natural_sif_sort_key(sif_code):
    """
    Returns a sort key for natural ordering of SIF codes (e.g., SIF-1, SIF-2, ..., SIF-10, SIF-100).
    """
    if not sif_code or not isinstance(sif_code, str):
        return (float("inf"), str(sif_code))
    
    match = re.match(r"^([a-zA-Z\-_]+)?(\d+)?(.*)$", sif_code.strip())
    if match:
        prefix, num, suffix = match.groups()
        num_val = int(num) if num is not None else float("inf")
        return (prefix or "", num_val, suffix or "")
    return (sif_code, float("inf"), "")


def calculate_monthly_returns_for_scheme(df):
    """
    Calculates monthly performance percentage for a single SIF scheme.
    Maintained for backward compatibility, returns yearly-keyed dictionary.
    
    Expected DataFrame columns: 'sif_code', 'nav_date', 'nav'
    
    Returns:
        dict: { year (int): { 'sif_code': str, 'year': int, 'jan': float|None, ..., 'dec': float|None } }
    """
    if df is None or df.empty:
        return {}

    if "sif_code" not in df.columns or df["sif_code"].dropna().empty:
        return {}
    
    sif_code = str(df["sif_code"].dropna().iloc[0]).strip()
    if not sif_code:
        return {}

    monthly_dict = calculate_monthly_returns(df)
    if not monthly_dict:
        return {}

    yearly_results = {}
    for key, val in monthly_dict.items():
        year_str, month_str = key.split("-")
        year = int(year_str)
        month_idx = int(month_str) - 1
        if year not in yearly_results:
            yearly_results[year] = {"sif_code": sif_code, "year": year}
            for col in MONTH_COLUMNS:
                yearly_results[year][col] = None
        yearly_results[year][MONTH_COLUMNS[month_idx]] = val

    return yearly_results

