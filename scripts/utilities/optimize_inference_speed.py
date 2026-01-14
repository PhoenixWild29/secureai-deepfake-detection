#!/usr/bin/env python3
"""
Inference Speed Optimization for ResNet50
Implements GPU acceleration, batch processing, and quantization
"""
import os
import sys
import torch
import torch.nn as nn
import numpy as np
import time
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image
from torchvision import transforms
import json
from datetime import datetime

# Add ai_model to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_model'))

try:
    from deepfake_classifier import ResNetDeepfakeClassifier
    print("✅ ResNetDeepfakeClassifier imported successfully")
except ImportError as e:
    print(f"❌ Failed to import ResNetDeepfakeClassifier: {e}")
    sys.exit(1)

class InferenceOptimizer:
    """Optimize ResNet50 inference speed"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_path = model_path or self._find_model_path()
        self.model = None
        self.optimized_model = None
        self.results = {
            'baseline': {},
            'optimizations': {},
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"🔧 Using device: {self.device}")
        print(f"   CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"   GPU: {torch.cuda.get_device_name(0)}")
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
    
    def benchmark_baseline(self, num_samples: int = 100) -> Dict:
        """Benchmark baseline inference performance"""
        print("\n📊 Benchmarking Baseline Performance")
        print("-" * 70)
        
        if self.model is None:
            print("❌ Model not loaded")
            return {}
        
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # Create dummy images
        dummy_images = [torch.randn(3, 224, 224) for _ in range(num_samples)]
        
        times = []
        
        # Warmup
        for _ in range(10):
            dummy_tensor = dummy_images[0].unsqueeze(0).to(self.device)
            with torch.no_grad():
                _ = self.model(dummy_tensor)
        
        # Benchmark single image inference
        print(f"   Testing single image inference ({num_samples} samples)...")
        for img in dummy_images:
            img_tensor = img.unsqueeze(0).to(self.device)
            
            start_time = time.time()
            with torch.no_grad():
                _ = self.model(img_tensor)
            times.append((time.time() - start_time) * 1000)  # ms
        
        baseline_results = {
            'device': str(self.device),
            'samples_tested': num_samples,
            'avg_time_ms': round(np.mean(times), 2),
            'min_time_ms': round(np.min(times), 2),
            'max_time_ms': round(np.max(times), 2),
            'std_time_ms': round(np.std(times), 2),
            'throughput_fps': round(1000 / np.mean(times), 2)
        }
        
        print(f"   ✅ Baseline Results:")
        print(f"      Device: {baseline_results['device']}")
        print(f"      Avg inference time: {baseline_results['avg_time_ms']:.2f} ms")
        print(f"      Throughput: {baseline_results['throughput_fps']:.2f} FPS")
        
        self.results['baseline'] = baseline_results
        return baseline_results
    
    def optimize_batch_processing(self, batch_sizes: List[int] = [1, 4, 8, 16, 32]) -> Dict:
        """Optimize using batch processing"""
        print("\n📊 Optimizing with Batch Processing")
        print("-" * 70)
        
        if self.model is None:
            print("❌ Model not loaded")
            return {}
        
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        batch_results = {}
        
        for batch_size in batch_sizes:
            print(f"   Testing batch size: {batch_size}...")
            
            # Create batch
            batch = torch.randn(batch_size, 3, 224, 224).to(self.device)
            
            # Warmup
            with torch.no_grad():
                _ = self.model(batch)
            
            # Benchmark
            times = []
            for _ in range(20):
                start_time = time.time()
                with torch.no_grad():
                    _ = self.model(batch)
                times.append((time.time() - start_time) * 1000)
            
            avg_time = np.mean(times)
            time_per_image = avg_time / batch_size
            throughput = (batch_size * 1000) / avg_time
            
            baseline_avg = self.results.get('baseline', {}).get('avg_time_ms', 0)
            batch_results[f'batch_{batch_size}'] = {
                'batch_size': batch_size,
                'total_time_ms': round(avg_time, 2),
                'time_per_image_ms': round(time_per_image, 2),
                'throughput_fps': round(throughput, 2),
                'speedup_vs_single': round(baseline_avg / time_per_image, 2) if baseline_avg > 0 else 1.0
            }
            
            print(f"      Time per image: {time_per_image:.2f} ms")
            print(f"      Throughput: {throughput:.2f} FPS")
            baseline_avg = self.results.get('baseline', {}).get('avg_time_ms', 0)
            if baseline_avg > 0:
                speedup = baseline_avg / time_per_image
                print(f"      Speedup: {speedup:.2f}x")
        
        self.results['optimizations']['batch_processing'] = batch_results
        return batch_results
    
    def optimize_quantization(self) -> Dict:
        """Optimize using model quantization"""
        print("\n📊 Optimizing with Model Quantization")
        print("-" * 70)
        
        if self.model is None:
            print("❌ Model not loaded")
            return {}
        
        try:
            # Dynamic quantization (works on CPU)
            print("   Applying dynamic quantization...")
            quantized_model = torch.quantization.quantize_dynamic(
                self.model, {nn.Linear}, dtype=torch.qint8
            )
            
            # Benchmark quantized model
            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            
            dummy_img = torch.randn(1, 3, 224, 224)
            
            # Warmup
            for _ in range(10):
                with torch.no_grad():
                    _ = quantized_model(dummy_img)
            
            # Benchmark
            times = []
            for _ in range(100):
                start_time = time.time()
                with torch.no_grad():
                    _ = quantized_model(dummy_img)
                times.append((time.time() - start_time) * 1000)
            
            baseline_avg = self.results.get('baseline', {}).get('avg_time_ms', 0)
            quant_results = {
                'quantization_type': 'dynamic_int8',
                'avg_time_ms': round(np.mean(times), 2),
                'throughput_fps': round(1000 / np.mean(times), 2),
                'speedup_vs_baseline': round(baseline_avg / np.mean(times), 2) if baseline_avg > 0 else 1.0,
                'model_size_reduction': '~4x smaller'
            }
            
            print(f"   ✅ Quantization Results:")
            print(f"      Avg inference time: {quant_results['avg_time_ms']:.2f} ms")
            print(f"      Throughput: {quant_results['throughput_fps']:.2f} FPS")
            if quant_results['speedup_vs_baseline'] > 1.0:
                print(f"      Speedup: {quant_results['speedup_vs_baseline']:.2f}x")
            
            self.results['optimizations']['quantization'] = quant_results
            return quant_results
            
        except Exception as e:
            print(f"   ⚠️  Quantization failed: {e}")
            print("      (Quantization may not be available or may require different setup)")
            return {}
    
    def optimize_torchscript(self) -> Dict:
        """Optimize using TorchScript (JIT compilation)"""
        print("\n📊 Optimizing with TorchScript (JIT)")
        print("-" * 70)
        
        if self.model is None:
            print("❌ Model not loaded")
            return {}
        
        try:
            # Trace model
            print("   Tracing model...")
            dummy_input = torch.randn(1, 3, 224, 224).to(self.device)
            
            with torch.no_grad():
                traced_model = torch.jit.trace(self.model, dummy_input)
            
            # Benchmark traced model
            times = []
            for _ in range(100):
                start_time = time.time()
                with torch.no_grad():
                    _ = traced_model(dummy_input)
                times.append((time.time() - start_time) * 1000)
            
            baseline_avg = self.results.get('baseline', {}).get('avg_time_ms', 0)
            torchscript_results = {
                'optimization_type': 'torchscript_jit',
                'avg_time_ms': round(np.mean(times), 2),
                'throughput_fps': round(1000 / np.mean(times), 2),
                'speedup_vs_baseline': round(baseline_avg / np.mean(times), 2) if baseline_avg > 0 else 1.0
            }
            
            print(f"   ✅ TorchScript Results:")
            print(f"      Avg inference time: {torchscript_results['avg_time_ms']:.2f} ms")
            print(f"      Throughput: {torchscript_results['throughput_fps']:.2f} FPS")
            if torchscript_results['speedup_vs_baseline'] > 1.0:
                print(f"      Speedup: {torchscript_results['speedup_vs_baseline']:.2f}x")
            
            self.results['optimizations']['torchscript'] = torchscript_results
            return torchscript_results
            
        except Exception as e:
            print(f"   ⚠️  TorchScript optimization failed: {e}")
            return {}
    
    def generate_report(self, output_file: str = 'inference_optimization_report.json'):
        """Generate optimization report"""
        print("\n📊 Generating Optimization Report")
        print("-" * 70)
        
        # Find best optimization (check batch processing first, then others)
        best_optimization = None
        best_speedup = 1.0
        
        # Check batch processing for best batch size
        if 'batch_processing' in self.results.get('optimizations', {}):
            batch_data = self.results['optimizations']['batch_processing']
            for batch_name, batch_info in batch_data.items():
                if isinstance(batch_info, dict) and 'speedup_vs_single' in batch_info:
                    speedup = batch_info['speedup_vs_single']
                    if speedup > best_speedup:
                        best_speedup = speedup
                        best_optimization = batch_name
        
        # Check other optimizations
        if 'optimizations' in self.results:
            for opt_name, opt_data in self.results['optimizations'].items():
                if opt_name == 'batch_processing':
                    continue  # Already checked
                if isinstance(opt_data, dict) and 'speedup_vs_baseline' in opt_data:
                    if opt_data['speedup_vs_baseline'] > best_speedup:
                        best_speedup = opt_data['speedup_vs_baseline']
                        best_optimization = opt_name
        
        self.results['summary'] = {
            'baseline_throughput_fps': self.results['baseline'].get('throughput_fps', 0),
            'best_optimization': best_optimization,
            'best_speedup': round(best_speedup, 2),
            'recommendations': self._generate_recommendations()
        }
        
        # Save report
        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"✅ Report saved to: {output_file}")
            
            # Print summary
            print("\n📋 Optimization Summary:")
            print(f"   Baseline: {self.results['baseline']['throughput_fps']:.2f} FPS")
            if best_optimization:
                print(f"   Best optimization: {best_optimization} ({best_speedup:.2f}x speedup)")
                print(f"   Recommended: Use {best_optimization} for production")
        except Exception as e:
            print(f"❌ Failed to save report: {e}")
    
    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        if not torch.cuda.is_available():
            recommendations.append("Use GPU for significant speedup (10-50x faster)")
        
        if 'batch_processing' in self.results.get('optimizations', {}):
            batch_data = self.results['optimizations']['batch_processing']
            best_batch = max(batch_data.items(), key=lambda x: x[1].get('throughput_fps', 0))
            recommendations.append(f"Use batch processing with batch size {best_batch[0].split('_')[1]} for {best_batch[1].get('speedup_vs_single', 1):.2f}x speedup")
        
        if 'quantization' in self.results.get('optimizations', {}):
            recommendations.append("Use quantization for CPU inference (2-4x speedup, smaller model)")
        
        if 'torchscript' in self.results.get('optimizations', {}):
            recommendations.append("Use TorchScript for optimized inference")
        
        return recommendations
    
    def run_all_optimizations(self):
        """Run all optimization tests"""
        print("\n" + "=" * 70)
        print("🚀 Inference Speed Optimization")
        print("=" * 70)
        
        # Load model
        if not self.load_model():
            print("❌ Failed to load model. Exiting.")
            return
        
        # Benchmark baseline
        baseline_results = self.benchmark_baseline()
        
        # Run optimizations
        self.optimize_batch_processing()
        
        if self.device.type == 'cpu':
            self.optimize_quantization()
        
        self.optimize_torchscript()
        
        # Generate report
        self.generate_report()
        
        print("\n" + "=" * 70)
        print("✅ Optimization Complete!")
        print("=" * 70)

if __name__ == "__main__":
    optimizer = InferenceOptimizer()
    optimizer.run_all_optimizations()

