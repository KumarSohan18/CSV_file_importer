from app.database import SessionLocal, engine
from typing import Dict, List, Any

def process_csv_chunk(db: SessionLocal, chunk: List[Dict[str, Any]], task_id: str) -> Dict[str, Any]:
    """Ultra-fast processing using PostgreSQL COPY and UPSERT"""
    processed = 0
    errors = []
    
    if not chunk:
        return {"processed": 0, "errors": errors}
    
    # Prepare data for COPY
    # Use dictionary to handle duplicates within chunk (last occurrence wins)
    temp_table_name = f"temp_products_{task_id.replace('-', '_')}"
    rows_dict = {}  # key: sku_lower, value: (sku, name, description, active)
    
    for idx, row in enumerate(chunk):
        try:
            sku = row.get('sku', '').strip()
            if not sku:
                errors.append({"row_index": idx, "error": "SKU is required"})
                continue
            
            sku_lower = sku.lower()
            name = row.get('name', '').strip() or 'Unnamed Product'
            description = row.get('description', '').strip() or None
            
            # Overwrite if duplicate SKU (last occurrence wins)
            # This ensures SKU remains unique and duplicates are overwritten
            rows_dict[sku_lower] = (sku, name, description, True)
            
            # Count all rows processed (including duplicates that overwrite)
            processed += 1
            
        except Exception as e:
            errors.append({"row_index": idx, "error": str(e)})
    
    # Convert dictionary values to list (duplicates already handled, last occurrence kept)
    rows_data = list(rows_dict.values())
    
    if not rows_data:
        return {"processed": 0, "errors": errors}
    
    # Get raw connection for COPY
    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        
        # Create temporary table
        cursor.execute(f"""
            CREATE TEMP TABLE {temp_table_name} (
                sku VARCHAR(255),
                name VARCHAR(500),
                description TEXT,
                active BOOLEAN
            )
        """)
        
        # Use executemany for bulk insert (psycopg3 compatible)
        # This is PostgreSQL's optimized bulk insert method
        insert_query = f"""
            INSERT INTO {temp_table_name} (sku, name, description, active)
            VALUES (%s, %s, %s, %s)
        """
        
        # Execute bulk insert using executemany (very fast, works with psycopg3)
        cursor.executemany(insert_query, rows_data)
        
        # Create index on temp table for faster joins
        cursor.execute(f"""
            CREATE INDEX idx_temp_sku_lower ON {temp_table_name} (LOWER(sku))
        """)
        
        # UPSERT: Insert new products (case-insensitive check)
        cursor.execute(f"""
            INSERT INTO products (id, sku, name, description, active)
            SELECT gen_random_uuid(), t.sku, t.name, NULLIF(t.description, ''), t.active
            FROM {temp_table_name} t
            WHERE NOT EXISTS (
                SELECT 1 FROM products p 
                WHERE LOWER(p.sku) = LOWER(t.sku)
            )
        """)
        
        # Update existing products in single query (case-insensitive)
        cursor.execute(f"""
            UPDATE products p
            SET name = t.name,
                description = NULLIF(t.description, ''),
                active = t.active
            FROM {temp_table_name} t
            WHERE LOWER(p.sku) = LOWER(t.sku)
        """)
        
        # Drop temp table
        cursor.execute(f"DROP TABLE IF EXISTS {temp_table_name}")
        
        raw_conn.commit()
        cursor.close()
        
    except Exception as e:
        raw_conn.rollback()
        errors.append({"operation": "bulk_upsert", "error": str(e)})
    finally:
        raw_conn.close()
    
    return {"processed": processed, "errors": errors}

