def extract_schemes(data):
    """Converts the nested AMFI JSON data into a flat list of schemes."""
    if not data:
        return None
        
    print("Extracting schemes into a list...")
    all_schemes = []
    
    try:
        for data_item in data.get("data", []):
            for category in data_item.get("categories", []):
                for group in category.get("groups", []):
                    for scheme in group.get("schemes", []):
                        all_schemes.append(scheme)
                        
        print(f"Successfully extracted {len(all_schemes)} schemes.")
        return all_schemes
    except Exception as e:
        print(f"Error during parsing: {e}")
        return None
