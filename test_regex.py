import re

text = "SIF-100, SIF-101, SIF-102"
text = re.sub(r'(?<!\n)((?:SIF|S)[-\s]*\d+)(?=\s|$)', r'\n\1', text, flags=re.IGNORECASE)
print(repr(text))
