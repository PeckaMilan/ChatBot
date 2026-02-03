"""Document API endpoints."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from .models import DocumentListResponse, DocumentResponse, DocumentUploadResponse
from .service import get_document_service

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Supported content types
SUPPORTED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc",
    "text/plain": "txt",
    "text/markdown": "md",
}

# Max file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document for processing.

    Supported formats: PDF, DOCX, TXT, MD
    Max size: 10MB
    """
    # Validate content type
    if file.content_type not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Supported: {list(SUPPORTED_TYPES.keys())}",
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB",
        )

    # MVP: Use "default" user. In production, get from auth token
    user_id = "default"

    try:
        service = get_document_service()
        doc = await service.upload_document(
            file_content=content,
            filename=file.filename or "untitled",
            content_type=file.content_type,
            user_id=user_id,
        )

        return DocumentUploadResponse(
            id=doc["id"],
            filename=doc["filename"],
            status=doc["status"],
            message="Document uploaded and queued for processing",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/", response_model=DocumentListResponse)
async def list_documents():
    """List all uploaded documents."""
    # MVP: Use "default" user
    user_id = "default"

    service = get_document_service()
    docs = await service.list_documents(user_id)

    return DocumentListResponse(
        documents=[DocumentResponse(**doc) for doc in docs],
        total=len(docs),
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    """Get document by ID."""
    service = get_document_service()
    doc = await service.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(**doc)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and all its chunks."""
    service = get_document_service()
    doc = await service.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await service.delete_document(doc_id)

    return {"message": "Document deleted successfully"}
