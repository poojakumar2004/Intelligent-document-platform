import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent
UPLOAD_DIR = os.getenv('UPLOAD_DIR', str(PROJECT_ROOT / 'uploads'))
DATABASE_PATH = os.getenv('DATABASE_PATH', str(PROJECT_ROOT / 'documents.db'))

class Settings:
    PROJECT_NAME: str = 'Intelligent Document Extraction, Validation & API Platform'
    VERSION: str = '1.0.0'
    API_V1_STR: str = '/api/v1'
    
    # Upload and file validation limits
    UPLOAD_DIR: str = UPLOAD_DIR
    DATABASE_PATH: str = DATABASE_PATH
    MAX_PAGES: int = int(os.getenv('MAX_PAGES', '3'))
    MAX_FILE_SIZE_BYTES: int = int(os.getenv('MAX_FILE_SIZE_BYTES', str(10 * 1024 * 1024))) # 10MB
    ALLOWED_EXTENSIONS: set = {'pdf', 'jpg', 'jpeg', 'png'}
    ALLOWED_MIME_TYPES: set = {
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/jpg'
    }
    
    # Financial tolerance for rounding (0.05 covers standard half-cent/half-paisa rounding)
    FINANCIAL_TOLERANCE: float = float(os.getenv('FINANCIAL_TOLERANCE', '0.05'))
    
    # OCR and AI Provider keys
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
    OCR_SPACE_API_KEY: str = os.getenv('OCR_SPACE_API_KEY', 'helloworld')

settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
