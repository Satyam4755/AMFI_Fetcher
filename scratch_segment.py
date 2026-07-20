import re

def segment_records(text, fund_name):
    if not text: return []
    text = str(text)
    
    # 1. Normalize commas that are used as separators between plans without spaces
    if ',' in text and '\n' not in text:
        text = text.replace(',', '\n')
    elif ',' in text:
        text = re.sub(r',\s*(?=[a-zA-Z])', '\n', text)
        
    # 2. Inject newlines before logical boundaries
    if fund_name:
        fn_escaped = re.escape(fund_name)
        text = re.sub(f'(?i)(?<!\\n)({fn_escaped})', r'\n\1', text)
        
    text = re.sub(r'(?<!\n)(Regular Plan|Direct Plan)(?=\s|\-)', r'\n\1', text, flags=re.IGNORECASE)
    
    # 3. Handle known codes that are appended without space/newline
    text = re.sub(r'(?<!\n)(INF[A-Z0-9]{9})', r'\n\1', text, flags=re.IGNORECASE)
    text = re.sub(r'(?<!\n)((?:SIF|S)[-\s]*\d+)(?=\s|$)', r'\n\1', text, flags=re.IGNORECASE)

    # 4. Normalize bullets to newlines to break sub-items
    text = re.sub(r'[\u2022\u25E6\u2023\u25B8\u25B9\u2043\u2219\uf0b7\t]+', '\n', text)
    
    # 5. Clean up multiple newlines/spaces
    text = re.sub(r'\s{3,}', '\n', text)
    
    lines = []
    for line in text.split('\n'):
        clean_line = line.strip().strip('-–,.')
        clean_line = re.sub(r'^[\d\w]\)[\s\-]+', '', clean_line)
        clean_line = re.sub(r'^\d+\.[\s\-]+', '', clean_line)
        if clean_line:
            lines.append(clean_line)
            
    # Now that we have lines, we can optionally group them if a line doesn't look like a new record?
    # Actually, the user said "Everything before the next occurrence of Arudha... belongs to this record."
    # So if a line does NOT start a new record, it should be appended to the previous record!
    records = []
    current_record = ""
    for line in lines:
        is_boundary = False
        if fund_name and fund_name.lower() in line.lower():
            is_boundary = True
        elif re.search(r'regular plan|direct plan', line, re.IGNORECASE):
            is_boundary = True
            
        if is_boundary and current_record:
            records.append(current_record.strip())
            current_record = line
        else:
            current_record = current_record + " " + line if current_record else line
            
    if current_record:
        records.append(current_record.strip())
        
    return records

print(segment_records("Arudha Equity Long Short Fund-Regular Plan-Growth SIF-62 Arudha Equity Long Short Fund-Regular Plan-Daily IDCW SIF-63", "Arudha Equity Long Short Fund"))
