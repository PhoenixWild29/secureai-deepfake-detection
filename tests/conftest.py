#!/usr/bin/env python3
"""
Pytest Configuration and Shared Fixtures
Global setup for all DFDM tests
"""
import pytest
import time
import requests
import json
import os
from pathlib import Path
from typing import Dict, Optional, List
import warnings

# Suppress specific warnings
warnings.filterwarnings("ignore", category=UserWarning)


# Global configuration
@pytest.fixture(scope="session")
def api_config():
    """Configuration for API endpoint"""
    config = {
        'base_url': os.getenv('DFDM_API_URL', 'http://localhost:5000'),
        'analyze_endpoint': '/api/analyze',
        'health_endpoint': '/api/health',
        'timeout': 120,  # 2 minute timeout
        'retry_attempts': 3,
        'retry_delay': 2  # seconds
    }
    return config


@pytest.fixture(scope="session")
def api_client(api_config):
    """
    API client fixture with retry logic
    Returns a configured requests session for API calls
    """
    session = requests.Session()
    session.base_url = api_config['base_url']
    
    # Add retry logic
    class APIClient:
        def __init__(self, session, config):
            self.session = session
            self.config = config
            self.base_url = config['base_url']
        
        def call(self, endpoint, **kwargs):
            for attempt in range(self.config['retry_attempts']):
                try:
                    response = self.session.post(
                        f"{self.config['base_url']}{endpoint}",
                        timeout=self.config['timeout'],
                        **kwargs
                    )
                    response.raise_for_status()
                    return response
                except requests.exceptions.RequestException as e:
                    if attempt == self.config['retry_attempts'] - 1:
                        raise
                    time.sleep(self.config['retry_delay'])
    
    return APIClient(session, api_config)


@pytest.fixture(scope="session")
def data_loader():
    """Load test dataset"""
    from tests.test_data_loader import TestDataLoader
    
    loader = TestDataLoader(base_path="tests/test_data")
    try:
        videos = loader.load_all_test_videos()
        if len(videos) == 0:
            pytest.skip("No test data found")
        return loader
    except FileNotFoundError:
        pytest.skip("Test data directory not found")


@pytest.fixture(scope="session")
def health_check(api_client, api_config):
    """Verify API is healthy before running tests"""
    try:
        response = requests.get(
            f"{api_config['base_url']}{api_config['health_endpoint']}",
            timeout=5
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        pytest.fail("DFDM API is not accessible. Start the server first.")


@pytest.fixture
def analysis_request(api_client, api_config):
    """
    Main fixture for submitting video analysis requests
    Handles file upload and response parsing
    """
    def _analyze_video(video_path: Path, model_type: str = 'resnet') -> Dict:
        """
        Submit video for analysis and return parsed response
        
        Args:
            video_path: Path to video file
            model_type: Detection model to use
            
        Returns:
            Dictionary with parsed analysis results
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        # Prepare file upload
        with open(video_path, 'rb') as video_file:
            files = {'video': video_file}
            data = {'model_type': model_type} if 'model_type' in globals() else {}
            
            # Make API call with timing
            start_time = time.time()
            response = api_client.call(
                api_config['analyze_endpoint'],
                files=files,
                data=data
            )
            elapsed_time = time.time() - start_time
            
            # Parse response
            result = response.json()
            result['api_latency'] = elapsed_time
            
            return result
    
    return _analyze_video


# Test threshold configuration
@pytest.fixture(scope="session")
def test_thresholds():
    """
    Performance thresholds and acceptance criteria for tests
    These can be overridden per test
    """
    return {
        # Functional tests
        'confidence_threshold_real': 0.85,  # Real videos should have high authenticity
        'confidence_threshold_fake': 0.85,  # Fake videos should have high detection confidence
        
        # Performance tests
        'max_latency_per_second': 0.5,  # Max 0.5s per second of video
        'max_latency_absolute': 60,  # Absolute max 60 seconds
        
        # Adversarial tests
        'adversarial_robustness_threshold': 0.85,  # Maintain 85% accuracy on adversarial samples
        
        # Accuracy thresholds
        'min_accuracy': 0.95,
        'min_precision': 0.92,
        'min_recall': 0.90,
        'min_f1': 0.91,
        'max_fpr': 0.05,
        'max_fnr': 0.10,
        
        # Fairness thresholds
        'demographic_parity_cv': 0.15,  # Coefficient of variation
        'equalized_odds_threshold': 0.10,
        
        # Explainability thresholds
        'min_saliency_overlap': 0.70,
        'max_ece': 0.05,
    }


# Results collection fixture
@pytest.fixture(scope="session")
def results_collector():
    """
    Collect test results throughout the session for reporting
    """
    results = {
        'total_tests': 0,
        'passed_tests': 0,
        'failed_tests': 0,
        'skipped_tests': 0,
        'test_details': [],
        'false_positives': [],
        'false_negatives': [],
        'performance_metrics': {},
        'categories': {}
    }
    
    return results


# Pytest configuration
def pytest_configure(config):
    """Configure pytest options"""
    config.addinivalue_line(
        "markers", "functional: Mark test as functional/regression test"
    )
    config.addinivalue_line(
        "markers", "performance: Mark test as performance/latency test"
    )
    config.addinivalue_line(
        "markers", "adversarial: Mark test as adversarial robustness test"
    )
    config.addinivalue_line(
        "markers", "bias: Mark test as bias/fairness test"
    )
    config.addinivalue_line(
        "markers", "explainability: Mark test as XAI/explainability test"
    )
    config.addinivalue_line(
        "markers", "slow: Mark test as slow (may take several minutes)"
    )


def pytest_collection_modifyitems(config, items):
    """
    Automatically mark slow tests
    """
    for item in items:
        # Mark tests that are likely to be slow
        if any(keyword in item.name.lower() for keyword in 
               ['compression', 'adversarial', 'demographic', 'full_dataset']):
            item.add_marker(pytest.mark.slow)

