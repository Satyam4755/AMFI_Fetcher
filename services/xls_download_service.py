import os
import urllib.parse
import requests
import logging

logger = logging.getLogger(__name__)

def download_xls(summary_xls_url: str) -> str | None:
    """
    Downloads a Summary XLS file from the given URL and saves it locally.
    Returns the absolute path to the downloaded file, or None if it fails.
    """
    if not summary_xls_url or not isinstance(summary_xls_url, str):
        logger.error("Invalid URL provided for XLS download.")
        return None
        
    parsed_url = urllib.parse.urlparse(summary_xls_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        logger.error(f"Invalid URL format: {summary_xls_url}")
        return None
        
    filename = os.path.basename(parsed_url.path)
    if not filename:
        logger.error(f"Could not extract filename from URL: {summary_xls_url}")
        return None
        
    # Build absolute path to temp/xls relative to project root
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp", "xls")
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, filename)
    
    try:
        # Stream the download
        with requests.get(summary_xls_url, stream=True, timeout=15) as response:
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' in content_type or 'text/plain' in content_type:
                logger.info(f"HTML/Text file received, downloading anyway to attempt parsing as HTML table. URL: {summary_xls_url}")
                # We do not return None here anymore
                
            iterator = response.iter_content(chunk_size=8192)
            try:
                first_chunk = next(iterator)
            except StopIteration:
                first_chunk = b""
                
            if not first_chunk:
                logger.warning(f"Invalid XLS received from AMFI. Skipping download. (Empty content) URL: {summary_xls_url}")
                return None
                
            header = first_chunk[:50].lstrip().lower()
            if header.startswith(b"<!doctype") or header.startswith(b"<html"):
                logger.info(f"HTML body detected in XLS, downloading anyway. URL: {summary_xls_url}")
                # We do not return None here anymore
                
            with open(file_path, "wb") as f:
                f.write(first_chunk)
                for chunk in iterator:
                    if chunk:
                        f.write(chunk)
                        
        logger.info(f"Successfully downloaded XLS to: {file_path}")
        return file_path
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while downloading XLS from: {summary_xls_url}")
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            logger.warning(f"Summary XLS not found (404). Skipping. URL: {summary_xls_url}")
        else:
            status_code = e.response.status_code if e.response is not None else "Unknown"
            logger.error(f"HTTP error {status_code} downloading XLS from: {summary_xls_url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error downloading XLS from: {summary_xls_url} - {e}")
    except IOError as e:
        logger.error(f"File IO error while saving XLS to {file_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error downloading XLS: {e}")
        
    return None
