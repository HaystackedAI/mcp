import os

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


if load_dotenv:
    load_dotenv()


class Settings:
    ERP_API = os.getenv("ERP_API", "")
    BANK_API = os.getenv("BANK_API", "")
    VENDOR_API = os.getenv("VENDOR_API", "")
    OCR_API = os.getenv("OCR_API", "")

    # Public testing defaults (override with env vars when needed).
    VENDOR_SEARCH_URL = os.getenv(
        "VENDOR_SEARCH_URL", "https://jsonplaceholder.typicode.com/users"
    )
    BANK_TRANSACTIONS_URL = os.getenv(
        "BANK_TRANSACTIONS_URL", "https://httpbin.org/anything/transactions"
    )
    OCR_URL = os.getenv("OCR_URL", "https://postman-echo.com/post")


settings = Settings()
