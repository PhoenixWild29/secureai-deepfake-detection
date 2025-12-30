#!/usr/bin/env python3
"""
Adversarial Robustness Tests
Test DFDM resilience against evasion attempts and adversarial attacks
"""
import pytest
import numpy as np
from pathlib import Path


@pytest.mark.adversarial
class TestAdversarialRobustness:
    """Test model robustness against adversarial attacks and evasion techniques"""
    
    def test_adversarial_pgd_attack(self, analysis_request, data_loader, test_thresholds):
        """
        Test resilience against Projected Gradient Descent (PGD) attacks
        Verify model maintains high accuracy on perturbed deepfakes
        """
        # Load adversarial test set
        adversarial_videos = data_loader.get_test_subset('adversarial_pgd', limit=50)
        
        if len(adversarial_videos) == 0:
            pytest.skip("No adversarial test videos available")
        
        correct_detections = 0
        total_videos = len(adversarial_videos)
        results = []
        
        for video in adversarial_videos:
            result = analysis_request(video.filepath)
            is_fake = result['result']['is_fake']
            confidence = result['result'].get('confidence', 0)
            
            # Adversarial deepfakes should still be detected as fake
            if is_fake:
                correct_detections += 1
            else:
                results.append({
                    'filename': video.filepath.name,
                    'confidence': confidence,
                    'predicted': 'real',
                    'expected': 'deepfake'
                })
        
        # Calculate robustness score
        robustness_score = correct_detections / total_videos
        
        # Assert robustness threshold
        threshold = test_thresholds['adversarial_robustness_threshold']
        assert robustness_score >= threshold, \
            f"Adversarial robustness too low: {robustness_score:.3f} (expected >= {threshold})"
        
        pytest.adversarial_robustness = robustness_score
        pytest.adversarial_failures = results
    
    def test_compression_resilience(self, analysis_request, data_loader):
        """
        Test detection accuracy on multi-pass compressed videos
        Verify model can detect deepfakes even after quality degradation
        """
        compression_rounds = []
        
        # Test different compression levels
        for round_num in [1, 3, 5]:
            compression_videos = data_loader.get_test_subset(f'compression_round_{round_num}', limit=20)
            if len(compression_videos) > 0:
                compression_rounds.append({'round': round_num, 'videos': compression_videos})
        
        if len(compression_rounds) == 0:
            pytest.skip("No compressed test videos available")
        
        compression_results = {}
        
        for round_data in compression_rounds:
            round_num = round_data['round']
            videos = round_data['videos']
            
            correct_detections = 0
            for video in videos:
                result = analysis_request(video.filepath)
                is_fake = result['result']['is_fake']
                
                if is_fake:  # Correctly identified as fake
                    correct_detections += 1
            
            accuracy = correct_detections / len(videos)
            compression_results[round_num] = {
                'accuracy': accuracy,
                'total': len(videos),
                'correct': correct_detections
            }
        
        # Verify accuracy degrades gracefully with compression
        baseline_acc = compression_results.get(1, {}).get('accuracy', 0)
        
        for round_num in sorted(compression_results.keys()):
            acc = compression_results[round_num]['accuracy']
            # Accuracy should remain reasonable even with heavy compression
            assert acc >= 0.80, \
                f"Detection accuracy too low after compression round {round_num}: {acc:.3f}"
            
            # But some degradation is expected
            if round_num > baseline_acc * 0.7:
                pytest.warn(f"Compression round {round_num} accuracy suspiciously high")
        
        pytest.compression_results = compression_results
    
    def test_diffusion_model_detection(self, analysis_request, data_loader):
        """
        Test detection of diffusion-based deepfakes (latest generation)
        Diffusion models are the newest threat
        """
        diffusion_videos = []
        
        # Test different diffusion generators
        for category in ['stable_diffusion', 'runway_gen2']:
            category_videos = data_loader.get_test_subset(category, limit=30)
            diffusion_videos.extend(category_videos)
        
        if len(diffusion_videos) == 0:
            pytest.skip("No diffusion-based test videos available")
        
        detected_count = 0
        category_results = {}
        
        for video in diffusion_videos:
            result = analysis_request(video.filepath)
            is_fake = result['result']['is_fake']
            confidence = result['result'].get('confidence', 0)
            
            if is_fake:
                detected_count += 1
            
            # Track by category
            if video.category not in category_results:
                category_results[video.category] = {'total': 0, 'detected': 0}
            
            category_results[video.category]['total'] += 1
            if is_fake:
                category_results[video.category]['detected'] += 1
        
        overall_accuracy = detected_count / len(diffusion_videos)
        
        # Diffusion models are harder to detect, lower threshold
        assert overall_accuracy >= 0.85, \
            f"Diffusion model detection rate too low: {overall_accuracy:.3f}"
        
        # Calculate per-category accuracy
        for category, stats in category_results.items():
            category_acc = stats['detected'] / stats['total'] if stats['total'] > 0 else 0
            category_results[category]['accuracy'] = category_acc
        
        pytest.diffusion_results = {
            'overall_accuracy': overall_accuracy,
            'category_breakdown': category_results
        }
    
    def test_gan_detection_variants(self, analysis_request, data_loader):
        """
        Test detection of various GAN-based deepfake generators
        Compare performance across different GAN architectures
        """
        gan_categories = ['deepfacelab', 'faceswap', 'stylegan']
        gan_results = {}
        
        for category in gan_categories:
            category_videos = data_loader.get_test_subset(category, limit=30)
            
            if len(category_videos) > 0:
                detected = 0
                for video in category_videos:
                    result = analysis_request(video.filepath)
                    if result['result']['is_fake']:
                        detected += 1
                
                accuracy = detected / len(category_videos)
                gan_results[category] = {
                    'accuracy': accuracy,
                    'total': len(category_videos),
                    'detected': detected
                }
        
        if len(gan_results) == 0:
            pytest.skip("No GAN-based test videos available")
        
        # All GAN variants should maintain good detection rates
        for category, results in gan_results.items():
            assert results['accuracy'] >= 0.88, \
                f"GAN variant {category} detection too low: {results['accuracy']:.3f}"
        
        pytest.gan_variant_results = gan_results
    
    def test_audio_visual_mismatch(self, analysis_request, data_loader):
        """
        Test detection of audio-visual mismatch artifacts
        """
        av_videos = []
        
        for category in ['wav2lip', 'voice_clone']:
            category_videos = data_loader.get_test_subset(category, limit=25)
            av_videos.extend(category_videos)
        
        if len(av_videos) == 0:
            pytest.skip("No audio-visual test videos available")
        
        detected = 0
        for video in av_videos:
            result = analysis_request(video.filepath)
            if result['result']['is_fake']:
                detected += 1
        
        accuracy = detected / len(av_videos)
        
        assert accuracy >= 0.88, \
            f"Audio-visual mismatch detection too low: {accuracy:.3f}"
        
        pytest.audio_visual_accuracy = accuracy
    
    def test_low_quality_detection(self, analysis_request, data_loader):
        """
        Test detection of low-quality deepfakes
        Real-world videos are often low quality due to multiple shares
        """
        low_quality_videos = data_loader.get_test_subset('authentic_360p', limit=20)
        
        # Also test compressed
        compressed = data_loader.get_test_subset('compression', limit=20)
        low_quality_videos.extend(compressed)
        
        if len(low_quality_videos) == 0:
            pytest.skip("No low-quality test videos available")
        
        # Test with limited set for performance
        sample_size = min(30, len(low_quality_videos))
        test_sample = low_quality_videos[:sample_size]
        
        detected = 0
        for video in test_sample:
            result = analysis_request(video.filepath)
            # For low quality deepfakes, should still detect as fake
            if result['result']['is_fake']:
                detected += 1
        
        accuracy = detected / len(test_sample)
        
        # Lower threshold for low-quality videos
        assert accuracy >= 0.80, \
            f"Low-quality detection too low: {accuracy:.3f}"
        
        pytest.low_quality_accuracy = accuracy

