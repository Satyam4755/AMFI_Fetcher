import os
import glob
import json
import logging
import pandas as pd

from services.performance_service import calculate_performance_metrics

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("PerformanceCalculator")

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    historical_dir = os.path.join(project_root, "data", "sif", "scheme", "nav", "historical")
    perf_dir = os.path.join(project_root, "data", "sif", "scheme", "performance")
    
    os.makedirs(perf_dir, exist_ok=True)
    
    csv_files = glob.glob(os.path.join(historical_dir, "*.csv"))
    if not csv_files:
        logger.warning(f"No historical NAV CSV files found in {historical_dir}")
        return
        
    logger.info(f"Found {len(csv_files)} historical NAV files for performance calculation.")
    
    success_count = 0
    fail_count = 0
    
    for file_path in csv_files:
        sif_code_file = os.path.basename(file_path).replace(".csv", "")
        # Depending on how the file is named, e.g. "sif_1", but the sif_code inside might be "SIF-1"
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                logger.warning(f"File {file_path} is empty. Skipping.")
                fail_count += 1
                continue
                
            metrics = calculate_performance_metrics(df)
            
            if metrics:
                sif_code_internal = metrics.get("sif_code")
                # Using the internal sif_code from the CSV (e.g. SIF-1) for naming, 
                # but let's normalize it to lowercase for consistency (e.g. sif_1.json)
                safe_name = sif_code_internal.replace("-", "_").lower()
                out_path = os.path.join(perf_dir, f"{safe_name}.json")
                
                with open(out_path, "w") as f:
                    json.dump(metrics, f, indent=4)
                    
                success_count += 1
            else:
                logger.warning(f"Failed to calculate metrics for {file_path}. Data might be invalid.")
                fail_count += 1
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            fail_count += 1
            
    logger.info(f"Performance Calculation Complete. Success: {success_count}, Failed: {fail_count}")
    logger.info(f"Output Directory: {perf_dir}")

if __name__ == "__main__":
    main()
