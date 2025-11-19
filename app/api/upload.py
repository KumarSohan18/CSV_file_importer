from fastapi import APIRouter, UploadFile, File, HTTPException
from app.tasks.import_tasks import import_products_task
from app.config import settings
import os
import uuid
import aiofiles

router = APIRouter()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    """Upload CSV file for processing"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Generate unique task ID and file path
    task_id = str(uuid.uuid4())
    file_path = os.path.join(settings.UPLOAD_DIR, f"{task_id}.csv")
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        await f.write(content)
    
    # Start Celery task
    task = import_products_task.delay(file_path, task_id)
    
    return {
        "task_id": task.id,
        "message": "Upload started",
        "status": "processing"
    }

