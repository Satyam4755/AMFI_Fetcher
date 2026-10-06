import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Connection": "close",
}

def get_scheme_documents(scheme_id: str) -> dict | None:
    """
    Fetches the document URLs for a given AMFI Scheme.
    Returns a dictionary of URLs or None if unavailable/errors occur.
    """
    if not scheme_id:
        logger.error("No scheme_id provided.")
        return None
        
    url = f"https://www.amfiindia.com/api/sif-schemes/{scheme_id}/documents"
    
    try:
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                json_data = json.loads(resp.read().decode("utf-8"))
                data_list = json_data.get("data", [])
                if not data_list:
                    return None
                doc_info = data_list[0]
                return {
                    "scheme_id": doc_info.get("schemeId", scheme_id),
                    "info_pdf_url": doc_info.get("infoDocumentUrl", ""),
                    "summary_pdf_url": doc_info.get("summaryPdfUrl", ""),
                    "summary_xls_url": doc_info.get("summaryXlsUrl", ""),
                    "summary_xml_url": doc_info.get("summaryXmlUrl", "")
                }
    except Exception as e:
        logger.warning(f"Error fetching documents for scheme_id={scheme_id}: {e}")
        
    return None
