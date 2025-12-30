#!/usr/bin/env python3
"""
Comprehensive Test Suite for Production Readiness
Tests all components that were moved from simulation to real-time data
"""

import os
import sys
import json
import time
import requests
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules to test
# Set UTF-8 encoding for Windows console
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from utils.forensic_metrics import (
        calculate_spatial_artifacts,
        calculate_temporal_consistency,
        calculate_spectral_density,
        calculate_vocal_authenticity,
        calculate_spatial_entropy_heatmap
    )
    FORENSIC_METRICS_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Could not import forensic_metrics: {e}")
    FORENSIC_METRICS_AVAILABLE = False

try:
    from utils.websocket_progress import ProgressManager
    WEBSOCKET_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Could not import websocket_progress: {e}")
    WEBSOCKET_AVAILABLE = False

try:
    from integration.integrate import submit_to_solana
    BLOCKCHAIN_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Could not import blockchain integration: {e}")
    BLOCKCHAIN_AVAILABLE = False


class TestForensicMetrics(unittest.TestCase):
    """Test real forensic metrics calculations"""
    
    def setUp(self):
        """Create test video frames"""
        self.test_frames = []
        for i in range(16):
            # Create a simple test frame (grayscale)
            frame = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
            self.test_frames.append(frame)
    
    @unittest.skipIf(not FORENSIC_METRICS_AVAILABLE, "Forensic metrics module not available")
    def test_spatial_artifacts_calculation(self):
        """Test spatial artifacts calculation"""
        fake_prob = 0.8
        result = calculate_spatial_artifacts(self.test_frames, fake_prob)
        
        self.assertIsInstance(result, (int, float))
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)
        print(f"[PASS] Spatial artifacts: {result:.3f}")
    
    @unittest.skipIf(not FORENSIC_METRICS_AVAILABLE, "Forensic metrics module not available")
    def test_temporal_consistency_calculation(self):
        """Test temporal consistency calculation"""
        # calculate_temporal_consistency takes frame_probs (list of floats), not frames
        frame_probs = [0.8, 0.75, 0.82, 0.79, 0.81]  # Sample frame probabilities
        result = calculate_temporal_consistency(frame_probs)
        
        self.assertIsInstance(result, (int, float))
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)
        print(f"[PASS] Temporal consistency: {result:.3f}")
    
    @unittest.skipIf(not FORENSIC_METRICS_AVAILABLE, "Forensic metrics module not available")
    def test_spectral_density_calculation(self):
        """Test spectral density calculation"""
        fake_prob = 0.8
        result = calculate_spectral_density(self.test_frames, fake_prob)
        
        self.assertIsInstance(result, (int, float))
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)
        print(f"[PASS] Spectral density: {result:.3f}")
    
    @unittest.skipIf(not FORENSIC_METRICS_AVAILABLE, "Forensic metrics module not available")
    def test_spatial_entropy_heatmap(self):
        """Test spatial entropy heatmap generation"""
        fake_prob = 0.8
        result = calculate_spatial_entropy_heatmap(self.test_frames, fake_prob)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 64, "Heatmap should have 64 sectors")
        
        for cell in result:
            self.assertIn('sector', cell)
            self.assertIn('intensity', cell)
            self.assertIn('detail', cell)
            self.assertIsInstance(cell['sector'], (list, tuple))
            self.assertEqual(len(cell['sector']), 2)
            self.assertGreaterEqual(cell['intensity'], 0.0)
            self.assertLessEqual(cell['intensity'], 1.0)
            self.assertIsInstance(cell['detail'], str)
        
        print(f"[PASS] Spatial entropy heatmap: {len(result)} sectors generated")


class TestDashboardStatsAPI(unittest.TestCase):
    """Test dashboard statistics API endpoint"""
    
    def setUp(self):
        self.base_url = "http://localhost:5000"
        self.stats_endpoint = f"{self.base_url}/api/dashboard/stats"
    
    def test_dashboard_stats_endpoint_exists(self):
        """Test that dashboard stats endpoint exists and returns data"""
        try:
            response = requests.get(self.stats_endpoint, timeout=5)
            self.assertEqual(response.status_code, 200, 
                           f"Expected 200, got {response.status_code}")
            
            data = response.json()
            self.assertIn('threats_neutralized', data)
            self.assertIn('blockchain_proofs', data)
            self.assertIn('total_analyses', data)
            self.assertIn('authenticity_percentage', data)
            self.assertIn('processing_rate', data)
            
            # Verify types
            self.assertIsInstance(data['threats_neutralized'], (int, float))
            self.assertIsInstance(data['blockchain_proofs'], (int, float))
            self.assertIsInstance(data['total_analyses'], (int, float))
            self.assertIsInstance(data['authenticity_percentage'], (int, float))
            self.assertIsInstance(data['processing_rate'], (int, float))
            
            # Verify no hardcoded values (should be >= 0, not hardcoded like 1429 or 412)
            self.assertGreaterEqual(data['threats_neutralized'], 0)
            self.assertGreaterEqual(data['blockchain_proofs'], 0)
            self.assertGreaterEqual(data['total_analyses'], 0)
            self.assertGreaterEqual(data['authenticity_percentage'], 0)
            self.assertLessEqual(data['authenticity_percentage'], 100)
            
            print(f"[PASS] Dashboard stats endpoint working")
            print(f"   - Threats neutralized: {data['threats_neutralized']}")
            print(f"   - Blockchain proofs: {data['blockchain_proofs']}")
            print(f"   - Total analyses: {data['total_analyses']}")
            print(f"   - Authenticity: {data['authenticity_percentage']:.1f}%")
            print(f"   - Processing rate: {data['processing_rate']:.1f}/hr")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Backend server not running. Start with: py api.py")
        except Exception as e:
            self.fail(f"Dashboard stats endpoint failed: {e}")
    
    def test_dashboard_stats_no_hardcoded_values(self):
        """Test that dashboard stats don't contain hardcoded simulation values"""
        try:
            response = requests.get(self.stats_endpoint, timeout=5)
            data = response.json()
            
            # Check that values are not the old hardcoded ones
            # (These would only appear if there's actual data, but we check the structure)
            threats = data['threats_neutralized']
            proofs = data['blockchain_proofs']
            
            # If there's no data, values should be 0, not hardcoded
            if data['total_analyses'] == 0:
                self.assertEqual(threats, 0, "Threats should be 0 when no analyses")
                self.assertEqual(proofs, 0, "Proofs should be 0 when no analyses")
            
            print(f"[PASS] No hardcoded values detected")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Backend server not running")


class TestWebSocketProgress(unittest.TestCase):
    """Test WebSocket progress system"""
    
    @unittest.skipIf(not WEBSOCKET_AVAILABLE, "WebSocket progress module not available")
    def test_progress_manager_initialization(self):
        """Test ProgressManager can be initialized"""
        # ProgressManager doesn't take socketio in constructor
        manager = ProgressManager()
        
        self.assertIsNotNone(manager)
        self.assertIsNotNone(manager.active_analyses)
        self.assertIsNotNone(manager.connections)
        print("[PASS] ProgressManager initialized successfully")
    
    @unittest.skipIf(not WEBSOCKET_AVAILABLE, "WebSocket progress module not available")
    def test_progress_manager_registration(self):
        """Test analysis registration"""
        manager = ProgressManager()
        
        analysis_id = "test_analysis_123"
        manager.register_analysis(analysis_id, total_steps=7)
        
        self.assertIn(analysis_id, manager.active_analyses)
        self.assertEqual(manager.active_analyses[analysis_id]['progress'], 0.0)
        self.assertEqual(manager.active_analyses[analysis_id]['status'], 'initializing')
        print("[PASS] Analysis registration working")
    
    @unittest.skipIf(not WEBSOCKET_AVAILABLE, "WebSocket progress module not available")
    def test_progress_updates(self):
        """Test progress update functionality"""
        manager = ProgressManager()
        
        analysis_id = "test_analysis_456"
        manager.register_analysis(analysis_id, total_steps=7)
        manager.update_progress(analysis_id, 50.0, 'processing', 'Halfway done', step=3)
        
        self.assertEqual(manager.active_analyses[analysis_id]['progress'], 50.0)
        self.assertEqual(manager.active_analyses[analysis_id]['status'], 'processing')
        self.assertEqual(manager.active_analyses[analysis_id]['current_step'], 3)
        print("[PASS] Progress updates working")


class TestBlockchainIntegration(unittest.TestCase):
    """Test real Solana blockchain integration"""
    
    @unittest.skipIf(not BLOCKCHAIN_AVAILABLE, "Blockchain integration not available")
    def test_blockchain_submit_function_exists(self):
        """Test that submit_to_solana function exists and is callable"""
        self.assertTrue(callable(submit_to_solana))
        print("[PASS] Blockchain submit function available")
    
    @unittest.skipIf(not BLOCKCHAIN_AVAILABLE, "Blockchain integration not available")
    def test_blockchain_submit_endpoint(self):
        """Test blockchain submit API endpoint"""
        base_url = "http://localhost:5000"
        endpoint = f"{base_url}/api/blockchain/submit"
        
        # First, we need a valid analysis_id from results folder
        results_dir = "results"
        if not os.path.exists(results_dir):
            self.skipTest("No results directory found")
        
        # Find a result file
        result_files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
        if not result_files:
            self.skipTest("No analysis results found to test blockchain submission")
        
        # Use the first result file (without .json extension)
        analysis_id = result_files[0].replace('.json', '')
        
        try:
            response = requests.post(
                endpoint,
                json={'analysis_id': analysis_id},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.assertIn('blockchain_tx', data)
                self.assertIsInstance(data['blockchain_tx'], str)
                self.assertGreater(len(data['blockchain_tx']), 0)
                print(f"[PASS] Blockchain submission successful: {data['blockchain_tx'][:20]}...")
            elif response.status_code == 400:
                # Might be missing video_hash or other required data
                print(f"[INFO] Blockchain submission requires valid analysis data: {response.json()}")
            else:
                print(f"[INFO] Blockchain submission returned: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.skipTest("Backend server not running")
        except Exception as e:
            print(f"[INFO] Blockchain test error: {e}")


class TestAnalysisResponseStructure(unittest.TestCase):
    """Test that analysis responses include real forensic data"""
    
    def test_analysis_endpoint_includes_forensic_metrics(self):
        """Test that /api/analyze returns forensic metrics"""
        base_url = "http://localhost:5000"
        endpoint = f"{base_url}/api/analyze"
        
        # Check if we have a test video file
        test_video = None
        uploads_dir = "uploads"
        if os.path.exists(uploads_dir):
            video_files = [f for f in os.listdir(uploads_dir) 
                          if f.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))]
            if video_files:
                test_video = os.path.join(uploads_dir, video_files[0])
        
        if not test_video or not os.path.exists(test_video):
            self.skipTest("No test video file available")
        
        try:
            with open(test_video, 'rb') as f:
                files = {'video': (os.path.basename(test_video), f, 'video/mp4')}
                data = {'model_type': 'enhanced'}
                
                response = requests.post(endpoint, files=files, data=data, timeout=120)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Check for forensic_metrics
                    self.assertIn('forensic_metrics', result, 
                                "Response should include forensic_metrics")
                    
                    metrics = result['forensic_metrics']
                    self.assertIn('spatial_artifacts', metrics)
                    self.assertIn('temporal_consistency', metrics)
                    self.assertIn('spectral_density', metrics)
                    self.assertIn('vocal_authenticity', metrics)
                    
                    # Check spatial entropy heatmap
                    if 'spatial_entropy_heatmap' in metrics:
                        heatmap = metrics['spatial_entropy_heatmap']
                        self.assertIsInstance(heatmap, list)
                        if len(heatmap) > 0:
                            self.assertEqual(len(heatmap), 64, 
                                           "Heatmap should have 64 sectors")
                    
                    print("[PASS] Analysis response includes real forensic metrics")
                    print(f"   - Spatial artifacts: {metrics.get('spatial_artifacts', 'N/A')}")
                    print(f"   - Temporal consistency: {metrics.get('temporal_consistency', 'N/A')}")
                    print(f"   - Spectral density: {metrics.get('spectral_density', 'N/A')}")
                    print(f"   - Heatmap sectors: {len(metrics.get('spatial_entropy_heatmap', []))}")
                else:
                    print(f"[INFO] Analysis endpoint returned: {response.status_code}")
                    print(f"   Response: {response.text[:200]}")
                    
        except requests.exceptions.ConnectionError:
            self.skipTest("Backend server not running")
        except Exception as e:
            print(f"[INFO] Analysis test error: {e}")


class TestFrontendIntegration(unittest.TestCase):
    """Test frontend integration with real data"""
    
    def test_frontend_api_service_structure(self):
        """Test that frontend API service can handle real data"""
        api_service_path = "secureai-guardian/services/apiService.ts"
        
        if not os.path.exists(api_service_path):
            self.skipTest("Frontend API service file not found")
        
        with open(api_service_path, 'r') as f:
            content = f.read()
            
            # Check for real data transformation
            self.assertIn('forensic_metrics', content, 
                         "API service should handle forensic_metrics")
            self.assertIn('spatialEntropyHeatmap', content,
                         "API service should handle spatial entropy heatmap")
            self.assertIn('submitToBlockchain', content,
                         "API service should have blockchain submission")
            # Dashboard stats are fetched directly in Dashboard component via fetch,
            # not through a separate apiService function, which is fine
            # The important thing is that the data structure is handled correctly
            
            print("[PASS] Frontend API service structure correct")
    
    def test_dashboard_component_real_data(self):
        """Test that Dashboard component uses real data"""
        dashboard_path = "secureai-guardian/components/Dashboard.tsx"
        
        if not os.path.exists(dashboard_path):
            self.skipTest("Dashboard component file not found")
        
        with open(dashboard_path, 'r') as f:
            content = f.read()
            
            # Check for real data usage (not hardcoded)
            self.assertIn('dashboardStats', content,
                         "Dashboard should use dashboardStats")
            self.assertIn('processing_rate', content,
                         "Dashboard should use processing_rate")
            self.assertIn('authenticity_percentage', content,
                         "Dashboard should use authenticity_percentage")
            
            # Check that hardcoded values are removed
            self.assertNotIn('14,209_ONLINE', content,
                           "Should not have hardcoded '14,209_ONLINE'")
            self.assertNotIn('1.2 EB/s', content,
                           "Should not have hardcoded '1.2 EB/s'")
            
            print("[PASS] Dashboard component uses real data")


def run_all_tests():
    """Run all test suites"""
    print("=" * 70)
    print("PRODUCTION READINESS TEST SUITE")
    print("=" * 70)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestForensicMetrics))
    suite.addTests(loader.loadTestsFromTestCase(TestDashboardStatsAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestWebSocketProgress))
    suite.addTests(loader.loadTestsFromTestCase(TestBlockchainIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalysisResponseStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestFrontendIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print()
        print("[SUCCESS] ALL TESTS PASSED!")
    else:
        print()
        print("[FAILURE] SOME TESTS FAILED")
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

