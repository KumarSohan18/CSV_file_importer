"""
Script to create the database if it doesn't exist.
Run this before starting the application.
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from app.config import settings

def create_database():
    # Parse the database URL to get connection details
    # Format: postgresql://user:password@host:port/dbname
    db_url = settings.DATABASE_URL
    
    # Extract components
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', '')
    
    parts = db_url.split('@')
    if len(parts) == 2:
        user_pass = parts[0].split(':')
        host_db = parts[1].split('/')
        
        if len(user_pass) == 2:
            user = user_pass[0]
            password = user_pass[1]
        else:
            user = user_pass[0]
            password = None
        
        if len(host_db) == 2:
            host_port = host_db[0].split(':')
            host = host_port[0] if host_port else 'localhost'
            port = host_port[1] if len(host_port) > 1 else '5432'
            dbname = host_db[1]
        else:
            host = 'localhost'
            port = '5432'
            dbname = None
    else:
        print("Invalid database URL format")
        return
    
    # Connect to PostgreSQL server (not to a specific database)
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{dbname}'")
        exists = cursor.fetchone()
        
        if not exists:
            # Create database
            cursor.execute(f'CREATE DATABASE {dbname}')
            print(f"Database '{dbname}' created successfully!")
        else:
            print(f"Database '{dbname}' already exists.")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Error creating database: {e}")
        print("\nYou can also create it manually using:")
        print(f"  psql -U {user} -h {host} -p {port} -c 'CREATE DATABASE {dbname};'")
        print("\nOr connect to psql and run:")
        print(f"  CREATE DATABASE {dbname};")

if __name__ == "__main__":
    create_database()

