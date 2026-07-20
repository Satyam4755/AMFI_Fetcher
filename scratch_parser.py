import re
import json

def get_canonical_traits(text):
    text_lower = text.lower()
    
    # Plan type
    plan = "regular"
    if "direct" in text_lower or "dir" in text_lower.split():
        plan = "direct"
        
    # Option type
    option = "growth"
    if any(k in text_lower for k in ["idcw", "dividend", "div", "payout", "reinvestment", "re-investment", "transfer"]):
        option = "idcw"
        
    # Subtype for IDCW
    subtype = "unknown"
    if option == "idcw":
        if "reinvest" in text_lower:
            subtype = "reinvestment"
        elif "transfer" in text_lower:
            subtype = "transfer"
        elif "payout" in text_lower:
            subtype = "payout"
            
    return {"plan": plan, "option": option, "subtype": subtype if option == "idcw" else None}

def tokenize_section(text, is_amfi=False, is_isin=False):
    if not text: return []
    text = str(text)
    
    # Pre-process: insert newlines before known codes if they don't have them
    if is_isin:
        text = re.sub(r'(?<!\n)(INF[A-Z0-9]{9})', r'\n\1', text, flags=re.IGNORECASE)
    if is_amfi:
        text = re.sub(r'(?<!\n)((?:SIF|S)[-\s]*\d+)(?=\s|$)', r'\n\1', text, flags=re.IGNORECASE)
    
    # Split by common delimiters: newlines, multiple spaces, commas
    # Wait, some names contain commas (e.g. "Growth, Payout")
    # Actually, newlines and bullets are the best primary splitters.
    # We should split by newline, bullet character, or commas if they separate distinct items.
    
    # Normalize bullet points and tabs to newlines
    text = re.sub(r'[\u2022\u25E6\u2023\u25B8\u25B9\u2043\u2219\t]+', '\n', text)
    
    # Also if there are multiple spaces, they often indicate a new column
    text = re.sub(r'\s{3,}', '\n', text)
    
    lines = []
    for line in text.split('\n'):
        # Further split by commas if it seems like a list? 
        # For now, let's just stick to newline splitting as it handles most tables.
        clean_line = line.strip().strip('-–,.')
        if clean_line:
            lines.append(clean_line)
            
    return lines

print(tokenize_section("Growth SIF-35 \n Direct Growth SIF-36", is_amfi=True))
print(get_canonical_traits("Direct Plan - IDCW Payout"))
