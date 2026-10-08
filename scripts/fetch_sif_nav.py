import argparse
import csv
import datetime
import glob
import logging
import os
import sys

# Add project root to python path to import modules properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import AMFI_SIF_URL
from services.api_client import fetch_text
from services.parser import extract_schemes
from services.csv_service import save_to_csv
from services.historical_nav_service import (
    parse_nav_date,
    clean_nav_value,
    update_historical_nav,
)
from services.aum_service import fetch_latest_sif_aum, merge_aum_into_schemes

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("SIFNavPipeline")


def load_stored_schemes_map(daily_nav_dir: str, target_file: str | None = None) -> dict[str, dict]:
    """
    Loads known NAV records per scheme from target_file if it exists,
    or from the latest daily CSV file in daily_nav_dir.
    Returns: {sif_code: {'dt': datetime, 'nav_date': str, 'nav': str, 'AUM': str}}
    """
    file_to_read = None
    if target_file and os.path.exists(target_file):
        file_to_read = target_file
    else:
        files = sorted(glob.glob(os.path.join(daily_nav_dir, "*.csv")))
        if files:
            file_to_read = files[-1]

    if not file_to_read or not os.path.exists(file_to_read):
        return {}

    stored = {}
    try:
        with open(file_to_read, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                code = r.get("sif_code")
                if not code:
                    continue
                code = code.strip()
                dt, date_str = parse_nav_date(r.get("nav_date"))
                stored[code] = {
                    "sif_code": code,
                    "dt": dt,
                    "nav_date": date_str or r.get("nav_date", "").strip(),
                    "nav": str(r.get("nav", "")).strip(),
                    "AUM": str(r.get("AUM", "")).strip() if "AUM" in r else "",
                }
    except Exception as e:
        logger.warning(f"Error reading stored NAV snapshot from {file_to_read}: {e}")
    return stored


def evaluate_nav_updates(
    incoming_schemes: list[dict],
    stored_map: dict[str, dict],
    target_csv_path: str
) -> tuple[bool, list[dict]]:
    """
    Evaluates whether incoming schemes from AMFI contain new/updated data.
    Returns (has_updates, list_of_updates).
    """
    target_exists = os.path.exists(target_csv_path)
    updates = []

    for s in incoming_schemes:
        code = s.get("sif_code")
        if not code:
            continue
        code = code.strip()

        in_dt, in_date_str = parse_nav_date(s.get("nav_date"))
        in_nav_val = clean_nav_value(s.get("nav"))
        in_nav_str = str(s.get("nav", "")).strip()

        if code not in stored_map:
            updates.append({
                "sif_code": code,
                "reason": "new_scheme",
                "old_date": None,
                "old_nav": None,
                "new_date": in_date_str,
                "new_nav": in_nav_str,
            })
            continue

        st = stored_map[code]
        st_dt = st.get("dt")
        st_nav_str = st.get("nav")

        # 1. Incoming date is newer than stored date
        if in_dt and st_dt and in_dt > st_dt:
            updates.append({
                "sif_code": code,
                "reason": "newer_date",
                "old_date": st.get("nav_date"),
                "old_nav": st_nav_str,
                "new_date": in_date_str,
                "new_nav": in_nav_str,
            })
        # 2. Same date but NAV value is corrected/updated
        elif in_dt and st_dt and in_dt == st_dt and in_nav_str != st_nav_str:
            updates.append({
                "sif_code": code,
                "reason": "updated_nav_value",
                "old_date": st.get("nav_date"),
                "old_nav": st_nav_str,
                "new_date": in_date_str,
                "new_nav": in_nav_str,
            })

    if not target_exists:
        return True, updates

    return len(updates) > 0, updates


def sync_sif_nav(
    base_dir: str = "data/sif/scheme/nav/daily",
    force: bool = False,
    target_date_str: str | None = None,
) -> bool:
    """
    Executes the SIF NAV pipeline with per-scheme freshness check.
    Fetches latest AMFI NAV data and creates/updates the daily snapshot for the target execution date.
    """
    logger.info("Starting SIF NAV pipeline...")
    os.makedirs(base_dir, exist_ok=True)

    # Step 1: Fetch Text from AMFI
    text_data = fetch_text(AMFI_SIF_URL)
    if not text_data:
        logger.error("Failed to fetch API data from AMFI. Pipeline aborted.")
        return False

    # Step 2: Parse to flat list of schemes
    schemes = extract_schemes(text_data)
    if not schemes:
        logger.error("No schemes extracted from AMFI feed. Pipeline aborted.")
        return False

    # Determine target daily snapshot filename
    if target_date_str:
        today_str = target_date_str.replace("-", "").strip()
    else:
        today_str = datetime.date.today().strftime("%Y%m%d")

    csv_path = os.path.join(base_dir, f"{today_str}.csv")

    # Step 3: Check for updates across all individual schemes
    stored_map = load_stored_schemes_map(base_dir, target_file=csv_path)
    has_updates, updates = evaluate_nav_updates(schemes, stored_map, csv_path)

    if not force and not has_updates and os.path.exists(csv_path):
        logger.info("All SIF schemes are already up to date with the latest AMFI NAVs. Daily snapshot skipped.")
        return True

    if updates:
        logger.info(f"Found {len(updates)} scheme NAV updates from AMFI:")
        for u in updates[:10]:
            logger.info(
                f"  {u['sif_code']} ({u['reason']}): {u['old_date']} ({u['old_nav']}) -> {u['new_date']} ({u['new_nav']})"
            )
        if len(updates) > 10:
            logger.info(f"  ... and {len(updates) - 10} more scheme updates.")

    # Step 4: Fetch and merge latest SIF AUM
    try:
        sif_aum_map, aum_meta = fetch_latest_sif_aum()
        if sif_aum_map:
            schemes = merge_aum_into_schemes(schemes, sif_aum_map)
            logger.info(
                f"Merged AUM data ({aum_meta.get('financial_year')} / {aum_meta.get('period')}) for {len(sif_aum_map)} SIFs."
            )
        else:
            logger.info("No AUM data available. Preserving or setting empty AUM column.")
            for s in schemes:
                code = s.get("sif_code", "")
                if code in stored_map and stored_map[code].get("AUM"):
                    s["AUM"] = stored_map[code]["AUM"]
                else:
                    s["AUM"] = ""
    except Exception as e:
        logger.warning(f"Could not fetch SIF AUM data ({e}). Preserving existing AUM.")
        for s in schemes:
            code = s.get("sif_code", "")
            if code in stored_map and stored_map[code].get("AUM"):
                s["AUM"] = stored_map[code]["AUM"]
            else:
                s["AUM"] = ""

    # Step 5: Save to Daily CSV
    csv_saved = save_to_csv(schemes, csv_path)
    if not csv_saved:
        logger.error("Pipeline failed at CSV generation.")
        return False

    # Step 6: Complete and update history and performance metrics
    hist_dir = os.path.normpath(os.path.join(base_dir, "..", "historical"))
    update_historical_nav(schemes, base_dir=hist_dir, recalculate_perf=True)

    # Cleanup temporary files if any
    if os.path.exists("SIF_NAVAll.txt"):
        try:
            os.remove("SIF_NAVAll.txt")
        except OSError:
            pass

    logger.info("Pipeline completed successfully.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Fetch and sync latest AMFI SIF NAV data.")
    parser.add_argument("--force", action="store_true", help="Force update even if no newer dates detected.")
    parser.add_argument("--date", type=str, default=None, help="Specific snapshot date (YYYYMMDD or YYYY-MM-DD).")
    args = parser.parse_args()

    sync_sif_nav(
        force=args.force,
        target_date_str=args.date,
    )


if __name__ == "__main__":
    main()
