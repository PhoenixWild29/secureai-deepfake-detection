/**
 * SecureSage Embeddable Widget
 * Embed SecureSage AI consultant on any website
 * Usage: <div id="secureai-sage-widget"></div>
 */

(function() {
  'use strict';

  const WIDGET_ID = 'secureai-sage-widget';
  const API_BASE_URL = 'https://guardian.secureai.dev'; // Backend API URL
  const WIDGET_VERSION = '1.0.0';

  class SecureSageWidget {
    constructor(containerId, options = {}) {
      this.containerId = containerId || WIDGET_ID;
      this.options = {
        apiUrl: options.apiUrl || API_BASE_URL,
        theme: options.theme || 'dark',
        position: options.position || 'bottom-right', // bottom-right, bottom-left, etc.
        width: options.width || '400px',
        height: options.height || '600px',
        ...options
      };
      this.messages = [];
      this.isOpen = false;
      this.isTyping = false;
      this.init();
    }

    init() {
      this.createWidget();
      this.attachStyles();
    }

    createWidget() {
      const container = document.getElementById(this.containerId);
      if (!container) {
        console.error(`Container with id "${this.containerId}" not found`);
        return;
      }

      // Create widget wrapper
      this.widget = document.createElement('div');
      this.widget.className = 'secureai-sage-widget';
      this.widget.innerHTML = this.getWidgetHTML();
      container.appendChild(this.widget);

      // Attach event listeners
      this.attachEventListeners();
    }

    getWidgetHTML() {
      return `
        <div class="sage-widget-container ${this.options.theme}" style="width: ${this.options.width}; height: ${this.options.height};">
          <div class="sage-widget-header">
            <div class="sage-widget-header-left">
              <div class="sage-status-dot"></div>
              <span class="sage-title">SecureSage v4.2</span>
            </div>
            <button class="sage-toggle-btn" aria-label="Toggle SecureSage">
              <svg class="sage-icon-close" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
              <svg class="sage-icon-open" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
              </svg>
            </button>
          </div>
          
          <div class="sage-widget-body">
            <div class="sage-messages" id="sage-messages-${this.containerId}">
              <div class="sage-message sage-message-assistant">
                <div class="sage-message-content">
                  SecureSage active. How can I assist you with cybersecurity and SecureAI services today?
                </div>
              </div>
            </div>
            
            <div class="sage-widget-input-area">
              <form class="sage-input-form" id="sage-form-${this.containerId}">
                <input 
                  type="text" 
                  class="sage-input" 
                  id="sage-input-${this.containerId}"
                  placeholder="Ask SecureSage anything..."
                  autocomplete="off"
                />
                <button type="submit" class="sage-send-btn" aria-label="Send message">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M13 5l7 7-7 7M5 5l7 7-7 7"/>
                  </svg>
                </button>
              </form>
            </div>
          </div>
        </div>
      `;
    }

    attachEventListeners() {
      const toggleBtn = this.widget.querySelector('.sage-toggle-btn');
      const form = this.widget.querySelector(`#sage-form-${this.containerId}`);
      const input = this.widget.querySelector(`#sage-input-${this.containerId}`);
      const messagesContainer = this.widget.querySelector(`#sage-messages-${this.containerId}`);

      // Toggle widget
      toggleBtn.addEventListener('click', () => {
        this.toggleWidget();
      });

      // Handle form submission
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = input.value.trim();
        if (message && !this.isTyping) {
          this.sendMessage(message);
          input.value = '';
        }
      });

      // Auto-resize messages container
      this.scrollToBottom();
    }

    toggleWidget() {
      this.isOpen = !this.isOpen;
      const body = this.widget.querySelector('.sage-widget-body');
      const toggleBtn = this.widget.querySelector('.sage-toggle-btn');
      
      if (this.isOpen) {
        body.style.display = 'flex';
        toggleBtn.querySelector('.sage-icon-close').style.display = 'block';
        toggleBtn.querySelector('.sage-icon-open').style.display = 'none';
      } else {
        body.style.display = 'none';
        toggleBtn.querySelector('.sage-icon-close').style.display = 'none';
        toggleBtn.querySelector('.sage-icon-open').style.display = 'block';
      }
    }

    async sendMessage(message) {
      // Add user message
      this.addMessage('user', message);
      
      // Show typing indicator
      this.showTyping();
      
      try {
        // Call backend API
        const response = await fetch(`${this.options.apiUrl}/api/sage/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            history: this.messages.map(m => ({ role: m.role, content: m.content })),
            context: {
              result: null,
              view: 'WEBSITE',
              tier: 'VISITOR',
              auditHistory: [],
              scanHistory: []
            }
          })
        });

        this.hideTyping();

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || `HTTP ${response.status}`);
        }

        const data = await response.json();
        this.addMessage('assistant', data.response || 'Communication uplink unstable.');
        
      } catch (error) {
        this.hideTyping();
        this.addMessage('assistant', `SecureSage is temporarily unavailable. Please try again later. Error: ${error.message}`);
        console.error('SecureSage API Error:', error);
      }
    }

    addMessage(role, content) {
      this.messages.push({ role, content });
      
      const messagesContainer = this.widget.querySelector(`#sage-messages-${this.containerId}`);
      const messageDiv = document.createElement('div');
      messageDiv.className = `sage-message sage-message-${role}`;
      messageDiv.innerHTML = `
        <div class="sage-message-content">${this.escapeHtml(content)}</div>
      `;
      
      messagesContainer.appendChild(messageDiv);
      this.scrollToBottom();
    }

    showTyping() {
      this.isTyping = true;
      const messagesContainer = this.widget.querySelector(`#sage-messages-${this.containerId}`);
      const typingDiv = document.createElement('div');
      typingDiv.className = 'sage-message sage-message-assistant sage-typing';
      typingDiv.id = 'sage-typing-indicator';
      typingDiv.innerHTML = `
        <div class="sage-message-content">
          <div class="sage-typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <span class="sage-typing-text">Neural Query</span>
        </div>
      `;
      messagesContainer.appendChild(typingDiv);
      this.scrollToBottom();
    }

    hideTyping() {
      this.isTyping = false;
      const typingIndicator = this.widget.querySelector('#sage-typing-indicator');
      if (typingIndicator) {
        typingIndicator.remove();
      }
    }

    scrollToBottom() {
      const messagesContainer = this.widget.querySelector(`#sage-messages-${this.containerId}`);
      if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }
    }

    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    attachStyles() {
      if (document.getElementById('secureai-sage-widget-styles')) {
        return; // Styles already attached
      }

      const style = document.createElement('style');
      style.id = 'secureai-sage-widget-styles';
      style.textContent = this.getStyles();
      document.head.appendChild(style);
    }

    getStyles() {
      return `
        .secureai-sage-widget {
          position: fixed;
          ${this.options.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
          ${this.options.position.includes('bottom') ? 'bottom: 20px;' : 'top: 20px;'}
          z-index: 10000;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }

        .sage-widget-container {
          background: #0a0e17;
          border: 1px solid rgba(59, 130, 246, 0.3);
          border-radius: 1rem;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 50px rgba(59, 130, 246, 0.1);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          backdrop-filter: blur(20px);
        }

        .sage-widget-header {
          background: rgba(59, 130, 246, 0.1);
          border-bottom: 1px solid rgba(59, 130, 246, 0.2);
          padding: 12px 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .sage-widget-header-left {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .sage-status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #3b82f6;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .sage-title {
          color: white;
          font-size: 11px;
          font-weight: 900;
          letter-spacing: 0.2em;
          text-transform: uppercase;
        }

        .sage-toggle-btn {
          background: transparent;
          border: none;
          color: white;
          cursor: pointer;
          padding: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: opacity 0.2s;
        }

        .sage-toggle-btn:hover {
          opacity: 0.7;
        }

        .sage-icon-close {
          display: none;
        }

        .sage-widget-body {
          display: flex;
          flex-direction: column;
          flex: 1;
          min-height: 0;
        }

        .sage-messages {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          scroll-behavior: smooth;
        }

        .sage-messages::-webkit-scrollbar {
          width: 6px;
        }

        .sage-messages::-webkit-scrollbar-thumb {
          background: rgba(59, 130, 246, 0.3);
          border-radius: 3px;
        }

        .sage-message {
          display: flex;
          max-width: 85%;
          animation: slideUp 0.3s ease-out;
        }

        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .sage-message-user {
          align-self: flex-end;
          justify-content: flex-end;
        }

        .sage-message-assistant {
          align-self: flex-start;
          justify-content: flex-start;
        }

        .sage-message-content {
          padding: 12px 16px;
          border-radius: 1rem;
          font-size: 13px;
          line-height: 1.5;
          word-wrap: break-word;
        }

        .sage-message-user .sage-message-content {
          background: #3b82f6;
          color: white;
          border-top-right-radius: 4px;
        }

        .sage-message-assistant .sage-message-content {
          background: rgba(31, 41, 55, 0.8);
          color: #e5e7eb;
          border: 1px solid rgba(75, 85, 99, 0.5);
          border-top-left-radius: 4px;
        }

        .sage-typing .sage-message-content {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .sage-typing-dots {
          display: flex;
          gap: 4px;
        }

        .sage-typing-dots span {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #3b82f6;
          animation: bounce 1.4s infinite;
        }

        .sage-typing-dots span:nth-child(2) {
          animation-delay: 0.2s;
        }

        .sage-typing-dots span:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-8px); }
        }

        .sage-typing-text {
          font-size: 10px;
          font-weight: 900;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          color: rgba(59, 130, 246, 0.6);
        }

        .sage-widget-input-area {
          border-top: 1px solid rgba(75, 85, 99, 0.3);
          padding: 12px;
          background: rgba(17, 24, 39, 0.5);
        }

        .sage-input-form {
          display: flex;
          gap: 8px;
        }

        .sage-input {
          flex: 1;
          background: rgba(0, 0, 0, 0.4);
          border: 1px solid rgba(75, 85, 99, 0.5);
          border-radius: 0.75rem;
          padding: 10px 14px;
          color: white;
          font-size: 13px;
          font-family: 'Courier New', monospace;
          outline: none;
          transition: border-color 0.2s;
        }

        .sage-input:focus {
          border-color: #3b82f6;
        }

        .sage-input::placeholder {
          color: rgba(156, 163, 175, 0.5);
        }

        .sage-send-btn {
          background: #3b82f6;
          border: none;
          border-radius: 0.75rem;
          color: white;
          padding: 10px 14px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background 0.2s, transform 0.1s;
        }

        .sage-send-btn:hover {
          background: #2563eb;
        }

        .sage-send-btn:active {
          transform: scale(0.95);
        }

        .sage-send-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        /* Mobile responsive */
        @media (max-width: 768px) {
          .secureai-sage-widget {
            right: 10px !important;
            left: 10px !important;
            bottom: 10px !important;
          }

          .sage-widget-container {
            width: calc(100vw - 20px) !important;
            height: calc(100vh - 20px) !important;
            max-height: 600px;
          }
        }
      `;
    }
  }

  // Auto-initialize if container exists
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      if (document.getElementById(WIDGET_ID)) {
        window.secureaiSage = new SecureSageWidget();
      }
    });
  } else {
    if (document.getElementById(WIDGET_ID)) {
      window.secureaiSage = new SecureSageWidget();
    }
  }

  // Export for manual initialization
  window.SecureSageWidget = SecureSageWidget;
})();
