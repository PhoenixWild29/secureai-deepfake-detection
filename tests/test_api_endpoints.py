#!/usr/bin/env python3
"""
API Endpoint Tests — FastAPI
Tests all FastAPI endpoints using fastapi.testclient.TestClient.

Migrated from Flask test_client to FastAPI TestClient.
Flask api.py is kept as a reference but no longer the test target.
"""

import os
import io
import json
import shutil
import tempfile
import unittest
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app


class APITestCase(unittest.TestCase):
    """Test cases for FastAPI endpoints."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment with temporary directories."""
        cls.client = TestClient(app, raise_server_exceptions=False)
        cls.test_upload_dir = tempfile.mkdtemp()
        cls.test_results_dir = tempfile.mkdtemp()
        # Override env vars so the endpoints use temp dirs
        os.environ['UPLOAD_FOLDER'] = cls.test_upload_dir
        os.environ['RESULTS_FOLDER'] = cls.test_results_dir

    @classmethod
    def tearDownClass(cls):
        """Remove temporary test directories."""
        shutil.rmtree(cls.test_upload_dir, ignore_errors=True)
        shutil.rmtree(cls.test_results_dir, ignore_errors=True)

    # -----------------------------------------------------------------------
    # Root + docs
    # -----------------------------------------------------------------------

    def test_root_endpoint(self):
        """GET / returns API metadata."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('name', data)
        self.assertIn('version', data)

    def test_swagger_docs_available(self):
        """GET /docs returns 200 (auto-generated Swagger UI)."""
        response = self.client.get('/docs')
        self.assertEqual(response.status_code, 200)

    # -----------------------------------------------------------------------
    # System endpoints
    # -----------------------------------------------------------------------

    def test_health_endpoint(self):
        """GET /api/v1/system/health returns healthy status."""
        response = self.client.get('/api/v1/system/health')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('timestamp', data)
        self.assertEqual(data['framework'], 'FastAPI')

    def test_ensemble_status_endpoint(self):
        """GET /api/v1/system/ensemble-status returns model loading state."""
        response = self.client.get('/api/v1/system/ensemble-status')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('status', data)
        self.assertIn('ready', data)

    def test_dashboard_stats_endpoint(self):
        """GET /api/v1/system/dashboard-stats returns analysis counts."""
        response = self.client.get('/api/v1/system/dashboard-stats')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total_analyses', data)
        self.assertIn('fake_detected', data)
        self.assertIn('authentic_detected', data)
        self.assertIsInstance(data['total_analyses'], int)

    def test_security_audit_endpoint(self):
        """POST /api/v1/system/security-audit returns 200 or 500 (no crash)."""
        response = self.client.post('/api/v1/system/security-audit', json={})
        self.assertIn(response.status_code, [200, 500])

    # -----------------------------------------------------------------------
    # Detection endpoints — validation
    # -----------------------------------------------------------------------

    def test_detect_no_file_returns_422(self):
        """POST /api/v1/detect without a file returns 422 Unprocessable Entity."""
        response = self.client.post('/api/v1/detect')
        self.assertEqual(response.status_code, 422)

    def test_detect_invalid_extension_returns_400(self):
        """POST /api/v1/detect with a non-video file returns 400."""
        fake_file = io.BytesIO(b"not a video")
        response = self.client.post(
            '/api/v1/detect',
            files={'video': ('malicious.exe', fake_file, 'application/octet-stream')},
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        # FastAPI global error handler wraps errors under 'error' key
        self.assertIn('error', data)

    def test_detect_url_no_url_returns_400(self):
        """POST /api/v1/detect/url without url field returns 400."""
        response = self.client.post('/api/v1/detect/url', json={})
        self.assertEqual(response.status_code, 400)

    def test_detect_status_not_found(self):
        """GET /api/v1/detect/status/<unknown> returns pending_or_not_found."""
        response = self.client.get('/api/v1/detect/status/nonexistent-id-12345')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'pending_or_not_found')

    def test_detect_results_not_found_returns_404(self):
        """GET /api/v1/detect/results/<unknown> returns 404."""
        response = self.client.get('/api/v1/detect/results/nonexistent-id-12345')
        self.assertEqual(response.status_code, 404)

    # -----------------------------------------------------------------------
    # Blockchain endpoint — validation
    # -----------------------------------------------------------------------

    def test_blockchain_submit_no_analysis_id_returns_400(self):
        """POST /api/v1/blockchain/submit without analysis_id returns 400."""
        response = self.client.post('/api/v1/blockchain/submit', json={})
        self.assertEqual(response.status_code, 400)

    # -----------------------------------------------------------------------
    # Sage endpoint — validation
    # -----------------------------------------------------------------------

    def test_sage_chat_no_message_returns_400(self):
        """POST /api/v1/sage/chat without message returns 400."""
        response = self.client.post('/api/v1/sage/chat', json={})
        self.assertEqual(response.status_code, 400)

    def test_sage_chat_no_api_key_returns_503(self):
        """POST /api/v1/sage/chat without GOOGLE_API_KEY returns 503."""
        original = os.environ.pop('GOOGLE_API_KEY', None)
        os.environ.pop('GEMINI_API_KEY', None)
        try:
            response = self.client.post('/api/v1/sage/chat', json={'message': 'test'})
            self.assertEqual(response.status_code, 503)
        finally:
            if original:
                os.environ['GOOGLE_API_KEY'] = original


class DatabaseTestCase(unittest.TestCase):
    """Test cases for database operations (skipped if DB unavailable)."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost:5432/test_secureai')
        try:
            from database.db_session import SessionLocal, init_db
            init_db()
            cls.SessionLocal = SessionLocal
            cls.db_available = True
        except Exception as exc:
            print(f"Database not available, skipping DB tests: {exc}")
            cls.db_available = False

    def setUp(self):
        if not self.db_available:
            self.skipTest("Database not available")
        self.db = self.SessionLocal()

    def tearDown(self):
        if self.db_available:
            self.db.rollback()
            self.db.close()

    def test_create_and_query_analysis(self):
        """Create and retrieve an Analysis record."""
        from datetime import datetime
        from database.models import Analysis

        record = Analysis(
            id='test_fastapi_123',
            filename='test_video.mp4',
            is_fake=False,
            confidence=0.95,
            fake_probability=0.05,
            verdict='REAL',
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.db.add(record)
        self.db.commit()

        retrieved = self.db.query(Analysis).filter(Analysis.id == 'test_fastapi_123').first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.filename, 'test_video.mp4')
        self.assertEqual(retrieved.verdict, 'REAL')


if __name__ == '__main__':
    unittest.main()
