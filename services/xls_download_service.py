import os
import re
import urllib.parse
import urllib.request
import urllib.error
import logging

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Connection": "close",
}

def _fetch_url(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = response.read()
                if data and b"404 - File" not in data and len(data) > 100:
                    return data
    except Exception as e:
        logger.debug(f"Failed to fetch {url}: {e}")
    return None

def download_xls(summary_url: str) -> str | None:
    """
    Downloads an AMFI Summary document (XLS, XML, etc.) from the given URL and saves it locally.
    Generates URL candidate variations (e.g., uppercase S-X vs lowercase s_x, .xml vs .xls)
    if the primary URL fails or returns 404.
    Returns the absolute path to the downloaded file, or None if it fails.
    """
    if not summary_url or not isinstance(summary_url, str):
        logger.error("Invalid URL provided for document download.")
        return None

    # Candidate URLs to try in priority order (prefer XML formats first for stability and speed)
    urls_to_try = []

    # If URL contains SSD_s_X or SSD_S-X, generate variations
    m = re.search(r"SSD_([sS][-_]?\d+)\.(xls|xml)", summary_url)
    if m:
        raw_id = m.group(1)
        num_m = re.search(r"\d+", raw_id)
        if num_m:
            num = num_m.group(0)
            base_url = summary_url[:summary_url.rfind("/")]
            urls_to_try = [
                f"{base_url}/SSD_S-{num}.xml",
                f"{base_url}/SSD_s_{num}.xml",
                f"{base_url}/SSD_S-{num}.xls",
                f"{base_url}/SSD_s_{num}.xls",
            ]

    if summary_url not in urls_to_try:
        urls_to_try.append(summary_url)

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp", "documents")
    os.makedirs(output_dir, exist_ok=True)

    for url in urls_to_try:
        filename = os.path.basename(urllib.parse.urlparse(url).path)
        if not filename:
            continue
        file_path = os.path.join(output_dir, filename)

        if os.path.exists(file_path) and os.path.getsize(file_path) > 100:
            with open(file_path, "rb") as f:
                header = f.read(100)
            if b"404 - File" not in header:
                logger.info(f"Using locally cached document: {file_path}")
                return file_path

        data = _fetch_url(url)
        if data:
            with open(file_path, "wb") as f:
                f.write(data)
            logger.info(f"Successfully downloaded document from {url} to: {file_path}")
            return file_path

    logger.warning(f"Could not download document for {summary_url} after trying {len(urls_to_try)} variations.")
    return None

