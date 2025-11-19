from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.tasks.import_tasks import import_products_task
from app.config import settings
from app.database import get_db, engine
from app.models import FileUpload
from sqlalchemy.orm import Session
import os
import uuid

router = APIRouter()

@router.post("/")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload CSV file for processing"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read file content
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    file_id = uuid.uuid4()
    
    # Store file content in PostgreSQL using raw connection for large files
    # This avoids SQLAlchemy ORM overhead and connection timeouts for large blobs
    try:
        raw_conn = engine.raw_connection()
        try:
            cursor = raw_conn.cursor()
            # Use parameterized query with binary data
            cursor.execute(
                """
                INSERT INTO file_uploads (id, task_id, file_content, created_at)
                VALUES (%s, %s, %s, NOW())
                """,
                (file_id, task_id, content)
            )
            raw_conn.commit()
            cursor.close()
        finally:
            raw_conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store file: {str(e)}")
    
    # Start Celery task with task_id - worker will retrieve file from database
    task = import_products_task.delay(task_id)
    
    return {
        "task_id": task.id,
        "message": "Upload started",
        "status": "processing"
    }

