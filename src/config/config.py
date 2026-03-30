import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 🕵️ Extreme Stabilization: Hard-coded master keys to prevent .env loading mismatches
    SECRET_KEY = os.getenv('SECRET_KEY', "twin-sync-master-static-99b8f2d3e4f5")
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', "jwt-static-hardened-twin-secret-77x3y2z1")
    
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 Hours for local stability
    JWT_TOKEN_LOCATION = ['headers']
    JWT_COOKIE_CSRF_PROTECT = False # Solve the 422 on POST/Chat for local dev
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    
    # Database: SQLite for Native
    DB_URL = os.getenv('DATABASE_URL')
    NATIVE_MODE = not DB_URL or 'postgresql' not in DB_URL
    SQLALCHEMY_DATABASE_URI = DB_URL if DB_URL else 'sqlite:///digital-twins.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 🔄 Real-time Sync Support
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    SOCKETIO_REDIS_URL = REDIS_URL if not NATIVE_MODE else None # Forced None for Native Mode reliability
    
    # ⚙️ Celery & Background Tasks
    broker_url = os.getenv('CELERY_BROKER_URL', REDIS_URL) if not NATIVE_MODE else None
    result_backend = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL) if not NATIVE_MODE else None

    
    # 🤖 Live AI System
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')  # Primary: LLaMA 3 via Groq
    
    # 📧 Email Sync Credentials
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASS = os.getenv('SMTP_PASS', '')
    
    # 🧠 ML Model Analytics
    MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_models')
    
    # 🛡️ Performance & Security
    CACHE_TYPE = "SimpleCache"
    RATELIMIT_STORAGE_URL = "memory://"
