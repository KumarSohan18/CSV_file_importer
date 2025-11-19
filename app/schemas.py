from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class ProductBase(BaseModel):
    sku: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    active: bool = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    active: Optional[bool] = None

class Product(ProductBase):
    id: UUID
    
    class Config:
        from_attributes = True

class ProductListResponse(BaseModel):
    items: list[Product]
    total: int
    page: int
    page_size: int
    total_pages: int

class WebhookBase(BaseModel):
    url: str
    event_type: str
    enabled: bool = True

class WebhookCreate(WebhookBase):
    pass

class Webhook(WebhookBase):
    id: UUID
    
    class Config:
        from_attributes = True

class WebhookTestResponse(BaseModel):
    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None

