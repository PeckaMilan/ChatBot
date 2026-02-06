"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Google Cloud / Firebase
    google_cloud_project: str = ""
    google_application_credentials: str = ""
    firebase_project_id: str = ""

    # Gemini API
    google_api_key: str = ""

    # Cloud Storage
    gcs_bucket_name: str = ""

    # Application
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8080

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    # Rate limiting
    rate_limit_per_minute: int = 60

    # JWT Configuration
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # Admin authentication
    admin_api_token: str = ""

    # Public API URL (for widget embed code)
    public_api_url: str = "https://chatbot-api-182382115587.europe-west1.run.app"

    # Stripe billing (optional)
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
