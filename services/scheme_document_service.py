import requests
import logging

logger = logging.getLogger(__name__)

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
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        json_data = response.json()
        data_list = json_data.get("data", [])
        
        if not data_list or len(data_list) == 0:
            logger.info(f"No document information available for scheme_id={scheme_id}.")
            return None
            
        doc_info = data_list[0]
        
        result = {
            "scheme_id": doc_info.get("schemeId", scheme_id),
            "info_pdf_url": doc_info.get("infoDocumentUrl", ""),
            "summary_pdf_url": doc_info.get("summaryPdfUrl", ""),
            "summary_xls_url": doc_info.get("summaryXlsUrl", ""),
            "summary_xml_url": doc_info.get("summaryXmlUrl", "")
        }
        
        logger.info(f"Successfully fetched documents for scheme_id={scheme_id}.")
        return result
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while fetching documents for scheme_id={scheme_id}.")
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error {e.response.status_code} fetching documents for scheme_id={scheme_id}.")
    except requests.exceptions.JSONDecodeError:
        logger.error(f"Invalid JSON received for scheme_id={scheme_id}.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching documents for scheme_id={scheme_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching documents for scheme_id={scheme_id}: {e}")
        
    return None
