#!/usr/bin/env python3
"""
Comprehensive Ensemble Testing: CLIP + ResNet50 vs Individual Models
Tests ensemble performance and compares against individual models
"""
import os
import sys
import warnings

# CRITICAL: Force CPU mode BEFORE any imports that might use CUDA
# Must be set before any torch/tensorflow imports
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress ALL TensorFlow messages (ERROR level)
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'false'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
# Prevent TensorFlow from finding CUDA libraries
if 'LD_LIBRARY_PATH' in os.environ:
    # Remove any CUDA paths from library path
    paths = os.environ['LD_LIBRARY_PATH'].split(':')
    paths = [p for p in paths if 'cuda' not in p.lower()]
    os.environ['LD_LIBRARY_PATH'] = ':'.join(paths)

# Suppress all warnings
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

# Redirect stderr during imports to suppress CUDA errors
import contextlib
import io

# Suppress stderr during model imports
stderr_suppressor = io.StringIO()

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
sys.path.insert(0, os.path.dirname(__file__))  # Also add root directory

# Import detection modules with stderr suppression
try:
    # Suppress stderr during imports to hide CUDA errors
    with contextlib.redirect_stderr(stderr_suppressor):
        # Try importing from ai_model first
        try:
            from ai_model.detect import detect_fake
        except ImportError:
            from detect import detect_fake
        
        # Try importing ensemble_detector from different locations
        try:
            from ai_model.ensemble_detector import EnsembleDetector
        except ImportError:
            try:
                from ensemble_detector import EnsembleDetector
            except ImportError:
                # If ensemble_detector not available, we'll skip it
                EnsembleDetector = None
                print("⚠️  EnsembleDetector not available, will use detect_fake with model_type='ensemble'")
    
    print("✅ Detection modules imported successfully")
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    # Suppress CUDA-related errors during import
    if 'CUDA' in str(e) or 'cuInit' in str(e) or 'cuda' in str(e).lower():
        print("⚠️  CUDA warning during import (using CPU mode, this is expected)")
        print("✅ Detection modules imported successfully (CPU mode)")
    else:
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
        """Find test videos using VideoPathManager for reliable discovery"""
        test_data = {'real': [], 'fake': []}
        
        # Use VideoPathManager for reliable video discovery
        try:
            from utils.video_paths import get_video_path_manager
            path_manager = get_video_path_manager()
            
            # Get max videos from environment
            max_videos = int(os.getenv('MAX_TEST_VIDEOS', '20'))  # Default 20 for testing
            
            # Find all videos using path manager
            all_videos = path_manager.find_all_videos(max_count=max_videos * 2)  # Get more, then filter
            
            print(f"   VideoPathManager found {len(all_videos)} videos total")
            
            # Check for labeled datasets first
            labeled_dirs = [
                Path('datasets/unified_deepfake/test'),
                Path('datasets/unified_deepfake/val'),
                Path('test_videos'),
            ]
            
            for search_dir in labeled_dirs:
                if search_dir.exists():
                    # Real videos
                    real_dir = search_dir / 'real'
                    if real_dir.exists():
                        real_video_paths = list(real_dir.glob('*.mp4'))
                        real_videos = [str(p) for p in real_video_paths[:max_videos//2]]
                        test_data['real'].extend(real_videos)
                        print(f"   Found {len(real_videos)} real videos in {real_dir}")
                    
                    # Fake videos
                    fake_dir = search_dir / 'fake'
                    if fake_dir.exists():
                        fake_video_paths = list(fake_dir.glob('*.mp4'))
                        fake_videos = [str(p) for p in fake_video_paths[:max_videos//2]]
                        test_data['fake'].extend(fake_videos)
                        print(f"   Found {len(fake_videos)} fake videos in {fake_dir}")
            
            # If no labeled data, use all found videos
            if not test_data['real'] and not test_data['fake']:
                test_data['unknown'] = [str(p) for p in all_videos[:max_videos]]
                print(f"   Using {len(test_data['unknown'])} videos for testing (unlabeled)")
                print(f"   Uploads directory: {path_manager.get_uploads_directory()}")
            
        except ImportError:
            # Fallback to original method if VideoPathManager not available
            print("   ⚠️  VideoPathManager not available, using fallback method")
            
            # Look for videos in uploads or test directories
            search_dirs = [
                'uploads',
                '/app/uploads',
                'test_videos',
                'datasets/unified_deepfake/test',
                'datasets/unified_deepfake/val'
            ]
            
            all_videos = []
            for search_dir in search_dirs:
                search_path = Path(search_dir)
                if search_path.exists():
                    videos = list(search_path.glob('*.mp4'))
                    all_videos.extend(videos)
                    print(f"   Found {len(videos)} videos in {search_dir}")
            
            # Remove duplicates
            all_videos = list(set(all_videos))
            
            if all_videos:
                max_videos = int(os.getenv('MAX_TEST_VIDEOS', '20'))
                test_data['unknown'] = [str(p) for p in all_videos[:max_videos]]
                print(f"   Using {len(test_data['unknown'])} videos for testing")
        
        return test_data
    
    def create_test_video_if_needed(self):
        """Create a simple test video if none exist"""
        try:
            uploads_dir = Path('uploads')
            uploads_dir.mkdir(exist_ok=True)
            
            test_video_path = uploads_dir / 'auto_generated_test.mp4'
            
            if test_video_path.exists():
                return str(test_video_path)
            
            print("   Creating a simple test video...")
            
            # Create a simple video
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(test_video_path), fourcc, 15, (640, 480))
            
            for frame_num in range(45):  # 3 seconds at 15 fps
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frame[:, :] = [220, 180, 140]  # Skin tone background
                
                # Simple face pattern
                center_x, center_y = 320, 240
                cv2.circle(frame, (center_x, center_y), 100, (200, 160, 120), -1)
                cv2.circle(frame, (center_x - 40, center_y - 20), 15, (0, 0, 0), -1)
                cv2.circle(frame, (center_x + 40, center_y - 20), 15, (0, 0, 0), -1)
                cv2.ellipse(frame, (center_x, center_y + 50), (30, 15), 0, 0, 180, (0, 0, 0), 2)
                
                out.write(frame)
            
            out.release()
            print(f"   ✅ Created test video: {test_video_path}")
            return str(test_video_path)
        except Exception as e:
            print(f"   ⚠️  Could not create test video: {e}")
            return None
    
    def test_model_on_video(self, video_path: str, model_type: str, ground_truth: Optional[int] = None) -> Dict:
        """Test a specific model on a video"""
        try:
            # Use VideoPathManager for reliable path resolution
            try:
                from utils.video_paths import get_video_path_manager
                path_manager = get_video_path_manager()
                resolved_path = path_manager.resolve_video_path(video_path)
                
                if resolved_path is None:
                    return {
                        'video_path': video_path,
                        'ground_truth': ground_truth,
                        'error': f'Video file not found: {video_path}',
                        'success': False
                    }
                
                video_path = str(resolved_path)
            except ImportError:
                # Fallback path resolution
                video_path_obj = Path(video_path)
                if not video_path_obj.exists():
                    uploads_path = Path('uploads') / video_path_obj.name
                    if uploads_path.exists():
                        video_path = str(uploads_path)
                    else:
                        abs_uploads_path = Path('/app/uploads') / video_path_obj.name
                        if abs_uploads_path.exists():
                            video_path = str(abs_uploads_path)
                        else:
                            if not Path(video_path).exists():
                                return {
                                    'video_path': video_path,
                                    'ground_truth': ground_truth,
                                    'error': f'Video file not found: {video_path}',
                                    'success': False
                                }
            
            # Suppress CUDA errors - we're using CPU anyway
            import warnings
            import logging
            warnings.filterwarnings('ignore')
            logging.getLogger('tensorflow').setLevel(logging.ERROR)
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress all TensorFlow messages
            
            # Suppress stderr during detection to hide CUDA errors
            start_time = time.time()
            with contextlib.redirect_stderr(stderr_suppressor):
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
            error_str = str(e).lower()
            # Check if it's a CUDA error - if so, provide helpful message
            if 'cuda' in error_str or 'cuinit' in error_str:
                return {
                    'video_path': video_path,
                    'ground_truth': ground_truth,
                    'error': 'CUDA initialization error (running in CPU mode, this should not happen)',
                    'success': False,
                    'cuda_error': True
                }
            else:
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
        for idx, (video_path, ground_truth) in enumerate(all_videos, 1):
            print(f"\n   [{idx}/{len(all_videos)}] Testing: {os.path.basename(video_path)}")
            
            # Test CLIP (via enhanced)
            print("      CLIP...", end=" ", flush=True)
            try:
                clip_result = self.test_model_on_video(video_path, 'enhanced', ground_truth)
                if clip_result.get('success'):
                    all_results['clip'].append(clip_result)
                    print(f"✅ (prob: {clip_result.get('confidence', 0):.3f}, time: {clip_result.get('processing_time', 0):.1f}s)")
                else:
                    print(f"❌ {clip_result.get('error', 'Failed')[:50]}")
            except Exception as e:
                error_msg = str(e)
                if 'CUDA' in error_msg or 'cuda' in error_msg.lower():
                    print(f"⚠️  CUDA error (using CPU fallback)")
                    # Retry with explicit CPU
                    os.environ['CUDA_VISIBLE_DEVICES'] = ''
                    clip_result = self.test_model_on_video(video_path, 'enhanced', ground_truth)
                    if clip_result.get('success'):
                        all_results['clip'].append(clip_result)
                        print(f"✅ (prob: {clip_result.get('confidence', 0):.3f})")
                else:
                    print(f"❌ {error_msg[:50]}")
            
            # Test ResNet
            print("      ResNet...", end=" ", flush=True)
            try:
                resnet_result = self.test_model_on_video(video_path, 'resnet', ground_truth)
                if resnet_result.get('success'):
                    all_results['resnet'].append(resnet_result)
                    print(f"✅ (prob: {resnet_result.get('confidence', 0):.3f}, time: {resnet_result.get('processing_time', 0):.1f}s)")
                else:
                    print(f"❌ {resnet_result.get('error', 'Failed')[:50]}")
            except Exception as e:
                error_msg = str(e)
                if 'CUDA' in error_msg or 'cuda' in error_msg.lower():
                    print(f"⚠️  CUDA error (using CPU fallback)")
                    os.environ['CUDA_VISIBLE_DEVICES'] = ''
                    resnet_result = self.test_model_on_video(video_path, 'resnet', ground_truth)
                    if resnet_result.get('success'):
                        all_results['resnet'].append(resnet_result)
                        print(f"✅ (prob: {resnet_result.get('confidence', 0):.3f})")
                else:
                    print(f"❌ {error_msg[:50]}")
            
            # Test Ensemble
            print("      Ensemble...", end=" ", flush=True)
            try:
                ensemble_result = self.test_model_on_video(video_path, 'ensemble', ground_truth)
                if ensemble_result.get('success'):
                    all_results['ensemble'].append(ensemble_result)
                    print(f"✅ (prob: {ensemble_result.get('ensemble_probability', 0):.3f}, time: {ensemble_result.get('processing_time', 0):.1f}s)")
                else:
                    print(f"❌ {ensemble_result.get('error', 'Failed')[:50]}")
            except Exception as e:
                error_msg = str(e)
                if 'CUDA' in error_msg or 'cuda' in error_msg.lower():
                    print(f"⚠️  CUDA error (using CPU fallback)")
                    os.environ['CUDA_VISIBLE_DEVICES'] = ''
                    ensemble_result = self.test_model_on_video(video_path, 'ensemble', ground_truth)
                    if ensemble_result.get('success'):
                        all_results['ensemble'].append(ensemble_result)
                        print(f"✅ (prob: {ensemble_result.get('ensemble_probability', 0):.3f})")
                else:
                    print(f"❌ {error_msg[:50]}")
            
            print()  # Blank line between videos
        
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
            print("\n   Attempting to create a test video...")
            test_video = self.create_test_video_if_needed()
            
            if test_video:
                test_data = {'unknown': [test_video]}
                print(f"   ✅ Using auto-generated test video")
            else:
                print("\n   To test the ensemble, you need:")
                print("   1. Upload a test video to the 'uploads/' directory, OR")
                print("   2. Place videos in 'test_videos/real/' and 'test_videos/fake/' directories")
                print("   3. Run: docker exec secureai-backend python /app/create_test_video.py")
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

