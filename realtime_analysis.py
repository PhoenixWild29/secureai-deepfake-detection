#!/usr/bin/env python3
"""
Real-time video streaming analysis for SecureAI
Supports webcam, RTSP streams, and live video analysis
"""
import cv2
import time
import threading
import queue
import numpy as np
from datetime import datetime
import argparse
import sys

from ai_model.detect import detect_fake

class RealTimeAnalyzer:
    """Real-time video stream analyzer"""

    def __init__(self, source=0, analysis_interval=2.0, display=True):
        """
        Initialize real-time analyzer

        Args:
            source: Video source (0 for webcam, RTSP URL for streams)
            analysis_interval: Seconds between full analyses
            display: Whether to show video feed
        """
        self.source = source
        self.analysis_interval = analysis_interval
        self.display = display
        self.running = False
        self.cap = None
        self.last_analysis_time = 0
        self.current_result = None
        self.frame_count = 0
        self.fps = 0
        self.start_time = time.time()

        # Threading
        self.analysis_thread = None
        self.frame_queue = queue.Queue(maxsize=10)

        print("🎥 Initializing Real-Time Analyzer...")
        print(f"   Source: {source}")
        print(f"   Analysis Interval: {analysis_interval}s")
        print(f"   Display: {display}")

    def start(self):
        """Start the real-time analysis"""
        print("🚀 Starting real-time analysis...")

        # Initialize video capture
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            print(f"❌ Failed to open video source: {self.source}")
            return False

        # Get video properties
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)

        print("✅ Video stream opened:")
        print(f"   Resolution: {width}x{height}")
        print(f"   FPS: {fps}")

        self.running = True

        # Start analysis thread
        self.analysis_thread = threading.Thread(target=self._analysis_worker, daemon=True)
        self.analysis_thread.start()

        # Start main loop
        self._main_loop()

        return True

    def stop(self):
        """Stop the analysis"""
        print("🛑 Stopping real-time analysis...")
        self.running = False

        if self.analysis_thread:
            self.analysis_thread.join(timeout=2.0)

        if self.cap:
            self.cap.release()

        cv2.destroyAllWindows()
        print("✅ Analysis stopped")

    def _main_loop(self):
        """Main video processing loop"""
        frame_skip = 0  # Process every frame for display, but analyze less frequently

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                print("❌ Failed to read frame")
                break

            self.frame_count += 1

            # Calculate FPS
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                self.fps = self.frame_count / elapsed

            # Display frame with overlay
            if self.display:
                display_frame = self._add_overlay(frame.copy())
                cv2.imshow('SecureAI Real-Time Analysis', display_frame)

                # Check for quit key
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # 'q' or ESC
                    break

            # Queue frame for analysis (every N frames)
            frame_skip += 1
            if frame_skip >= 30:  # Analyze every 30 frames (~1 second at 30fps)
                frame_skip = 0
                try:
                    self.frame_queue.put(frame.copy(), timeout=0.1)
                except queue.Full:
                    pass  # Skip if queue is full

        self.stop()

    def _analysis_worker(self):
        """Background worker for video analysis"""
        while self.running:
            try:
                # Get frame from queue
                frame = self.frame_queue.get(timeout=1.0)

                # Check if it's time for full analysis
                current_time = time.time()
                if current_time - self.last_analysis_time >= self.analysis_interval:
                    self._analyze_frame(frame)
                    self.last_analysis_time = current_time

            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Analysis error: {e}")
                time.sleep(0.1)

    def _analyze_frame(self, frame):
        """Analyze a single frame"""
        try:
            # Save frame temporarily for analysis
            temp_path = f"temp_frame_{int(time.time())}.jpg"
            cv2.imwrite(temp_path, frame)

            # Run detection (this will simulate analysis)
            start_time = time.time()
            result = detect_fake(temp_path)
            analysis_time = time.time() - start_time

            # Update current result
            self.current_result = {
                'timestamp': datetime.now().isoformat(),
                'result': result,
                'analysis_time': analysis_time,
                'frame_number': self.frame_count
            }

            # Clean up
            try:
                import os
                os.remove(temp_path)
            except:
                pass

        except Exception as e:
            print(f"❌ Frame analysis error: {e}")

    def _add_overlay(self, frame):
        """Add analysis overlay to frame"""
        height, width = frame.shape[:2]

        # Add semi-transparent overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (400, 150), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

        # Add text information
        y_offset = 30
        cv2.putText(frame, f"SecureAI Real-Time Analysis", (20, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y_offset += 25

        cv2.putText(frame, f"FPS: {self.fps:.1f}", (20, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        y_offset += 20

        cv2.putText(frame, f"Frames: {self.frame_count}", (20, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        y_offset += 25

        # Show current analysis result
        if self.current_result:
            result = self.current_result['result']
            status = "FAKE" if result['is_fake'] else "AUTHENTIC"
            color = (0, 0, 255) if result['is_fake'] else (0, 255, 0)

            cv2.putText(frame, f"Status: {status}", (20, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            y_offset += 25

            confidence = result['confidence']
            cv2.putText(frame, f"Confidence: {confidence:.1%}", (20, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            y_offset += 20

            analysis_time = self.current_result['analysis_time']
            cv2.putText(frame, f"Analysis: {analysis_time:.2f}s", (20, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, f"Time: {timestamp}", (width - 150, height - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Add controls help
        cv2.putText(frame, "Press 'Q' or ESC to quit", (20, height - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

        return frame

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='SecureAI Real-Time Video Analysis')
    parser.add_argument('--source', type=str, default='0',
                       help='Video source (0 for webcam, or RTSP URL)')
    parser.add_argument('--interval', type=float, default=2.0,
                       help='Analysis interval in seconds')
    parser.add_argument('--no-display', action='store_true',
                       help='Disable video display (for headless operation)')

    args = parser.parse_args()

    # Convert source to int if it's a digit (webcam index)
    try:
        source = int(args.source)
    except ValueError:
        source = args.source  # RTSP URL

    analyzer = RealTimeAnalyzer(
        source=source,
        analysis_interval=args.interval,
        display=not args.no_display
    )

    try:
        success = analyzer.start()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    finally:
        analyzer.stop()

if __name__ == "__main__":
    print("🎥 SecureAI Real-Time Video Analysis")
    print("=" * 50)
    main()