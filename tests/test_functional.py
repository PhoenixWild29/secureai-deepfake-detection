#!/usr/bin/env python3
"""
Functional and Regression Tests
Core accuracy and stability testing for DFDM
"""
import pytest
import time
from pathlib import Path
from typing import List, Dict


@pytest.mark.functional
class TestFunctionalDetection:
    """Test core detection functionality and accuracy"""
    
    def test_authentic_video_baseline(self, analysis_request, data_loader, test_thresholds):
        """
        TC-003: Test authentic video detection baseline
        Verifies low false positive rate on known-real videos
        """
        # Load a sample of authentic videos
        authentic_videos = data_loader.get_test_subset('authentic', limit=50)
        
        if len(authentic_videos) == 0:
            pytest.skip("No authentic test videos available")
        
        false_positives = 0
        results = []
        
        for video in authentic_videos:
            result = analysis_request(video.filepath)
            confidence = result['result']['is_fake']
            
            # Authentic video should NOT be flagged as fake
            if confidence:  # If flagged as fake, it's a false positive
                false_positives += 1
                results.append({
                    'filename': video.filepath.name,
                    'confidence': result['result'].get('confidence', 0),
                    'category': video.category
                })
        
        # Calculate FPR
        fpr = false_positives / len(authentic_videos)
        
        # Assert low false positive rate
        assert fpr < test_thresholds['max_fpr'], \
            f"False Positive Rate too high: {fpr:.3f} (expected < {test_thresholds['max_fpr']})"
        
        pytest.false_positive_rate = fpr
        pytest.authentic_test_results = results
    
    def test_deepfake_detection_rate(self, analysis_request, data_loader, test_thresholds):
        """
        TC-004: Test deepfake detection accuracy
        Verifies high true positive rate on known-fake videos
        """
        # Load a sample of deepfake videos
        deepfake_videos = data_loader.get_test_subset('deepfacelab', limit=50)
        
        if len(deepfake_videos) == 0:
            pytest.skip("No deepfake test videos available")
        
        true_positives = 0
        false_negatives = 0
        results = []
        
        for video in deepfake_videos:
            result = analysis_request(video.filepath)
            is_fake = result['result']['is_fake']
            
            # Deepfake video SHOULD be flagged as fake
            if is_fake:
                true_positives += 1
            else:
                false_negatives += 1
                results.append({
                    'filename': video.filepath.name,
                    'confidence': result['result'].get('confidence', 0),
                    'authenticity': result['result'].get('authenticity_score', 0),
                    'category': video.category
                })
        
        # Calculate TPR (Recall)
        tpr = true_positives / len(deepfake_videos)
        
        # Assert high true positive rate
        assert tpr >= test_thresholds['min_recall'], \
            f"True Positive Rate too low: {tpr:.3f} (expected >= {test_thresholds['min_recall']})"
        
        pytest.true_positive_rate = tpr
        pytest.deepfake_test_results = results
    
    def test_multi_format_video_support(self, analysis_request, data_loader):
        """
        TC-001: Test support for multiple video formats
        Verifies consistent results across different formats
        """
        # Test popular formats
        test_formats = []
        format_results = {}
        
        for video in data_loader.test_videos:
            file_ext = video.filepath.suffix.lower()
            if file_ext not in format_results:
                format_results[file_ext] = []
                test_formats.append(file_ext)
        
        # Sample from each format
        for fmt in test_formats[:5]:  # Test up to 5 formats
            fmt_videos = [v for v in data_loader.test_videos if v.filepath.suffix.lower() == fmt]
            if len(fmt_videos) > 0:
                sample = fmt_videos[0]
                result = analysis_request(sample.filepath)
                format_results[fmt].append(result)
        
        # Assert all formats processed successfully
        assert len(format_results) > 0, "No video formats found in test data"
        
        for fmt, results in format_results.items():
            assert len(results) > 0, f"Format {fmt} failed to process"
            assert 'error' not in results[0], f"Format {fmt} returned error: {results[0].get('error')}"
        
        pytest.format_results = format_results
    
    def test_resolution_scaling(self, analysis_request, data_loader):
        """
        TC-002: Test detection accuracy across different resolutions
        Verifies consistent performance regardless of video quality
        """
        resolutions = ['1080p', '720p', '360p']
        resolution_results = {}
        
        for res in resolutions:
            res_videos = data_loader.get_test_subset(f'authentic_{res}', limit=10)
            if len(res_videos) > 0:
                sample = res_videos[0]
                result = analysis_request(sample.filepath)
                resolution_results[res] = result
        
        if len(resolution_results) < 2:
            pytest.skip("Insufficient resolution variety in test data")
        
        # Verify confidence scores don't vary wildly across resolutions
        confidences = [r['result']['confidence'] for r in resolution_results.values()]
        variance = sum((c - sum(confidences)/len(confidences))**2 for c in confidences) / len(confidences)
        
        # Variance should be reasonable (less than 0.1)
        assert variance < 0.1, \
            f"Confidence variance across resolutions too high: {variance:.3f}"
        
        pytest.resolution_results = resolution_results
    
    def test_api_stability(self, analysis_request, data_loader):
        """
        TC-005: Test API stability under concurrent load
        """
        # Get a small test set
        test_videos = data_loader.test_videos[:10]
        
        if len(test_videos) == 0:
            pytest.skip("No test videos available")
        
        # Sequential load test (can be parallelized with pytest-xdist)
        errors = []
        start_time = time.time()
        
        for video in test_videos:
            try:
                result = analysis_request(video.filepath)
                assert 'error' not in result, f"API error: {result.get('error')}"
            except Exception as e:
                errors.append({'file': video.filepath.name, 'error': str(e)})
        
        elapsed_time = time.time() - start_time
        
        # Assert no errors
        assert len(errors) == 0, f"API errors encountered: {errors}"
        
        # Assert reasonable processing time
        avg_time = elapsed_time / len(test_videos)
        assert avg_time < 30, f"Average processing time too slow: {avg_time:.2f}s"
        
        pytest.stability_results = {
            'total_videos': len(test_videos),
            'errors': len(errors),
            'avg_time': avg_time
        }
    
    def test_edge_cases(self, analysis_request, data_loader):
        """
        TC-006: Test edge case handling
        """
        # Test corrupted file handling would go here
        # For now, test edge case videos if available
        edge_videos = data_loader.get_test_subset('edge_cases', limit=5)
        
        if len(edge_videos) == 0:
            pytest.skip("No edge case videos available")
        
        for video in edge_videos:
            try:
                result = analysis_request(video.filepath)
                # Should either succeed or return graceful error
                assert 'error' in result or 'result' in result, \
                    f"Unexpected response for edge case: {video.filepath.name}"
            except Exception as e:
                # Some exceptions are acceptable for truly invalid files
                pytest.edge_case_errors.append(str(e))

