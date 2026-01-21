"""RAG Pipeline API Server"""

import os
import sys
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import shutil
import tempfile
from pathlib import Path

# Add project root to path if running directly
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager
from services.rag_pipeline.pipeline import RAGPipeline

from services.rag_pipeline.database import init_db, get_db, Document
from sqlalchemy.orm import Session
from fastapi import Depends
import uuid

# Initialize database
init_db()

# Initialize logging
log_manager = LogManager("rag_pipeline")
logger = log_manager.get_logger()

# Load config
def _merge_dict(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _merge_dict(base.get(key, {}), value)
        else:
            base[key] = value
    return base

def _coerce_int(value: Any) -> Any:
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return value

try:
    config_loader = ConfigLoader()
    config = config_loader.load_defaults()
    rag_config = config_loader.load_config("rag")
    embedding_config = config_loader.load_config("embedding")
    vector_db_config = config_loader.load_config("vector_db")
    _merge_dict(config, rag_config)

    embedding_settings = dict(config.get("embedding", {}))
    active_embedding = embedding_config.get("active_embedding")
    embedding_providers = embedding_config.get("embedding_providers", {})
    if active_embedding and active_embedding in embedding_providers:
        provider_config = dict(embedding_providers.get(active_embedding, {}))
        embedding_settings["provider"] = active_embedding
        if "model" in provider_config:
            embedding_settings["model"] = provider_config.get("model")
        if "dimension" in provider_config:
            embedding_settings["dimension"] = _coerce_int(provider_config.get("dimension"))
        embedding_settings[active_embedding] = provider_config
    config["embedding"] = embedding_settings

    vector_db_settings = dict(config.get("vector_db", {}))
    active_vector_db = vector_db_config.get("active")
    vector_db_providers = vector_db_config.get("providers", {})
    if active_vector_db and active_vector_db in vector_db_providers:
        provider_config = dict(vector_db_providers.get(active_vector_db, {}))
        vector_db_settings.update(provider_config)
        vector_db_settings["provider"] = active_vector_db
    if "port" in vector_db_settings:
        vector_db_settings["port"] = _coerce_int(vector_db_settings.get("port"))
    if "dimension" in vector_db_settings:
        # Allow embedding config to override vector_db dimension if not explicitly set in vector_db provider
        # But here vector_db_settings already merged provider config.
        # If vector_db config says 1024, but embedding is 2048, we should probably warn or sync.
        # Let's trust embedding dimension if it's set in config
        if "embedding" in config and "dimension" in config["embedding"]:
             vector_db_settings["dimension"] = _coerce_int(config["embedding"]["dimension"])
        else:
             vector_db_settings["dimension"] = _coerce_int(vector_db_settings.get("dimension"))
    config["vector_db"] = vector_db_settings
except Exception as e:
    logger.warning(f"Failed to load config: {e}. Using defaults.")
    config = {}

# Initialize Pipeline
# Ensure we pass the full config, but pipeline expects specific sections
pipeline = RAGPipeline(config)

app = FastAPI(
    title="RAG Pipeline API",
    description="Document Ingestion and Retrieval API",
    version="1.0.0"
)

# ... (CORS)

# Models
class DocumentResponse(BaseModel):
    id: str
    name: str
    size: int
    uploaded_at: str
    status: str
    chunks: int
    error_message: Optional[str] = None

class IngestTextRequest(BaseModel):
    text: str
    doc_id: str
    metadata: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    rerank: bool = False

class SearchResultResponse(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: Optional[Dict[str, Any]] = None

@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "RAG Pipeline API",
        "status": "running",
        "collection": pipeline.collection_name
    }

@app.get("/api/v1/documents", response_model=List[DocumentResponse], tags=["Documents"])
async def list_documents(db: Session = Depends(get_db)):
    """List all documents"""
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [
        DocumentResponse(
            id=d.id,
            name=d.name,
            size=d.size,
            uploaded_at=d.uploaded_at.isoformat(),
            status=d.status,
            chunks=d.chunks,
            error_message=d.error_message
        ) for d in docs
    ]

@app.delete("/api/v1/documents/{doc_id}", tags=["Documents"])
async def delete_document(doc_id: str, db: Session = Depends(get_db)):
    """Delete a document"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 1. Delete physical file
    try:
        upload_dir = Path(project_root) / "uploads"
        # Try to find file with both patterns (with and without uuid prefix if logic changed)
        # Current logic uses: f"{doc_id}_{doc.name}"
        file_path = upload_dir / f"{doc_id}_{doc.name}"
        if file_path.exists():
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")
        else:
            logger.warning(f"File not found for deletion: {file_path}")
            
            # Fallback: check if there are other files starting with doc_id
            # in case naming convention changed
            for f in upload_dir.glob(f"{doc_id}_*"):
                os.remove(f)
                logger.info(f"Deleted fallback file: {f}")
                
    except Exception as e:
        logger.error(f"Failed to delete file for {doc_id}: {e}")
        # Continue to delete from DB/Vector store even if file delete fails
    
    # 2. Delete from vector store
    try:
        pipeline.vector_store.delete_by_doc_id(doc_id)
    except Exception as e:
        logger.error(f"Failed to delete vectors for {doc_id}: {e}")

    # 3. Delete record from DB
    db.delete(doc)
    db.commit()
    return {"status": "success", "id": doc_id}

@app.post("/api/v1/documents", response_model=DocumentResponse, tags=["Documents"])
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a file without indexing"""
    # Create DB record
    doc_id = str(uuid.uuid4())
    file_size = 0
    
    # Save to persistent storage (not just temp) because we need it later for indexing
    # For now, we'll use a 'uploads' directory in the service folder
    upload_dir = Path(project_root) / "uploads"
    upload_dir.mkdir(exist_ok=True)
    
    file_path = upload_dir / f"{doc_id}_{file.filename}"
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        file_size = file_path.stat().st_size
    
    db_doc = Document(
        id=doc_id,
        name=file.filename,
        size=file_size,
        status="uploaded"  # New status
    )
    db.add(db_doc)
    db.commit()
    
    return DocumentResponse(
        id=db_doc.id,
        name=db_doc.name,
        size=db_doc.size,
        uploaded_at=db_doc.uploaded_at.isoformat(),
        status=db_doc.status,
        chunks=db_doc.chunks,
        error_message=db_doc.error_message
    )

@app.post("/api/v1/documents/{doc_id}/index", tags=["Documents"])
async def index_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start indexing a previously uploaded document"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.status == "indexed":
         return {"status": "already_indexed", "id": doc_id}
         
    # Update status
    doc.status = "processing"
    db.commit()
    
    # Locate file
    upload_dir = Path(project_root) / "uploads"
    file_path = upload_dir / f"{doc_id}_{doc.name}"
    
    if not file_path.exists():
        doc.status = "error"
        doc.error_message = "File not found on server"
        db.commit()
        raise HTTPException(status_code=404, detail="File source not found")

    # Add to background task
    background_tasks.add_task(process_document_task, str(file_path), doc_id)
    
    return {"status": "processing_started", "id": doc_id}

async def process_document_task(file_path: str, doc_id: str):
    """Background task for processing document"""
    # We need a new DB session for the background task
    db = next(get_db())
    doc = db.query(Document).filter(Document.id == doc_id).first()
    
    try:
        # Ingest
        result = await pipeline.ingest_document(
            file_path,
            metadata={"original_filename": doc.name, "doc_id": doc_id}
        )
        
        # Update DB
        doc.status = "indexed"
        doc.chunks = result.get("chunks_created", 0)
        db.commit()
        logger.info(f"Successfully indexed document {doc_id}")
        
    except Exception as e:
        logger.error(f"Indexing failed for {doc_id}: {e}")
        doc.status = "error"
        doc.error_message = str(e)
        db.commit()
    finally:
        db.close()


@app.post("/api/v1/ingest/text", tags=["Ingestion"])
async def ingest_text(request: IngestTextRequest):
    """Ingest raw text"""
    try:
        result = await pipeline.ingest_text(
            request.text,
            request.doc_id,
            request.metadata
        )
        return result
    except Exception as e:
        logger.error(f"Text ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/search", response_model=List[SearchResultResponse], tags=["Search"])
async def search(request: SearchRequest):
    """Search for documents"""
    try:
        results = await pipeline.search(
            request.query,
            top_k=request.top_k,
            rerank=request.rerank
        )
        
        # Convert internal SearchResult objects to response model
        response = []
        for res in results:
            response.append(SearchResultResponse(
                chunk_id=res.chunk_id,
                content=res.content,
                score=res.score,
                metadata=res.metadata
            ))
        return response
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    port = config.get("ports", {}).get("rag_pipeline", 9305)
    # Use server:app instead of main:app
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
