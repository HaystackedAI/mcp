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

CLASSIFICATION CATEGORIES
  ├── customer_invoice → invoice table
  ├── vendor_bill → invoice table
  ├── payment_voucher → receipt table
  ├── sales_receipt → receipt table
  ├── bank_statement → bankstatement table
  ├── creditcard_statement → bankstatement table
  └── unknown → log metadata only



How do multiple systems reliably call the same document-processing capabilities without duplicating logic?
