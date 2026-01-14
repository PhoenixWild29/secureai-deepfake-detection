#!/usr/bin/env python3
"""
Test Enhanced Deepfake Detection Models
Evaluate performance on advanced datasets from reviewed repositories
"""
import torch
import numpy as np
import cv2
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse
import time
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from tqdm import tqdm

from enhanced_detector import EnsembleDetector
from deepfake_classifier import DeepfakeClassifier
from detect import detect_fake, benchmark_models

class ModelEvaluator:
    """Evaluate deepfake detection models on test datasets"""

    def __init__(self, model_paths: Dict[str, str], device: str = 'auto'):
        self.device = torch.device(device if device != 'auto' else
                                 ('cuda' if torch.cuda.is_available() else 'cpu'))
        print(f"Using device: {self.device}")

        self.models = {}
        self.load_models(model_paths)

    def load_models(self, model_paths: Dict[str, str]):
        """Load all models"""
        print("Loading models...")

        # Load enhanced ensemble model
        if 'enhanced' in model_paths:
            try:
                self.models['enhanced'] = EnsembleDetector(
                    use_laa=True, use_clip=True, use_dm_aware=True
                ).to(self.device)

                checkpoint = torch.load(model_paths['enhanced'], map_location=self.device)
                if 'model_state_dict' in checkpoint:
                    self.models['enhanced'].load_state_dict(checkpoint['model_state_dict'])
                else:
                    self.models['enhanced'].load_state_dict(checkpoint)

                self.models['enhanced'].eval()
                print("✅ Loaded enhanced ensemble model")
            except Exception as e:
                print(f"❌ Failed to load enhanced model: {e}")

        # Load CNN model
        if 'cnn' in model_paths:
            try:
                self.models['cnn'] = DeepfakeClassifier().to(self.device)
                checkpoint = torch.load(model_paths['cnn'], map_location=self.device)
                if 'model_state_dict' in checkpoint:
                    self.models['cnn'].load_state_dict(checkpoint['model_state_dict'])
                else:
                    self.models['cnn'].load_state_dict(checkpoint)

                self.models['cnn'].eval()
                print("✅ Loaded CNN model")
            except Exception as e:
                print(f"❌ Failed to load CNN model: {e}")

    def extract_frames(self, video_path: str, frame_count: int = 30) -> List[np.ndarray]:
        """Extract frames from video"""
        cap = cv2.VideoCapture(video_path)
        frames = []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            cap.release()
            return [np.zeros((224, 224, 3), dtype=np.uint8)] * frame_count

        # Sample frames evenly
        frame_indices = np.linspace(0, total_frames-1, frame_count, dtype=int)

        for frame_idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (224, 224))
                frames.append(frame)
            else:
                frames.append(np.zeros((224, 224, 3), dtype=np.uint8))

        cap.release()
        return frames

    def preprocess_frames(self, frames: List[np.ndarray]) -> torch.Tensor:
        """Preprocess frames for model input"""
        # Convert to tensor and normalize
        frames_tensor = []
        for frame in frames:
            frame_tensor = torch.from_numpy(frame).float().permute(2, 0, 1) / 255.0
            # Normalize with ImageNet stats
            frame_tensor = torch.nn.functional.normalize(
                frame_tensor, mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
            )
            frames_tensor.append(frame_tensor)

        return torch.stack(frames_tensor).unsqueeze(0)  # Add batch dimension

    def predict_video(self, video_path: str, model_name: str) -> Tuple[int, float]:
        """Predict if video is fake using specified model"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not loaded")

        model = self.models[model_name]

        # Extract and preprocess frames
        frames = self.extract_frames(video_path)
        if not frames:
            return 0, 0.5  # Default to real with 0.5 confidence

        frames_tensor = self.preprocess_frames(frames).to(self.device)

        with torch.no_grad():
            if model_name == 'enhanced':
                # Enhanced model returns logits
                outputs = model(frames_tensor)
                probs = torch.softmax(outputs, dim=1)
                confidence, prediction = torch.max(probs, 1)
                return prediction.item(), confidence.item()
            elif model_name == 'cnn':
                # CNN model has predict_video method
                prediction, confidence = model.predict_video(frames_tensor.squeeze(0))
                return prediction, confidence

    def evaluate_dataset(self, dataset_path: str, model_name: str) -> Dict:
        """Evaluate model on a dataset"""
        print(f"Evaluating {model_name} on {dataset_path}...")

        dataset_path = Path(dataset_path)
        results = {
            'model': model_name,
            'dataset': dataset_path.name,
            'predictions': [],
            'labels': [],
            'confidences': [],
            'processing_times': []
        }

        # Evaluate real videos
        real_dir = dataset_path / 'real'
        if real_dir.exists():
            for video_file in tqdm(list(real_dir.glob('*.mp4')), desc=f'{model_name} - Real videos'):
                start_time = time.time()
                pred, conf = self.predict_video(str(video_file), model_name)
                processing_time = time.time() - start_time

                results['predictions'].append(pred)
                results['labels'].append(0)  # 0 = real
                results['confidences'].append(conf)
                results['processing_times'].append(processing_time)

        # Evaluate fake videos
        fake_dir = dataset_path / 'fake'
        if fake_dir.exists():
            for video_file in tqdm(list(fake_dir.glob('*.mp4')), desc=f'{model_name} - Fake videos'):
                start_time = time.time()
                pred, conf = self.predict_video(str(video_file), model_name)
                processing_time = time.time() - start_time

                results['predictions'].append(pred)
                results['labels'].append(1)  # 1 = fake
                results['confidences'].append(conf)
                results['processing_times'].append(processing_time)

        return results

    def calculate_metrics(self, results: Dict) -> Dict:
        """Calculate evaluation metrics"""
        predictions = np.array(results['predictions'])
        labels = np.array(results['labels'])
        confidences = np.array(results['confidences'])
        times = np.array(results['processing_times'])

        # Basic metrics
        accuracy = np.mean(predictions == labels)

        # Classification report
        report = classification_report(labels, predictions,
                                    target_names=['Real', 'Fake'],
                                    output_dict=True)

        # Confusion matrix
        cm = confusion_matrix(labels, predictions)

        # ROC AUC (using confidence scores as probabilities for fake class)
        try:
            auc = roc_auc_score(labels, confidences)
        except:
            auc = 0.5  # fallback

        # Performance metrics
        avg_time = np.mean(times)
        fps = 1.0 / avg_time if avg_time > 0 else 0

        metrics = {
            'accuracy': accuracy,
            'precision': report['Fake']['precision'],
            'recall': report['Fake']['recall'],
            'f1_score': report['Fake']['f1-score'],
            'auc': auc,
            'avg_processing_time': avg_time,
            'fps': fps,
            'confusion_matrix': cm.tolist(),
            'classification_report': report
        }

        return metrics

    def plot_results(self, all_results: List[Dict], output_dir: str):
        """Plot evaluation results"""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        # Prepare data for plotting
        models = list(set(r['model'] for r in all_results))
        datasets = list(set(r['dataset'] for r in all_results))

        # Accuracy comparison
        plt.figure(figsize=(12, 6))

        for i, dataset in enumerate(datasets):
            plt.subplot(2, 2, i+1)
            accuracies = []
            model_names = []

            for result in all_results:
                if result['dataset'] == dataset:
                    metrics = self.calculate_metrics(result)
                    accuracies.append(metrics['accuracy'] * 100)
                    model_names.append(result['model'])

            plt.bar(model_names, accuracies)
            plt.title(f'Accuracy on {dataset}')
            plt.ylabel('Accuracy (%)')
            plt.ylim(0, 100)

        plt.tight_layout()
        plt.savefig(output_dir / 'accuracy_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()

        # Confusion matrices
        for result in all_results:
            metrics = self.calculate_metrics(result)
            cm = np.array(metrics['confusion_matrix'])

            plt.figure(figsize=(6, 4))
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                       xticklabels=['Real', 'Fake'],
                       yticklabels=['Real', 'Fake'])
            plt.title(f'Confusion Matrix - {result["model"]} on {result["dataset"]}')
            plt.ylabel('True Label')
            plt.xlabel('Predicted Label')

            plt.savefig(output_dir / f'cm_{result["model"]}_{result["dataset"]}.png',
                       dpi=300, bbox_inches='tight')
            plt.close()

    def benchmark_all(self, test_datasets: List[str], output_dir: str = 'benchmark_results'):
        """Benchmark all loaded models on all test datasets"""
        output_dir = Path(output_dir) / f"benchmark_{int(time.time())}"
        output_dir.mkdir(parents=True, exist_ok=True)

        print("🚀 Starting comprehensive model benchmarking...")
        print(f"Models: {list(self.models.keys())}")
        print(f"Datasets: {test_datasets}")
        print(f"Output: {output_dir}")

        all_results = []

        # Evaluate each model on each dataset
        for model_name in self.models.keys():
            for dataset_path in test_datasets:
                if not Path(dataset_path).exists():
                    print(f"⚠️  Dataset not found: {dataset_path}")
                    continue

                try:
                    result = self.evaluate_dataset(dataset_path, model_name)
                    all_results.append(result)

                    # Save individual results
                    result_file = output_dir / f'results_{model_name}_{Path(dataset_path).name}.json'
                    with open(result_file, 'w') as f:
                        json.dump(result, f, indent=2)

                except Exception as e:
                    print(f"❌ Failed to evaluate {model_name} on {dataset_path}: {e}")

        # Calculate and save metrics
        summary_results = []
        for result in all_results:
            metrics = self.calculate_metrics(result)
            summary_result = {
                'model': result['model'],
                'dataset': result['dataset'],
                **metrics
            }
            summary_results.append(summary_result)

        # Save summary
        summary_df = pd.DataFrame(summary_results)
        summary_df.to_csv(output_dir / 'benchmark_summary.csv', index=False)

        # Plot results
        self.plot_results(all_results, output_dir)

        # Print summary
        print("\n📊 Benchmark Summary:")
        print(summary_df.to_string(index=False))

        print(f"\n✅ Benchmarking completed! Results saved to {output_dir}")

        return summary_results

def main():
    parser = argparse.ArgumentParser(description='Test Enhanced Deepfake Detection Models')
    parser.add_argument('--enhanced_model', type=str,
                       default='training_runs/enhanced_*/best_model.pth',
                       help='Path to enhanced model checkpoint')
    parser.add_argument('--cnn_model', type=str,
                       default='ai_model/deepfake_classifier_best.pth',
                       help='Path to CNN model checkpoint')
    parser.add_argument('--test_datasets', nargs='+',
                       default=['datasets/train', 'datasets/val'],
                       help='Test dataset directories')
    parser.add_argument('--output_dir', type=str, default='benchmark_results',
                       help='Output directory for results')
    parser.add_argument('--device', type=str, default='auto',
                       help='Device to use (auto, cuda, cpu)')

    args = parser.parse_args()

    # Find model paths (handle wildcards)
    model_paths = {}

    if args.enhanced_model:
        enhanced_path = Path(args.enhanced_model)
        if enhanced_path.exists():
            model_paths['enhanced'] = str(enhanced_path)
        else:
            # Try to find latest enhanced model
            training_runs = Path('training_runs')
            if training_runs.exists():
                enhanced_dirs = list(training_runs.glob('enhanced_*'))
                if enhanced_dirs:
                    latest_dir = max(enhanced_dirs, key=lambda x: x.stat().st_mtime)
                    best_model = latest_dir / 'best_model.pth'
                    if best_model.exists():
                        model_paths['enhanced'] = str(best_model)

    if args.cnn_model and Path(args.cnn_model).exists():
        model_paths['cnn'] = args.cnn_model

    if not model_paths:
        print("❌ No models found! Please train models first or specify correct paths.")
        return

    print(f"Found models: {model_paths}")

    # Create evaluator
    evaluator = ModelEvaluator(model_paths, args.device)

    # Run benchmarking
    results = evaluator.benchmark_all(args.test_datasets, args.output_dir)

    # Print top performers
    if results:
        df = pd.DataFrame(results)
        print("\n🏆 Top Performing Models:")
        top_acc = df.nlargest(3, 'accuracy')[['model', 'dataset', 'accuracy', 'auc', 'fps']]
        print(top_acc.to_string(index=False))

if __name__ == "__main__":
    main()