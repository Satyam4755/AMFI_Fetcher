import logging
import re

logger = logging.getLogger(__name__)

def build_composite_mapping(rows: list[dict]) -> dict:
    """
    Converts parsed Scheme Summary XLS rows into a composite mapping structure.
    Extracts SEBI Code, AMFI Codes, and ISINs using robust regular expressions.
    """
    result = {
        "sebi_code": None,
        "amfi_mapping": [],
        "isin_mapping": []
    }
    
    if not rows:
        logger.warning("Empty rows provided to build_composite_mapping.")
        return result
        
    sebi_code = None
    amfi_text = ""
    isin_text = ""
    
    for row in rows:
        doc_key = row.get("SCHEME SUMMARY DOCUMENT")
        if not doc_key or not isinstance(doc_key, str):
            continue
            
        doc_key = doc_key.strip()
        
        # Dynamically locate the value column (ignoring the identifier columns)
        val = None
        for k, v in row.items():
            if k not in ["Fields", "SCHEME SUMMARY DOCUMENT"] and v is not None:
                val = str(v).strip()
                break
                
        if not val:
            continue
            
        if doc_key == "SEBI Codes":
            sebi_code = val
        elif doc_key == "AMFI Codes (To be phased out)":
            amfi_text = val
        elif doc_key == "ISINs":
            isin_text = val

    if sebi_code:
        result["sebi_code"] = sebi_code
        
        # Process AMFI mappings using regex to find all occurrences of "SIF-" followed by digits
        amfi_matches = re.findall(r"SIF-\d+", amfi_text)
        
        # Remove duplicates while preserving order
        unique_amfi_codes = list(dict.fromkeys(amfi_matches))
        
        for code in unique_amfi_codes:
            result["amfi_mapping"].append({
                "sebi_code": sebi_code,
                "amfi_code": code
            })
                
        # Process ISIN mappings using regex to find "INF" followed by alphanumeric characters
        isin_matches = re.findall(r"INF[a-zA-Z0-9]+", isin_text)
        
        # Remove duplicates while preserving order
        unique_isins = list(dict.fromkeys(isin_matches))
        
        for isin in unique_isins:
            result["isin_mapping"].append({
                "sebi_code": sebi_code,
                "isin": isin
            })
                
    else:
        logger.warning("No SEBI Code found in the provided rows.")
        
    logger.info(f"Built composite mapping: {1 if sebi_code else 0} SEBI code, {len(result['amfi_mapping'])} AMFI mappings, {len(result['isin_mapping'])} ISIN mappings.")
    return result
