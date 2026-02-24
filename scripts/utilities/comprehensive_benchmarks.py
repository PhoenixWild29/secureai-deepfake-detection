#!/usr/bin/env python3
"""
Comprehensive Benchmark Suite for SecureAI DeepFake Detection System
Tests multiple models, datasets, and performance metrics
"""

import sys
import os
import time
import json
import glob
from pathlib import Path
from typing import Dict, List, Any
import concurrent.futures
from datetime import datetime

# Add ai_model to path
sys.path.append('ai_model')

try:
    from detect import detect_fake
    print("✅ Detection module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import detection module: {e}")
    sys.exit(1)

class BenchmarkSuite:
    def __init__(self):
        self.results = {}
        self.test_videos = self._find_test_videos()
        self.test_images = self._find_test_images()

    def _find_test_videos(self) -> List[str]:
        """Find all test video files"""
        video_paths = []
        search_dirs = ['test_batch_videos', 'test_videos.py', '.', 'uploads']

        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                videos = glob.glob(os.path.join(search_dir, '*.mp4'))
                video_paths.extend(videos)

        return list(set(video_paths))  # Remove duplicates

    def _find_test_images(self) -> Dict[str, List[str]]:
        """Find test images organized by real/fake"""
        images = {'real': [], 'fake': []}

        # Look in dataset directories
        dataset_dirs = ['datasets/train', 'datasets/val']

        for dataset_dir in dataset_dirs:
            if os.path.exists(dataset_dir):
                for category in ['real', 'fake']:
                    category_path = os.path.join(dataset_dir, category)
                    if os.path.exists(category_path):
                        img_files = glob.glob(os.path.join(category_path, '*.jpg'))
                        images[category].extend(img_files)

        return images

    def benchmark_model(self, model_type: str, model_name: str) -> Dict[str, Any]:
        """Benchmark a specific model type"""
        print(f"\n🔬 Testing {model_name} ({model_type})...")

        results = {
            'model_type': model_type,
            'model_name': model_name,
            'video_results': [],
            'image_results': [],
            'metrics': {}
        }

        # Test on videos
        if self.test_videos:
            print(f"   📹 Testing {len(self.test_videos)} videos...")
            video_results = []

            for video_path in self.test_videos[:5]:  # Limit to 5 videos for speed
                try:
                    start_time = time.time()
                    result = detect_fake(video_path, model_type=model_type)
                    processing_time = time.time() - start_time

                    video_result = {
                        'video': os.path.basename(video_path),
                        'is_fake': result.get('is_fake', False),
                        'confidence': result.get('confidence', 0.5),
                        'processing_time': processing_time,
                        'success': True
                    }
                    video_results.append(video_result)
                    print(".2f")

                except Exception as e:
                    video_result = {
                        'video': os.path.basename(video_path),
                        'error': str(e),
                        'success': False
                    }
                    video_results.append(video_result)
                    print(f"      ❌ {os.path.basename(video_path)}: ERROR - {e}")

            results['video_results'] = video_results

        # Calculate video metrics
        if results['video_results']:
            successful_results = [r for r in results['video_results'] if r['success']]
            if successful_results:
                avg_time = sum(r['processing_time'] for r in successful_results) / len(successful_results)
                avg_confidence = sum(r['confidence'] for r in successful_results) / len(successful_results)
                fake_detections = sum(1 for r in successful_results if r['is_fake'])

                results['metrics']['videos'] = {
                    'total_tested': len(successful_results),
                    'average_processing_time': avg_time,
                    'average_confidence': avg_confidence,
                    'fake_detections': fake_detections,
                    'success_rate': len(successful_results) / len(results['video_results'])
                }

        return results

    def run_comprehensive_benchmarks(self) -> Dict[str, Any]:
        """Run benchmarks across all available models"""
        print("🧪 COMPREHENSIVE MODEL BENCHMARK SUITE")
        print("=" * 60)
        print(f"📊 Found {len(self.test_videos)} test videos")
        print(f"🖼️  Found {len(self.test_images['real'])} real images, {len(self.test_images['fake'])} fake images")

        # Test different model types
        models_to_test = [
            ('cnn', 'CNN Classifier'),
            ('enhanced', 'Enhanced Ensemble'),
        ]

        all_results = {}

        for model_type, model_name in models_to_test:
            try:
                results = self.benchmark_model(model_type, model_name)
                all_results[model_type] = results
            except Exception as e:
                print(f"❌ Failed to benchmark {model_name}: {e}")
                all_results[model_type] = {
                    'model_type': model_type,
                    'model_name': model_name,
                    'error': str(e)
                }

        # Generate summary
        summary = self._generate_summary(all_results)

        return {
            'timestamp': datetime.now().isoformat(),
            'models_tested': all_results,
            'summary': summary,
            'system_info': {
                'test_videos_count': len(self.test_videos),
                'real_images_count': len(self.test_images['real']),
                'fake_images_count': len(self.test_images['fake'])
            }
        }

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of benchmark results"""
        summary = {
            'best_performing_model': None,
            'fastest_model': None,
            'model_comparison': {}
        }

        best_accuracy = 0
        fastest_time = float('inf')

        for model_type, result in results.items():
            if 'error' in result:
                continue

            model_info = {
                'name': result['model_name'],
                'videos_tested': 0,
                'avg_processing_time': 0,
                'avg_confidence': 0,
                'fake_detections': 0
            }

            if 'metrics' in result and 'videos' in result['metrics']:
                metrics = result['metrics']['videos']
                model_info.update({
                    'videos_tested': metrics['total_tested'],
                    'avg_processing_time': metrics['average_processing_time'],
                    'avg_confidence': metrics['average_confidence'],
                    'fake_detections': metrics['fake_detections']
                })

                # Track best models
                if metrics['success_rate'] > best_accuracy:
                    best_accuracy = metrics['success_rate']
                    summary['best_performing_model'] = model_type

                if metrics['average_processing_time'] < fastest_time:
                    fastest_time = metrics['average_processing_time']
                    summary['fastest_model'] = model_type

            summary['model_comparison'][model_type] = model_info

        return summary

    def save_results(self, results: Dict[str, Any], output_dir: str = 'benchmark_results'):
        """Save benchmark results to file"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = int(time.time())
        filename = f'comprehensive_benchmark_{timestamp}.json'
        filepath = output_path / filename

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n💾 Results saved to: {filepath}")

        # Also save a human-readable summary
        summary_file = output_path / f'benchmark_summary_{timestamp}.txt'
        with open(summary_file, 'w') as f:
            f.write("SECUREAI DEEPFAKE DETECTION - BENCHMARK SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Timestamp: {results['timestamp']}\n\n")

            f.write("SYSTEM INFO:\n")
            f.write(f"- Test Videos: {results['system_info']['test_videos_count']}\n")
            f.write(f"- Real Images: {results['system_info']['real_images_count']}\n")
            f.write(f"- Fake Images: {results['system_info']['fake_images_count']}\n\n")

            f.write("MODEL COMPARISON:\n")
            for model_type, info in results['summary']['model_comparison'].items():
                f.write(f"\n{model_type.upper()} ({info['name']}):\n")
                f.write(f"  Videos Tested: {info['videos_tested']}\n")
                f.write(f"  Average Processing Time: {info['avg_processing_time']:.2f} seconds\n")
                f.write(f"  Average Confidence: {info['avg_confidence']:.2f}\n")
                f.write(f"  Fake Detections: {info['fake_detections']}\n")

            f.write("\nRECOMMENDATIONS:\n")
            if results['summary']['best_performing_model']:
                best = results['summary']['best_performing_model']
                f.write(f"- Best Performing: {best}\n")
            if results['summary']['fastest_model']:
                fastest = results['summary']['fastest_model']
                f.write(f"- Fastest: {fastest}\n")

        print(f"📄 Summary saved to: {summary_file}")

def main():
    """Main benchmark execution"""
    try:
        suite = BenchmarkSuite()
        results = suite.run_comprehensive_benchmarks()
        suite.save_results(results)

        print("\n🎉 Comprehensive benchmarking completed successfully!")
        print("📊 Check benchmark_results/ for detailed reports")

    except Exception as e:
        print(f"❌ Benchmark suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()