import logging
import os
import sys

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.aum_service import fetch_latest_sif_aum, update_daily_csv_files

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("SIF_AUM_Updater")


def main():
    logger.info("Starting SIF AUM update pipeline...")
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    daily_nav_dir = os.path.join(project_root, "data", "sif", "scheme", "nav", "daily")
    
    sif_aum_map, metadata = fetch_latest_sif_aum()
    
    if not sif_aum_map:
        logger.error("Failed to fetch SIF AUM data from AMFI. Pipeline aborted.")
        sys.exit(1)
        
    logger.info(
        f"Fetched AUM for FY: {metadata.get('financial_year')} | "
        f"Period: {metadata.get('period')} | "
        f"Total schemes: {len(sif_aum_map)}"
    )
    
    updated_files = update_daily_csv_files(daily_dir=daily_nav_dir, sif_aum_map=sif_aum_map)
    logger.info(f"SIF AUM update completed. Updated {updated_files} daily CSV files.")


if __name__ == "__main__":
    main()
