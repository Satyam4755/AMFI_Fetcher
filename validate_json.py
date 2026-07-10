import json
import glob
import os

json_dir = "data/sif/schemes"
files = glob.glob(os.path.join(json_dir, "*.json"))

total_schemes = len(files)
total_populated = 0
total_missing = 0

def count_fields(d):
    global total_populated, total_missing
    if isinstance(d, dict):
        for k, v in d.items():
            if v is None or v == [] or v == {}:
                total_missing += 1
            else:
                total_populated += 1
                if isinstance(v, dict) or isinstance(v, list):
                    count_fields(v)
    elif isinstance(d, list):
        for item in d:
            count_fields(item)

for file in files:
    with open(file, 'r') as f:
        data = json.load(f)
        count_fields(data)

print("Validation Summary:")
print(f"Schemes Processed/JSON Files Generated: {total_schemes}")
print(f"Populated Fields Count: {total_populated}")
print(f"Missing Fields Count: {total_missing}")

# Check sif_1.json specifically
sif1 = os.path.join(json_dir, "sif_1.json")
if os.path.exists(sif1):
    with open(sif1, 'r') as f:
        data = json.load(f)
        populated = sum(1 for v in data.values() if v is not None and v != [] and v != {})
        print(f"\nsif_1.json exists and has {populated} top-level populated fields.")
else:
    print("\nsif_1.json does not exist yet.")
