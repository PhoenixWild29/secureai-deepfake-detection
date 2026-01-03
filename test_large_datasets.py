#!/usr/bin/env python3
"""
Large Dataset Testing for Generalization Validation
Tests ResNet50 on multiple benchmark datasets to confirm generalization
"""
import os
import sys
import torch
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
from tqdm import tqdm

# Add ai_model to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_model'))

try:
    from deepfake_classifier import ResNetDeepfakeClassifier
    print("✅ ResNetDeepfakeClassifier imported successfully")
except ImportError as e:
    print(f"❌ Failed to import ResNetDeepfakeClassifier: {e}")
    sys.exit(1)

class LargeDatasetTester:
    """Test ResNet50 on large benchmark datasets"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.model_path = model_path or self._find_model_path()
        self.results = {
            'datasets': {},
            'overall': {},
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"🔧 Using device: {self.device}")
        print("=" * 70)
    
    def _find_model_path(self) -> Optional[str]:
        """Find ResNet50 model file"""
        possible_paths = [
            'ai_model/resnet_resnet50_final.pth',
            'ai_model/resnet_resnet50_best.pth',
            'resnet_resnet50_final.pth',
            'resnet_resnet50_best.pth'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def load_model(self) -> bool:
        """Load ResNet50 model"""
        if not self.model_path or not os.path.exists(self.model_path):
            print(f"❌ Model file not found: {self.model_path}")
            return False
        
        try:
            self.model = ResNetDeepfakeClassifier(model_name='resnet50', pretrained=False)
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            self.model.to(self.device)
            self.model.eval()
            print(f"✅ Model loaded from: {self.model_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            return False
    
    def find_datasets(self) -> Dict[str, Dict]:
        """Find available test datasets"""
        datasets = {}
        
        # Check for various dataset structures
        dataset_configs = [
            {
                'name': 'unified_deepfake',
                'base_path': 'datasets/unified_deepfake',
                'test_paths': ['test/real', 'test/fake', 'val/real', 'val/fake'],
                'video_extensions': ['.mp4', '.avi', '.mov'],
                'image_extensions': ['.jpg', '.jpeg', '.png']
            },
            {
                'name': 'celeb_df_pp',
                'base_path': 'datasets/celeb_df_pp',
                'test_paths': ['videos/real', 'videos/fake'],
                'video_extensions': ['.mp4', '.avi'],
                'image_extensions': ['.jpg', '.jpeg']
            },
            {
                'name': 'train_val_split',
                'base_path': 'datasets',
                'test_paths': ['val/real', 'val/fake', 'train/real', 'train/fake'],
                'video_extensions': ['.mp4'],
                'image_extensions': ['.jpg', '.jpeg', '.png']
            }
        ]
        
        for config in dataset_configs:
            base = Path(config['base_path'])
            if not base.exists():
                continue
            
            real_samples = []
            fake_samples = []
            
            # Look for test/val splits first, then train
            for split in ['test', 'val', 'train']:
                real_path = base / split / 'real'
                fake_path = base / split / 'fake'
                
                if real_path.exists():
                    for ext in config['image_extensions']:
                        real_samples.extend(list(real_path.glob(f'*{ext}')))
                
                if fake_path.exists():
                    for ext in config['image_extensions']:
                        fake_samples.extend(list(fake_path.glob(f'*{ext}')))
            
            # Also check direct real/fake folders
            real_direct = base / 'real'
            fake_direct = base / 'fake'
            
            if real_direct.exists():
                for ext in config['image_extensions']:
                    real_samples.extend(list(real_direct.glob(f'*{ext}')))
            
            if fake_direct.exists():
                for ext in config['image_extensions']:
                    fake_samples.extend(list(fake_direct.glob(f'*{ext}')))
            
            # Remove duplicates
            real_samples = list(set(real_samples))[:500]  # Limit to 500 per category
            fake_samples = list(set(fake_samples))[:500]
            
            if real_samples or fake_samples:
                datasets[config['name']] = {
                    'real_samples': [str(p) for p in real_samples],
                    'fake_samples': [str(p) for p in fake_samples],
                    'total_samples': len(real_samples) + len(fake_samples)
                }
                print(f"✅ Found {config['name']}: {len(real_samples)} real, {len(fake_samples)} fake")
        
        return datasets
    
    def test_dataset(self, dataset_name: str, dataset_info: Dict) -> Dict:
        """Test model on a specific dataset"""
        print(f"\n📊 Testing on {dataset_name}...")
        print("-" * 70)
        
        real_samples = dataset_info['real_samples']
        fake_samples = dataset_info['fake_samples']
        
        if not real_samples and not fake_samples:
            return {'error': 'No samples found'}
        
        # Prepare transform
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        all_predictions = []
        all_labels = []
        all_confidences = []
        all_times = []
        
        # Test on real images
        print(f"   Testing {len(real_samples)} real images...")
        for img_path in tqdm(real_samples, desc="   Real", leave=False):
            try:
                img = Image.open(img_path).convert('RGB')
                img_tensor = transform(img).unsqueeze(0).to(self.device)
                
                start_time = time.time()
                with torch.no_grad():
                    output = self.model(img_tensor)
                    probs = torch.softmax(output, dim=1)
                    pred_class = int(torch.argmax(output, dim=1).item())
                    fake_prob = probs[0][1].item()  # Probability of fake
                
                inference_time = (time.time() - start_time) * 1000
                
                all_predictions.append(pred_class)
                all_labels.append(0)  # Real = 0
                all_confidences.append(fake_prob)
                all_times.append(inference_time)
            except Exception as e:
                print(f"     ⚠️  Error on {img_path}: {e}")
                continue
        
        # Test on fake images
        print(f"   Testing {len(fake_samples)} fake images...")
        for img_path in tqdm(fake_samples, desc="   Fake", leave=False):
            try:
                img = Image.open(img_path).convert('RGB')
                img_tensor = transform(img).unsqueeze(0).to(self.device)
                
                start_time = time.time()
                with torch.no_grad():
                    output = self.model(img_tensor)
                    probs = torch.softmax(output, dim=1)
                    pred_class = int(torch.argmax(output, dim=1).item())
                    fake_prob = probs[0][1].item()  # Probability of fake
                
                inference_time = (time.time() - start_time) * 1000
                
                all_predictions.append(pred_class)
                all_labels.append(1)  # Fake = 1
                all_confidences.append(fake_prob)
                all_times.append(inference_time)
            except Exception as e:
                print(f"     ⚠️  Error on {img_path}: {e}")
                continue
        
        if len(all_predictions) == 0:
            return {'error': 'No predictions generated'}
        
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
        
        results = {
            'dataset_name': dataset_name,
            'samples_tested': len(all_predictions),
            'real_samples': len([l for l in all_labels if l == 0]),
            'fake_samples': len([l for l in all_labels if l == 1]),
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
        
        print(f"   ✅ Results:")
        print(f"      Accuracy: {results['accuracy']:.2%}")
        print(f"      Precision: {results['precision']:.2%}")
        print(f"      Recall: {results['recall']:.2%}")
        print(f"      F1-Score: {results['f1_score']:.2%}")
        print(f"      AUC-ROC: {results['auc_roc']:.4f}")
        print(f"      Samples: {results['samples_tested']} ({results['real_samples']} real, {results['fake_samples']} fake)")
        
        return results
    
    def run_all_tests(self, output_file: str = 'large_dataset_test_results.json'):
        """Run tests on all available datasets"""
        print("\n" + "=" * 70)
        print("🚀 Large Dataset Generalization Testing")
        print("=" * 70)
        
        # Load model
        if not self.load_model():
            print("❌ Failed to load model. Exiting.")
            return
        
        # Find datasets
        print("\n📁 Finding available datasets...")
        datasets = self.find_datasets()
        
        if not datasets:
            print("⚠️  No test datasets found!")
            print("   Expected locations:")
            print("     - datasets/unified_deepfake/test/ or /val/")
            print("     - datasets/celeb_df_pp/videos/")
            print("     - datasets/val/ or datasets/train/")
            return
        
        print(f"\n✅ Found {len(datasets)} dataset(s) to test")
        
        # Test each dataset
        for dataset_name, dataset_info in datasets.items():
            results = self.test_dataset(dataset_name, dataset_info)
            if 'error' not in results:
                self.results['datasets'][dataset_name] = results
        
        # Calculate overall statistics
        if self.results['datasets']:
            all_accuracies = [d['accuracy'] for d in self.results['datasets'].values()]
            all_f1s = [d['f1_score'] for d in self.results['datasets'].values()]
            all_aucs = [d['auc_roc'] for d in self.results['datasets'].values()]
            total_samples = sum(d['samples_tested'] for d in self.results['datasets'].values())
            
            self.results['overall'] = {
                'datasets_tested': len(self.results['datasets']),
                'total_samples': total_samples,
                'avg_accuracy': round(np.mean(all_accuracies), 4),
                'avg_f1_score': round(np.mean(all_f1s), 4),
                'avg_auc_roc': round(np.mean(all_aucs), 4),
                'min_accuracy': round(min(all_accuracies), 4),
                'max_accuracy': round(max(all_accuracies), 4)
            }
            
            print("\n" + "=" * 70)
            print("📊 Overall Results")
            print("=" * 70)
            print(f"   Datasets tested: {self.results['overall']['datasets_tested']}")
            print(f"   Total samples: {self.results['overall']['total_samples']}")
            print(f"   Average Accuracy: {self.results['overall']['avg_accuracy']:.2%}")
            print(f"   Average F1-Score: {self.results['overall']['avg_f1_score']:.2%}")
            print(f"   Average AUC-ROC: {self.results['overall']['avg_auc_roc']:.4f}")
            print(f"   Accuracy Range: {self.results['overall']['min_accuracy']:.2%} - {self.results['overall']['max_accuracy']:.2%}")
        
        # Save results
        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\n✅ Results saved to: {output_file}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")

if __name__ == "__main__":
    tester = LargeDatasetTester()
    tester.run_all_tests()

