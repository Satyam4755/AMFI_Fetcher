import pandas as pd
import warnings
warnings.filterwarnings('ignore')

try:
    tables = pd.read_html("https://portal.amfiindia.com/spages/SSD_S-4.xls")
    print(f"Found {len(tables)} tables")
    for i, t in enumerate(tables):
        print(f"Table {i} shape: {t.shape}")
        if i == 0:
            print(t.head(10))
except Exception as e:
    print(f"Failed: {e}")
