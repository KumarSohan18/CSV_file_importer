from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api import products, upload, webhooks, progress
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create tables (with error handling)
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")
    logger.error("Please ensure PostgreSQL is running and the database exists.")
    logger.error("Run 'python create_db.py' to create the database.")

app = FastAPI(title="Product Importer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(progress.router, prefix="/api/progress", tags=["progress"])

@app.get("/")
async def root():
    return {"message": "Product Importer API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

