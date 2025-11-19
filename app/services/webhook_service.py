import httpx
import time
from typing import Dict, Any
from app.models import Webhook
from app.schemas import WebhookTestResponse

def trigger_webhooks(db, event_type: str, payload: Dict[str, Any]):
    """Trigger all enabled webhooks for an event type"""
    webhooks = db.query(Webhook).filter(
        Webhook.event_type == event_type,
        Webhook.enabled == True
    ).all()
    
    for webhook in webhooks:
        try:
            httpx.post(webhook.url, json=payload, timeout=5.0)
        except Exception as e:
            print(f"Webhook error: {e}")

def test_webhook(webhook: Webhook) -> WebhookTestResponse:
    """Test a webhook and return response details"""
    try:
        start_time = time.time()
        
        # Validate URL format
        if not webhook.url.startswith(('http://', 'https://')):
            return WebhookTestResponse(
                success=False,
                error=f"Invalid URL format: {webhook.url}. URL must start with http:// or https://"
            )
        
        response = httpx.post(
            webhook.url,
            json={"test": True, "event": webhook.event_type},
            timeout=10.0,
            follow_redirects=True
        )
        response_time = (time.time() - start_time) * 1000
        
        is_success = 200 <= response.status_code < 300
        
        return WebhookTestResponse(
            success=is_success,
            status_code=response.status_code,
            response_time_ms=round(response_time, 2),
            error=None if is_success else f"HTTP {response.status_code}: {response.text[:200]}"
        )
    except httpx.TimeoutException:
        return WebhookTestResponse(
            success=False,
            error="Request timeout: Webhook did not respond within 10 seconds"
        )
    except httpx.ConnectError as e:
        return WebhookTestResponse(
            success=False,
            error=f"Connection error: Could not connect to {webhook.url}. Check if the URL is correct and the server is running."
        )
    except httpx.RequestError as e:
        return WebhookTestResponse(
            success=False,
            error=f"Request error: {str(e)}"
        )
    except Exception as e:
        return WebhookTestResponse(
            success=False,
            error=f"Unexpected error: {str(e)}"
        )

