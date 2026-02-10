"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.config import get_settings
from src.core.rate_limiter import limiter
from src.features.admin.router import router as admin_router
from src.features.analytics.router import router as analytics_router
from src.features.chat.router import router as chat_router
from src.features.documents.router import router as documents_router
from src.features.scraper.router import router as scraper_router

# Multi-tenant SaaS features
from src.features.billing.router import router as billing_router
from src.features.customer_portal.router import router as customer_portal_router
from src.features.admin_portal.router import router as admin_portal_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    settings = get_settings()
    print(f"Starting ChatBot Platform in {settings.app_env} mode")
    yield
    # Shutdown
    print("Shutting down ChatBot Platform")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ChatBot Platform",
        description="ChatBase alternative - embeddable chatbot platform with RAG",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files for widget
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Include routers
    app.include_router(documents_router)
    app.include_router(chat_router)
    app.include_router(admin_router)
    app.include_router(analytics_router)
    app.include_router(scraper_router)

    # Multi-tenant SaaS routers
    app.include_router(billing_router)
    app.include_router(customer_portal_router)
    app.include_router(admin_portal_router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "0.1.0"}

    # API info endpoint
    @app.get("/")
    async def root():
        return {
            "name": "ChatBot Platform",
            "version": "0.1.0",
            "docs": "/docs" if settings.app_debug else None,
            "portal": "/portal",
        }

    # Customer portal redirect
    @app.get("/portal")
    async def portal_redirect():
        return RedirectResponse(url="/static/portal/index.html")

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )
