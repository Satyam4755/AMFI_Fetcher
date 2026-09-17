import glob
import logging
import os
import re

import pandas as pd

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
    
    Expected DataFrame columns: 'sif_code', 'nav_date', 'nav'
    
    Formula:
        monthly_return = round(((last_nav_of_month / first_nav_of_month) - 1) * 100, 2)
    
    Returns:
        dict: { year (int): { 'sif_code': str, 'year': int, 'jan': float|None, ..., 'dec': float|None } }
    """
    if df is None or df.empty:
        return {}

    df = df.copy()

    # AMFI date format is usually dd-MMM-yyyy (e.g. 09-Jul-2026) or ISO format
    df["nav_date"] = pd.to_datetime(df["nav_date"], format="mixed", errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")

    # Drop invalid rows
    df = df.dropna(subset=["nav_date", "nav"])
    # Drop non-positive NAV values
    df = df[df["nav"] > 0]

    if df.empty:
        return {}

    # Extract SIF code
    if "sif_code" not in df.columns or df["sif_code"].dropna().empty:
        return {}
    
    sif_code = str(df["sif_code"].dropna().iloc[0]).strip()
    if not sif_code:
        return {}

    # Sort strictly chronologically
    df = df.sort_values("nav_date").reset_index(drop=True)

    df["year"] = df["nav_date"].dt.year
    df["month"] = df["nav_date"].dt.month

    yearly_results = {}

    for year, year_df in df.groupby("year"):
        row = {"sif_code": sif_code, "year": int(year)}
        for m in range(1, 13):
            month_col = MONTH_COLUMNS[m - 1]
            month_df = year_df[year_df["month"] == m]
            if month_df.empty:
                row[month_col] = None
            else:
                first_nav = float(month_df.iloc[0]["nav"])
                last_nav = float(month_df.iloc[-1]["nav"])
                if first_nav <= 0 or last_nav <= 0:
                    row[month_col] = None
                else:
                    return_val = round(((last_nav / first_nav) - 1.0) * 100.0, 2)
                    row[month_col] = return_val
        yearly_results[int(year)] = row

    return yearly_results


def generate_all_heatmaps(historical_dir, heatmap_dir):
    """
    Reads all historical NAV CSV files from historical_dir, calculates monthly returns,
    and deterministically outputs/overwrites data/sif/scheme/heatMap/<year>.csv for every available year.
    
    Returns:
        dict: Summary metadata { 'years_generated': list of years, 'schemes_processed': int }
    """
    os.makedirs(heatmap_dir, exist_ok=True)

    csv_files = glob.glob(os.path.join(historical_dir, "*.csv"))
    if not csv_files:
        logger.warning(f"No historical NAV CSV files found in {historical_dir}")
        return {"years_generated": [], "schemes_processed": 0}

    logger.info(f"Found {len(csv_files)} historical NAV files for heatmap generation.")

    # Data structure: { year: { sif_code: row_dict } }
    yearly_schemes_map = {}
    schemes_processed = 0

    for file_path in sorted(csv_files):
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                continue

            scheme_yearly = calculate_monthly_returns_for_scheme(df)
            if not scheme_yearly:
                continue

            schemes_processed += 1
            for year, row in scheme_yearly.items():
                if year not in yearly_schemes_map:
                    yearly_schemes_map[year] = {}
                sif_code = row["sif_code"]
                yearly_schemes_map[year][sif_code] = row

        except Exception as e:
            logger.error(f"Error processing historical file {file_path} for heatmap: {e}")

    years_generated = sorted(yearly_schemes_map.keys())

    for year in years_generated:
        schemes_dict = yearly_schemes_map[year]
        # Sort schemes by natural SIF code order
        sorted_sif_codes = sorted(schemes_dict.keys(), key=natural_sif_sort_key)

        rows = []
        for sif_code in sorted_sif_codes:
            r = schemes_dict[sif_code]
            row_dict = {
                "sif_code": r["sif_code"],
                "year": r["year"],
            }
            for col in MONTH_COLUMNS:
                val = r.get(col)
                row_dict[col] = f"{val:.2f}" if (val is not None and not pd.isna(val)) else ""
            rows.append(row_dict)

        out_df = pd.DataFrame(rows, columns=HEADER)
        out_path = os.path.join(heatmap_dir, f"{year}.csv")
        out_df.to_csv(out_path, index=False)
        logger.info(f"Generated heatmap for year {year} ({len(rows)} schemes) at {out_path}")

    return {
        "years_generated": years_generated,
        "schemes_processed": schemes_processed,
    }
