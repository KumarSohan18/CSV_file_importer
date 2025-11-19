from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.tasks.import_tasks import import_products_task
from app.config import settings
from app.database import get_db
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
    
    # Store file content in PostgreSQL (Redis is too small for large files)
    # On Render, web service and worker are separate containers, so we use database
    file_upload = FileUpload(
        task_id=task_id,
        file_content=content
    )
    db.add(file_upload)
    db.commit()
    
    # Start Celery task with task_id - worker will retrieve file from database
    task = import_products_task.delay(task_id)
    
    return {
        "task_id": task.id,
        "message": "Upload started",
        "status": "processing"
    }

