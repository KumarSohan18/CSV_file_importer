from fastapi import APIRouter, UploadFile, File, HTTPException
from app.tasks.import_tasks import import_products_task
from app.config import settings
import os
import uuid
import base64

router = APIRouter()

@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    """Upload CSV file for processing"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Read file content
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Encode file content as base64 to pass through Redis/Celery
    # On Render, web service and worker are separate containers with no shared filesystem
    file_content_b64 = base64.b64encode(content).decode('utf-8')
    
    # Start Celery task with file content instead of file path
    task = import_products_task.delay(file_content_b64, task_id)
    
    return {
        "task_id": task.id,
        "message": "Upload started",
        "status": "processing"
    }

