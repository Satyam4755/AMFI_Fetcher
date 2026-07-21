import re

text = "SIF-100, SIF-101, SIF-102"
if ',' in text and '\n' not in text:
    text = text.replace(',', '\n')
elif ',' in text:
    text = re.sub(r',\s*(?=[a-zA-Z])', '\n', text)

text = re.sub(r'(?<!\n)(Regular Plan|Direct Plan|Regular|Direct)(?=\s|\-)', r'\n\1', text, flags=re.IGNORECASE)
text = re.sub(r'(?<!\n)(INF[A-Z0-9]{9})', r'\n\1', text, flags=re.IGNORECASE)
# Fix the regex to allow commas or ends or other non-word chars
text = re.sub(r'(?<!\n)((?:SIF|S)[-\s]*\d+)(?=\b|[^a-zA-Z0-9])', r'\n\1', text, flags=re.IGNORECASE)

lines = []
for line in text.split('\n'):
    clean_line = line.strip().strip('-–,.')
    if clean_line:
        lines.append(clean_line)

records = []
current_record = []
for line in lines:
    is_boundary = False
    if re.search(r'^(regular plan|direct plan|regular|direct)\b', line, re.IGNORECASE):
        is_boundary = True
    elif re.search(r'^(INF[A-Z0-9]{9}|(?:SIF|S)[-\s]*\d+)', line, re.IGNORECASE):
        is_boundary = True

    if is_boundary and current_record:
        records.append(" ".join(current_record))
        current_record = []
        
    current_record.append(line)

if current_record:
    records.append(" ".join(current_record))

print(records)
