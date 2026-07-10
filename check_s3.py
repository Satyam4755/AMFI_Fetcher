import pandas as pd
df = pd.read_excel("/Users/smritisoni/Desktop/AMFI_Fetcher/temp/xls/SSD_S-3.xls")
has_altiva = df.astype(str).apply(lambda x: x.str.contains('altiva', case=False)).any().any()
print("Contains Altiva?", has_altiva)
