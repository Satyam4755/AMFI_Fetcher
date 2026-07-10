import os
import json
import logging

logger = logging.getLogger(__name__)

def save_scheme_to_json(sif_id, scheme_dict, base_dir="data/sif/schemes"):
    """
    Saves the deeply nested scheme dictionary into a single JSON file.
    The filename is formatted as sif_{sif_id}.json.
    """
    if not scheme_dict:
        logger.warning(f"No scheme data provided for SIF {sif_id}.")
        return False
        
    try:
        os.makedirs(base_dir, exist_ok=True)
        
        # Format the filename to match sif_120.json (from SIF-120 or just 120)
        sif_id_str = str(sif_id).lower()
        if sif_id_str.startswith("sif-"):
            safe_name = sif_id_str.replace("-", "_")
        elif sif_id_str.startswith("sif_"):
            safe_name = sif_id_str
        else:
            safe_name = f"sif_{sif_id_str}"
            
        filename = f"{safe_name}.json"
        filepath = os.path.join(base_dir, filename)
        
        # Write to JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(scheme_dict, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Successfully saved scheme JSON to: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving scheme JSON for SIF {sif_id}: {e}")
        return False
