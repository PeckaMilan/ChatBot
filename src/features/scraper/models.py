"""Scraper data models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class ScrapeType(str, Enum):
    """Type of scrape operation."""
    SINGLE = "single"
    SITEMAP = "sitemap"


class ScrapeRequest(BaseModel):
    """Request to scrape a URL or sitemap."""
    url: HttpUrl
    scrape_type: ScrapeType = ScrapeType.SINGLE
    max_pages: int = Field(default=50, ge=1, le=500)
    include_patterns: list[str] | None = None
    exclude_patterns: list[str] | None = None
    chunking_strategy: str = Field(default="semantic")


class ScrapeResult(BaseModel):
    """Result of a scrape operation."""
    url: str
    title: str | None
    content: str
    word_count: int
    scraped_at: datetime


class ScrapeJobResponse(BaseModel):
    """Response for scrape job creation."""
    job_id: str
    status: str
    url: str
    pages_processed: int
    pages_failed: int
    message: str
    documents: list[dict] = []


class ScrapedDocument(BaseModel):
    """Scraped content as a document."""
    id: str
    source_url: str
    title: str | None
    content_preview: str
    chunk_count: int
    status: str
    scraped_at: datetime
