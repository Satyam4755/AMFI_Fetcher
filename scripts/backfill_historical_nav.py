import argparse
import csv
import glob
import logging
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.historical_nav_service import (
    clean_nav_value,
    discover_eligible_non_direct_sifs,
    fetch_daily_sif_nav_from_amfi,
    fetch_historical_nav_from_amfi,
    merge_historical_records,
    parse_nav_date,
    read_existing_historical_csv,
    write_historical_nav_csv,
)
from services.aum_service import fetch_latest_sif_aum, merge_aum_into_schemes
from services.performance_service import calculate_performance_metrics

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("HistoricalBackfill")


def run_backfill(
    target_sif_code: str | None = None,
    custom_from_date: str | None = None,
    custom_to_date: str | None = None,
    recalculate_performance: bool = True,
    details_dir: str = "data/sif/scheme/details",
    hist_dir: str = "data/sif/scheme/nav/historical",
    daily_dir: str = "data/sif/scheme/nav/daily",
    gap_start: str = "2026-08-19",
    gap_end: str = "2026-08-31"
) -> dict:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    details_path = os.path.join(project_root, details_dir)
    hist_path = os.path.join(project_root, hist_dir)
    daily_path = os.path.join(project_root, daily_dir)
    perf_path = os.path.join(project_root, "data", "sif", "scheme", "performance")

    os.makedirs(hist_path, exist_ok=True)
    os.makedirs(daily_path, exist_ok=True)
    os.makedirs(perf_path, exist_ok=True)

    logger.info("Step 1: Discovering eligible non-Direct SIF plans...")
    all_eligible = discover_eligible_non_direct_sifs(details_dir=details_path)

    if target_sif_code:
        norm_target = target_sif_code.strip().upper()
        eligible_plans = [p for p in all_eligible if p["sif_code"].upper() == norm_target]
        if not eligible_plans:
            # If not in discovered list, allow targeted backfill if it follows SIF naming
            logger.info(f"Target SIF code '{norm_target}' not found in auto-discovery. Creating ad-hoc target.")
            eligible_plans = [{"sif_code": norm_target, "inception": None, "name": norm_target}]
        logger.info(f"Targeted backfill for specific SIF code: {norm_target}")
    else:
        eligible_plans = all_eligible
        logger.info(f"Discovered {len(eligible_plans)} eligible non-Direct SIF plans.")

    # Record baseline record counts before backfill
    records_before_total = 0
    existing_hist_files = glob.glob(os.path.join(hist_path, "*.csv"))
    for hf in existing_hist_files:
        rows = read_existing_historical_csv(hf)
        records_before_total += len(rows)

    logger.info(f"Baseline total historical NAV records across all files before repair: {records_before_total}")

    # Backfill each eligible non-Direct SIF plan
    logger.info("Step 2: Fetching authoritative historical NAV from AMFI...")
    successful_plans = []
    plans_no_data = []
    records_after_total = 0
    all_dates = []
    missing_gap_repaired_count = 0

    for plan in eligible_plans:
        sif_code = plan["sif_code"]
        inception = plan.get("inception")

        if custom_from_date:
            from_date = custom_from_date.strip()
        else:
            from_date = inception if inception else "2024-01-01"

        to_date = custom_to_date.strip() if custom_to_date else None

        safe_name = sif_code.lower().replace("-", "_")
        csv_file = os.path.join(hist_path, f"{safe_name}.csv")
        existing_rows = read_existing_historical_csv(csv_file)

        logger.info(f"Processing {sif_code} (Range: {from_date} to {to_date or 'latest'})...")
        amfi_rows = fetch_historical_nav_from_amfi(sif_code, from_date=from_date, to_date=to_date)

        if not amfi_rows and not existing_rows:
            plans_no_data.append(sif_code)
            logger.warning(f"No historical NAV records returned by AMFI for {sif_code}")
            continue

        merged = merge_historical_records(existing_rows, amfi_rows)
        if merged:
            write_historical_nav_csv(sif_code, merged, base_dir=hist_path)
            successful_plans.append(sif_code)
            records_after_total += len(merged)

            for r in merged:
                dt, _ = parse_nav_date(r["nav_date"])
                if dt:
                    all_dates.append(dt)
                    if datetime(2026, 8, 19) <= dt <= datetime(2026, 8, 31):
                        missing_gap_repaired_count += 1
        else:
            plans_no_data.append(sif_code)

    # Step 3: Repair missing daily CSV snapshots in 19-Aug-2026 to 31-Aug-2026 (when doing full run)
    daily_repaired_files = []
    if not target_sif_code and gap_start and gap_end:
        logger.info(f"Step 3: Checking and repairing daily CSV snapshots between {gap_start} and {gap_end}...")
        sif_aum_map = {}
        try:
            sif_aum_map, _ = fetch_latest_sif_aum()
        except Exception as e:
            logger.warning(f"Could not fetch latest AUM for daily repair: {e}")

        start_dt = datetime.strptime(gap_start, "%Y-%m-%d")
        end_dt = datetime.strptime(gap_end, "%Y-%m-%d")
        cur_dt = start_dt

        while cur_dt <= end_dt:
            date_iso = cur_dt.strftime("%Y-%m-%d")
            daily_filename = cur_dt.strftime("%Y%m%d") + ".csv"
            daily_file_path = os.path.join(daily_path, daily_filename)

            # Fetch daily snapshot from AMFI
            daily_schemes = fetch_daily_sif_nav_from_amfi(date_iso)
            if daily_schemes:
                if sif_aum_map:
                    daily_schemes = merge_aum_into_schemes(daily_schemes, sif_aum_map)
                else:
                    for s in daily_schemes:
                        s["AUM"] = ""

                fieldnames = ["sif_code", "nav_date", "nav", "AUM"]
                with open(daily_file_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(daily_schemes)

                daily_repaired_files.append(daily_filename)
                logger.info(f"Saved daily snapshot for {date_iso} ({len(daily_schemes)} records) to {daily_filename}")

            cur_dt += timedelta(days=1)

    # Step 4: Recalculate Performance Metrics if requested
    performance_recalculated_count = 0
    if recalculate_performance:
        logger.info("Step 4: Recalculating performance JSON metrics...")
        import pandas as pd
        import json

        csv_files_to_recalc = []
        if target_sif_code:
            target_safe = target_sif_code.strip().lower().replace("-", "_")
            csv_files_to_recalc = glob.glob(os.path.join(hist_path, f"{target_safe}.csv"))
        else:
            csv_files_to_recalc = glob.glob(os.path.join(hist_path, "*.csv"))

        for file_path in csv_files_to_recalc:
            try:
                df = pd.read_csv(file_path)
                if df.empty:
                    continue
                metrics = calculate_performance_metrics(df)
                if metrics:
                    sif_code_internal = metrics.get("sif_code")
                    safe_name = sif_code_internal.replace("-", "_").lower()
                    out_path = os.path.join(perf_path, f"{safe_name}.json")
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(metrics, f, indent=4)
                    performance_recalculated_count += 1
            except Exception as e:
                logger.error(f"Error recalculating performance for {file_path}: {e}")

        logger.info(f"Performance metrics successfully recalculated for {performance_recalculated_count} funds.")

    min_date_str = min(all_dates).strftime("%d-%b-%Y") if all_dates else "N/A"
    max_date_str = max(all_dates).strftime("%d-%b-%Y") if all_dates else "N/A"

    report = {
        "eligible_plans_count": len(eligible_plans),
        "plans_backfilled_count": len(successful_plans),
        "plans_no_data": plans_no_data,
        "earliest_nav_date": min_date_str,
        "latest_nav_date": max_date_str,
        "records_before": records_before_total,
        "records_after": records_after_total,
        "gap_records_repaired": missing_gap_repaired_count,
        "daily_files_repaired": daily_repaired_files,
        "performance_files_recalculated": performance_recalculated_count
    }

    logger.info("=== Backfill Summary ===")
    logger.info(f"Target SIF Code: {target_sif_code or 'ALL'}")
    logger.info(f"Eligible Non-Direct Plans: {report['eligible_plans_count']}")
    logger.info(f"Plans Backfilled: {report['plans_backfilled_count']}")
    logger.info(f"Date Range: {report['earliest_nav_date']} to {report['latest_nav_date']}")
    logger.info(f"NAV Records Before vs After: {report['records_before']} -> {report['records_after']}")
    logger.info(f"19-Aug to 31-Aug Gap Records Repaired: {report['gap_records_repaired']}")
    logger.info(f"Daily Snapshot CSVs Repaired: {len(report['daily_files_repaired'])}")
    logger.info(f"Performance JSONs Recalculated: {report['performance_files_recalculated']}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Backfill historical SIF NAV dataset from AMFI API.")
    parser.add_argument("--sif-code", type=str, default="", help="Optional specific SIF code to backfill (e.g. SIF-13)")
    parser.add_argument("--from-date", type=str, default="", help="Optional start date for historical recovery (YYYY-MM-DD or dd-MMM-yyyy)")
    parser.add_argument("--to-date", type=str, default="", help="Optional end date for historical recovery (YYYY-MM-DD or dd-MMM-yyyy)")
    parser.add_argument(
        "--no-performance",
        action="store_true",
        help="Skip performance JSON recalculation after backfill"
    )

    args = parser.parse_args()

    sif_code = args.sif_code if args.sif_code.strip() else None
    from_date = args.from_date if args.from_date.strip() else None
    to_date = args.to_date if args.to_date.strip() else None
    recalc_perf = not args.no_performance

    run_backfill(
        target_sif_code=sif_code,
        custom_from_date=from_date,
        custom_to_date=to_date,
        recalculate_performance=recalc_perf
    )


if __name__ == "__main__":
    main()
