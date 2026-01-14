#!/usr/bin/env python3
"""
Simple Model Benchmarking Script
Test trained models on available datasets
"""
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add ai_model to path
sys.path.append('ai_model')

from detect import detect_fake

def benchmark_model_on_videos(model_type, video_files, model_name="CNN"):
    """Benchmark a model on a list of videos"""
    print(f"🔬 Benchmarking {model_name} on {len(video_files)} videos...")

    results = []
    total_time = 0

    for i, video_path in enumerate(video_files, 1):
        print(f"   [{i}/{len(video_files)}] Testing {os.path.basename(video_path)}...")

        try:
            start_time = time.time()
            result = detect_fake(video_path, model_type=model_type)
            processing_time = time.time() - start_time
            total_time += processing_time

            video_result = {
                'filename': os.path.basename(video_path),
                'is_fake': result.get('is_fake', False),
                'confidence': result.get('confidence', 0.0),
                'processing_time': processing_time,
                'model': model_name
            }
            results.append(video_result)

            status = "🚨 FAKE" if video_result['is_fake'] else "✅ REAL"
            print(".2f")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                'filename': os.path.basename(video_path),
                'error': str(e),
                'model': model_name
            })

    return results, total_time

def main():
    print("🚀 SecureAI Model Benchmarking")
    print("=" * 50)

    # Test videos
    test_dirs = ['test_batch_videos', 'test_videos']
    video_files = []

    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            for file in os.listdir(test_dir):
                if file.endswith('.mp4'):
                    video_files.append(os.path.join(test_dir, file))

    if not video_files:
        print("❌ No test videos found!")
        return

    print(f"📹 Found {len(video_files)} test videos:")
    for video in video_files:
        print(f"   - {os.path.basename(video)}")

    # Benchmark models
    models_to_test = ['cnn']  # Only test CNN since that's what we trained
    all_results = []

    for model in models_to_test:
        results, total_time = benchmark_model_on_videos(model, video_files, "CNN")
        all_results.extend(results)

        # Summary for this model
        successful_results = [r for r in results if 'error' not in r]
        if successful_results:
            fake_count = sum(1 for r in successful_results if r['is_fake'])
            avg_confidence = sum(r['confidence'] for r in successful_results) / len(successful_results)
            avg_time = total_time / len(successful_results)

            print(f"\n📊 {model.upper()} Model Summary:")
            print(f"   Videos processed: {len(successful_results)}")
            print(f"   Detected as fake: {fake_count}")
            print(".1f")
            print(".2f")
            print(".2f")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("benchmark_results")
    output_dir.mkdir(exist_ok=True)

    # JSON results
    json_file = output_dir / f"benchmark_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'total_videos': len(video_files),
            'results': all_results
        }, f, indent=2, default=str)

    # CSV summary
    successful_results = [r for r in all_results if 'error' not in r]
    if successful_results:
        df = pd.DataFrame(successful_results)
        csv_file = output_dir / f"benchmark_summary_{timestamp}.csv"
        df.to_csv(csv_file, index=False)

        print(f"\n💾 Results saved:")
        print(f"   JSON: {json_file}")
        print(f"   CSV: {csv_file}")

    print("\n✅ Benchmarking completed!")

if __name__ == "__main__":
    main()