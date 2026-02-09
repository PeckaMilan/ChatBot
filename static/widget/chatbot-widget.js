(function() {
  'use strict';

  const ChatbotWidget = {
    config: null,
    container: null,
    isOpen: false,
    sessionId: null,
    messages: [],
    userToken: null,
    currentMessageId: null,
    darkMode: false,

    init: function(config) {
      this._initConfig = config;
      this.config = {
        widgetId: config.widgetId || 'default',
        apiUrl: config.apiUrl || window.location.origin,
        position: config.position || 'bottom-right',
        primaryColor: config.primaryColor || '#007bff',
        title: config.title || 'Chat',
        welcomeMessage: config.welcomeMessage || 'Hello! How can I help you today?',
        placeholder: config.placeholder || 'Type a message...',
        userToken: config.userToken || null,
        poweredBy: config.poweredBy !== false,
        logoUrl: config.logoUrl || null,
        autoOpen: config.autoOpen || false,
        openDelay: config.openDelay || 0,
        streaming: config.streaming !== false,
        darkMode: config.darkMode || false,
      };

      this.userToken = this.config.userToken;
      this.darkMode = this.config.darkMode;
      this.sessionId = this.getOrCreateSessionId();
      this.injectStyles();
      this.createWidget();
      this.bindEvents();
      this.addWelcomeMessage();

      if (this.config.autoOpen) {
        setTimeout(() => this.toggleWindow(), this.config.openDelay);
      }

      // Fetch latest config from API and apply dynamic updates
      this.fetchRemoteConfig();
    },

    fetchRemoteConfig: async function() {
      try {
        const response = await fetch(
          `${this.config.apiUrl}/api/chat/widget/${this.config.widgetId}/config`
        );
        if (!response.ok) return;

        const remote = await response.json();
        const init = this._initConfig;

        // Apply remote config only for fields NOT explicitly set in init()
        const newTitle = init.title || remote.chatbot_name || this.config.title;
        const newColor = init.primaryColor || remote.widget_color || this.config.primaryColor;
        const newWelcome = init.welcomeMessage || remote.welcome_message || this.config.welcomeMessage;

        const changed = newTitle !== this.config.title
          || newColor !== this.config.primaryColor
          || newWelcome !== this.config.welcomeMessage;

        if (!changed) return;

        this.config.title = newTitle;
        this.config.primaryColor = newColor;
        this.config.welcomeMessage = newWelcome;

        // Update DOM
        const header = document.getElementById('chatbot-header');
        if (header) {
          header.style.background = newColor;
          header.querySelector('span').textContent = newTitle;
        }
        const toggle = document.getElementById('chatbot-toggle');
        if (toggle) toggle.style.background = newColor;
        const send = document.getElementById('chatbot-send');
        if (send) send.style.background = newColor;
        if (this.container) {
          this.container.style.setProperty('--chatbot-primary', newColor);
        }
      } catch (e) {
        // Silently fail - use config from init()
      }
    },

    // Set user token dynamically (for SPA apps)
    identify: function(token) {
      this.userToken = token;
      // Clear session to force re-authentication
      localStorage.removeItem('chatbot_session_' + this.config.widgetId);
      this.sessionId = this.getOrCreateSessionId();
    },

    // Toggle dark mode
    setDarkMode: function(enabled) {
      this.darkMode = enabled;
      if (this.container) {
        this.container.classList.toggle('dark-mode', enabled);
      }
    },

    // Get current state
    getState: function() {
      return this.config ? 'initialized' : 'not_initialized';
    },

    getOrCreateSessionId: function() {
      const key = 'chatbot_session_' + this.config.widgetId;
      let sessionId = localStorage.getItem(key);
      if (!sessionId) {
        // Use crypto API for better entropy when available
        if (typeof crypto !== 'undefined' && crypto.randomUUID) {
          sessionId = 'sess_' + crypto.randomUUID();
        } else {
          sessionId = 'sess_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 11);
        }
        localStorage.setItem(key, sessionId);
      }
      return sessionId;
    },

    escapeHtml: function(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    },

    renderMarkdown: function(text) {
      if (!text) return '';
      let html = this.escapeHtml(text);
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
      html = html.replace(/^### (.+)$/gm, '<h4 style="margin:6px 0 2px;font-size:1em;font-weight:600">$1</h4>');
      html = html.replace(/^## (.+)$/gm, '<h3 style="margin:6px 0 2px;font-size:1.05em;font-weight:600">$1</h3>');
      html = html.replace(/^# (.+)$/gm, '<h2 style="margin:6px 0 2px;font-size:1.1em;font-weight:600">$1</h2>');
      html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
      html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
      html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul style="margin:4px 0;padding-left:18px">$1</ul>');
      html = html.replace(/\n/g, '<br>');
      html = html.replace(/<br><ul/g, '<ul');
      html = html.replace(/<\/ul><br>/g, '</ul>');
      html = html.replace(/<\/li><br><li>/g, '</li><li>');
      return html;
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
        .chatbot-header-actions {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        #chatbot-dark-toggle, #chatbot-close {
          background: none;
          border: none;
          color: white;
          cursor: pointer;
          padding: 4px;
          opacity: 0.8;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        #chatbot-dark-toggle:hover, #chatbot-close:hover {
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
        .chatbot-message-wrapper {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .chatbot-message-wrapper.user {
          align-items: flex-end;
        }
        .chatbot-message-wrapper.assistant {
          align-items: flex-start;
        }
        .chatbot-message {
          max-width: 85%;
          padding: 12px 16px;
          border-radius: 16px;
          word-wrap: break-word;
        }
        .chatbot-message.user {
          color: white;
          border-bottom-right-radius: 4px;
        }
        .chatbot-message.assistant {
          background: #f1f3f4;
          color: #202124;
          border-bottom-left-radius: 4px;
        }
        .chatbot-message.typing {
          background: #f1f3f4;
        }
        .chatbot-feedback {
          display: flex;
          gap: 4px;
          margin-top: 4px;
        }
        .chatbot-feedback-btn {
          background: none;
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          padding: 4px 8px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 12px;
          color: #666;
          transition: all 0.2s;
        }
        .chatbot-feedback-btn:hover {
          background: #f5f5f5;
          border-color: #ccc;
        }
        .chatbot-feedback-btn.selected {
          background: #e3f2fd;
          border-color: #2196f3;
          color: #1976d2;
        }
        .chatbot-feedback-btn.selected.negative {
          background: #ffebee;
          border-color: #f44336;
          color: #d32f2f;
        }
        .chatbot-feedback-btn svg {
          width: 14px;
          height: 14px;
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
          background: white;
          color: #202124;
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
        /* Dark mode styles */
        #chatbot-widget-container.dark-mode #chatbot-window {
          background: #1e1e1e;
        }
        #chatbot-widget-container.dark-mode #chatbot-messages {
          background: #1e1e1e;
        }
        #chatbot-widget-container.dark-mode .chatbot-message.assistant {
          background: #333;
          color: #e0e0e0;
        }
        #chatbot-widget-container.dark-mode #chatbot-input-container {
          background: #1e1e1e;
          border-top-color: #333;
        }
        #chatbot-widget-container.dark-mode #chatbot-input {
          background: #333;
          color: #e0e0e0;
          border-color: #444;
        }
        #chatbot-widget-container.dark-mode #chatbot-input::placeholder {
          color: #888;
        }
        #chatbot-widget-container.dark-mode .chatbot-feedback-btn {
          background: #333;
          border-color: #444;
          color: #aaa;
        }
        #chatbot-widget-container.dark-mode .chatbot-feedback-btn:hover {
          background: #444;
          border-color: #555;
        }
        #chatbot-widget-container.dark-mode .chatbot-feedback-btn.selected {
          background: #1a3a5c;
          border-color: #2196f3;
          color: #64b5f6;
        }
        #chatbot-widget-container.dark-mode .chatbot-feedback-btn.selected.negative {
          background: #4a2020;
          border-color: #f44336;
          color: #ef9a9a;
        }
      `;
      document.head.appendChild(styles);
    },

    createWidget: function() {
      this.container = document.createElement('div');
      this.container.id = 'chatbot-widget-container';
      this.container.className = this.config.position;
      if (this.darkMode) {
        this.container.classList.add('dark-mode');
      }
      this.container.style.setProperty('--chatbot-primary', this.config.primaryColor);

      // Escape user-controlled content to prevent XSS
      const safeTitle = this.escapeHtml(this.config.title);
      const safePlaceholder = this.escapeHtml(this.config.placeholder);

      this.container.innerHTML = `
        <div id="chatbot-window">
          <div id="chatbot-header" style="background: ${this.config.primaryColor}">
            <span>${safeTitle}</span>
            <div class="chatbot-header-actions">
              <button id="chatbot-dark-toggle" aria-label="Toggle dark mode" title="Toggle dark mode">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                  <path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/>
                </svg>
              </button>
              <button id="chatbot-close" aria-label="Close chat">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                  <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
              </button>
            </div>
          </div>
          <div id="chatbot-messages" aria-live="polite"></div>
          <div id="chatbot-input-container">
            <input type="text" id="chatbot-input" placeholder="${safePlaceholder}" />
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
      const darkToggle = document.getElementById('chatbot-dark-toggle');
      const input = document.getElementById('chatbot-input');
      const send = document.getElementById('chatbot-send');

      toggle.addEventListener('click', () => this.toggleWindow());
      close.addEventListener('click', () => this.toggleWindow());
      darkToggle.addEventListener('click', () => this.setDarkMode(!this.darkMode));

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
        this.addMessage('assistant', this.config.welcomeMessage, false);
      }
    },

    addMessage: function(role, content, showFeedback = true) {
      const messagesContainer = document.getElementById('chatbot-messages');

      const wrapperEl = document.createElement('div');
      wrapperEl.className = `chatbot-message-wrapper ${role}`;

      const messageEl = document.createElement('div');
      messageEl.className = `chatbot-message ${role}`;

      if (role === 'user') {
        messageEl.style.background = this.config.primaryColor;
        messageEl.textContent = content;
      } else {
        messageEl.innerHTML = this.renderMarkdown(content);
      }
      wrapperEl.appendChild(messageEl);

      // Add feedback buttons for assistant messages (except welcome)
      if (role === 'assistant' && showFeedback) {
        const messageId = 'msg_' + Math.random().toString(36).slice(2, 11);
        messageEl.dataset.messageId = messageId;

        const feedbackEl = document.createElement('div');
        feedbackEl.className = 'chatbot-feedback';
        feedbackEl.innerHTML = `
          <button class="chatbot-feedback-btn" data-feedback="positive" data-message-id="${messageId}" title="Good response">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg>
          </button>
          <button class="chatbot-feedback-btn" data-feedback="negative" data-message-id="${messageId}" title="Bad response">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z"/></svg>
          </button>
        `;
        wrapperEl.appendChild(feedbackEl);

        // Bind feedback events
        feedbackEl.querySelectorAll('.chatbot-feedback-btn').forEach(btn => {
          btn.addEventListener('click', (e) => this.submitFeedback(e));
        });
      }

      messagesContainer.appendChild(wrapperEl);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;

      this.messages.push({ role, content });
      return messageEl;
    },

    createStreamingMessage: function() {
      const messagesContainer = document.getElementById('chatbot-messages');

      const wrapperEl = document.createElement('div');
      wrapperEl.className = 'chatbot-message-wrapper assistant';
      wrapperEl.id = 'chatbot-streaming-wrapper';

      const messageEl = document.createElement('div');
      messageEl.className = 'chatbot-message assistant';
      messageEl.id = 'chatbot-streaming';
      messageEl.textContent = '';

      wrapperEl.appendChild(messageEl);
      messagesContainer.appendChild(wrapperEl);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;

      return messageEl;
    },

    finalizeStreamingMessage: function(content) {
      const streamingWrapper = document.getElementById('chatbot-streaming-wrapper');
      const streamingEl = document.getElementById('chatbot-streaming');

      if (streamingWrapper && streamingEl) {
        // Render markdown now that streaming is complete
        streamingEl.innerHTML = this.renderMarkdown(content);

        const messageId = 'msg_' + Math.random().toString(36).slice(2, 11);
        streamingEl.dataset.messageId = messageId;
        streamingEl.removeAttribute('id');
        streamingWrapper.removeAttribute('id');

        // Add feedback buttons
        const feedbackEl = document.createElement('div');
        feedbackEl.className = 'chatbot-feedback';
        feedbackEl.innerHTML = `
          <button class="chatbot-feedback-btn" data-feedback="positive" data-message-id="${messageId}" title="Good response">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg>
          </button>
          <button class="chatbot-feedback-btn" data-feedback="negative" data-message-id="${messageId}" title="Bad response">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z"/></svg>
          </button>
        `;
        streamingWrapper.appendChild(feedbackEl);

        // Bind feedback events
        feedbackEl.querySelectorAll('.chatbot-feedback-btn').forEach(btn => {
          btn.addEventListener('click', (e) => this.submitFeedback(e));
        });
      }

      this.messages.push({ role: 'assistant', content });
    },

    submitFeedback: async function(e) {
      const btn = e.currentTarget;
      const feedback = btn.dataset.feedback;
      const messageId = btn.dataset.messageId;

      // Prevent double-click
      if (btn.classList.contains('selected')) return;

      // Mark button as selected
      const feedbackContainer = btn.parentElement;
      feedbackContainer.querySelectorAll('.chatbot-feedback-btn').forEach(b => {
        b.classList.remove('selected', 'negative');
      });
      btn.classList.add('selected');
      if (feedback === 'negative') {
        btn.classList.add('negative');
      }

      try {
        await fetch(`${this.config.apiUrl}/api/chat/widget/${this.config.widgetId}/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message_id: messageId,
            session_id: this.sessionId,
            feedback: feedback,
          }),
        });
      } catch (error) {
        console.error('Feedback submission failed:', error);
      }
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

    sendMessage: async function() {
      const input = document.getElementById('chatbot-input');
      const send = document.getElementById('chatbot-send');
      const message = input.value.trim();

      if (!message) return;

      // Disable input
      input.value = '';
      input.disabled = true;
      send.disabled = true;

      // Add user message
      this.addMessage('user', message, false);

      // Use streaming if enabled
      if (this.config.streaming) {
        await this.sendStreamingMessage(message);
      } else {
        await this.sendRegularMessage(message);
      }

      input.disabled = false;
      send.disabled = false;
      input.focus();
    },

    sendStreamingMessage: async function(message) {
      const messagesContainer = document.getElementById('chatbot-messages');

      try {
        const headers = { 'Content-Type': 'application/json' };
        if (this.userToken) {
          headers['X-User-Token'] = this.userToken;
        }

        const response = await fetch(`${this.config.apiUrl}/api/chat/widget/${this.config.widgetId}/stream`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({
            message: message,
            session_id: this.sessionId,
          }),
        });

        if (response.status === 429) {
          this.addMessage('assistant', 'Too many messages. Please wait a moment and try again.');
          return;
        }
        if (response.status === 402) {
          this.addMessage('assistant', 'Chat limit reached. Please contact the site administrator.');
          return;
        }
        if (!response.ok) {
          throw new Error('Stream request failed');
        }

        const messageEl = this.createStreamingMessage();
        let fullContent = '';

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const text = decoder.decode(value, { stream: true });
          const lines = text.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.chunk) {
                  fullContent += data.chunk;
                  messageEl.textContent = fullContent;
                  messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }

                if (data.done) {
                  this.finalizeStreamingMessage(fullContent);
                }

                if (data.error) {
                  messageEl.textContent = 'Sorry, an error occurred. Please try again.';
                  this.finalizeStreamingMessage(messageEl.textContent);
                }
              } catch (e) {
                // Ignore parse errors for incomplete chunks
              }
            }
          }
        }

        // Ensure message is finalized even if no done signal
        if (fullContent && !document.querySelector('.chatbot-feedback')) {
          this.finalizeStreamingMessage(fullContent);
        }

      } catch (error) {
        console.error('ChatBot streaming error:', error);
        // Fall back to regular message on streaming error
        await this.sendRegularMessage(message);
      }
    },

    sendRegularMessage: async function(message) {
      this.showTyping();

      try {
        const headers = { 'Content-Type': 'application/json' };
        if (this.userToken) {
          headers['X-User-Token'] = this.userToken;
        }

        const response = await fetch(`${this.config.apiUrl}/api/chat/widget/${this.config.widgetId}`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({
            message: message,
            session_id: this.sessionId,
          }),
        });

        if (response.status === 429) {
          throw new Error('rate_limit');
        }
        if (response.status === 402) {
          throw new Error('usage_limit');
        }
        if (!response.ok) {
          throw new Error('Chat request failed');
        }

        const data = await response.json();
        this.hideTyping();
        this.addMessage('assistant', data.message);

        if (data.session_id) {
          this.sessionId = data.session_id;
          localStorage.setItem('chatbot_session_' + this.config.widgetId, this.sessionId);
        }
      } catch (error) {
        console.error('ChatBot error:', error);
        this.hideTyping();

        let errorMessage = 'Sorry, something went wrong. Please try again.';
        if (error.message === 'rate_limit') {
          errorMessage = 'Too many messages. Please wait a moment and try again.';
        } else if (error.message === 'usage_limit') {
          errorMessage = 'Chat limit reached. Please contact the site administrator.';
        }

        this.addMessage('assistant', errorMessage);
      }
    },
  };

  // Expose globally
  window.ChatbotWidget = ChatbotWidget;
})();
