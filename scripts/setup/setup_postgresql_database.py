#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script
Creates database, user, and configures .env file
"""

import os
import sys
import subprocess
import psycopg2
from psycopg2 import sql
from pathlib import Path

# Configuration
POSTGRES_PASSWORD = "RNYZa9z8"
POSTGRES_PORT = 5432
DB_NAME = "secureai_db"
DB_USER = "secureai"
DB_PASSWORD = "SecureAI2024!DB"

def find_postgresql_bin():
    """Find PostgreSQL installation directory"""
    possible_paths = [
        r"C:\Program Files\PostgreSQL\16\bin",
        r"C:\Program Files\PostgreSQL\15\bin",
        r"C:\Program Files\PostgreSQL\14\bin",
        r"C:\Program Files\PostgreSQL\13\bin",
    ]
    
    for path in possible_paths:
        if os.path.exists(os.path.join(path, "psql.exe")):
            return path
    
    return None

def test_postgres_connection():
    """Test connection to PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=POSTGRES_PORT,
            user="postgres",
            password=POSTGRES_PASSWORD,
            database="postgres"
        )
        conn.close()
        return True
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        return False

def create_database_and_user():
    """Create database and user"""
    try:
        # Connect as postgres superuser
        conn = psycopg2.connect(
            host="localhost",
            port=POSTGRES_PORT,
            user="postgres",
            password=POSTGRES_PASSWORD,
            database="postgres"
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (DB_NAME,)
        )
        if cursor.fetchone():
            print(f"WARNING: Database '{DB_NAME}' already exists")
            response = input("Do you want to recreate it? (y/n): ")
            if response.lower() == 'y':
                cursor.execute(
                    sql.SQL("DROP DATABASE {}").format(
                        sql.Identifier(DB_NAME)
                    )
                )
                print(f"OK: Dropped existing database '{DB_NAME}'")
            else:
                print("Keeping existing database")
        else:
            # Create database
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(DB_NAME)
                )
            )
            print(f"OK: Created database '{DB_NAME}'")
        
        # Check if user exists
        cursor.execute(
            "SELECT 1 FROM pg_user WHERE usename = %s",
            (DB_USER,)
        )
        if cursor.fetchone():
            print(f"WARNING: User '{DB_USER}' already exists")
            # Update password
            cursor.execute(
                sql.SQL("ALTER USER {} WITH PASSWORD %s").format(
                    sql.Identifier(DB_USER)
                ),
                (DB_PASSWORD,)
            )
            print(f"OK: Updated password for user '{DB_USER}'")
        else:
            # Create user
            cursor.execute(
                sql.SQL("CREATE USER {} WITH ENCRYPTED PASSWORD %s").format(
                    sql.Identifier(DB_USER)
                ),
                (DB_PASSWORD,)
            )
            print(f"OK: Created user '{DB_USER}'")
        
        # Grant privileges
        cursor.execute(
            sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                sql.Identifier(DB_NAME),
                sql.Identifier(DB_USER)
            )
        )
        print(f"OK: Granted privileges on database '{DB_NAME}' to user '{DB_USER}'")
        
        # Connect to new database to grant schema privileges
        conn.close()
        conn = psycopg2.connect(
            host="localhost",
            port=POSTGRES_PORT,
            user="postgres",
            password=POSTGRES_PASSWORD,
            database=DB_NAME
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        cursor.execute(
            sql.SQL("GRANT ALL ON SCHEMA public TO {}").format(
                sql.Identifier(DB_USER)
            )
        )
        print(f"OK: Granted schema privileges to user '{DB_USER}'")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"ERROR: Error creating database/user: {e}")
        return False

def update_env_file():
    """Update .env file with DATABASE_URL"""
    env_file = Path(".env")
    database_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@localhost:{POSTGRES_PORT}/{DB_NAME}"
    
    if env_file.exists():
        # Read existing .env
        lines = env_file.read_text().splitlines()
        
        # Remove old DATABASE_URL if exists
        lines = [line for line in lines if not line.startswith("DATABASE_URL=")]
        
        # Add new DATABASE_URL
        lines.append(f"DATABASE_URL={database_url}")
        
        env_file.write_text("\n".join(lines) + "\n")
        print("OK: Updated .env file with DATABASE_URL")
    else:
        # Create new .env file
        env_file.write_text(f"DATABASE_URL={database_url}\n")
        print("OK: Created .env file with DATABASE_URL")
    
    return True

def main():
    print("=" * 50)
    print("PostgreSQL Database Setup")
    print("=" * 50)
    print()
    print("Configuration:")
    print(f"  PostgreSQL Password: {POSTGRES_PASSWORD}")
    print(f"  Port: {POSTGRES_PORT}")
    print(f"  Database Name: {DB_NAME}")
    print(f"  Database User: {DB_USER}")
    print()
    
    # Test connection
    print("Step 1: Testing PostgreSQL connection...")
    if not test_postgres_connection():
        print("\nERROR: Cannot connect to PostgreSQL")
        print("Please check:")
        print("  1. PostgreSQL service is running")
        print("  2. Password is correct")
        print("  3. Port is 5432")
        return 1
    
    print("OK: PostgreSQL connection successful")
    print()
    
    # Create database and user
    print("Step 2: Creating database and user...")
    if not create_database_and_user():
        return 1
    
    print()
    
    # Update .env file
    print("Step 3: Updating .env file...")
    if not update_env_file():
        return 1
    
    print()
    print("=" * 50)
    print("OK: Setup Complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. Initialize database schema:")
    print("     py -c \"from database.db_session import init_db; init_db()\"")
    print()
    print("  2. Test connection:")
    print("     py -c \"from database.db_session import get_db; db = next(get_db()); print('✅ Connected!')\"")
    print()
    print("  3. (Optional) Migrate existing data:")
    print("     py database/migrate_from_files.py")
    print()
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

