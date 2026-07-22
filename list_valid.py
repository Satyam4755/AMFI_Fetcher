import json
import glob
import os

files = glob.glob("/Users/smritisoni/Desktop/My_SIF/AMFI_Fetcher_clone/data/sif/scheme/details/*.json")
for f in files:
    if "temp_" not in f:
        with open(f, 'r') as fp:
            data = json.load(fp)
        print(data.get('fund_name'))

