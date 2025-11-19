from sqlalchemy import Column, String, Boolean, Text, Index, LargeBinary, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid
from datetime import datetime

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

class FileUpload(Base):
    """Temporary storage for CSV file content (for large files that can't fit in Redis)"""
    __tablename__ = "file_uploads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), nullable=False, unique=True, index=True)
    file_content = Column(LargeBinary, nullable=True)  # Nullable for large object storage
    large_object_oid = Column(String(50), nullable=True)  # PostgreSQL large object OID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        size = len(self.file_content) if self.file_content else 0
        return f"<FileUpload(task_id={self.task_id}, size={size}, lo_oid={self.large_object_oid})>"

