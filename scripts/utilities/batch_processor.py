#!/usr/bin/env python3
"""
Batch video processing for SecureAI
Analyze multiple videos concurrently with progress tracking
"""
import os
import glob
import time
import threading
import concurrent.futures
from datetime import datetime
import json
import argparse
from pathlib import Path

from ai_model.detect import detect_fake
from integration.integrate import submit_to_solana

class BatchProcessor:
    """Batch video processor with memory-efficient sequential analysis"""

    def __init__(self, max_workers=1, output_dir="batch_results"):
        """
        Initialize batch processor

        Args:
            max_workers: Maximum number of concurrent analyses (default 1 for memory efficiency)
            output_dir: Directory to save results
        """
        self.max_workers = max_workers
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Progress tracking
        self.total_files = 0
        self.completed = 0
        self.failed = 0
        self.start_time = None
        self.results = []

        print("📦 Initializing Memory-Efficient Batch Processor...")
        print(f"   Max Workers: {max_workers} (sequential processing for memory efficiency)")
        print(f"   Output Directory: {output_dir}")
        print("   💡 Memory optimization: Sequential processing, model cleanup between videos")

    def process_directory(self, input_dir, pattern="*.mp4", recursive=False):
        """Process all videos in a directory"""
        input_path = Path(input_dir)

        if recursive:
            video_files = list(input_path.rglob(pattern))
        else:
            video_files = list(input_path.glob(pattern))

        video_files = [f for f in video_files if f.is_file()]

        if not video_files:
            print(f"❌ No video files found in {input_dir} with pattern {pattern}")
            return False

        print(f"📁 Found {len(video_files)} video files")
        for video in video_files[:5]:  # Show first 5
            print(f"   - {video.name}")

        if len(video_files) > 5:
            print(f"   ... and {len(video_files) - 5} more")

        return self.process_files(video_files)

    def process_files(self, video_files):
        """Process a list of video files sequentially for memory efficiency"""
        self.total_files = len(video_files)
        self.completed = 0
        self.failed = 0
        self.start_time = time.time()
        self.results = []

        print(f"🚀 Starting memory-efficient batch processing of {self.total_files} videos...")
        print("   📊 Processing sequentially to minimize memory usage")
        print("=" * 60)

        # Process files sequentially instead of concurrently
        for video_file in video_files:
            try:
                result = self._process_single_video(video_file)
                if result:
                    self.completed += 1
                    self.results.append(result)
                    self._print_progress(result)
                else:
                    self.failed += 1
                    print(f"❌ Failed: {video_file.name}")

            except Exception as e:
                self.failed += 1
                print(f"❌ Error processing {video_file.name}: {e}")

        # Print final summary
        self._print_final_summary()
        self._save_results()

        return True

    def _process_single_video(self, video_path):
        """Process a single video file with memory cleanup"""
        import gc
        import torch

        try:
            video_path = Path(video_path)

            # Run analysis (use CNN model which we know works)
            start_time = time.time()
            result = detect_fake(str(video_path), model_type='cnn')
            processing_time = time.time() - start_time

            # Add metadata
            result.update({
                'filename': video_path.name,
                'filepath': str(video_path),
                'file_size': video_path.stat().st_size,
                'processing_time': f"{processing_time:.2f} seconds",
                'timestamp': datetime.now().isoformat()
            })

            # Submit to blockchain (skip for testing to avoid hanging)
            try:
                tx_result = submit_to_solana(result['video_hash'], result['authenticity_score'])
                result['blockchain_tx'] = tx_result
            except Exception as e:
                print(f"⚠️  Blockchain submission failed (continuing): {e}")
                result['blockchain_tx'] = 'skipped'

            # Memory cleanup after processing
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            return result

        except Exception as e:
            print(f"❌ Processing error for {video_path.name}: {e}")
            # Cleanup on error too
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return None

    def _print_progress(self, result):
        """Print progress update"""
        filename = result['filename']
        status = "🚨 FAKE" if result['is_fake'] else "✅ AUTHENTIC"
        confidence = result['confidence']
        processing_time = result['processing_time']

        progress = f"[{self.completed + self.failed}/{self.total_files}]"
        print(f"{progress} ✅ {filename}: {status} ({confidence:.1%}) - {processing_time}")

    def _print_final_summary(self):
        """Print final processing summary"""
        end_time = time.time()
        total_time = end_time - (self.start_time or end_time)

        print("\n" + "=" * 60)
        print("📊 BATCH PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Total Videos: {self.total_files}")
        print(f"Successfully Processed: {self.completed}")
        print(f"Failed: {self.failed}")
        print(f"⏱️  Total Time: {total_time:.2f}s")
        print(f"⚡ Avg Time per Video: {total_time/self.total_files:.2f}s")

        if self.results:
            fake_count = sum(1 for r in self.results if r['is_fake'])
            authentic_count = len(self.results) - fake_count
            print(f"🚨 Detected as Fake: {fake_count}")
            print(f"✅ Detected as Authentic: {authentic_count}")

            # Average confidence
            avg_confidence = sum(r['confidence'] for r in self.results) / len(self.results)
            print(f"🎯 Average Confidence: {avg_confidence:.1%}")

    def _save_results(self):
        """Save results to JSON file"""
        if not self.results:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"batch_results_{timestamp}.json"

        summary = {
            'batch_info': {
                'total_files': self.total_files,
                'completed': self.completed,
                'failed': self.failed,
                'processing_time': time.time() - (self.start_time or time.time()),
                'timestamp': datetime.now().isoformat()
            },
            'results': self.results
        }

        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        print(f"💾 Results saved to: {output_file}")

        # Also save CSV summary
        csv_file = self.output_dir / f"batch_summary_{timestamp}.csv"
        with open(csv_file, 'w') as f:
            f.write("filename,is_fake,confidence,authenticity_score,processing_time\n")
            for result in self.results:
                f.write(f"{result['filename']},{result['is_fake']},{result['confidence']:.4f},{result['authenticity_score']},{result['processing_time']}\n")

        print(f"📊 Summary CSV saved to: {csv_file}")

def main():
    """Command-line interface for batch processing"""
    parser = argparse.ArgumentParser(description='SecureAI Batch Video Processor')
    parser.add_argument('input', help='Input directory or file pattern')
    parser.add_argument('--pattern', default='*.mp4',
                       help='File pattern (default: *.mp4)')
    parser.add_argument('--recursive', '-r', action='store_true',
                       help='Process directories recursively')
    parser.add_argument('--workers', type=int, default=1,
                       help='Maximum concurrent workers (default: 1 for memory efficiency)')
    parser.add_argument('--output', default='batch_results',
                       help='Output directory for results')

    args = parser.parse_args()

    # Memory usage warning
    if args.workers > 1:
        print("⚠️  WARNING: Using multiple workers increases memory usage significantly!")
        print("   Each worker loads a full model into memory.")
        print(f"   Estimated memory usage: ~{args.workers * 500}MB - {args.workers * 2000}MB")
        response = input("   Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("   Switching to single worker for memory efficiency...")
            args.workers = 1

    processor = BatchProcessor(max_workers=args.workers, output_dir=args.output)

    input_path = Path(args.input)
    if input_path.is_dir():
        success = processor.process_directory(args.input, args.pattern, args.recursive)
    elif input_path.is_file():
        success = processor.process_files([input_path])
    else:
        # Try as glob pattern
        import glob
        files = glob.glob(args.input)
        if files:
            success = processor.process_files([Path(f) for f in files])
        else:
            print(f"❌ Input not found: {args.input}")
            return

    if success:
        print("✅ Batch processing completed successfully!")
    else:
        print("❌ Batch processing failed!")

if __name__ == "__main__":
    print("📦 SecureAI Batch Video Processor")
    print("=" * 50)
    main()