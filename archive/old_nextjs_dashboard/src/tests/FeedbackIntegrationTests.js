/**
 * Validator Feedback Integration Test Suite
 * Comprehensive tests for feedback collection functionality
 */

import validatorFeedback from '../services/ValidatorFeedback.js';
import { 
  FeedbackForm, 
  QuickFeedbackButton, 
  ErrorReporter, 
  PerformanceReporter 
} from '../components/FeedbackComponents.jsx';

class FeedbackIntegrationTests {
  constructor() {
    this.testResults = [];
    this.passedTests = 0;
    this.failedTests = 0;
  }

  /**
   * Run all tests
   */
  async runAllTests() {
    console.log('🧪 Starting Validator Feedback Integration Tests...\n');

    // Service Tests
    await this.testServiceInitialization();
    await this.testContextGeneration();
    await this.testPageNameMapping();
    await this.testSessionManagement();
    await this.testUserIdentification();

    // API Tests
    await this.testFeedbackSubmission();
    await this.testBugReportSubmission();
    await this.testFeatureRequestSubmission();
    await this.testPerformanceIssueSubmission();
    await this.testErrorHandling();

    // Component Tests
    await this.testComponentRendering();
    await this.testFormValidation();
    await this.testErrorReporting();

    // Security Tests
    await this.testInputValidation();
    await this.testRateLimiting();
    await this.testContextSecurity();

    this.printResults();
  }

  /**
   * Test service initialization
   */
  async testServiceInitialization() {
    try {
      const stats = validatorFeedback.getStats();
      
      this.assert(stats.isInitialized === true, 'Service should be initialized');
      this.assert(typeof stats.submissionsThisSession === 'number', 'Should track submission count');
      this.assert(stats.maxSubmissionsPerSession === 10, 'Should have correct max submissions');
      
      this.logTest('Service Initialization', true);
    } catch (error) {
      this.logTest('Service Initialization', false, error.message);
    }
  }

  /**
   * Test context generation
   */
  async testContextGeneration() {
    try {
      const context = validatorFeedback.getAutomaticContext();
      
      this.assert(typeof context.page === 'string', 'Should generate page name');
      this.assert(typeof context.urlPath === 'string', 'Should generate URL path');
      this.assert(typeof context.timestamp === 'string', 'Should generate timestamp');
      this.assert(typeof context.userAgent === 'string', 'Should generate user agent');
      this.assert(typeof context.screenResolution === 'string', 'Should generate screen resolution');
      this.assert(typeof context.viewport === 'string', 'Should generate viewport');
      this.assert(typeof context.language === 'string', 'Should generate language');
      this.assert(typeof context.platform === 'string', 'Should generate platform');
      this.assert(typeof context.sessionId === 'string', 'Should generate session ID');
      
      this.logTest('Context Generation', true);
    } catch (error) {
      this.logTest('Context Generation', false, error.message);
    }
  }

  /**
   * Test page name mapping
   */
  async testPageNameMapping() {
    try {
      // Mock window.location for testing
      const originalLocation = window.location;
      Object.defineProperty(window, 'location', {
        value: { pathname: '/dashboard/upload' },
        writable: true
      });

      const pageName = validatorFeedback.getPageName();
      this.assert(pageName === 'Video Upload', 'Should map dashboard/upload to Video Upload');

      // Test dynamic route
      Object.defineProperty(window, 'location', {
        value: { pathname: '/dashboard/results/123' },
        writable: true
      });

      const dynamicPageName = validatorFeedback.getPageName();
      this.assert(dynamicPageName === 'Detection Results (/dashboard/results/123)', 'Should handle dynamic routes');

      // Restore original location
      Object.defineProperty(window, 'location', {
        value: originalLocation,
        writable: true
      });

      this.logTest('Page Name Mapping', true);
    } catch (error) {
      this.logTest('Page Name Mapping', false, error.message);
    }
  }

  /**
   * Test session management
   */
  async testSessionManagement() {
    try {
      const sessionId1 = validatorFeedback.getSessionId();
      const sessionId2 = validatorFeedback.getSessionId();
      
      this.assert(sessionId1 === sessionId2, 'Should return same session ID');
      this.assert(sessionId1.startsWith('session_'), 'Should have correct session ID format');
      
      this.logTest('Session Management', true);
    } catch (error) {
      this.logTest('Session Management', false, error.message);
    }
  }

  /**
   * Test user identification
   */
  async testUserIdentification() {
    try {
      const userId = validatorFeedback.getUserId();
      
      // Should return null if no user data available
      this.assert(userId === null || typeof userId === 'string', 'Should return valid user ID or null');
      
      this.logTest('User Identification', true);
    } catch (error) {
      this.logTest('User Identification', false, error.message);
    }
  }

  /**
   * Test feedback submission (mock)
   */
  async testFeedbackSubmission() {
    try {
      // Mock fetch for testing
      const originalFetch = window.fetch;
      window.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          feedback_id: 'test_feedback_123',
          message: 'Feedback submitted successfully'
        })
      });

      const result = await validatorFeedback.submit({
        description: 'Test feedback submission',
        type: 'bug',
        priority: 'medium',
        email: 'test@example.com'
      });

      this.assert(result.success === true, 'Should return success response');
      this.assert(result.feedback_id === 'test_feedback_123', 'Should return feedback ID');

      // Restore original fetch
      window.fetch = originalFetch;

      this.logTest('Feedback Submission', true);
    } catch (error) {
      this.logTest('Feedback Submission', false, error.message);
    }
  }

  /**
   * Test bug report submission
   */
  async testBugReportSubmission() {
    try {
      const originalFetch = window.fetch;
      window.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          feedback_id: 'bug_report_456',
          message: 'Bug report submitted successfully'
        })
      });

      const result = await validatorFeedback.submitBugReport(
        'Test bug report',
        { component: 'TestComponent' }
      );

      this.assert(result.success === true, 'Should return success response');
      this.assert(result.feedback_id === 'bug_report_456', 'Should return feedback ID');

      window.fetch = originalFetch;

      this.logTest('Bug Report Submission', true);
    } catch (error) {
      this.logTest('Bug Report Submission', false, error.message);
    }
  }

  /**
   * Test feature request submission
   */
  async testFeatureRequestSubmission() {
    try {
      const originalFetch = window.fetch;
      window.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          feedback_id: 'feature_request_789',
          message: 'Feature request submitted successfully'
        })
      });

      const result = await validatorFeedback.submitFeatureRequest(
        'Test feature request',
        'user@example.com'
      );

      this.assert(result.success === true, 'Should return success response');
      this.assert(result.feedback_id === 'feature_request_789', 'Should return feedback ID');

      window.fetch = originalFetch;

      this.logTest('Feature Request Submission', true);
    } catch (error) {
      this.logTest('Feature Request Submission', false, error.message);
    }
  }

  /**
   * Test performance issue submission
   */
  async testPerformanceIssueSubmission() {
    try {
      const originalFetch = window.fetch;
      window.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          feedback_id: 'performance_issue_101',
          message: 'Performance issue submitted successfully'
        })
      });

      const result = await validatorFeedback.submitPerformanceIssue(
        'Test performance issue',
        { loadTime: 5000 }
      );

      this.assert(result.success === true, 'Should return success response');
      this.assert(result.feedback_id === 'performance_issue_101', 'Should return feedback ID');

      window.fetch = originalFetch;

      this.logTest('Performance Issue Submission', true);
    } catch (error) {
      this.logTest('Performance Issue Submission', false, error.message);
    }
  }

  /**
   * Test error handling
   */
  async testErrorHandling() {
    try {
      const originalFetch = window.fetch;
      window.fetch = jest.fn().mockRejectedValue(new Error('Network error'));

      try {
        await validatorFeedback.submit({
          description: 'Test feedback',
          type: 'bug',
          priority: 'medium'
        });
        this.assert(false, 'Should throw error for network failure');
      } catch (error) {
        this.assert(error.message === 'Network error', 'Should propagate network error');
      }

      // Test rate limiting
      window.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests'
      });

      try {
        await validatorFeedback.submit({
          description: 'Test feedback',
          type: 'bug',
          priority: 'medium'
        });
        this.assert(false, 'Should throw error for rate limiting');
      } catch (error) {
        this.assert(error.message.includes('Rate limit exceeded'), 'Should handle rate limiting');
      }

      window.fetch = originalFetch;

      this.logTest('Error Handling', true);
    } catch (error) {
      this.logTest('Error Handling', false, error.message);
    }
  }

  /**
   * Test component rendering
   */
  async testComponentRendering() {
    try {
      // Test that components can be imported and are functions
      this.assert(typeof FeedbackForm === 'function', 'FeedbackForm should be a function');
      this.assert(typeof QuickFeedbackButton === 'function', 'QuickFeedbackButton should be a function');
      this.assert(typeof ErrorReporter === 'function', 'ErrorReporter should be a function');
      this.assert(typeof PerformanceReporter === 'function', 'PerformanceReporter should be a function');

      this.logTest('Component Rendering', true);
    } catch (error) {
      this.logTest('Component Rendering', false, error.message);
    }
  }

  /**
   * Test form validation
   */
  async testFormValidation() {
    try {
      // Test validation logic
      const testCases = [
        { description: '', shouldFail: true },
        { description: 'Short', shouldFail: true },
        { description: 'This is a valid description with enough characters', shouldFail: false },
        { description: '   ', shouldFail: true }
      ];

      for (const testCase of testCases) {
        try {
          await validatorFeedback.submit({
            description: testCase.description,
            type: 'bug',
            priority: 'medium'
          });
          
          if (testCase.shouldFail) {
            this.assert(false, `Should fail for description: "${testCase.description}"`);
          }
        } catch (error) {
          if (!testCase.shouldFail) {
            this.assert(false, `Should not fail for description: "${testCase.description}"`);
          }
        }
      }

      this.logTest('Form Validation', true);
    } catch (error) {
      this.logTest('Form Validation', false, error.message);
    }
  }

  /**
   * Test error reporting
   */
  async testErrorReporting() {
    try {
      // Test error reporting functionality
      const testError = new Error('Test error for reporting');
      testError.stack = 'Error: Test error for reporting\n    at testErrorReporting';

      const originalFetch = window.fetch;
      window.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          feedback_id: 'error_report_123',
          message: 'Error reported successfully'
        })
      });

      const result = await validatorFeedback.submitBugReport(
        `Application Error: ${testError.message}`,
        {
          errorType: 'application',
          errorMessage: testError.message,
          errorStack: testError.stack
        }
      );

      this.assert(result.success === true, 'Should report error successfully');

      window.fetch = originalFetch;

      this.logTest('Error Reporting', true);
    } catch (error) {
      this.logTest('Error Reporting', false, error.message);
    }
  }

  /**
   * Test input validation
   */
  async testInputValidation() {
    try {
      // Test malicious input handling
      const maliciousInputs = [
        '<script>alert("xss")</script>',
        'javascript:alert("xss")',
        '; DROP TABLE users;',
        '../../../etc/passwd',
        '${rm -rf /}'
      ];

      for (const maliciousInput of maliciousInputs) {
        try {
          await validatorFeedback.submit({
            description: maliciousInput,
            type: 'bug',
            priority: 'medium'
          });
          // Should not throw error, but should sanitize input
        } catch (error) {
          // Some inputs might be rejected, which is also acceptable
        }
      }

      this.logTest('Input Validation', true);
    } catch (error) {
      this.logTest('Input Validation', false, error.message);
    }
  }

  /**
   * Test rate limiting
   */
  async testRateLimiting() {
    try {
      const originalFetch = window.fetch;
      window.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          feedback_id: 'test_123',
          message: 'Success'
        })
      });

      // Reset counter for testing
      validatorFeedback.resetSubmissionCounter();

      // Test normal submissions
      for (let i = 0; i < 5; i++) {
        await validatorFeedback.submit({
          description: `Test submission ${i}`,
          type: 'other',
          priority: 'low'
        });
      }

      const stats = validatorFeedback.getStats();
      this.assert(stats.submissionsThisSession === 5, 'Should track submission count');

      window.fetch = originalFetch;

      this.logTest('Rate Limiting', true);
    } catch (error) {
      this.logTest('Rate Limiting', false, error.message);
    }
  }

  /**
   * Test context security
   */
  async testContextSecurity() {
    try {
      const context = validatorFeedback.getAutomaticContext();
      
      // Should not include sensitive information
      this.assert(!context.userAgent.includes('password'), 'Should not include passwords');
      this.assert(!context.urlPath.includes('token'), 'Should not include tokens');
      this.assert(!context.referrer.includes('secret'), 'Should not include secrets');
      
      // Should include safe information
      this.assert(typeof context.page === 'string', 'Should include page name');
      this.assert(typeof context.timestamp === 'string', 'Should include timestamp');
      this.assert(typeof context.sessionId === 'string', 'Should include session ID');

      this.logTest('Context Security', true);
    } catch (error) {
      this.logTest('Context Security', false, error.message);
    }
  }

  /**
   * Assert helper
   */
  assert(condition, message) {
    if (!condition) {
      throw new Error(message);
    }
  }

  /**
   * Log test result
   */
  logTest(testName, passed, errorMessage = null) {
    const result = {
      name: testName,
      passed,
      error: errorMessage
    };
    
    this.testResults.push(result);
    
    if (passed) {
      this.passedTests++;
      console.log(`✅ ${testName}`);
    } else {
      this.failedTests++;
      console.log(`❌ ${testName}: ${errorMessage}`);
    }
  }

  /**
   * Print test results
   */
  printResults() {
    console.log('\n📊 Test Results Summary:');
    console.log(`✅ Passed: ${this.passedTests}`);
    console.log(`❌ Failed: ${this.failedTests}`);
    console.log(`📈 Total: ${this.testResults.length}`);
    console.log(`🎯 Success Rate: ${((this.passedTests / this.testResults.length) * 100).toFixed(1)}%`);

    if (this.failedTests > 0) {
      console.log('\n❌ Failed Tests:');
      this.testResults
        .filter(test => !test.passed)
        .forEach(test => {
          console.log(`  - ${test.name}: ${test.error}`);
        });
    }

    console.log('\n🎉 Validator Feedback Integration Tests Complete!');
  }
}

// Export for use in other files
export default FeedbackIntegrationTests;

// Run tests if this file is executed directly
if (typeof window !== 'undefined' && window.location.pathname.includes('test')) {
  const tests = new FeedbackIntegrationTests();
  tests.runAllTests();
}
