import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.heatmap_service import generate_all_heatmaps

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("HeatmapGenerator")


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    historical_dir = os.path.join(project_root, "data", "sif", "scheme", "nav", "historical")
    heatmap_dir = os.path.join(project_root, "data", "sif", "scheme", "heatMap")

    logger.info("Starting monthly performance heatmap generation...")
    result = generate_all_heatmaps(historical_dir, heatmap_dir)
    logger.info(
        f"Heatmap generation complete. Processed {result.get('schemes_processed', 0)} schemes across years: {result.get('years_generated', [])}"
    )


if __name__ == "__main__":
    main()
