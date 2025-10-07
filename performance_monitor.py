#!/usr/bin/env python3
"""
Real-time Performance Monitor for SecureAI DeepFake Detection System
Monitors system performance metrics in real-time during operation
"""

import time
import json
import logging
import psutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess
import sys

class PerformanceMonitor:
    """
    Real-time performance monitoring for the SecureAI system
    """
    
    def __init__(self, output_dir: str = "performance_monitoring"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Monitoring configuration
        self.monitoring_interval = 1  # seconds
        self.metrics_history = []
        self.max_history_size = 3600  # 1 hour of data at 1-second intervals
        
        # Performance targets
        self.targets = {
            "frame_processing_time": 0.100,  # 100ms
            "memory_usage": 8 * 1024 * 1024 * 1024,  # 8GB
            "cpu_usage": 0.80,  # 80%
            "gpu_usage": 0.80,  # 80%
            "detection_accuracy": 0.95  # 95%
        }
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = self.output_dir / f"performance_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Collect current system performance metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_used = memory.used
            memory_percent = memory.percent
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_used = disk.used
            disk_percent = (disk.used / disk.total) * 100
            
            # Network metrics
            network = psutil.net_io_counters()
            
            # Process metrics (if main process is running)
            process_metrics = self.get_process_metrics()
            
            # GPU metrics (if available)
            gpu_metrics = self.get_gpu_metrics()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": cpu_count
                },
                "memory": {
                    "used_bytes": memory_used,
                    "used_percent": memory_percent,
                    "available_bytes": memory.available,
                    "total_bytes": memory.total
                },
                "disk": {
                    "used_bytes": disk_used,
                    "used_percent": disk_percent,
                    "free_bytes": disk.free,
                    "total_bytes": disk.total
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                },
                "process": process_metrics,
                "gpu": gpu_metrics
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {str(e)}")
            return {"timestamp": datetime.now().isoformat(), "error": str(e)}
    
    def get_process_metrics(self) -> Dict[str, Any]:
        """Get metrics for the main SecureAI process"""
        try:
            # Look for Python processes running main.py
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
                try:
                    if proc.info['name'] == 'python' and proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline'])
                        if 'main.py' in cmdline:
                            return {
                                "pid": proc.info['pid'],
                                "cpu_percent": proc.cpu_percent(),
                                "memory_used": proc.memory_info().rss,
                                "memory_percent": proc.memory_percent()
                            }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {"status": "process_not_found"}
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_gpu_metrics(self) -> Dict[str, Any]:
        """Get GPU metrics if available"""
        try:
            # Try to get GPU metrics using nvidia-ml-py or similar
            # This is a placeholder - implement actual GPU monitoring
            return {
                "status": "not_implemented",
                "note": "GPU monitoring requires additional setup"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def check_performance_targets(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Check if current metrics meet performance targets"""
        target_status = {}
        
        try:
            # Memory usage check
            memory_used = metrics.get("memory", {}).get("used_bytes", 0)
            target_status["memory_target_met"] = memory_used <= self.targets["memory_usage"]
            
            # CPU usage check
            cpu_usage = metrics.get("cpu", {}).get("usage_percent", 0) / 100
            target_status["cpu_target_met"] = cpu_usage <= self.targets["cpu_usage"]
            
            # Process-specific checks
            process_metrics = metrics.get("process", {})
            if "memory_used" in process_metrics:
                target_status["process_memory_target_met"] = process_metrics["memory_used"] <= self.targets["memory_usage"]
            
            # Overall target status
            target_status["overall_targets_met"] = all([
                target_status.get("memory_target_met", True),
                target_status.get("cpu_target_met", True),
                target_status.get("process_memory_target_met", True)
            ])
            
        except Exception as e:
            self.logger.error(f"Error checking performance targets: {str(e)}")
            target_status["error"] = str(e)
        
        return target_status
    
    def monitor_loop(self):
        """Main monitoring loop"""
        self.logger.info("🔄 Starting performance monitoring loop...")
        
        while self.monitoring_active:
            try:
                # Collect metrics
                metrics = self.get_system_metrics()
                
                # Check performance targets
                target_status = self.check_performance_targets(metrics)
                metrics["target_status"] = target_status
                
                # Add to history
                self.metrics_history.append(metrics)
                
                # Trim history if too large
                if len(self.metrics_history) > self.max_history_size:
                    self.metrics_history = self.metrics_history[-self.max_history_size:]
                
                # Log alerts if targets not met
                if not target_status.get("overall_targets_met", True):
                    self.logger.warning("⚠️  Performance targets not met!")
                    for target, met in target_status.items():
                        if not met and target != "overall_targets_met":
                            self.logger.warning(f"  • {target}: FAILED")
                
                # Save metrics to file periodically
                if len(self.metrics_history) % 60 == 0:  # Every minute
                    self.save_metrics_snapshot()
                
                # Wait for next interval
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(self.monitoring_interval)
    
    def save_metrics_snapshot(self):
        """Save current metrics snapshot to file"""
        try:
            if not self.metrics_history:
                return
            
            # Get latest metrics
            latest_metrics = self.metrics_history[-1]
            
            # Create snapshot file
            snapshot_file = self.output_dir / f"metrics_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            snapshot_data = {
                "snapshot_time": datetime.now().isoformat(),
                "latest_metrics": latest_metrics,
                "history_size": len(self.metrics_history),
                "monitoring_duration_minutes": len(self.metrics_history) / 60
            }
            
            with open(snapshot_file, "w") as f:
                json.dump(snapshot_data, f, indent=2)
            
            self.logger.info(f"📊 Metrics snapshot saved: {snapshot_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving metrics snapshot: {str(e)}")
    
    def start_monitoring(self):
        """Start performance monitoring"""
        if self.monitoring_active:
            self.logger.warning("⚠️  Monitoring is already active")
            return
        
        self.logger.info("🚀 Starting Performance Monitoring...")
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info(f"✅ Performance monitoring started (interval: {self.monitoring_interval}s)")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        if not self.monitoring_active:
            self.logger.warning("⚠️  Monitoring is not active")
            return
        
        self.logger.info("🛑 Stopping Performance Monitoring...")
        self.monitoring_active = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        # Save final metrics
        self.save_metrics_snapshot()
        
        self.logger.info("✅ Performance monitoring stopped")
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate performance report from collected metrics"""
        self.logger.info("📊 Generating Performance Report...")
        
        if not self.metrics_history:
            return {"error": "No metrics data available"}
        
        try:
            # Calculate statistics
            cpu_usage = [m.get("cpu", {}).get("usage_percent", 0) for m in self.metrics_history]
            memory_usage = [m.get("memory", {}).get("used_bytes", 0) for m in self.metrics_history]
            memory_percent = [m.get("memory", {}).get("used_percent", 0) for m in self.metrics_history]
            
            # Target compliance
            target_compliance = [m.get("target_status", {}).get("overall_targets_met", True) for m in self.metrics_history]
            compliance_rate = sum(target_compliance) / len(target_compliance) if target_compliance else 0
            
            report = {
                "report_generated_at": datetime.now().isoformat(),
                "monitoring_duration_minutes": len(self.metrics_history) / 60,
                "total_data_points": len(self.metrics_history),
                "performance_summary": {
                    "cpu_usage": {
                        "average": sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0,
                        "peak": max(cpu_usage) if cpu_usage else 0,
                        "min": min(cpu_usage) if cpu_usage else 0
                    },
                    "memory_usage": {
                        "average_bytes": sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                        "peak_bytes": max(memory_usage) if memory_usage else 0,
                        "average_percent": sum(memory_percent) / len(memory_percent) if memory_percent else 0,
                        "peak_percent": max(memory_percent) if memory_percent else 0
                    },
                    "target_compliance_rate": compliance_rate
                },
                "performance_targets": self.targets,
                "recommendations": []
            }
            
            # Generate recommendations
            if compliance_rate < 0.95:
                report["recommendations"].append(
                    "Target compliance below 95%. Consider system optimization."
                )
            
            avg_memory_gb = report["performance_summary"]["memory_usage"]["average_bytes"] / (1024**3)
            if avg_memory_gb > 6:
                report["recommendations"].append(
                    f"Average memory usage ({avg_memory_gb:.1f}GB) approaching limit. Monitor closely."
                )
            
            avg_cpu = report["performance_summary"]["cpu_usage"]["average"]
            if avg_cpu > 70:
                report["recommendations"].append(
                    f"Average CPU usage ({avg_cpu:.1f}%) is high. Consider load balancing."
                )
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating performance report: {str(e)}")
            return {"error": str(e)}
    
    def save_performance_report(self, report: Dict[str, Any]):
        """Save performance report to file"""
        try:
            report_file = self.output_dir / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"📊 Performance report saved: {report_file}")
            
            # Print summary
            if "performance_summary" in report:
                summary = report["performance_summary"]
                print("\n" + "="*50)
                print("📊 PERFORMANCE MONITORING SUMMARY")
                print("="*50)
                print(f"⏱️  Monitoring Duration: {report.get('monitoring_duration_minutes', 0):.1f} minutes")
                print(f"📈 Data Points Collected: {report.get('total_data_points', 0)}")
                print(f"🎯 Target Compliance: {summary.get('target_compliance_rate', 0):.1%}")
                
                cpu = summary.get("cpu_usage", {})
                print(f"💻 CPU Usage: {cpu.get('average', 0):.1f}% (peak: {cpu.get('peak', 0):.1f}%)")
                
                memory = summary.get("memory_usage", {})
                avg_mem_gb = memory.get("average_bytes", 0) / (1024**3)
                peak_mem_gb = memory.get("peak_bytes", 0) / (1024**3)
                print(f"🧠 Memory Usage: {avg_mem_gb:.1f}GB (peak: {peak_mem_gb:.1f}GB)")
                
                if report.get("recommendations"):
                    print("\n💡 Recommendations:")
                    for rec in report["recommendations"]:
                        print(f"  • {rec}")
                
                print("="*50)
            
        except Exception as e:
            self.logger.error(f"Error saving performance report: {str(e)}")
    
    def run_dashboard_mode(self):
        """Run in dashboard mode with real-time display"""
        self.logger.info("🖥️  Starting Dashboard Mode...")
        
        try:
            self.start_monitoring()
            
            print("\n🖥️  PERFORMANCE MONITORING DASHBOARD")
            print("="*60)
            print("Press Ctrl+C to stop monitoring...")
            print("="*60)
            
            # Real-time dashboard loop
            while self.monitoring_active:
                try:
                    if self.metrics_history:
                        latest = self.metrics_history[-1]
                        
                        # Clear screen and display metrics
                        print("\033[2J\033[H", end="")  # Clear screen
                        
                        print("🖥️  PERFORMANCE MONITORING DASHBOARD")
                        print("="*60)
                        print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
                        print(f"📊 Data Points: {len(self.metrics_history)}")
                        
                        # CPU metrics
                        cpu = latest.get("cpu", {})
                        print(f"💻 CPU Usage: {cpu.get('usage_percent', 0):.1f}%")
                        
                        # Memory metrics
                        memory = latest.get("memory", {})
                        memory_gb = memory.get("used_bytes", 0) / (1024**3)
                        print(f"🧠 Memory: {memory_gb:.1f}GB ({memory.get('used_percent', 0):.1f}%)")
                        
                        # Target status
                        target_status = latest.get("target_status", {})
                        overall_status = target_status.get("overall_targets_met", True)
                        status_icon = "✅" if overall_status else "❌"
                        print(f"🎯 Targets: {status_icon} {'MET' if overall_status else 'FAILED'}")
                        
                        # Process metrics
                        process = latest.get("process", {})
                        if "memory_used" in process:
                            proc_mem_gb = process["memory_used"] / (1024**3)
                            print(f"🔄 Process Memory: {proc_mem_gb:.1f}GB")
                        
                        print("="*60)
                        print("Press Ctrl+C to stop...")
                    
                    time.sleep(5)  # Update every 5 seconds
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"Dashboard error: {str(e)}")
                    time.sleep(5)
            
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_monitoring()
            print("\n✅ Performance monitoring stopped.")

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SecureAI Performance Monitor")
    parser.add_argument("--dashboard", action="store_true", help="Run in dashboard mode")
    parser.add_argument("--duration", type=int, default=60, help="Monitoring duration in minutes")
    parser.add_argument("--interval", type=int, default=1, help="Monitoring interval in seconds")
    
    args = parser.parse_args()
    
    print("🚀 SecureAI Performance Monitor")
    print("="*50)
    
    monitor = PerformanceMonitor()
    monitor.monitoring_interval = args.interval
    
    try:
        if args.dashboard:
            monitor.run_dashboard_mode()
        else:
            print(f"🔄 Starting monitoring for {args.duration} minutes...")
            monitor.start_monitoring()
            
            # Wait for specified duration
            time.sleep(args.duration * 60)
            
            monitor.stop_monitoring()
            
            # Generate and save report
            report = monitor.generate_performance_report()
            monitor.save_performance_report(report)
    
    except KeyboardInterrupt:
        print("\n🛑 Monitoring interrupted by user")
        monitor.stop_monitoring()
    except Exception as e:
        print(f"❌ Monitoring error: {str(e)}")
        monitor.stop_monitoring()

if __name__ == "__main__":
    main()
