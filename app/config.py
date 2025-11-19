from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:admin123@localhost/productdb")
    
    # Redis/Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
    CELERY_RESULT_BACKEND: str = os.getenv("REDIS_URL", os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"))
    
    # App
    SECRET_KEY: str = "your-secret-key-change-in-production"
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/tmp/uploads") 
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500MB
    
    class Config:
        env_file = ".env"

settings = Settings()

