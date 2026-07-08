import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scheme_document_service import get_scheme_documents

result = get_scheme_documents("S-3")

print(result)