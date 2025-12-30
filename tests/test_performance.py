#!/usr/bin/env python3
"""
Performance Tests
Load testing and performance benchmarks
"""

import unittest
import time
import concurrent.futures
import requests
import statistics
from typing import List, Dict

class PerformanceTestCase(unittest.TestCase):
    """Performance and load tests"""
    
    BASE_URL = 'http://localhost:5000'
    
    def test_response_time(self):
        """Test API response times"""
        response_times = []
        
        for _ in range(10):
            start = time.time()
            try:
                response = requests.get(f'{self.BASE_URL}/api/health', timeout=5)
                elapsed = time.time() - start
                if response.status_code == 200:
                    response_times.append(elapsed)
            except:
                pass
        
        if response_times:
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            print(f"\nResponse Time Stats:")
            print(f"  Average: {avg_time:.3f}s")
            print(f"  Max: {max_time:.3f}s")
            
            # Assert reasonable response time
            self.assertLess(avg_time, 1.0, "Average response time should be < 1s")
    
    def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        def make_request():
            try:
                response = requests.get(f'{self.BASE_URL}/api/health', timeout=5)
                return response.status_code == 200
            except:
                return False
        
        # Make 20 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        success_rate = sum(results) / len(results) if results else 0
        print(f"\nConcurrent Request Success Rate: {success_rate * 100:.1f}%")
        self.assertGreater(success_rate, 0.8, "Should handle 80%+ concurrent requests")


if __name__ == '__main__':
    unittest.main()
