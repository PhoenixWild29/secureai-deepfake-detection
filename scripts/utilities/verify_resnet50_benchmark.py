#!/usr/bin/env python3
"""
ResNet50 Deepfake Detection Model Verification and Benchmarking
Comprehensive testing with measurable metrics
"""
import os
import sys
import torch
import torch.nn as nn
import numpy as np
import cv2
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from PIL import Image
from torchvision import transforms
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

# Add ai_model to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_model'))

try:
    from deepfake_classifier import ResNetDeepfakeClassifier
    print("✅ ResNetDeepfakeClassifier imported successfully")
except ImportError as e:
    print(f"❌ Failed to import ResNetDeepfakeClassifier: {e}")
    sys.exit(1)

class ResNet50Verifier:
    """Comprehensive ResNet50 verification and benchmarking"""
    
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.model_path = None
        self.results = {
            'verification': {},
            'benchmarks': {},
            'performance': {},
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"🔧 Using device: {self.device}")
        print("=" * 70)
    
    def verify_model_file(self) -> Dict[str, any]:
        """Step 1: Verify model file exists and structure"""
        print("\n📦 STEP 1: Verifying Model File")
        print("-" * 70)
        
        verification = {
            'file_exists': False,
            'file_path': None,
            'file_size_mb': 0,
            'model_structure': {},
            'is_trained': False,
            'parameter_count': 0
        }
        
        # Check multiple possible paths
        possible_paths = [
            'ai_model/resnet_resnet50_final.pth',
            'ai_model/resnet_resnet50_best.pth',
            'resnet_resnet50_final.pth',
            'resnet_resnet50_best.pth',
            os.path.join(os.path.dirname(__file__), 'ai_model', 'resnet_resnet50_final.pth'),
            os.path.join(os.path.dirname(__file__), 'ai_model', 'resnet_resnet50_best.pth')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                verification['file_exists'] = True
                verification['file_path'] = path
                self.model_path = path
                
                # Get file size
                file_size = os.path.getsize(path) / (1024 * 1024)  # MB
                verification['file_size_mb'] = round(file_size, 2)
                
                print(f"✅ Model file found: {path}")
                print(f"   Size: {file_size:.2f} MB")
                
                # Load and inspect model structure
                try:
                    state_dict = torch.load(path, map_location='cpu')
                    
                    # Count parameters
                    param_count = sum(p.numel() for p in state_dict.values() if isinstance(p, torch.Tensor))
                    verification['parameter_count'] = param_count
                    
                    # Check model structure
                    keys = list(state_dict.keys())
                    verification['model_structure'] = {
                        'total_layers': len(keys),
                        'has_classifier': 'fc.weight' in keys or 'model.fc.weight' in keys,
                        'sample_keys': keys[:5] if len(keys) > 5 else keys
                    }
                    
                    # Determine if trained (has classifier head with 2 classes)
                    if 'fc.weight' in state_dict:
                        fc_shape = state_dict['fc.weight'].shape
                        verification['is_trained'] = (fc_shape[0] == 2)  # 2 classes: real/fake
                        print(f"   Parameters: {param_count:,}")
                        print(f"   Classifier head: {fc_shape} ({'✅ Trained for deepfake detection' if verification['is_trained'] else '⚠️  May be ImageNet only'})")
                    elif 'model.fc.weight' in state_dict:
                        fc_shape = state_dict['model.fc.weight'].shape
                        verification['is_trained'] = (fc_shape[0] == 2)
                        print(f"   Parameters: {param_count:,}")
                        print(f"   Classifier head: {fc_shape} ({'✅ Trained for deepfake detection' if verification['is_trained'] else '⚠️  May be ImageNet only'})")
                    else:
                        print("   ⚠️  No classifier head found - may be feature extractor only")
                    
                    break
                except Exception as e:
                    print(f"   ❌ Error loading model: {e}")
                    verification['error'] = str(e)
        
        if not verification['file_exists']:
            print("❌ Model file not found in any expected location")
            print("   Searched paths:")
            for path in possible_paths:
                print(f"     - {path}")
        
        self.results['verification'] = verification
        return verification
    
    def load_model(self) -> bool:
        """Step 2: Load model into memory"""
        print("\n📦 STEP 2: Loading Model")
        print("-" * 70)
        
        if not self.model_path:
            print("❌ Model path not set. Run verify_model_file() first.")
            return False
        
        try:
            self.model = ResNetDeepfakeClassifier(model_name='resnet50', pretrained=False)
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            self.model.to(self.device)
            self.model.eval()
            
            print("✅ Model loaded successfully")
            print(f"   Device: {self.device}")
            print(f"   Model type: ResNet50")
            print(f"   Mode: Evaluation (inference)")
            
            return True
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_inference(self, num_samples: int = 5) -> Dict[str, any]:
        """Step 3: Test inference on dummy data"""
        print("\n📦 STEP 3: Testing Inference")
        print("-" * 70)
        
        if self.model is None:
            print("❌ Model not loaded. Run load_model() first.")
            return {}
        
        inference_results = {
            'success': False,
            'samples_tested': 0,
            'avg_inference_time_ms': 0,
            'sample_predictions': []
        }
        
        try:
            # Create dummy input (224x224 RGB image)
            dummy_input = torch.randn(1, 3, 224, 224).to(self.device)
            
            # Warmup
            with torch.no_grad():
                _ = self.model(dummy_input)
            
            # Time inference
            times = []
            predictions = []
            
            for i in range(num_samples):
                start_time = time.time()
                with torch.no_grad():
                    output = self.model(dummy_input)
                    probs = torch.softmax(output, dim=1)
                    pred_class = int(torch.argmax(output, dim=1).item())
                    confidence = probs[0][pred_class].item()
                
                inference_time = (time.time() - start_time) * 1000  # ms
                times.append(inference_time)
                predictions.append({
                    'prediction': 'fake' if pred_class == 1 else 'real',
                    'confidence': round(confidence, 4),
                    'inference_time_ms': round(inference_time, 2)
                })
            
            inference_results['success'] = True
            inference_results['samples_tested'] = num_samples
            inference_results['avg_inference_time_ms'] = round(np.mean(times), 2)
            inference_results['sample_predictions'] = predictions
            
            print(f"✅ Inference test successful")
            print(f"   Samples tested: {num_samples}")
            print(f"   Average inference time: {inference_results['avg_inference_time_ms']:.2f} ms")
            print(f"   Throughput: {1000 / inference_results['avg_inference_time_ms']:.2f} FPS")
            
        except Exception as e:
            print(f"❌ Inference test failed: {e}")
            import traceback
            traceback.print_exc()
            inference_results['error'] = str(e)
        
        self.results['performance']['inference_test'] = inference_results
        return inference_results
    
    def find_test_data(self) -> Dict[str, List[str]]:
        """Find available test data"""
        test_data = {
            'real_images': [],
            'fake_images': [],
            'real_videos': [],
            'fake_videos': []
        }
        
        # Check for image datasets
        dataset_dirs = [
            'datasets/train',
            'datasets/val',
            'datasets/unified_deepfake/train',
            'datasets/unified_deepfake/val',
            'datasets/unified_deepfake/test'
        ]
        
        for dataset_dir in dataset_dirs:
            if os.path.exists(dataset_dir):
                # Real images
                real_dir = os.path.join(dataset_dir, 'real')
                if os.path.exists(real_dir):
                    real_imgs = [os.path.join(real_dir, f) for f in os.listdir(real_dir) 
                                if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                    test_data['real_images'].extend(real_imgs[:50])  # Limit to 50
                
                # Fake images
                fake_dir = os.path.join(dataset_dir, 'fake')
                if os.path.exists(fake_dir):
                    fake_imgs = [os.path.join(fake_dir, f) for f in os.listdir(fake_dir) 
                                if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                    test_data['fake_images'].extend(fake_imgs[:50])  # Limit to 50
        
        # Remove duplicates
        test_data['real_images'] = list(set(test_data['real_images']))[:100]
        test_data['fake_images'] = list(set(test_data['fake_images']))[:100]
        
        return test_data
    
    def benchmark_on_images(self, max_samples: int = 100) -> Dict[str, any]:
        """Step 4: Benchmark on test images"""
        print("\n📦 STEP 4: Benchmarking on Test Images")
        print("-" * 70)
        
        if self.model is None:
            print("❌ Model not loaded. Run load_model() first.")
            return {}
        
        # Find test data
        test_data = self.find_test_data()
        
        if not test_data['real_images'] and not test_data['fake_images']:
            print("⚠️  No test images found. Skipping image benchmark.")
            print("   Expected locations:")
            print("     - datasets/train/real/ and datasets/train/fake/")
            print("     - datasets/val/real/ and datasets/val/fake/")
            return {'skipped': True, 'reason': 'No test data found'}
        
        print(f"   Found {len(test_data['real_images'])} real images")
        print(f"   Found {len(test_data['fake_images'])} fake images")
        
        # Prepare data
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # Test on real images
        real_predictions = []
        real_labels = []
        real_confidences = []
        real_times = []
        
        print("\n   Testing on REAL images...")
        for img_path in test_data['real_images'][:max_samples//2]:
            try:
                img = Image.open(img_path).convert('RGB')
                img_tensor = transform(img).unsqueeze(0).to(self.device)
                
                start_time = time.time()
                with torch.no_grad():
                    output = self.model(img_tensor)
                    probs = torch.softmax(output, dim=1)
                    pred_class = int(torch.argmax(output, dim=1).item())
                    confidence = probs[0][pred_class].item()
                
                inference_time = (time.time() - start_time) * 1000
                
                real_predictions.append(pred_class)  # 0 = real
                real_labels.append(0)  # Ground truth: real
                real_confidences.append(probs[0][1].item())  # Fake probability
                real_times.append(inference_time)
            except Exception as e:
                print(f"     ⚠️  Error processing {img_path}: {e}")
                continue
        
        # Test on fake images
        fake_predictions = []
        fake_labels = []
        fake_confidences = []
        fake_times = []
        
        print("   Testing on FAKE images...")
        for img_path in test_data['fake_images'][:max_samples//2]:
            try:
                img = Image.open(img_path).convert('RGB')
                img_tensor = transform(img).unsqueeze(0).to(self.device)
                
                start_time = time.time()
                with torch.no_grad():
                    output = self.model(img_tensor)
                    probs = torch.softmax(output, dim=1)
                    pred_class = int(torch.argmax(output, dim=1).item())
                    confidence = probs[0][pred_class].item()
                
                inference_time = (time.time() - start_time) * 1000
                
                fake_predictions.append(pred_class)  # 1 = fake
                fake_labels.append(1)  # Ground truth: fake
                fake_confidences.append(probs[0][1].item())  # Fake probability
                fake_times.append(inference_time)
            except Exception as e:
                print(f"     ⚠️  Error processing {img_path}: {e}")
                continue
        
        # Combine results
        all_predictions = real_predictions + fake_predictions
        all_labels = real_labels + fake_labels
        all_confidences = real_confidences + fake_confidences
        all_times = real_times + fake_times
        
        if len(all_predictions) == 0:
            print("❌ No predictions generated. Check test data.")
            return {'error': 'No predictions'}
        
        # Calculate metrics
        accuracy = accuracy_score(all_labels, all_predictions)
        precision = precision_score(all_labels, all_predictions, zero_division=0)
        recall = recall_score(all_labels, all_predictions, zero_division=0)
        f1 = f1_score(all_labels, all_predictions, zero_division=0)
        
        try:
            auc = roc_auc_score(all_labels, all_confidences)
        except:
            auc = 0.5
        
        cm = confusion_matrix(all_labels, all_predictions)
        
        benchmark_results = {
            'samples_tested': len(all_predictions),
            'real_samples': len(real_predictions),
            'fake_samples': len(fake_predictions),
            'accuracy': round(accuracy, 4),
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1_score': round(f1, 4),
            'auc_roc': round(auc, 4),
            'avg_inference_time_ms': round(np.mean(all_times), 2),
            'throughput_fps': round(1000 / np.mean(all_times), 2),
            'confusion_matrix': cm.tolist(),
            'true_positives': int(cm[1][1]) if cm.shape == (2, 2) else 0,
            'true_negatives': int(cm[0][0]) if cm.shape == (2, 2) else 0,
            'false_positives': int(cm[0][1]) if cm.shape == (2, 2) else 0,
            'false_negatives': int(cm[1][0]) if cm.shape == (2, 2) else 0
        }
        
        print(f"\n✅ Benchmark complete!")
        print(f"   Samples tested: {benchmark_results['samples_tested']} ({benchmark_results['real_samples']} real, {benchmark_results['fake_samples']} fake)")
        print(f"   Accuracy: {benchmark_results['accuracy']:.2%}")
        print(f"   Precision: {benchmark_results['precision']:.2%}")
        print(f"   Recall: {benchmark_results['recall']:.2%}")
        print(f"   F1-Score: {benchmark_results['f1_score']:.2%}")
        print(f"   AUC-ROC: {benchmark_results['auc_roc']:.4f}")
        print(f"   Avg inference time: {benchmark_results['avg_inference_time_ms']:.2f} ms")
        print(f"   Throughput: {benchmark_results['throughput_fps']:.2f} FPS")
        print(f"\n   Confusion Matrix:")
        print(f"     True Negatives (Real→Real):  {benchmark_results['true_negatives']}")
        print(f"     False Positives (Real→Fake): {benchmark_results['false_positives']}")
        print(f"     False Negatives (Fake→Real): {benchmark_results['false_negatives']}")
        print(f"     True Positives (Fake→Fake):  {benchmark_results['true_positives']}")
        
        self.results['benchmarks']['image_benchmark'] = benchmark_results
        return benchmark_results
    
    def generate_report(self, output_file: str = 'resnet50_verification_report.json'):
        """Generate comprehensive report"""
        print("\n📊 Generating Report")
        print("-" * 70)
        
        # Add summary
        self.results['summary'] = {
            'model_verified': self.results['verification'].get('file_exists', False),
            'model_loaded': self.model is not None,
            'inference_tested': self.results['performance'].get('inference_test', {}).get('success', False),
            'benchmark_completed': 'image_benchmark' in self.results['benchmarks'],
            'overall_status': '✅ PASS' if (
                self.results['verification'].get('file_exists', False) and
                self.model is not None and
                self.results['performance'].get('inference_test', {}).get('success', False)
            ) else '❌ FAIL'
        }
        
        # Save report
        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"✅ Report saved to: {output_file}")
        except Exception as e:
            print(f"❌ Failed to save report: {e}")
    
    def run_full_verification(self):
        """Run complete verification pipeline"""
        print("\n" + "=" * 70)
        print("🚀 ResNet50 Deepfake Detection Model Verification")
        print("=" * 70)
        
        # Step 1: Verify model file
        verification = self.verify_model_file()
        if not verification.get('file_exists', False):
            print("\n❌ Verification failed: Model file not found")
            return False
        
        # Step 2: Load model
        if not self.load_model():
            print("\n❌ Verification failed: Could not load model")
            return False
        
        # Step 3: Test inference
        self.test_inference()
        
        # Step 4: Benchmark on test data
        self.benchmark_on_images()
        
        # Generate report
        self.generate_report()
        
        print("\n" + "=" * 70)
        print("✅ Verification Complete!")
        print("=" * 70)
        
        return True

if __name__ == "__main__":
    verifier = ResNet50Verifier()
    verifier.run_full_verification()

