"""Scraper API endpoints."""

from fastapi import APIRouter, HTTPException, Query

from .models import ScrapeRequest, ScrapeJobResponse
from .service import get_scraper_service

router = APIRouter(prefix="/api/scraper", tags=["scraper"])


@router.post("/scrape", response_model=ScrapeJobResponse)
async def scrape_url(request: ScrapeRequest):
    """
    Scrape a URL or sitemap and add content to knowledge base.

    For single URLs, extracts text content and creates a document.
    For sitemaps, discovers URLs and scrapes up to max_pages.

    Args:
        request: Scrape configuration including URL, type, and options

    Returns:
        Scrape job response with results
    """
    try:
        service = get_scraper_service()
        result = await service.scrape_and_ingest(request)

        return ScrapeJobResponse(
            job_id="sync",
            status="completed",
            url=str(request.url),
            pages_processed=result["processed"],
            pages_failed=result["failed"],
            message=f"Scraped {result['processed']} pages, {result['failed']} failed",
            documents=[r for r in result["results"] if "error" not in r],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.get("/documents")
async def list_scraped_documents():
    """
    List all documents created from web scraping.

    Returns:
        List of scraped documents with metadata
    """
    service = get_scraper_service()
    docs = await service.list_scraped_documents()
    return {
        "documents": docs,
        "total": len(docs),
    }


@router.delete("/documents/{doc_id}")
async def delete_scraped_document(doc_id: str):
    """
    Delete a scraped document and its chunks.

    Args:
        doc_id: Document ID to delete

    Returns:
        Success message
    """
    try:
        service = get_scraper_service()
        await service.delete_scraped_document(doc_id)
        return {"message": "Scraped document deleted", "document_id": doc_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@router.post("/preview")
async def preview_scrape(url: str = Query(..., description="URL to preview")):
    """
    Preview what would be scraped from a URL without storing.

    Args:
        url: URL to preview

    Returns:
        Extracted content preview
    """
    try:
        service = get_scraper_service()
        result = await service.scrape_url(url)
        return {
            "url": result.url,
            "title": result.title,
            "word_count": result.word_count,
            "content_preview": result.content[:1000] + "..." if len(result.content) > 1000 else result.content,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.get("/sitemap")
async def find_sitemap(url: str = Query(..., description="Base URL to find sitemap")):
    """
    Find sitemap for a given domain.

    Args:
        url: Base URL of the website

    Returns:
        Sitemap URL if found
    """
    from .sitemap import SitemapParser

    parser = SitemapParser()
    sitemap_url = await parser.find_sitemap(url)

    if sitemap_url:
        return {"sitemap_url": sitemap_url, "found": True}
    else:
        return {"sitemap_url": None, "found": False, "message": "No sitemap found"}
