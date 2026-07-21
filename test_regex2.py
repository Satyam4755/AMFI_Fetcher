import re

text = "Regular Plan - SIF-100, Direct Plan - SIF-101, Regular Plan - SIF-102"
if ',' in text and '\n' not in text:
    text = text.replace(',', '\n')
elif ',' in text:
    text = re.sub(r',\s*(?=[a-zA-Z])', '\n', text)

text = re.sub(r'(?<!\n)(Regular Plan|Direct Plan|Regular|Direct)(?=\s|\-)', r'\n\1', text, flags=re.IGNORECASE)
text = re.sub(r'(?<!\n)(INF[A-Z0-9]{9})', r'\n\1', text, flags=re.IGNORECASE)
text = re.sub(r'(?<!\n)((?:SIF|S)[-\s]*\d+)(?=\s|$)', r'\n\1', text, flags=re.IGNORECASE)

print(repr(text))
