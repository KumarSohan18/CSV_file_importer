from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import sys

# Convert postgresql:// to postgresql+psycopg:// for psycopg3 (Python 3.13 compatible)
# Only convert if psycopg3 is available (Python 3.13+), otherwise use psycopg2
database_url = settings.DATABASE_URL
if database_url.startswith('postgresql://') and '+psycopg' not in database_url:
    # Check if Python 3.13+ or if psycopg3 is installed
    if sys.version_info >= (3, 13):
        try:
            import psycopg
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        except ImportError:
            pass  # Fall back to psycopg2

# Optimize engine for bulk operations and large file uploads
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  # Disable SQL logging for performance
    connect_args={
        "connect_timeout": 60,  # 60 second connection timeout
        "options": "-c statement_timeout=300000"  # 5 minute statement timeout for large inserts
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

