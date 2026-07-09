import sys
import subprocess
from pathlib import Path

def main():
    print("Starting Full NAV Update Pipeline...")
    
    # Resolve the base directory
    base_dir = Path(__file__).resolve().parent.parent
    
    # Define script paths
    fetch_script = base_dir / "scripts" / "fetch_sif_nav.py"
    import_script = base_dir / "scripts" / "import_sif_csv.py"
    
    try:
        # Step 1: Fetch Data
        print(f"\n--- Running {fetch_script.name} ---")
        subprocess.run([sys.executable, str(fetch_script)], check=True)
        
        # Step 2: Import Data
        print(f"\n--- Running {import_script.name} ---")
        subprocess.run([sys.executable, str(import_script)], check=True)
        
        # Success Summary
        print("\n--- Pipeline Success Summary ---")
        print("• NAV data fetched successfully.")
        print("• CSV generated successfully.")
        print("• SQLite database updated successfully.")
        print("• Full NAV update completed.")
        
    except subprocess.CalledProcessError as e:
        print(f"\nPipeline failed during execution of {e.cmd[1]} with exit code {e.returncode}.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
