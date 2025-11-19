from sqlalchemy import Column, String, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid

class Product(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String(255), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    active = Column(Boolean, default=True, nullable=False)
    
    # Case-insensitive unique constraint on SKU (handled in application logic)
    # Database-level constraint would require a computed column or trigger
    
    def __repr__(self):
        return f"<Product(sku={self.sku}, name={self.name})>"

class Webhook(Base):
    __tablename__ = "webhooks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(500), nullable=False)
    event_type = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    secret = Column(String(255))
    
    def __repr__(self):
        return f"<Webhook(url={self.url}, event={self.event_type})>"

