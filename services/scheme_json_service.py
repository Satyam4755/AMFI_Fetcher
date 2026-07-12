import os
import json
import logging

logger = logging.getLogger(__name__)

def save_scheme_to_json(sif_id, scheme_dict, base_dir="data/sif/scheme/details"):
    """
    Saves the deeply nested scheme dictionary into a single JSON file.
    The filename is exactly as passed in `sif_id` (assumed to be the normalized SEBI code).
    """
    if not scheme_dict:
        logger.warning(f"No scheme data provided for SIF {sif_id}.")
        return False
        
    try:
        os.makedirs(base_dir, exist_ok=True)
        
        # The provided sif_id is expected to be the fully formatted, normalized SEBI code.
        filename = f"{sif_id}.json"
        filepath = os.path.join(base_dir, filename)
        
        # Write to JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(scheme_dict, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Successfully saved scheme JSON to: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving scheme JSON for SIF {sif_id}: {e}")
        return False
