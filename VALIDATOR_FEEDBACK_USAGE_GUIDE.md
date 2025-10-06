# Validator Feedback SDK - Quick Usage Guide

## 🚀 **Getting Started**

The Validator Feedback SDK is now integrated into the SecureAI DeepFake Detection application. Here's how to use it:

### **1. Basic Usage**

```javascript
// The service is automatically initialized and available globally
window.ValidatorFeedback.submit({
  description: 'User feedback description',
  type: 'bug', // bug, feature_request, performance, other
  priority: 'medium', // low, medium, high
  email: 'user@example.com' // optional
});
```

### **2. Using React Components**

```jsx
import { FeedbackForm, QuickFeedbackButton, FeedbackWidget } from './components/FeedbackComponents';

// Modal feedback form
<FeedbackForm 
  isOpen={isModalOpen}
  onClose={() => setIsModalOpen(false)}
  initialType="bug"
  initialDescription="Pre-filled description"
/>

// Quick feedback button
<QuickFeedbackButton 
  type="feature_request"
  description="Quick feature request"
>
  Suggest Feature
</QuickFeedbackButton>

// Floating feedback widget (already integrated in App.js)
<FeedbackWidget />
```

### **3. Error Reporting**

```jsx
import { ErrorReporter } from './components/FeedbackComponents';

// In error boundaries or catch blocks
<ErrorReporter 
  error={errorObject}
  onReport={() => console.log('Error reported')}
/>
```

### **4. Specialized Methods**

```javascript
// Bug report with context
await ValidatorFeedback.submitBugReport(
  'Bug description',
  { component: 'MyComponent', userAction: 'click_button' }
);

// Feature request with email
await ValidatorFeedback.submitFeatureRequest(
  'Feature description',
  'user@example.com'
);

// Performance issue with metrics
await ValidatorFeedback.submitPerformanceIssue(
  'Performance description',
  { loadTime: 5000, renderTime: 2000 }
);
```

## 🔧 **Configuration**

### **Available Configuration Options:**

```javascript
// Get current statistics
const stats = ValidatorFeedback.getStats();
console.log('Submissions this session:', stats.submissionsThisSession);

// Reset submission counter (for testing)
ValidatorFeedback.resetSubmissionCounter();

// Get automatic context
const context = ValidatorFeedback.getAutomaticContext();
console.log('Current page:', context.page);
console.log('Session ID:', context.sessionId);
```

## 🎯 **Integration Points**

### **Already Integrated:**
- ✅ **App.js**: FeedbackWidget added to main layout
- ✅ **Error Boundary**: ErrorReporter integrated into WorkflowErrorBoundary
- ✅ **Automatic Tracking**: JavaScript errors and performance issues automatically tracked

### **Adding to New Components:**

```jsx
import { QuickFeedbackButton } from '../components/FeedbackComponents';

function MyComponent() {
  return (
    <div>
      <h2>My Component</h2>
      <QuickFeedbackButton 
        type="bug"
        description="Issue with MyComponent"
      >
        Report Issue
      </QuickFeedbackButton>
    </div>
  );
}
```

## 🔒 **Security & Privacy**

### **Automatic Context (Privacy-Safe):**
- Page name (human-readable)
- URL path (relative only)
- Timestamp
- User agent
- Screen resolution
- Viewport size
- Language
- Platform
- Session ID
- User ID (if available)

### **Rate Limiting:**
- Maximum 10 submissions per session
- Automatic rate limit handling
- Graceful degradation when limits exceeded

## 🧪 **Testing**

### **Demo Component:**
```jsx
import FeedbackDemo from './components/FeedbackDemo';

// Add to any page for testing
<FeedbackDemo />
```

### **Test Suite:**
```javascript
import FeedbackIntegrationTests from './tests/FeedbackIntegrationTests';

// Run comprehensive tests
const tests = new FeedbackIntegrationTests();
await tests.runAllTests();
```

## 📊 **Monitoring**

### **Automatic Tracking:**
- JavaScript errors
- Unhandled promise rejections
- Network errors (for API endpoints)
- Performance issues (slow page loads)

### **Manual Tracking:**
```javascript
// Track custom events
ValidatorFeedback.submit({
  description: 'Custom event occurred',
  type: 'other',
  priority: 'low',
  context: { event: 'custom_event', data: 'additional_info' }
});
```

## 🎨 **Styling**

### **CSS Classes Available:**
- `.feedback-modal-overlay` - Modal backdrop
- `.feedback-modal` - Modal container
- `.feedback-form` - Form styling
- `.feedback-btn` - Button styling
- `.feedback-widget` - Widget styling
- `.error-reporter` - Error reporter styling

### **Customization:**
```css
/* Override default styles */
.feedback-btn-primary {
  background-color: #your-brand-color;
}

.feedback-widget-toggle {
  background-color: #your-accent-color;
}
```

## 🚨 **Error Handling**

### **Common Error Scenarios:**
```javascript
try {
  await ValidatorFeedback.submit(feedback);
} catch (error) {
  if (error.message.includes('Rate limit exceeded')) {
    // Handle rate limiting
    console.log('Please try again later');
  } else if (error.message.includes('Network error')) {
    // Handle network issues
    console.log('Please check your connection');
  } else {
    // Handle other errors
    console.error('Feedback submission failed:', error);
  }
}
```

## 📱 **Responsive Behavior**

### **Mobile Optimizations:**
- Touch-friendly buttons (44px minimum)
- Responsive modal sizing
- Mobile-optimized widget positioning
- Swipe gestures for widget interaction

### **Desktop Features:**
- Keyboard navigation
- Hover effects
- Full modal functionality
- Drag-and-drop support (future)

## 🔮 **Advanced Usage**

### **Custom Context:**
```javascript
await ValidatorFeedback.submit({
  description: 'Feedback with custom context',
  type: 'bug',
  priority: 'high',
  context: {
    customField: 'customValue',
    userPreferences: { theme: 'dark' },
    componentState: { isLoading: true }
  }
});
```

### **Batch Operations:**
```javascript
// Submit multiple feedback items
const feedbackItems = [
  { description: 'Issue 1', type: 'bug' },
  { description: 'Issue 2', type: 'feature_request' }
];

for (const item of feedbackItems) {
  try {
    await ValidatorFeedback.submit(item);
  } catch (error) {
    console.error('Failed to submit:', item, error);
  }
}
```

---

## 🎉 **Ready to Use!**

The Validator Feedback SDK is now fully integrated and ready for production use. Users can:

1. **Report bugs** through the floating widget or error reporters
2. **Suggest features** via the feedback form
3. **Report performance issues** automatically or manually
4. **Provide general feedback** through multiple entry points

All feedback is automatically captured with relevant context and sent to the Validator dashboard for team review and action.

**Happy feedback collecting!** 🚀
