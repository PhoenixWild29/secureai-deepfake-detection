#!/usr/bin/env python3
"""
Comprehensive Ensemble Testing: CLIP + ResNet50 vs Individual Models
Tests ensemble performance and compares against individual models
"""
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from PIL import Image
import cv2
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

# Add ai_model to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_model'))

try:
    from detect import detect_fake
    from ensemble_detector import EnsembleDetector
    print("✅ Detection modules imported successfully")
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

class EnsembleTester:
    """Comprehensive ensemble testing"""
    
    def __init__(self):
        self.results = {
            'individual_models': {},
            'ensemble': {},
            'comparison': {},
            'timestamp': datetime.now().isoformat()
        }
    
    def find_test_videos(self) -> Dict[str, List[str]]:
        """Find test videos"""
        test_data = {'real': [], 'fake': []}
        
        # Look for videos in uploads or test directories
        search_dirs = [
            'uploads',
            'test_videos',
            'datasets/unified_deepfake/test',
            'datasets/unified_deepfake/val'
        ]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                # Real videos
                real_dir = Path(search_dir) / 'real'
                if real_dir.exists():
                    test_data['real'].extend([
                        str(p) for p in real_dir.glob('*.mp4')[:10]
                    ])
                
                # Fake videos
                fake_dir = Path(search_dir) / 'fake'
                if fake_dir.exists():
                    test_data['fake'].extend([
                        str(p) for p in fake_dir.glob('*.mp4')[:10]
                    ])
        
        # Also check for any videos in uploads
        uploads_dir = Path('uploads')
        if uploads_dir.exists():
            all_videos = list(uploads_dir.glob('*.mp4'))[:20]
            # If we don't have labeled data, use all videos
            if not test_data['real'] and not test_data['fake']:
                # We'll test but won't know ground truth
                test_data['unknown'] = [str(p) for p in all_videos]
        
        return test_data
    
    def test_model_on_video(self, video_path: str, model_type: str, ground_truth: Optional[int] = None) -> Dict:
        """Test a specific model on a video"""
        try:
            start_time = time.time()
            result = detect_fake(video_path, model_type=model_type)
            processing_time = time.time() - start_time
            
            # Extract prediction
            is_fake = result.get('is_fake', False)
            confidence = result.get('confidence', 0.0)
            
            # For ensemble, get individual model scores
            if model_type == 'ensemble':
                clip_prob = result.get('clip_fake_probability', 0.5)
                resnet_prob = result.get('resnet_fake_probability', 0.5)
                ensemble_prob = result.get('ensemble_fake_probability', confidence)
                
                return {
                    'video_path': video_path,
                    'ground_truth': ground_truth,
                    'prediction': 1 if is_fake else 0,
                    'confidence': confidence,
                    'ensemble_probability': ensemble_prob,
                    'clip_probability': clip_prob,
                    'resnet_probability': resnet_prob,
                    'processing_time': processing_time,
                    'method': result.get('method', model_type),
                    'success': True
                }
            else:
                return {
                    'video_path': video_path,
                    'ground_truth': ground_truth,
                    'prediction': 1 if is_fake else 0,
                    'confidence': confidence,
                    'processing_time': processing_time,
                    'method': result.get('method', model_type),
                    'success': True
                }
        except Exception as e:
            return {
                'video_path': video_path,
                'ground_truth': ground_truth,
                'error': str(e),
                'success': False
            }
    
    def test_all_models(self, test_data: Dict) -> Dict:
        """Test all models on available videos"""
        print("\n" + "=" * 70)
        print("🧪 Testing All Models")
        print("=" * 70)
        
        all_results = {
            'clip': [],
            'resnet': [],
            'ensemble': []
        }
        
        # Get all videos to test
        all_videos = []
        for label, videos in test_data.items():
            if label == 'unknown':
                # Unknown videos - test but can't calculate accuracy
                for video in videos:
                    all_videos.append((video, None))
            else:
                # Labeled videos
                ground_truth = 1 if label == 'fake' else 0
                for video in videos:
                    all_videos.append((video, ground_truth))
        
        if not all_videos:
            print("⚠️  No test videos found!")
            print("   Looking for videos in:")
            print("     - uploads/")
            print("     - test_videos/")
            print("     - datasets/unified_deepfake/test/ or /val/")
            return {}
        
        print(f"\n📹 Found {len(all_videos)} video(s) to test")
        
        # Test each model
        for video_path, ground_truth in all_videos:
            print(f"\n   Testing: {os.path.basename(video_path)}")
            
            # Test CLIP (via enhanced)
            print("      CLIP...", end=" ", flush=True)
            clip_result = self.test_model_on_video(video_path, 'enhanced', ground_truth)
            if clip_result.get('success'):
                all_results['clip'].append(clip_result)
                print(f"✅ (prob: {clip_result.get('confidence', 0):.3f})")
            else:
                print(f"❌ {clip_result.get('error', 'Failed')}")
            
            # Test ResNet
            print("      ResNet...", end=" ", flush=True)
            resnet_result = self.test_model_on_video(video_path, 'resnet', ground_truth)
            if resnet_result.get('success'):
                all_results['resnet'].append(resnet_result)
                print(f"✅ (prob: {resnet_result.get('confidence', 0):.3f})")
            else:
                print(f"❌ {resnet_result.get('error', 'Failed')}")
            
            # Test Ensemble
            print("      Ensemble...", end=" ", flush=True)
            ensemble_result = self.test_model_on_video(video_path, 'ensemble', ground_truth)
            if ensemble_result.get('success'):
                all_results['ensemble'].append(ensemble_result)
                print(f"✅ (prob: {ensemble_result.get('ensemble_probability', 0):.3f})")
            else:
                print(f"❌ {ensemble_result.get('error', 'Failed')}")
        
        return all_results
    
    def calculate_metrics(self, results: List[Dict], model_name: str) -> Dict:
        """Calculate metrics for a model"""
        if not results:
            return {}
        
        # Filter successful results with ground truth
        valid_results = [r for r in results if r.get('success') and r.get('ground_truth') is not None]
        
        if not valid_results:
            return {
                'model': model_name,
                'samples_tested': len(results),
                'note': 'No ground truth labels available - showing predictions only'
            }
        
        predictions = [r['prediction'] for r in valid_results]
        labels = [r['ground_truth'] for r in valid_results]
        confidences = [r['confidence'] for r in valid_results]
        times = [r['processing_time'] for r in valid_results]
        
        accuracy = accuracy_score(labels, predictions)
        precision = precision_score(labels, predictions, zero_division=0)
        recall = recall_score(labels, predictions, zero_division=0)
        f1 = f1_score(labels, predictions, zero_division=0)
        
        try:
            auc = roc_auc_score(labels, confidences)
        except:
            auc = 0.5
        
        return {
            'model': model_name,
            'samples_tested': len(valid_results),
            'accuracy': round(accuracy, 4),
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1_score': round(f1, 4),
            'auc_roc': round(auc, 4),
            'avg_processing_time': round(np.mean(times), 2),
            'avg_confidence': round(np.mean(confidences), 4)
        }
    
    def compare_models(self, all_results: Dict):
        """Compare all models"""
        print("\n" + "=" * 70)
        print("📊 Model Comparison")
        print("=" * 70)
        
        # Calculate metrics for each model
        clip_metrics = self.calculate_metrics(all_results.get('clip', []), 'CLIP')
        resnet_metrics = self.calculate_metrics(all_results.get('resnet', []), 'ResNet50')
        ensemble_metrics = self.calculate_metrics(all_results.get('ensemble', []), 'Ensemble')
        
        self.results['individual_models']['clip'] = clip_metrics
        self.results['individual_models']['resnet'] = resnet_metrics
        self.results['ensemble'] = ensemble_metrics
        
        # Print comparison
        print("\n📈 Performance Metrics:")
        print("-" * 70)
        
        for metrics in [clip_metrics, resnet_metrics, ensemble_metrics]:
            if not metrics:
                continue
            
            print(f"\n{metrics['model']}:")
            if 'note' in metrics:
                print(f"   {metrics['note']}")
                print(f"   Samples tested: {metrics['samples_tested']}")
            else:
                print(f"   Accuracy: {metrics['accuracy']:.2%}")
                print(f"   Precision: {metrics['precision']:.2%}")
                print(f"   Recall: {metrics['recall']:.2%}")
                print(f"   F1-Score: {metrics['f1_score']:.2%}")
                print(f"   AUC-ROC: {metrics['auc_roc']:.4f}")
                print(f"   Avg Processing Time: {metrics['avg_processing_time']:.2f}s")
                print(f"   Avg Confidence: {metrics['avg_confidence']:.3f}")
        
        # Compare if we have metrics
        if clip_metrics and 'accuracy' in clip_metrics and resnet_metrics and 'accuracy' in resnet_metrics and ensemble_metrics and 'accuracy' in ensemble_metrics:
            comparison = {
                'clip_accuracy': clip_metrics['accuracy'],
                'resnet_accuracy': resnet_metrics['accuracy'],
                'ensemble_accuracy': ensemble_metrics['accuracy'],
                'improvement_over_clip': ensemble_metrics['accuracy'] - clip_metrics['accuracy'],
                'improvement_over_resnet': ensemble_metrics['accuracy'] - resnet_metrics['accuracy'],
                'best_model': 'ensemble' if ensemble_metrics['accuracy'] >= max(clip_metrics['accuracy'], resnet_metrics['accuracy']) else ('clip' if clip_metrics['accuracy'] > resnet_metrics['accuracy'] else 'resnet')
            }
            
            self.results['comparison'] = comparison
            
            print("\n📊 Comparison Summary:")
            print("-" * 70)
            print(f"   Ensemble vs CLIP: {comparison['improvement_over_clip']:+.2%}")
            print(f"   Ensemble vs ResNet: {comparison['improvement_over_resnet']:+.2%}")
            print(f"   Best Model: {comparison['best_model'].upper()}")
            
            if comparison['improvement_over_clip'] > 0 or comparison['improvement_over_resnet'] > 0:
                print("\n   ✅ Ensemble provides improvement!")
            elif comparison['improvement_over_clip'] == 0 and comparison['improvement_over_resnet'] == 0:
                print("\n   ⚠️  Ensemble matches best individual model")
            else:
                print("\n   ⚠️  Individual model performs better (may need ensemble tuning)")
    
    def run_full_test(self, output_file: str = 'ensemble_test_results.json'):
        """Run complete ensemble test"""
        print("\n" + "=" * 70)
        print("🚀 Comprehensive Ensemble Testing")
        print("=" * 70)
        
        # Find test videos
        print("\n📁 Finding test videos...")
        test_data = self.find_test_videos()
        
        if not test_data or (not test_data.get('real') and not test_data.get('fake') and not test_data.get('unknown')):
            print("⚠️  No test videos found!")
            print("\n   To test the ensemble, you need:")
            print("   1. Upload a test video to the 'uploads/' directory, OR")
            print("   2. Place videos in 'test_videos/real/' and 'test_videos/fake/' directories")
            print("\n   The script will test on any videos it finds.")
            return
        
        # Test all models
        all_results = self.test_all_models(test_data)
        
        if not all_results:
            return
        
        # Compare models
        self.compare_models(all_results)
        
        # Save results
        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\n✅ Results saved to: {output_file}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")
        
        print("\n" + "=" * 70)
        print("✅ Ensemble Testing Complete!")
        print("=" * 70)

if __name__ == "__main__":
    tester = EnsembleTester()
    tester.run_full_test()

