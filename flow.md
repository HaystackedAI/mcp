UPLOAD
  ↓
DETECT TYPE
  ↓
CSV/TXT → parse → LLM → classify → store
IMAGE → OCR → LLM → classify → store
PDF
  ├── text PDF → extract → LLM → classify → store
  └── image PDF → render pages → OCR → LLM → classify → store
  ↓
ROUTING + RULES



How do multiple systems reliably call the same document-processing capabilities without duplicating logic?