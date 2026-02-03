(function() {
  'use strict';

  const ChatbotWidget = {
    config: null,
    container: null,
    isOpen: false,
    sessionId: null,
    messages: [],

    init: function(config) {
      this.config = {
        widgetId: config.widgetId || 'default',
        apiUrl: config.apiUrl || window.location.origin,
        position: config.position || 'bottom-right',
        primaryColor: config.primaryColor || '#007bff',
        title: config.title || 'Chat',
        welcomeMessage: config.welcomeMessage || 'Hello! How can I help you today?',
        placeholder: config.placeholder || 'Type a message...',
      };

      this.sessionId = this.getOrCreateSessionId();
      this.injectStyles();
      this.createWidget();
      this.bindEvents();
      this.addWelcomeMessage();
    },

    getOrCreateSessionId: function() {
      const key = 'chatbot_session_' + this.config.widgetId;
      let sessionId = localStorage.getItem(key);
      if (!sessionId) {
        sessionId = 'sess_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
        localStorage.setItem(key, sessionId);
      }
      return sessionId;
    },

    injectStyles: function() {
      if (document.getElementById('chatbot-widget-styles')) return;

      const styles = document.createElement('style');
      styles.id = 'chatbot-widget-styles';
      styles.textContent = `
        #chatbot-widget-container {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
          font-size: 14px;
          line-height: 1.5;
          position: fixed;
          z-index: 999999;
        }
        #chatbot-widget-container.bottom-right {
          bottom: 20px;
          right: 20px;
        }
        #chatbot-widget-container.bottom-left {
          bottom: 20px;
          left: 20px;
        }
        #chatbot-toggle {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          border: none;
          cursor: pointer;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          display: flex;
          align-items: center;
          justify-content: center;
          transition: transform 0.2s, box-shadow 0.2s;
        }
        #chatbot-toggle:hover {
          transform: scale(1.05);
          box-shadow: 0 6px 16px rgba(0,0,0,0.2);
        }
        #chatbot-toggle svg {
          width: 28px;
          height: 28px;
          fill: white;
        }
        #chatbot-window {
          position: absolute;
          bottom: 70px;
          right: 0;
          width: 380px;
          max-width: calc(100vw - 40px);
          height: 500px;
          max-height: calc(100vh - 100px);
          background: white;
          border-radius: 16px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.15);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          opacity: 0;
          transform: translateY(20px) scale(0.95);
          pointer-events: none;
          transition: opacity 0.2s, transform 0.2s;
        }
        #chatbot-window.open {
          opacity: 1;
          transform: translateY(0) scale(1);
          pointer-events: auto;
        }
        #chatbot-header {
          padding: 16px 20px;
          color: white;
          font-weight: 600;
          font-size: 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        #chatbot-close {
          background: none;
          border: none;
          color: white;
          cursor: pointer;
          padding: 4px;
          opacity: 0.8;
        }
        #chatbot-close:hover {
          opacity: 1;
        }
        #chatbot-messages {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .chatbot-message {
          max-width: 85%;
          padding: 12px 16px;
          border-radius: 16px;
          word-wrap: break-word;
        }
        .chatbot-message.user {
          align-self: flex-end;
          color: white;
          border-bottom-right-radius: 4px;
        }
        .chatbot-message.assistant {
          align-self: flex-start;
          background: #f1f3f4;
          color: #202124;
          border-bottom-left-radius: 4px;
        }
        .chatbot-message.typing {
          background: #f1f3f4;
        }
        .chatbot-typing-indicator {
          display: flex;
          gap: 4px;
        }
        .chatbot-typing-indicator span {
          width: 8px;
          height: 8px;
          background: #90949c;
          border-radius: 50%;
          animation: chatbot-bounce 1.4s infinite ease-in-out both;
        }
        .chatbot-typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
        .chatbot-typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
        @keyframes chatbot-bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }
        #chatbot-input-container {
          padding: 12px 16px;
          border-top: 1px solid #e8eaed;
          display: flex;
          gap: 8px;
        }
        #chatbot-input {
          flex: 1;
          padding: 10px 16px;
          border: 1px solid #e8eaed;
          border-radius: 24px;
          outline: none;
          font-size: 14px;
          transition: border-color 0.2s;
        }
        #chatbot-input:focus {
          border-color: var(--chatbot-primary);
        }
        #chatbot-send {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: opacity 0.2s;
        }
        #chatbot-send:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        #chatbot-send svg {
          width: 20px;
          height: 20px;
          fill: white;
        }
      `;
      document.head.appendChild(styles);
    },

    createWidget: function() {
      this.container = document.createElement('div');
      this.container.id = 'chatbot-widget-container';
      this.container.className = this.config.position;
      this.container.style.setProperty('--chatbot-primary', this.config.primaryColor);

      this.container.innerHTML = `
        <div id="chatbot-window">
          <div id="chatbot-header" style="background: ${this.config.primaryColor}">
            <span>${this.config.title}</span>
            <button id="chatbot-close" aria-label="Close chat">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
              </svg>
            </button>
          </div>
          <div id="chatbot-messages"></div>
          <div id="chatbot-input-container">
            <input type="text" id="chatbot-input" placeholder="${this.config.placeholder}" />
            <button id="chatbot-send" style="background: ${this.config.primaryColor}" aria-label="Send message">
              <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
            </button>
          </div>
        </div>
        <button id="chatbot-toggle" style="background: ${this.config.primaryColor}" aria-label="Open chat">
          <svg viewBox="0 0 24 24">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
          </svg>
        </button>
      `;

      document.body.appendChild(this.container);
    },

    bindEvents: function() {
      const toggle = document.getElementById('chatbot-toggle');
      const close = document.getElementById('chatbot-close');
      const input = document.getElementById('chatbot-input');
      const send = document.getElementById('chatbot-send');

      toggle.addEventListener('click', () => this.toggleWindow());
      close.addEventListener('click', () => this.toggleWindow());

      send.addEventListener('click', () => this.sendMessage());
      input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });
    },

    toggleWindow: function() {
      this.isOpen = !this.isOpen;
      const window = document.getElementById('chatbot-window');
      window.classList.toggle('open', this.isOpen);
      if (this.isOpen) {
        document.getElementById('chatbot-input').focus();
      }
    },

    addWelcomeMessage: function() {
      if (this.config.welcomeMessage) {
        this.addMessage('assistant', this.config.welcomeMessage);
      }
    },

    addMessage: function(role, content) {
      const messagesContainer = document.getElementById('chatbot-messages');
      const messageEl = document.createElement('div');
      messageEl.className = `chatbot-message ${role}`;

      if (role === 'user') {
        messageEl.style.background = this.config.primaryColor;
      }

      messageEl.textContent = content;
      messagesContainer.appendChild(messageEl);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;

      this.messages.push({ role, content });
    },

    showTyping: function() {
      const messagesContainer = document.getElementById('chatbot-messages');
      const typingEl = document.createElement('div');
      typingEl.className = 'chatbot-message assistant typing';
      typingEl.id = 'chatbot-typing';
      typingEl.innerHTML = `
        <div class="chatbot-typing-indicator">
          <span></span><span></span><span></span>
        </div>
      `;
      messagesContainer.appendChild(typingEl);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    },

    hideTyping: function() {
      const typingEl = document.getElementById('chatbot-typing');
      if (typingEl) typingEl.remove();
    },

    async sendMessage: function() {
      const input = document.getElementById('chatbot-input');
      const send = document.getElementById('chatbot-send');
      const message = input.value.trim();

      if (!message) return;

      // Disable input
      input.value = '';
      input.disabled = true;
      send.disabled = true;

      // Add user message
      this.addMessage('user', message);
      this.showTyping();

      try {
        const response = await fetch(`${this.config.apiUrl}/api/chat/widget/${this.config.widgetId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: message,
            session_id: this.sessionId,
          }),
        });

        if (!response.ok) {
          throw new Error('Chat request failed');
        }

        const data = await response.json();
        this.hideTyping();
        this.addMessage('assistant', data.message);

        // Update session ID if changed
        if (data.session_id) {
          this.sessionId = data.session_id;
          localStorage.setItem('chatbot_session_' + this.config.widgetId, this.sessionId);
        }
      } catch (error) {
        console.error('ChatBot error:', error);
        this.hideTyping();
        this.addMessage('assistant', 'Sorry, something went wrong. Please try again.');
      } finally {
        input.disabled = false;
        send.disabled = false;
        input.focus();
      }
    },
  };

  // Expose globally
  window.ChatbotWidget = ChatbotWidget;
})();
