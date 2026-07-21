import json
import csv
import sys

def analyze_json(path):
    print(f"\n--- {path} ---")
    try:
        with open(path) as f:
            data = json.load(f)
            if isinstance(data, list):
                print(f"List of length {len(data)}")
                if data:
                    print("Keys:", list(data[0].keys()) if isinstance(data[0], dict) else "Primitive")
                    print("Sample item:", json.dumps(data[0], indent=2))
            else:
                print("Keys:", list(data.keys()))
                for k, v in data.items():
                    print(f"  {k} ({type(v).__name__}): {str(v)[:100]}")
    except Exception as e:
        print("Error:", e)

def analyze_csv(path):
    print(f"\n--- {path} ---")
    try:
        with open(path) as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            row1 = next(reader, None)
            print("Headers:", headers)
            print("Row 1:", row1)
    except Exception as e:
        print("Error:", e)

analyze_csv("data/sif_scheme.csv")
analyze_json("data/sif/scheme/details/s_13.json")
analyze_json("data/sif/scheme/performance/sif_40.json")
analyze_csv("data/sif/scheme/nav/historical/sif_61.csv")
