#!/usr/bin/env python3
"""
Migration Script: File-based to Database
Migrates existing JSON files to PostgreSQL database
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_session import SessionLocal, init_db
from database.models import Analysis, User, ProcessingStats

RESULTS_FOLDER = 'results'
USERS_FILE = 'users.json'


def migrate_analyses(db):
    """Migrate analysis results from JSON files to database"""
    results_dir = Path(RESULTS_FOLDER)
    
    if not results_dir.exists():
        print(f"⚠️  Results folder '{RESULTS_FOLDER}' not found. Skipping analysis migration.")
        return 0
    
    migrated = 0
    errors = 0
    
    for json_file in results_dir.glob('*.json'):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Extract analysis ID from filename (remove .json extension)
            analysis_id = json_file.stem
            
            # Check if already exists
            existing = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if existing:
                print(f"⏭️  Skipping {analysis_id} (already exists)")
                continue
            
            # Extract result data
            result = data.get('result', {})
            
            # Create analysis record
            analysis = Analysis(
                id=analysis_id,
                user_id=data.get('user_id'),
                filename=data.get('filename', result.get('filename', 'unknown')),
                source_url=data.get('source_url'),
                file_path=data.get('file_path'),
                s3_key=data.get('s3_key'),
                is_fake=result.get('is_fake', False),
                confidence=result.get('confidence', 0.0),
                fake_probability=result.get('fake_probability', 0.0),
                authenticity_score=result.get('authenticity_score'),
                verdict=result.get('verdict', 'UNKNOWN'),
                forensic_metrics=data.get('forensic_metrics'),
                spatial_entropy_heatmap=data.get('forensic_metrics', {}).get('spatial_entropy_heatmap'),
                blockchain_tx=data.get('blockchain_tx'),
                blockchain_network=data.get('blockchain_network'),
                blockchain_timestamp=datetime.fromisoformat(data['blockchain_timestamp'].replace('Z', '+00:00')) if data.get('blockchain_timestamp') else None,
                video_hash=result.get('video_hash') or data.get('aistore_info', {}).get('video_hash'),
                file_size=data.get('file_size'),
                duration=data.get('duration'),
                model_type=data.get('model_type'),
                processing_time=data.get('processing_time'),
                created_at=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')) if data.get('timestamp') else datetime.utcnow(),
            )
            
            db.add(analysis)
            migrated += 1
            
            if migrated % 10 == 0:
                db.commit()
                print(f"✅ Migrated {migrated} analyses...")
        
        except Exception as e:
            errors += 1
            print(f"❌ Error migrating {json_file.name}: {e}")
            continue
    
    db.commit()
    print(f"\n✅ Migration complete: {migrated} analyses migrated, {errors} errors")
    return migrated


def migrate_users(db):
    """Migrate users from JSON file to database"""
    if not os.path.exists(USERS_FILE):
        print(f"⚠️  Users file '{USERS_FILE}' not found. Skipping user migration.")
        return 0
    
    try:
        with open(USERS_FILE, 'r') as f:
            users_data = json.load(f)
        
        migrated = 0
        
        for user_id, user_data in users_data.items():
            # Check if already exists
            existing = db.query(User).filter(User.id == user_id).first()
            if existing:
                print(f"⏭️  Skipping user {user_id} (already exists)")
                continue
            
            user = User(
                id=user_id,
                username=user_data.get('username', f'user_{user_id}'),
                email=user_data.get('email', f'{user_id}@example.com'),
                password_hash=user_data.get('password_hash', ''),  # Should be hashed
                role=user_data.get('role', 'user'),
                created_at=datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00')) if user_data.get('created_at') else datetime.utcnow(),
                last_login=datetime.fromisoformat(user_data['last_login'].replace('Z', '+00:00')) if user_data.get('last_login') else None,
                is_active=user_data.get('is_active', True),
            )
            
            db.add(user)
            migrated += 1
        
        db.commit()
        print(f"✅ Migrated {migrated} users")
        return migrated
    
    except Exception as e:
        print(f"❌ Error migrating users: {e}")
        return 0


def main():
    """Main migration function"""
    print("🔄 Starting database migration from file-based storage...")
    print("=" * 60)
    
    # Initialize database
    print("\n📊 Step 1: Initializing database...")
    init_db()
    
    # Create session
    db = SessionLocal()
    
    try:
        # Migrate users
        print("\n👥 Step 2: Migrating users...")
        user_count = migrate_users(db)
        
        # Migrate analyses
        print("\n📹 Step 3: Migrating analyses...")
        analysis_count = migrate_analyses(db)
        
        print("\n" + "=" * 60)
        print("✅ Migration Summary:")
        print(f"   Users: {user_count}")
        print(f"   Analyses: {analysis_count}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    main()

