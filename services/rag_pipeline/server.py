"""RAG Pipeline API Server"""

import os
import sys
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Form, Query
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

from services.rag_pipeline.database import init_db, get_db, Document, KnowledgeBase
from sqlalchemy.orm import Session
from fastapi import Depends
import uuid
from datetime import datetime

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
        if "embedding" in config and "dimension" in config["embedding"]:
             vector_db_settings["dimension"] = _coerce_int(config["embedding"]["dimension"])
        else:
             vector_db_settings["dimension"] = _coerce_int(vector_db_settings.get("dimension"))
    config["vector_db"] = vector_db_settings
except Exception as e:
    logger.warning(f"Failed to load config: {e}. Using defaults.")
    config = {}

# Initialize database
init_db()

# Initialize Pipeline
pipeline = RAGPipeline(config)

app = FastAPI(
    title="RAG Pipeline API",
    description="Document Ingestion and Retrieval API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class DocumentResponse(BaseModel):
    id: str
    kb_id: str
    name: str
    size: int
    uploaded_at: str
    status: str
    chunks: int
    error_message: Optional[str] = None

class IngestTextRequest(BaseModel):
    text: str
    doc_id: str
    kb_id: str = "default"
    metadata: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    rerank: bool = False
    kb_ids: Optional[List[str]] = None

class SearchResultResponse(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: Optional[Dict[str, Any]] = None

class KnowledgeBaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    embedding_model: str = "zhipu"

class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class KnowledgeBaseResponse(BaseModel):
    id: str
    kb_id: str
    name: str
    description: Optional[str] = None
    embedding_model: str
    chunk_count: int
    doc_count: int
    created_at: str
    updated_at: str
    status: str

@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "RAG Pipeline API",
        "status": "running",
        "collection": pipeline.collection_name
    }

# --- Knowledge Base Management ---

@app.get("/api/v1/kb", response_model=List[KnowledgeBaseResponse], tags=["Knowledge Bases"])
async def list_knowledge_bases(db: Session = Depends(get_db)):
    """List all knowledge bases"""
    kbs = db.query(KnowledgeBase).filter(KnowledgeBase.status == 'active').all()
    return [
        KnowledgeBaseResponse(
            id=kb.id,
            kb_id=kb.kb_id,
            name=kb.name,
            description=kb.description,
            embedding_model=kb.embedding_model,
            chunk_count=kb.chunk_count,
            doc_count=kb.doc_count,
            created_at=kb.created_at.isoformat(),
            updated_at=kb.updated_at.isoformat(),
            status=kb.status
        ) for kb in kbs
    ]

@app.post("/api/v1/kb", response_model=KnowledgeBaseResponse, tags=["Knowledge Bases"])
async def create_knowledge_base(request: KnowledgeBaseCreate, db: Session = Depends(get_db)):
    """Create a new knowledge base"""
    # Check if name exists
    existing = db.query(KnowledgeBase).filter(KnowledgeBase.name == request.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Knowledge base with this name already exists")
    
    # Generate kb_id
    kb_uuid = str(uuid.uuid4())
    kb_id = f"kb_{kb_uuid}"
    
    new_kb = KnowledgeBase(
        kb_id=kb_id,
        name=request.name,
        description=request.description,
        embedding_model=request.embedding_model
    )
    db.add(new_kb)
    db.commit()
    db.refresh(new_kb)
    
    return KnowledgeBaseResponse(
        id=new_kb.id,
        kb_id=new_kb.kb_id,
        name=new_kb.name,
        description=new_kb.description,
        embedding_model=new_kb.embedding_model,
        chunk_count=new_kb.chunk_count,
        doc_count=new_kb.doc_count,
        created_at=new_kb.created_at.isoformat(),
        updated_at=new_kb.updated_at.isoformat(),
        status=new_kb.status
    )

@app.get("/api/v1/kb/{kb_id}", response_model=KnowledgeBaseResponse, tags=["Knowledge Bases"])
async def get_knowledge_base(kb_id: str, db: Session = Depends(get_db)):
    """Get knowledge base details"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    return KnowledgeBaseResponse(
        id=kb.id,
        kb_id=kb.kb_id,
        name=kb.name,
        description=kb.description,
        embedding_model=kb.embedding_model,
        chunk_count=kb.chunk_count,
        doc_count=kb.doc_count,
        created_at=kb.created_at.isoformat(),
        updated_at=kb.updated_at.isoformat(),
        status=kb.status
    )

@app.put("/api/v1/kb/{kb_id}", response_model=KnowledgeBaseResponse, tags=["Knowledge Bases"])
async def update_knowledge_base(kb_id: str, request: KnowledgeBaseUpdate, db: Session = Depends(get_db)):
    """Update knowledge base"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    if request.name:
        # Check name uniqueness if changed
        if request.name != kb.name:
            existing = db.query(KnowledgeBase).filter(KnowledgeBase.name == request.name).first()
            if existing:
                raise HTTPException(status_code=400, detail="Knowledge base name already taken")
        kb.name = request.name
        
    if request.description is not None:
        kb.description = request.description
        
    if request.status:
        kb.status = request.status
        
    db.commit()
    db.refresh(kb)
    
    return KnowledgeBaseResponse(
        id=kb.id,
        kb_id=kb.kb_id,
        name=kb.name,
        description=kb.description,
        embedding_model=kb.embedding_model,
        chunk_count=kb.chunk_count,
        doc_count=kb.doc_count,
        created_at=kb.created_at.isoformat(),
        updated_at=kb.updated_at.isoformat(),
        status=kb.status
    )

@app.delete("/api/v1/kb/{kb_id}", tags=["Knowledge Bases"])
async def delete_knowledge_base(kb_id: str, db: Session = Depends(get_db)):
    """Delete knowledge base and all its documents"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    # 1. Delete all documents files
    docs = db.query(Document).filter(Document.kb_id == kb_id).all()
    upload_dir = Path(project_root) / "uploads"
    for doc in docs:
        try:
            # Try to delete file
            file_path = upload_dir / f"{doc.id}_{doc.name}"
            if file_path.exists():
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Failed to delete file for {doc.id}: {e}")
            
    # 2. Delete from vector store
    try:
        pipeline.vector_store.delete_by_kb_id(kb_id)
    except Exception as e:
        logger.error(f"Failed to delete vectors for kb {kb_id}: {e}")
        
    # 3. Delete from DB (Cascade should handle documents, but we delete kb explicitly)
    db.delete(kb)
    db.commit()
    
    return {"status": "success", "id": kb_id}

# --- Document Management ---

@app.get("/api/v1/kb/{kb_id}/documents", response_model=List[DocumentResponse], tags=["Documents"])
async def list_documents(kb_id: str, db: Session = Depends(get_db)):
    """List all documents in a knowledge base"""
    # Verify KB exists
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    docs = db.query(Document).filter(Document.kb_id == kb_id).order_by(Document.uploaded_at.desc()).all()
    return [
        DocumentResponse(
            id=d.id,
            kb_id=d.kb_id,
            name=d.name,
            size=d.size,
            uploaded_at=d.uploaded_at.isoformat(),
            status=d.status,
            chunks=d.chunks,
            error_message=d.error_message
        ) for d in docs
    ]

@app.post("/api/v1/kb/{kb_id}/documents", response_model=DocumentResponse, tags=["Documents"])
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a file to a knowledge base without indexing"""
    # Verify KB exists
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Create DB record
    doc_id = str(uuid.uuid4())
    file_size = 0
    
    # Save to persistent storage
    upload_dir = Path(project_root) / "uploads"
    upload_dir.mkdir(exist_ok=True)
    
    file_path = upload_dir / f"{doc_id}_{file.filename}"
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        file_size = file_path.stat().st_size
    
    db_doc = Document(
        id=doc_id,
        kb_id=kb_id,
        name=file.filename,
        size=file_size,
        status="uploaded"
    )
    db.add(db_doc)
    
    # Update KB doc count
    kb.doc_count += 1
    
    db.commit()
    
    return DocumentResponse(
        id=db_doc.id,
        kb_id=db_doc.kb_id,
        name=db_doc.name,
        size=db_doc.size,
        uploaded_at=db_doc.uploaded_at.isoformat(),
        status=db_doc.status,
        chunks=db_doc.chunks,
        error_message=db_doc.error_message
    )

@app.post("/api/v1/kb/{kb_id}/documents/{doc_id}/index", tags=["Documents"])
async def index_document(
    kb_id: str,
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start indexing a previously uploaded document"""
    doc = db.query(Document).filter(Document.id == doc_id, Document.kb_id == kb_id).first()
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
    background_tasks.add_task(process_document_task, str(file_path), doc_id, kb_id)
    
    return {"status": "processing_started", "id": doc_id}

@app.delete("/api/v1/documents/{doc_id}", tags=["Documents"])
async def delete_document(doc_id: str, db: Session = Depends(get_db)):
    """Delete a document"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    kb_id = doc.kb_id
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
    
    # 1. Delete physical file
    try:
        upload_dir = Path(project_root) / "uploads"
        file_path = upload_dir / f"{doc_id}_{doc.name}"
        if file_path.exists():
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")
        else:
            # Fallback
            for f in upload_dir.glob(f"{doc_id}_*"):
                os.remove(f)
    except Exception as e:
        logger.error(f"Failed to delete file for {doc_id}: {e}")
    
    # 2. Delete from vector store
    try:
        pipeline.vector_store.delete_by_doc_id(doc_id)
    except Exception as e:
        logger.error(f"Failed to delete vectors for {doc_id}: {e}")

    # 3. Delete record from DB
    db.delete(doc)
    
    # Update KB stats
    if kb:
        kb.doc_count = max(0, kb.doc_count - 1)
        kb.chunk_count = max(0, kb.chunk_count - doc.chunks)
    
    db.commit()
    return {"status": "success", "id": doc_id}

async def process_document_task(file_path: str, doc_id: str, kb_id: str):
    """Background task for processing document"""
    # We need a new DB session for the background task
    db = next(get_db())
    doc = db.query(Document).filter(Document.id == doc_id).first()
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
    
    try:
        # Ingest
        result = await pipeline.ingest_document(
            file_path,
            metadata={"original_filename": doc.name, "doc_id": doc_id},
            kb_id=kb_id
        )
        
        # Update DB
        doc.status = "indexed"
        chunks_created = result.get("chunks_created", 0)
        doc.chunks = chunks_created
        
        if kb:
            kb.chunk_count += chunks_created
            
        db.commit()
        logger.info(f"Successfully indexed document {doc_id} into kb {kb_id}")
        
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
            request.metadata,
            kb_id=request.kb_id
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
            rerank=request.rerank,
            kb_ids=request.kb_ids
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
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
