from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Webhook
from app.schemas import Webhook as WebhookSchema, WebhookCreate, WebhookTestResponse
from app.services.webhook_service import test_webhook
from uuid import UUID

router = APIRouter()

@router.get("/", response_model=List[WebhookSchema])
def list_webhooks(db: Session = Depends(get_db)):
    """List all webhooks"""
    return db.query(Webhook).all()

@router.post("/", response_model=WebhookSchema)
def create_webhook(webhook: WebhookCreate, db: Session = Depends(get_db)):
    """Create a new webhook"""
    db_webhook = Webhook(**webhook.dict())
    db.add(db_webhook)
    db.commit()
    db.refresh(db_webhook)
    return db_webhook

@router.put("/{webhook_id}", response_model=WebhookSchema)
def update_webhook(webhook_id: UUID, webhook: WebhookCreate, db: Session = Depends(get_db)):
    """Update a webhook"""
    db_webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not db_webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    for key, value in webhook.dict().items():
        setattr(db_webhook, key, value)
    
    db.commit()
    db.refresh(db_webhook)
    return db_webhook

@router.delete("/{webhook_id}")
def delete_webhook(webhook_id: UUID, db: Session = Depends(get_db)):
    """Delete a webhook"""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    db.delete(webhook)
    db.commit()
    return {"message": "Webhook deleted successfully"}

@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
def test_webhook_endpoint(webhook_id: UUID, db: Session = Depends(get_db)):
    """Test a webhook"""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    try:
        result = test_webhook(webhook)
        return result
    except Exception as e:
        # Fallback error handling
        return WebhookTestResponse(
            success=False,
            error=f"Failed to test webhook: {str(e)}"
        )

