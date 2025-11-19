from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from celery_app import celery_app
import json
import asyncio

router = APIRouter()

@router.get("/{task_id}")
async def get_progress(task_id: str):
    """SSE endpoint for real-time progress updates"""
    async def event_generator():
        last_progress = -1
        
        while True:
            try:
                task = celery_app.AsyncResult(task_id)
                
                if task.state == 'PENDING':
                    yield f"data: {json.dumps({'progress': 0, 'status': 'pending', 'message': 'Waiting to start...'})}\n\n"
                elif task.state == 'PROGRESS':
                    meta = task.info or {}
                    progress = meta.get('progress', 0)
                    message = meta.get('message', '')
                    
                    # Send update if progress changed or every 0.5s for real-time feel
                    if progress != last_progress or True:  # Always send for smoother updates
                        payload = {
                            'progress': progress,
                            'status': 'processing',
                            'message': message,
                            'rows_processed': meta.get('rows_processed', 0),
                            'rows_total': meta.get('rows_total'),
                            'products_processed': meta.get('products_processed', 0),
                            'processing_speed': meta.get('processing_speed', 0),
                            'eta_seconds': meta.get('eta_seconds'),
                            'error_count': meta.get('error_count', 0)
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                        last_progress = progress
                elif task.state == 'SUCCESS':
                    result = task.result or {}
                    meta = task.info or {}
                    payload = {
                        'progress': 100,
                        'status': 'success',
                        'message': meta.get('message', 'Import complete'),
                        'rows_processed': meta.get('rows_processed', result.get('total', 0)),
                        'rows_total': meta.get('rows_total', result.get('total', 0)),
                        'products_processed': meta.get('products_processed', result.get('processed', 0)),
                        'processing_speed': meta.get('processing_speed', result.get('processing_speed', 0)),
                        'eta_seconds': 0,
                        'error_count': meta.get('error_count', result.get('error_count', 0)),
                        'result': result
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    break
                elif task.state == 'FAILURE':
                    meta = task.info or {}
                    payload = {
                        'progress': 0,
                        'status': 'failure',
                        'message': meta.get('message', str(task.info) if task.info else 'Import failed'),
                        'rows_processed': meta.get('rows_processed', 0),
                        'error_count': meta.get('error_count', 0)
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    break
                
                await asyncio.sleep(0.3)  # More frequent updates for smoother progress bar
            except Exception as e:
                yield f"data: {json.dumps({'progress': 0, 'status': 'failure', 'message': f'Error checking progress: {str(e)}'})}\n\n"
                break
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

