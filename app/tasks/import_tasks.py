from celery import Task
from celery_app import celery_app
from app.database import SessionLocal
from app.models import Product
from app.services.csv_processor import process_csv_chunk
from app.services.webhook_service import trigger_webhooks
import csv
import os
import time
from typing import Dict, Any

class ProgressTask(Task):
    """Custom task class to track progress"""
    _progress = 0
    _status = "pending"
    _message = ""

    def update_progress(self, progress: int, status: str, message: str = "", **kwargs):
        self._progress = progress
        self._status = status
        self._message = message
        meta = {'progress': progress, 'message': message, **kwargs}
        self.update_state(
            state=status,
            meta=meta
        )

@celery_app.task(bind=True, base=ProgressTask)
def import_products_task(self, task_id: str):
    """Process CSV file and import products efficiently for large files"""
    import tempfile
    from app.models import FileUpload
    
    db = SessionLocal()
    total_rows = 0
    processed = 0
    row_count = 0
    errors = []
    start_time = time.time()
    last_update_time = start_time
    last_row_count = 0
    
    # Retrieve file content from PostgreSQL (Redis is too small for large files)
    # On Render, web service and worker are separate containers, so we use database
    file_upload = db.query(FileUpload).filter(FileUpload.task_id == task_id).first()
    if not file_upload:
        raise RuntimeError(f"File upload not found for task_id: {task_id}")
    
    # Handle both regular bytea and large object storage
    if file_upload.large_object_oid:
        # Large object storage - retrieve from PostgreSQL
        from app.database import engine
        import io
        loid = int(file_upload.large_object_oid)
        raw_conn = engine.raw_connection()
        try:
            lo = raw_conn.connection.lobject(loid, 'rb')
            file_content = lo.read()
            lo.close()
        finally:
            raw_conn.close()
    elif file_upload.file_content:
        # Regular bytea storage
        file_content = file_upload.file_content
    else:
        raise RuntimeError("File content is empty - neither bytea nor large object found")
    
    if not file_content or len(file_content) == 0:
        raise RuntimeError("File content is empty")
    
    temp_file = None
    
    try:
        self.update_progress(
            0, 
            "PROGRESS", 
            f"Starting import... File size: {len(file_content):,} bytes",
            rows_processed=0,
            rows_total=None,
            processing_speed=0,
            eta_seconds=None
        )
        
        # Create temp file for processing
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tf:
            tf.write(file_content)
            temp_file = tf.name
        
        # Verify file was written correctly
        if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
            raise RuntimeError(f"Failed to create temp file or file is empty. Temp file: {temp_file}")
        
        # Ultra-fast processing: use very large chunks with COPY
        # COPY is so fast we can process much larger chunks
        chunk_size = 50000  # 50k rows per chunk for maximum COPY efficiency
        
        # Process file in chunks without pre-counting (saves one full file read)
        with open(temp_file, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            chunk = []
            
            # Check if file has headers
            if not reader.fieldnames:
                raise RuntimeError("CSV file has no headers or is empty")
            
            for row in reader:
                row_count += 1
                chunk.append(row)
                
                # Process chunk when it reaches size
                if len(chunk) >= chunk_size:
                    chunk_start = time.time()
                    result = process_csv_chunk(db, chunk, task_id)
                    processed += result['processed']
                    errors.extend(result['errors'])
                    
                    # Commit after each chunk for progress tracking
                    db.commit()
                    
                    # Calculate metrics
                    current_time = time.time()
                    elapsed = current_time - start_time
                    rows_since_last = row_count - last_row_count
                    time_since_last = current_time - last_update_time
                    
                    # Calculate processing speed (rows per second)
                    if time_since_last > 0:
                        current_speed = rows_since_last / time_since_last
                    else:
                        current_speed = row_count / elapsed if elapsed > 0 else 0
                    
                    # Estimate total rows (conservative estimate based on current speed)
                    # For files up to 500k, we estimate based on progress
                    estimated_total = max(row_count, int(row_count * 1.1))  # Add 10% buffer
                    
                    # Calculate ETA
                    remaining_rows = max(0, estimated_total - row_count)
                    eta_seconds = int(remaining_rows / current_speed) if current_speed > 0 else None
                    
                    # Update progress (cap at 95% until we know the actual total)
                    progress = min(int((row_count / estimated_total) * 95), 95)
                    
                    # Format speed
                    speed_str = f"{int(current_speed):,} rows/sec" if current_speed > 0 else "Calculating..."
                    
                    # Format ETA
                    if eta_seconds and eta_seconds > 0:
                        if eta_seconds < 60:
                            eta_str = f"{eta_seconds}s"
                        elif eta_seconds < 3600:
                            eta_str = f"{eta_seconds // 60}m {eta_seconds % 60}s"
                        else:
                            hours = eta_seconds // 3600
                            minutes = (eta_seconds % 3600) // 60
                            eta_str = f"{hours}h {minutes}m"
                    else:
                        eta_str = "Calculating..."
                    
                    message = f"Processing... {processed:,} products imported | {row_count:,} rows processed | {speed_str} | ETA: {eta_str}"
                    if errors:
                        message += f" | {len(errors)} errors"
                    
                    self.update_progress(
                        progress,
                        "PROGRESS",
                        message,
                        rows_processed=row_count,
                        rows_total=estimated_total,
                        products_processed=processed,
                        processing_speed=current_speed,
                        eta_seconds=eta_seconds,
                        error_count=len(errors)
                    )
                    
                    last_update_time = current_time
                    last_row_count = row_count
                    chunk = []
            
            # Process remaining rows
            if chunk:
                result = process_csv_chunk(db, chunk, task_id)
                processed += result['processed']
                errors.extend(result['errors'])
                db.commit()
        
        total_rows = row_count
        elapsed_total = time.time() - start_time
        final_speed = total_rows / elapsed_total if elapsed_total > 0 else 0
        
        # Trigger webhooks
        trigger_webhooks(db, "product.bulk_import", {
            "total": processed,
            "errors": len(errors)
        })
        
        # Update to 100% progress before returning (Celery will set SUCCESS automatically)
        self.update_progress(
            100, 
            "PROGRESS", 
            f"Import complete! {processed:,} products imported from {total_rows:,} rows in {elapsed_total:.1f}s ({int(final_speed):,} rows/sec)",
            rows_processed=total_rows,
            rows_total=total_rows,
            products_processed=processed,
            processing_speed=final_speed,
            eta_seconds=0,
            error_count=len(errors)
        )
        
        # Return result - Celery will automatically set state to SUCCESS
        return {
            "processed": processed,
            "errors": errors[:100],  # Limit error details to first 100
            "error_count": len(errors),
            "total": total_rows,
            "elapsed_time": elapsed_total,
            "processing_speed": final_speed
        }
        
    except Exception as e:
        # Extract serializable error info before raising
        error_message = str(e)
        error_type = type(e).__name__
        
        db.rollback()
        
        # Don't update state in exception handler - it can cause serialization issues
        # Celery will handle the FAILURE state automatically when we raise
        # The frontend will get the failure state from Celery's normal handling
        
        # Raise a new simple exception that Celery can serialize to Redis
        # This must be a simple exception with only string data
        raise RuntimeError(f"{error_type}: {error_message}")
    finally:
        # Clean up: delete file from database and large object if exists
        try:
            if file_upload:
                # Delete large object if it exists
                if file_upload.large_object_oid:
                    from app.database import engine
                    try:
                        loid = int(file_upload.large_object_oid)
                        raw_conn = engine.raw_connection()
                        try:
                            cursor = raw_conn.cursor()
                            cursor.execute("SELECT lo_unlink(%s)", (loid,))
                            raw_conn.commit()
                            cursor.close()
                        finally:
                            raw_conn.close()
                    except Exception:
                        pass  # Ignore large object deletion errors
                
                db.delete(file_upload)
                db.commit()
        except Exception:
            db.rollback()
        
        db.close()
        
        # Clean up temp file
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass  # Ignore cleanup errors

