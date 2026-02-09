"""Widget embed code generator."""

from typing import Optional


def generate_embed_code(
    widget_id: str,
    api_url: str,
    settings: dict,
    jwt_secret: Optional[str] = None,
) -> dict:
    """
    Generate embed code similar to ChatBase.

    Returns dict with multiple embed options.
    """
    chatbot_name = settings.get("chatbot_name", "Chat")
    chatbot_name_escaped = chatbot_name.replace('"', '\\"')

    # Standard embed - config fetched dynamically from API
    standard_embed = f'''<script>
(function(){{
  const script=document.createElement("script");
  script.src="{api_url}/static/widget/chatbot-widget.js";
  script.async=true;
  script.onload=function(){{
    ChatbotWidget.init({{
      widgetId:"{widget_id}",
      apiUrl:"{api_url}"
    }});
  }};
  document.body.appendChild(script);
}})();
</script>'''

    # With identity verification
    identity_embed = f'''<!-- Server-side: Generate JWT for your logged-in user -->
<script>
// 1. Get token from your backend
async function initChatbot() {{
  const response = await fetch('/api/chatbot-token');
  const {{ token }} = await response.json();

  // 2. Initialize widget with user identity
  ChatbotWidget.init({{
    widgetId: "{widget_id}",
    apiUrl: "{api_url}",
    userToken: token,
    title: "{chatbot_name_escaped}"
  }});
}}

// 3. Load widget script then initialize
const script = document.createElement("script");
script.src = "{api_url}/static/widget/chatbot-widget.js";
script.onload = initChatbot;
document.body.appendChild(script);
</script>

<!-- Your backend endpoint should generate JWT like this:
const jwt = require('jsonwebtoken');
const token = jwt.sign(
  {{ user_id: user.id, email: user.email }},
  '{jwt_secret or "YOUR_WIDGET_JWT_SECRET"}',
  {{ expiresIn: '24h' }}
);
-->'''

    # Iframe embed (alternative)
    iframe_embed = f'''<iframe
  src="{api_url}/widget/iframe/{widget_id}"
  width="400"
  height="600"
  frameborder="0"
  style="position:fixed;bottom:20px;right:20px;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.15);z-index:9999;"
  allow="microphone"
></iframe>'''

    return {
        "widget_id": widget_id,
        "api_url": api_url,
        "standard": standard_embed,
        "with_identity": identity_embed,
        "iframe": iframe_embed,
        "jwt_secret": jwt_secret,
    }
