import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

class Config:
    # Application security
    SECRET_KEY = os.getenv("SECRET_KEY", "returnity-mca-default-secret-key-2026")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

    # Database configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "returnity_db")

    # Uploads settings
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))  # 5 MB
    UPLOAD_FOLDER = BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads/items")
    EVIDENCE_FOLDER = BASE_DIR / os.getenv("EVIDENCE_FOLDER", "uploads/evidence")

    # Allowed extensions
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    ALLOWED_EVIDENCE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "pdf"}

    # Session settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds

    # Initial admin settings
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Returnity Administrator")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@returnity.org")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "AdminReturnity2026!")
    ADMIN_PHONE = os.getenv("ADMIN_PHONE", "9876543210")
