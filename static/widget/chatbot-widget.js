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
    _systemDarkQuery: null,

    init: function(config) {
      this._initConfig = config;
      this.config = {
        widgetId: config.widgetId || 'default',
        apiUrl: config.apiUrl || window.location.origin,
        position: config.position || 'bottom-right',
        primaryColor: config.primaryColor || '#667eea',
        title: config.title || 'Chat',
        welcomeMessage: config.welcomeMessage || 'Hello! How can I help you today?',
        placeholder: config.placeholder || 'Type a message...',
        userToken: config.userToken || null,
        poweredBy: config.poweredBy !== false,
        logoUrl: config.logoUrl || null,
        autoOpen: config.autoOpen || false,
        openDelay: config.openDelay || 0,
        streaming: config.streaming !== false,
        darkMode: config.darkMode || 'auto',
      };

      this.userToken = this.config.userToken;
      this.sessionId = this.getOrCreateSessionId();

      // Resolve dark mode: explicit true/false, or auto-detect from system
      if (this.config.darkMode === 'auto') {
        this._systemDarkQuery = window.matchMedia('(prefers-color-scheme: dark)');
        this.darkMode = this._systemDarkQuery.matches;
        this._systemDarkQuery.addEventListener('change', (e) => {
          // Only auto-switch if user hasn't manually toggled
          if (this.config.darkMode === 'auto') {
            this.setDarkMode(e.matches);
          }
        });
      } else {
        this.darkMode = !!this.config.darkMode;
      }

      this.injectStyles();
      this.createWidget();
      this.bindEvents();

      // Fetch remote config first, then show welcome message
      this.fetchRemoteConfig().then(() => {
        this.addWelcomeMessage();
        if (this.config.autoOpen) {
          setTimeout(() => this.toggleWindow(), this.config.openDelay);
        }
      });
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
        const newWelcome = remote.welcome_message || init.welcomeMessage || this.config.welcomeMessage;

        const changed = newTitle !== this.config.title
          || newColor !== this.config.primaryColor
          || newWelcome !== this.config.welcomeMessage;

        if (!changed) return;

        this.config.title = newTitle;
        this.config.primaryColor = newColor;
        this.config.welcomeMessage = newWelcome;

        // Update CSS custom property and DOM
        if (this.container) {
          this.container.style.setProperty('--cb-primary', newColor);
        }
        const headerTitle = this.container.querySelector('.cb-header-title');
        if (headerTitle) headerTitle.textContent = newTitle;
      } catch (e) {
        // Silently fail - use config from init()
      }
    },

    // Set user token dynamically (for SPA apps)
    identify: function(token) {
      this.userToken = token;
      localStorage.removeItem('chatbot_session_' + this.config.widgetId);
      this.sessionId = this.getOrCreateSessionId();
    },

    // Toggle dark mode
    setDarkMode: function(enabled) {
      this.darkMode = enabled;
      // Stop auto-detection if user manually toggles
      if (this._initConfig && this._initConfig.darkMode !== 'auto') {
        this.config.darkMode = enabled;
      }
      if (this.container) {
        this.container.classList.toggle('cb-dark', enabled);
      }
    },

    getState: function() {
      return this.config ? 'initialized' : 'not_initialized';
    },

    getOrCreateSessionId: function() {
      const key = 'chatbot_session_' + this.config.widgetId;
      let sessionId = localStorage.getItem(key);
      if (!sessionId) {
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

      // Code blocks (``` ... ```)
      html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, function(match, lang, code) {
        return '<pre class="cb-code-block"><code>' + code.trim() + '</code></pre>';
      });

      // Inline code
      html = html.replace(/`([^`]+)`/g, '<code class="cb-inline-code">$1</code>');

      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
      html = html.replace(/^### (.+)$/gm, '<h4 class="cb-heading">$1</h4>');
      html = html.replace(/^## (.+)$/gm, '<h3 class="cb-heading">$1</h3>');
      html = html.replace(/^# (.+)$/gm, '<h2 class="cb-heading">$1</h2>');
      html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
      html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
      html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul class="cb-list">$1</ul>');
      html = html.replace(/\n/g, '<br>');
      html = html.replace(/<br><ul/g, '<ul');
      html = html.replace(/<\/ul><br>/g, '</ul>');
      html = html.replace(/<\/li><br><li>/g, '</li><li>');
      html = html.replace(/<br><pre/g, '<pre');
      html = html.replace(/<\/pre><br>/g, '</pre>');
      return html;
    },

    _computeGradient: function(color) {
      // Generate a complementary gradient from the primary color
      // Parse hex to shift hue slightly for gradient end
      const hex = color.replace('#', '');
      const r = parseInt(hex.substring(0, 2), 16);
      const g = parseInt(hex.substring(2, 4), 16);
      const b = parseInt(hex.substring(4, 6), 16);

      // Shift toward purple/deeper tone
      const r2 = Math.max(0, Math.min(255, Math.round(r * 0.75)));
      const g2 = Math.max(0, Math.min(255, Math.round(g * 0.6)));
      const b2 = Math.max(0, Math.min(255, Math.round(b * 1.1)));

      const toHex = (n) => n.toString(16).padStart(2, '0');
      return `linear-gradient(135deg, ${color} 0%, #${toHex(r2)}${toHex(g2)}${toHex(b2)} 100%)`;
    },

    injectStyles: function() {
      if (document.getElementById('chatbot-widget-styles')) return;

      const styles = document.createElement('style');
      styles.id = 'chatbot-widget-styles';
      styles.textContent = `
        /* ─── CSS Custom Properties ─── */
        #chatbot-widget-container {
          --cb-primary: #667eea;
          --cb-primary-hover: #5a6fd6;
          --cb-radius-sm: 8px;
          --cb-radius-md: 12px;
          --cb-radius-lg: 20px;
          --cb-radius-full: 50%;
          --cb-shadow-sm: 0 2px 8px rgba(0,0,0,0.08);
          --cb-shadow-md: 0 8px 24px rgba(0,0,0,0.12);
          --cb-shadow-lg: 0 20px 60px rgba(0,0,0,0.15);
          --cb-shadow-toggle: 0 6px 20px rgba(102,126,234,0.4);
          --cb-font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
          --cb-fs-xs: 11px;
          --cb-fs-sm: 12px;
          --cb-fs-md: 13px;
          --cb-fs-base: 14px;
          --cb-fs-lg: 16px;
          --cb-fs-xl: 17px;
          --cb-fw-normal: 400;
          --cb-fw-medium: 500;
          --cb-fw-semibold: 600;
          --cb-transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
          --cb-bg-window: #ffffff;
          --cb-bg-input: #ffffff;
          --cb-bg-msg-assistant: #f0f2f5;
          --cb-bg-msg-user: var(--cb-primary);
          --cb-text-primary: #1a1d21;
          --cb-text-secondary: #5f6368;
          --cb-text-muted: #9aa0a6;
          --cb-border: #e4e7eb;
          --cb-border-focus: var(--cb-primary);
          --cb-source-green: #10b981;
          --cb-source-amber: #f59e0b;
          --cb-source-red: #ef4444;

          font-family: var(--cb-font);
          font-size: var(--cb-fs-base);
          line-height: 1.5;
          position: fixed;
          z-index: 999999;
        }

        /* ─── Positioning ─── */
        #chatbot-widget-container.bottom-right { bottom: 20px; right: 20px; }
        #chatbot-widget-container.bottom-left { bottom: 20px; left: 20px; }

        /* ─── Toggle Button (Glassmorphism) ─── */
        #chatbot-toggle {
          width: 60px;
          height: 60px;
          border-radius: var(--cb-radius-full);
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: var(--cb-shadow-toggle);
          transition: transform var(--cb-transition), box-shadow var(--cb-transition);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          position: relative;
          overflow: hidden;
        }
        #chatbot-toggle::before {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: inherit;
          background: inherit;
          opacity: 0.9;
        }
        #chatbot-toggle:hover {
          transform: scale(1.08) translateY(-2px);
          box-shadow: 0 8px 28px rgba(102,126,234,0.5);
        }
        #chatbot-toggle:active {
          transform: scale(0.95);
        }
        #chatbot-toggle svg {
          width: 28px;
          height: 28px;
          fill: white;
          position: relative;
          z-index: 1;
        }

        /* ─── Chat Window ─── */
        #chatbot-window {
          position: absolute;
          bottom: 72px;
          right: 0;
          width: 400px;
          max-width: calc(100vw - 32px);
          height: 520px;
          max-height: calc(100vh - 100px);
          background: var(--cb-bg-window);
          border-radius: var(--cb-radius-lg);
          box-shadow: var(--cb-shadow-lg);
          border: 1px solid var(--cb-border);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          opacity: 0;
          transform: translateY(16px) scale(0.96);
          pointer-events: none;
          transition: opacity var(--cb-transition), transform var(--cb-transition);
        }
        #chatbot-window.open {
          opacity: 1;
          transform: translateY(0) scale(1);
          pointer-events: auto;
        }

        /* ─── Header (Gradient) ─── */
        .cb-header {
          padding: 18px 20px;
          color: white;
          display: flex;
          align-items: center;
          justify-content: space-between;
          position: relative;
          overflow: hidden;
        }
        .cb-header::after {
          content: '';
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          height: 1px;
          background: rgba(255,255,255,0.15);
        }
        .cb-header-left {
          display: flex;
          align-items: center;
          gap: 10px;
          min-width: 0;
        }
        .cb-header-avatar {
          width: 32px;
          height: 32px;
          border-radius: var(--cb-radius-full);
          background: rgba(255,255,255,0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .cb-header-avatar svg {
          width: 18px;
          height: 18px;
          fill: white;
        }
        .cb-header-info {
          min-width: 0;
        }
        .cb-header-title {
          font-weight: var(--cb-fw-semibold);
          font-size: var(--cb-fs-lg);
          letter-spacing: -0.01em;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .cb-header-status {
          font-size: var(--cb-fs-xs);
          opacity: 0.8;
          font-weight: var(--cb-fw-normal);
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .cb-status-dot {
          width: 6px;
          height: 6px;
          border-radius: var(--cb-radius-full);
          background: #4ade80;
          display: inline-block;
        }
        .cb-header-actions {
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .cb-header-btn {
          background: rgba(255,255,255,0.1);
          border: none;
          color: white;
          cursor: pointer;
          padding: 6px;
          border-radius: var(--cb-radius-sm);
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background var(--cb-transition);
        }
        .cb-header-btn:hover {
          background: rgba(255,255,255,0.2);
        }
        .cb-header-btn svg {
          width: 18px;
          height: 18px;
          fill: currentColor;
        }

        /* ─── Messages ─── */
        #chatbot-messages {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          background: var(--cb-bg-window);
          scroll-behavior: smooth;
        }
        #chatbot-messages::-webkit-scrollbar {
          width: 4px;
        }
        #chatbot-messages::-webkit-scrollbar-track {
          background: transparent;
        }
        #chatbot-messages::-webkit-scrollbar-thumb {
          background: var(--cb-border);
          border-radius: 2px;
        }

        /* ─── Message Wrappers ─── */
        .cb-msg-wrap {
          display: flex;
          flex-direction: column;
          gap: 4px;
          animation: cbSlideIn var(--cb-transition) ease-out;
        }
        .cb-msg-wrap.user {
          align-items: flex-end;
          animation-name: cbSlideInRight;
        }
        .cb-msg-wrap.assistant {
          align-items: flex-start;
          animation-name: cbSlideInLeft;
        }

        @keyframes cbSlideInLeft {
          from { opacity: 0; transform: translateX(-12px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes cbSlideInRight {
          from { opacity: 0; transform: translateX(12px); }
          to { opacity: 1; transform: translateX(0); }
        }

        @media (prefers-reduced-motion: reduce) {
          .cb-msg-wrap { animation: none !important; }
          #chatbot-window { transition: opacity 0.1s !important; }
          #chatbot-toggle { transition: none !important; }
        }

        /* ─── Message Bubbles ─── */
        .cb-msg {
          max-width: 85%;
          padding: 10px 14px;
          border-radius: var(--cb-radius-md);
          word-wrap: break-word;
          font-size: var(--cb-fs-base);
          line-height: 1.55;
          letter-spacing: 0.01em;
        }
        .cb-msg.user {
          color: white;
          border-bottom-right-radius: 4px;
        }
        .cb-msg.assistant {
          background: var(--cb-bg-msg-assistant);
          color: var(--cb-text-primary);
          border-bottom-left-radius: 4px;
        }
        .cb-msg.typing {
          background: var(--cb-bg-msg-assistant);
        }

        /* ─── Markdown in Messages ─── */
        .cb-msg .cb-heading {
          margin: 8px 0 4px;
          font-weight: var(--cb-fw-semibold);
          line-height: 1.3;
        }
        .cb-msg h2.cb-heading { font-size: 1.05em; }
        .cb-msg h3.cb-heading { font-size: 1em; }
        .cb-msg h4.cb-heading { font-size: 0.95em; }
        .cb-msg .cb-list {
          margin: 4px 0;
          padding-left: 18px;
        }
        .cb-msg .cb-list li {
          margin-bottom: 2px;
        }
        .cb-msg .cb-code-block {
          background: #1e1e2e;
          color: #cdd6f4;
          padding: 10px 12px;
          border-radius: var(--cb-radius-sm);
          overflow-x: auto;
          font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
          font-size: var(--cb-fs-sm);
          line-height: 1.5;
          margin: 6px 0;
          white-space: pre-wrap;
          word-break: break-word;
        }
        .cb-msg .cb-inline-code {
          background: rgba(0,0,0,0.06);
          padding: 1px 5px;
          border-radius: 4px;
          font-family: 'SF Mono', 'Fira Code', Consolas, monospace;
          font-size: 0.9em;
        }

        /* ─── Feedback Buttons ─── */
        .cb-feedback {
          display: flex;
          gap: 4px;
          margin-top: 2px;
          opacity: 0;
          transition: opacity var(--cb-transition);
        }
        .cb-msg-wrap:hover .cb-feedback {
          opacity: 1;
        }
        .cb-feedback-btn {
          background: none;
          border: 1px solid var(--cb-border);
          border-radius: 6px;
          padding: 3px 8px;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: var(--cb-fs-sm);
          color: var(--cb-text-muted);
          transition: all var(--cb-transition);
        }
        .cb-feedback-btn:hover {
          background: var(--cb-bg-msg-assistant);
          border-color: var(--cb-text-muted);
          color: var(--cb-text-secondary);
        }
        .cb-feedback-btn.selected {
          background: #eff6ff;
          border-color: #3b82f6;
          color: #2563eb;
        }
        .cb-feedback-btn.selected.negative {
          background: #fef2f2;
          border-color: #ef4444;
          color: #dc2626;
        }
        .cb-feedback-btn svg { width: 13px; height: 13px; }

        /* ─── Typing Indicator ─── */
        .cb-typing-dots {
          display: flex;
          gap: 4px;
          padding: 4px 0;
        }
        .cb-typing-dots span {
          width: 7px;
          height: 7px;
          background: var(--cb-text-muted);
          border-radius: var(--cb-radius-full);
          animation: cbBounce 1.4s infinite ease-in-out both;
        }
        .cb-typing-dots span:nth-child(1) { animation-delay: -0.32s; }
        .cb-typing-dots span:nth-child(2) { animation-delay: -0.16s; }
        @keyframes cbBounce {
          0%, 80%, 100% { transform: scale(0); opacity: 0.4; }
          40% { transform: scale(1); opacity: 1; }
        }

        /* ─── Input Area ─── */
        .cb-input-area {
          padding: 12px 16px;
          border-top: 1px solid var(--cb-border);
          background: var(--cb-bg-window);
        }
        .cb-input-row {
          display: flex;
          gap: 8px;
          align-items: center;
        }
        #chatbot-input {
          flex: 1;
          padding: 10px 16px;
          border: 1.5px solid var(--cb-border);
          border-radius: 24px;
          outline: none;
          font-family: var(--cb-font);
          font-size: var(--cb-fs-base);
          color: var(--cb-text-primary);
          background: var(--cb-bg-input);
          transition: border-color var(--cb-transition), box-shadow var(--cb-transition);
        }
        #chatbot-input:focus {
          border-color: var(--cb-primary);
          box-shadow: 0 0 0 3px rgba(102,126,234,0.15);
        }
        #chatbot-input::placeholder {
          color: var(--cb-text-muted);
        }
        #chatbot-send {
          width: 40px;
          height: 40px;
          border-radius: var(--cb-radius-full);
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: opacity var(--cb-transition), transform var(--cb-transition);
          flex-shrink: 0;
        }
        #chatbot-send:hover:not(:disabled) {
          transform: scale(1.05);
        }
        #chatbot-send:active:not(:disabled) {
          transform: scale(0.92);
        }
        #chatbot-send:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }
        #chatbot-send svg { width: 18px; height: 18px; fill: white; }

        /* ─── Powered-By Footer ─── */
        .cb-powered-by {
          text-align: center;
          padding: 6px 0 2px;
          font-size: var(--cb-fs-xs);
          color: var(--cb-text-muted);
          letter-spacing: 0.02em;
        }
        .cb-powered-by a {
          color: var(--cb-text-muted);
          text-decoration: none;
          transition: color var(--cb-transition);
        }
        .cb-powered-by a:hover {
          color: var(--cb-text-secondary);
        }

        /* ─── Sources (Card Style) ─── */
        .cb-sources {
          max-width: 85%;
          margin-top: 4px;
        }
        .cb-sources-toggle {
          cursor: pointer;
          font-size: var(--cb-fs-sm);
          color: var(--cb-text-muted);
          padding: 4px 0;
          user-select: none;
          display: flex;
          align-items: center;
          gap: 6px;
          font-weight: var(--cb-fw-medium);
          transition: color var(--cb-transition);
        }
        .cb-sources-toggle:hover {
          color: var(--cb-text-secondary);
        }
        .cb-sources-toggle svg {
          width: 14px;
          height: 14px;
          fill: currentColor;
          transition: transform var(--cb-transition);
        }
        .cb-sources-toggle.open svg {
          transform: rotate(90deg);
        }
        .cb-sources-list {
          display: none;
          padding: 6px 0;
          gap: 6px;
          flex-direction: column;
        }
        .cb-sources-list.open {
          display: flex;
        }
        .cb-source-card {
          padding: 8px 10px;
          border-radius: var(--cb-radius-sm);
          background: var(--cb-bg-msg-assistant);
          border-left: 3px solid var(--cb-border);
          font-size: var(--cb-fs-md);
          line-height: 1.4;
          transition: background var(--cb-transition);
        }
        .cb-source-card:hover {
          background: var(--cb-border);
        }
        .cb-source-card.score-high { border-left-color: var(--cb-source-green); }
        .cb-source-card.score-mid { border-left-color: var(--cb-source-amber); }
        .cb-source-card.score-low { border-left-color: var(--cb-source-red); }
        .cb-source-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }
        .cb-source-name {
          font-weight: var(--cb-fw-medium);
          color: var(--cb-text-primary);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          min-width: 0;
        }
        .cb-source-badge {
          font-size: var(--cb-fs-xs);
          font-weight: var(--cb-fw-semibold);
          padding: 1px 6px;
          border-radius: 10px;
          white-space: nowrap;
          flex-shrink: 0;
        }
        .cb-source-badge.high { background: #d1fae5; color: #065f46; }
        .cb-source-badge.mid { background: #fef3c7; color: #92400e; }
        .cb-source-badge.low { background: #fee2e2; color: #991b1b; }
        .cb-source-text {
          color: var(--cb-text-muted);
          font-size: var(--cb-fs-sm);
          margin-top: 4px;
          overflow: hidden;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          line-height: 1.4;
        }
        .cb-source-text.expanded {
          -webkit-line-clamp: unset;
        }
        .cb-source-expand {
          font-size: var(--cb-fs-xs);
          color: var(--cb-primary);
          cursor: pointer;
          margin-top: 2px;
          display: inline-block;
          font-weight: var(--cb-fw-medium);
        }
        .cb-source-expand:hover {
          text-decoration: underline;
        }

        /* ─── PII Warning ─── */
        .cb-pii-warning {
          font-size: var(--cb-fs-sm);
          color: #92400e;
          background: linear-gradient(135deg, #fef3c7, #fde68a);
          padding: 8px 12px;
          border-radius: var(--cb-radius-sm);
          border-left: 3px solid #f59e0b;
          margin-bottom: 4px;
          max-width: 85%;
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: var(--cb-fw-medium);
        }
        .cb-pii-warning svg {
          width: 16px;
          height: 16px;
          fill: #d97706;
          flex-shrink: 0;
        }

        /* ═══════════════════════════════════ */
        /* ─── Dark Mode ─── */
        /* ═══════════════════════════════════ */
        #chatbot-widget-container.cb-dark {
          --cb-bg-window: #1a1d23;
          --cb-bg-input: #252830;
          --cb-bg-msg-assistant: #2a2d35;
          --cb-text-primary: #e4e7eb;
          --cb-text-secondary: #9ca3af;
          --cb-text-muted: #6b7280;
          --cb-border: #374151;
          --cb-shadow-lg: 0 20px 60px rgba(0,0,0,0.4);
        }
        #chatbot-widget-container.cb-dark #chatbot-window {
          border-color: #2d3340;
        }
        #chatbot-widget-container.cb-dark .cb-msg .cb-inline-code {
          background: rgba(255,255,255,0.1);
        }
        #chatbot-widget-container.cb-dark .cb-feedback-btn {
          border-color: #374151;
          color: #6b7280;
        }
        #chatbot-widget-container.cb-dark .cb-feedback-btn:hover {
          background: #2a2d35;
          border-color: #4b5563;
          color: #9ca3af;
        }
        #chatbot-widget-container.cb-dark .cb-feedback-btn.selected {
          background: #1e3a5f;
          border-color: #3b82f6;
          color: #60a5fa;
        }
        #chatbot-widget-container.cb-dark .cb-feedback-btn.selected.negative {
          background: #4a1d1d;
          border-color: #ef4444;
          color: #fca5a5;
        }
        #chatbot-widget-container.cb-dark .cb-source-card {
          background: #252830;
        }
        #chatbot-widget-container.cb-dark .cb-source-card:hover {
          background: #2d3340;
        }
        #chatbot-widget-container.cb-dark .cb-source-badge.high { background: #064e3b; color: #6ee7b7; }
        #chatbot-widget-container.cb-dark .cb-source-badge.mid { background: #78350f; color: #fcd34d; }
        #chatbot-widget-container.cb-dark .cb-source-badge.low { background: #7f1d1d; color: #fca5a5; }
        #chatbot-widget-container.cb-dark .cb-pii-warning {
          background: linear-gradient(135deg, #3d3520, #44391c);
          color: #fbbf24;
          border-left-color: #d97706;
        }
        #chatbot-widget-container.cb-dark .cb-pii-warning svg {
          fill: #fbbf24;
        }
        #chatbot-widget-container.cb-dark #chatbot-messages::-webkit-scrollbar-thumb {
          background: #374151;
        }

        /* ─── Mobile Responsive ─── */
        @media (max-width: 480px) {
          #chatbot-window {
            width: calc(100vw - 16px);
            height: calc(100vh - 80px);
            bottom: 68px;
            right: -12px;
            border-radius: var(--cb-radius-md);
          }
        }
      `;
      document.head.appendChild(styles);
    },

    createWidget: function() {
      this.container = document.createElement('div');
      this.container.id = 'chatbot-widget-container';
      this.container.className = this.config.position;
      if (this.darkMode) {
        this.container.classList.add('cb-dark');
      }
      this.container.style.setProperty('--cb-primary', this.config.primaryColor);

      const gradient = this._computeGradient(this.config.primaryColor);
      const safeTitle = this.escapeHtml(this.config.title);
      const safePlaceholder = this.escapeHtml(this.config.placeholder);

      const poweredByHtml = this.config.poweredBy
        ? '<div class="cb-powered-by">Powered by <a href="https://www.dwx.cz" target="_blank" rel="noopener">DWX</a></div>'
        : '';

      this.container.innerHTML = `
        <div id="chatbot-window">
          <div class="cb-header" style="background: ${gradient}">
            <div class="cb-header-left">
              <div class="cb-header-avatar">
                <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
              </div>
              <div class="cb-header-info">
                <div class="cb-header-title">${safeTitle}</div>
                <div class="cb-header-status"><span class="cb-status-dot"></span> Online</div>
              </div>
            </div>
            <div class="cb-header-actions">
              <button class="cb-header-btn" id="chatbot-dark-toggle" aria-label="Toggle dark mode" title="Toggle dark mode">
                <svg viewBox="0 0 24 24"><path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/></svg>
              </button>
              <button class="cb-header-btn" id="chatbot-close" aria-label="Close chat">
                <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
              </button>
            </div>
          </div>
          <div id="chatbot-messages" aria-live="polite"></div>
          <div class="cb-input-area">
            <div class="cb-input-row">
              <input type="text" id="chatbot-input" placeholder="${safePlaceholder}" />
              <button id="chatbot-send" style="background: ${gradient}" aria-label="Send message">
                <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
              </button>
            </div>
            ${poweredByHtml}
          </div>
        </div>
        <button id="chatbot-toggle" style="background: ${gradient}" aria-label="Open chat">
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
      darkToggle.addEventListener('click', () => {
        // Manual toggle overrides auto-detection
        this.config.darkMode = !this.darkMode;
        this.setDarkMode(!this.darkMode);
      });

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
      const win = document.getElementById('chatbot-window');
      win.classList.toggle('open', this.isOpen);
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
      wrapperEl.className = `cb-msg-wrap ${role}`;

      const messageEl = document.createElement('div');
      messageEl.className = `cb-msg ${role}`;

      if (role === 'user') {
        const gradient = this._computeGradient(this.config.primaryColor);
        messageEl.style.background = gradient;
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
        feedbackEl.className = 'cb-feedback';
        feedbackEl.innerHTML = `
          <button class="cb-feedback-btn" data-feedback="positive" data-message-id="${messageId}" title="Good response">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg>
          </button>
          <button class="cb-feedback-btn" data-feedback="negative" data-message-id="${messageId}" title="Bad response">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z"/></svg>
          </button>
        `;
        wrapperEl.appendChild(feedbackEl);

        feedbackEl.querySelectorAll('.cb-feedback-btn').forEach(btn => {
          btn.addEventListener('click', (e) => this.submitFeedback(e));
        });
      }

      messagesContainer.appendChild(wrapperEl);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;

      this.messages.push({ role, content });
      return wrapperEl;
    },

    createStreamingMessage: function() {
      const messagesContainer = document.getElementById('chatbot-messages');

      const wrapperEl = document.createElement('div');
      wrapperEl.className = 'cb-msg-wrap assistant';
      wrapperEl.id = 'chatbot-streaming-wrapper';

      const messageEl = document.createElement('div');
      messageEl.className = 'cb-msg assistant';
      messageEl.id = 'chatbot-streaming';
      messageEl.textContent = '';

      wrapperEl.appendChild(messageEl);
      messagesContainer.appendChild(wrapperEl);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;

      return messageEl;
    },

    finalizeStreamingMessage: function(content, sources, piiWarning) {
      const streamingWrapper = document.getElementById('chatbot-streaming-wrapper');
      const streamingEl = document.getElementById('chatbot-streaming');

      if (streamingWrapper && streamingEl) {
        streamingEl.innerHTML = this.renderMarkdown(content);

        const messageId = 'msg_' + Math.random().toString(36).slice(2, 11);
        streamingEl.dataset.messageId = messageId;
        streamingEl.removeAttribute('id');
        streamingWrapper.removeAttribute('id');

        // Add feedback buttons
        const feedbackEl = document.createElement('div');
        feedbackEl.className = 'cb-feedback';
        feedbackEl.innerHTML = `
          <button class="cb-feedback-btn" data-feedback="positive" data-message-id="${messageId}" title="Good response">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg>
          </button>
          <button class="cb-feedback-btn" data-feedback="negative" data-message-id="${messageId}" title="Bad response">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z"/></svg>
          </button>
        `;
        streamingWrapper.appendChild(feedbackEl);

        feedbackEl.querySelectorAll('.cb-feedback-btn').forEach(btn => {
          btn.addEventListener('click', (e) => this.submitFeedback(e));
        });

        if (sources && sources.length) {
          this.renderSources(streamingWrapper, sources);
        }

        if (piiWarning) {
          this.showPiiWarning(streamingWrapper);
        }
      }

      this.messages.push({ role: 'assistant', content });
    },

    submitFeedback: async function(e) {
      const btn = e.currentTarget;
      const feedback = btn.dataset.feedback;
      const messageId = btn.dataset.messageId;

      if (btn.classList.contains('selected')) return;

      const feedbackContainer = btn.parentElement;
      feedbackContainer.querySelectorAll('.cb-feedback-btn').forEach(b => {
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
        // Feedback submission failed silently
      }
    },

    renderSources: function(wrapperEl, sources) {
      if (!sources || !sources.length) return;

      const sourcesEl = document.createElement('div');
      sourcesEl.className = 'cb-sources';

      const toggle = document.createElement('div');
      toggle.className = 'cb-sources-toggle';
      toggle.innerHTML = '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg> Sources (' + sources.length + ')';

      const list = document.createElement('div');
      list.className = 'cb-sources-list';

      for (const source of sources) {
        const card = document.createElement('div');
        card.className = 'cb-source-card';

        const score = Math.round((source.score || 0) * 100);
        const scoreClass = score >= 70 ? 'high' : (score >= 50 ? 'mid' : 'low');
        card.classList.add('score-' + scoreClass);

        const name = source.filename || 'Document';
        const page = source.page_number ? ' (p.' + source.page_number + ')' : '';
        const text = source.text || '';

        let cardHtml = '<div class="cb-source-header">' +
          '<span class="cb-source-name">' + this.escapeHtml(name) + page + '</span>' +
          '<span class="cb-source-badge ' + scoreClass + '">' + score + '%</span>' +
          '</div>';

        if (text) {
          const needsExpand = text.length > 120;
          cardHtml += '<div class="cb-source-text' + (needsExpand ? '' : ' expanded') + '">' +
            this.escapeHtml(text) + '</div>';
          if (needsExpand) {
            cardHtml += '<span class="cb-source-expand">Show more</span>';
          }
        }

        card.innerHTML = cardHtml;

        // Bind expand/collapse
        const expandBtn = card.querySelector('.cb-source-expand');
        if (expandBtn) {
          expandBtn.addEventListener('click', function() {
            const textEl = card.querySelector('.cb-source-text');
            const isExpanded = textEl.classList.contains('expanded');
            textEl.classList.toggle('expanded');
            expandBtn.textContent = isExpanded ? 'Show more' : 'Show less';
          });
        }

        list.appendChild(card);
      }

      toggle.addEventListener('click', function() {
        const isOpen = toggle.classList.contains('open');
        toggle.classList.toggle('open');
        list.classList.toggle('open');
      });

      sourcesEl.appendChild(toggle);
      sourcesEl.appendChild(list);
      wrapperEl.appendChild(sourcesEl);
    },

    showPiiWarning: function(wrapperEl) {
      const warning = document.createElement('div');
      warning.className = 'cb-pii-warning';
      warning.innerHTML = '<svg viewBox="0 0 24 24"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg> Sensitive data detected and redacted before processing';
      wrapperEl.insertBefore(warning, wrapperEl.firstChild);
    },

    showTyping: function() {
      const messagesContainer = document.getElementById('chatbot-messages');
      const wrapperEl = document.createElement('div');
      wrapperEl.className = 'cb-msg-wrap assistant';
      wrapperEl.id = 'chatbot-typing';

      const messageEl = document.createElement('div');
      messageEl.className = 'cb-msg assistant typing';
      messageEl.innerHTML = '<div class="cb-typing-dots"><span></span><span></span><span></span></div>';

      wrapperEl.appendChild(messageEl);
      messagesContainer.appendChild(wrapperEl);
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

      input.value = '';
      input.disabled = true;
      send.disabled = true;

      this.addMessage('user', message, false);

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
                  this.finalizeStreamingMessage(fullContent, data.sources, data.pii_warning);
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
        if (fullContent && !document.querySelector('.cb-feedback')) {
          this.finalizeStreamingMessage(fullContent);
        }

      } catch (error) {
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
        const wrapperEl = this.addMessage('assistant', data.message);

        if (data.sources && data.sources.length) {
          this.renderSources(wrapperEl, data.sources);
        }

        if (data.pii_warning) {
          this.showPiiWarning(wrapperEl);
        }

        if (data.session_id) {
          this.sessionId = data.session_id;
          localStorage.setItem('chatbot_session_' + this.config.widgetId, this.sessionId);
        }
      } catch (error) {
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
