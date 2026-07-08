import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.xls_download_service import download_xls

url = "https://portal.amfiindia.com/spages/SSD_S-3.xls"

file_path = download_xls(url)

print(file_path)