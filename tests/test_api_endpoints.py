#!/usr/bin/env python3
"""
API Endpoint Tests
Comprehensive tests for all API endpoints
"""

import unittest
import os
import json
import tempfile
import shutil
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import app
from database.models import Analysis, User
from database.db_session import SessionLocal, init_db

class APITestCase(unittest.TestCase):
    """Test cases for API endpoints"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.app = app.test_client()
        cls.app.testing = True
        
        # Create temporary directories
        cls.test_upload_dir = tempfile.mkdtemp()
        cls.test_results_dir = tempfile.mkdtemp()
        
        # Update app config
        app.config['UPLOAD_FOLDER'] = cls.test_upload_dir
        app.config['RESULTS_FOLDER'] = cls.test_results_dir
        app.config['TESTING'] = True
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        shutil.rmtree(cls.test_upload_dir, ignore_errors=True)
        shutil.rmtree(cls.test_results_dir, ignore_errors=True)
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.app.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('healthy', data)
        self.assertTrue(data['healthy'])
    
    def test_analyze_endpoint_no_file(self):
        """Test analyze endpoint without file"""
        response = self.app.post('/api/analyze')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_dashboard_stats_endpoint(self):
        """Test dashboard stats endpoint"""
        response = self.app.get('/api/dashboard/stats')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('total_analyses', data)
        self.assertIn('fake_detected', data)
        self.assertIn('authentic_detected', data)
        self.assertIsInstance(data['total_analyses'], int)
    
    def test_security_audit_endpoint(self):
        """Test security audit endpoint"""
        # Note: This requires authentication in production
        # For testing, we'll check if endpoint exists
        response = self.app.get('/api/security/audit')
        # Should return 401 (unauthorized) or 200 (if auth disabled)
        self.assertIn(response.status_code, [200, 401])


class DatabaseTestCase(unittest.TestCase):
    """Test cases for database operations"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database"""
        # Use test database
        os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test_secureai'
        try:
            init_db()
        except Exception as e:
            print(f"Database setup failed: {e}")
            cls.db_available = False
        else:
            cls.db_available = True
    
    def setUp(self):
        """Set up for each test"""
        if not self.db_available:
            self.skipTest("Database not available")
        self.db = SessionLocal()
    
    def tearDown(self):
        """Clean up after each test"""
        if self.db_available:
            self.db.rollback()
            self.db.close()
    
    def test_create_analysis(self):
        """Test creating an analysis record"""
        analysis = Analysis(
            id='test_123',
            filename='test_video.mp4',
            is_fake=False,
            confidence=0.95,
            fake_probability=0.05,
            verdict='REAL',
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(analysis)
        self.db.commit()
        
        # Verify
        retrieved = self.db.query(Analysis).filter(Analysis.id == 'test_123').first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.filename, 'test_video.mp4')
        self.assertEqual(retrieved.verdict, 'REAL')
    
    def test_query_analyses(self):
        """Test querying analyses"""
        analyses = self.db.query(Analysis).limit(10).all()
        self.assertIsInstance(analyses, list)


if __name__ == '__main__':
    unittest.main()

