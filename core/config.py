import os

class Settings:
    ERP_API = os.getenv("ERP_API")
    BANK_API = os.getenv("BANK_API")
    VENDOR_API = os.getenv("VENDOR_API")
    OCR_API = os.getenv("OCR_API")

settings = Settings()