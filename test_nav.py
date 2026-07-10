import pandas as pd
import glob
nav_dir = "data/sif/nav"
csv_files = glob.glob(f"{nav_dir}/????-??-??.csv")
latest_csv_path = sorted(csv_files)[-1]
df = pd.read_csv(latest_csv_path)
sif_codes = df['sif_code'].dropna().unique().tolist()
unique_sifs = [str(code).replace("SIF-", "") for code in sif_codes]
print(sorted([int(float(x)) for x in unique_sifs]))
