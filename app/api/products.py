from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.database import get_db
from app.models import Product
from app.schemas import Product as ProductSchema, ProductCreate, ProductUpdate, ProductListResponse
from app.services.webhook_service import trigger_webhooks
from uuid import UUID

router = APIRouter()

@router.get("/", response_model=ProductListResponse)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sku: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List products with filtering and pagination"""
    query = db.query(Product)
    
    # Apply filters
    if sku:
        query = query.filter(func.lower(Product.sku).contains(sku.lower()))
    if name:
        query = query.filter(Product.name.contains(name))
    if description:
        query = query.filter(Product.description.contains(description))
    if active is not None:
        query = query.filter(Product.active == active)
    
    total = query.count()
    total_pages = (total + page_size - 1) // page_size
    
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.post("/", response_model=ProductSchema)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product"""
    # Check for duplicate SKU (case-insensitive)
    existing = db.query(Product).filter(
        func.lower(Product.sku) == product.sku.lower()
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    trigger_webhooks(db, "product.created", {"product_id": str(db_product.id)})
    
    return db_product

@router.get("/{product_id}", response_model=ProductSchema)
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    """Get a single product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.put("/{product_id}", response_model=ProductSchema)
def update_product(product_id: UUID, product: ProductUpdate, db: Session = Depends(get_db)):
    """Update a product"""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    
    trigger_webhooks(db, "product.updated", {"product_id": str(db_product.id)})
    
    return db_product

@router.delete("/{product_id}")
def delete_product(product_id: UUID, db: Session = Depends(get_db)):
    """Delete a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    
    trigger_webhooks(db, "product.deleted", {"product_id": str(product_id)})
    
    return {"message": "Product deleted successfully"}

@router.delete("/")
def delete_all_products(db: Session = Depends(get_db)):
    """Delete all products"""
    count = db.query(Product).delete()
    db.commit()
    
    trigger_webhooks(db, "product.bulk_delete", {"count": count})
    
    return {"message": f"Deleted {count} products"}

