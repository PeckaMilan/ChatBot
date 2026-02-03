"""Admin panel API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.firestore import get_firestore_client

router = APIRouter(prefix="/api/admin", tags=["admin"])


class SettingsUpdate(BaseModel):
    """Settings update model."""

    chatbot_name: str | None = None
    welcome_message: str | None = None
    system_prompt: str | None = None
    widget_color: str | None = None


class SettingsResponse(BaseModel):
    """Settings response model."""

    chatbot_name: str
    welcome_message: str
    system_prompt: str
    widget_color: str


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current chatbot settings."""
    # MVP: Use default user
    user_id = "default"

    firestore = get_firestore_client()
    settings = await firestore.get_settings(user_id)

    return SettingsResponse(**settings)


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(settings: SettingsUpdate):
    """Update chatbot settings."""
    # MVP: Use default user
    user_id = "default"

    firestore = get_firestore_client()

    # Get current settings and merge
    current = await firestore.get_settings(user_id)
    updated = {**current}

    if settings.chatbot_name is not None:
        updated["chatbot_name"] = settings.chatbot_name
    if settings.welcome_message is not None:
        updated["welcome_message"] = settings.welcome_message
    if settings.system_prompt is not None:
        updated["system_prompt"] = settings.system_prompt
    if settings.widget_color is not None:
        updated["widget_color"] = settings.widget_color

    await firestore.update_settings(user_id, updated)

    return SettingsResponse(**updated)


@router.get("/widget-code")
async def get_widget_code():
    """Get the embed code for the widget."""
    # MVP: Use default widget ID
    widget_id = "default"

    firestore = get_firestore_client()
    settings = await firestore.get_settings(widget_id)

    # Generate embed code
    embed_code = f'''<script src="/static/widget/chatbot-widget.js"></script>
<script>
  ChatbotWidget.init({{
    widgetId: "{widget_id}",
    apiUrl: window.location.origin,
    title: "{settings.get('chatbot_name', 'Chat')}",
    welcomeMessage: "{settings.get('welcome_message', 'Hello!')}",
    primaryColor: "{settings.get('widget_color', '#007bff')}"
  }});
</script>'''

    return {
        "embed_code": embed_code,
        "widget_id": widget_id,
    }
