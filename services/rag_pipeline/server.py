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

# Initialize logging
log_manager = LogManager("rag_pipeline")
logger = log_manager.get_logger()

# Load config
try:
    config_loader = ConfigLoader()
    config = config_loader.load_defaults()
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
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

@app.post("/api/v1/ingest/file", tags=["Ingestion"])
async def ingest_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """Ingest a file"""
    # Save to temp file
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    
    # Process immediately for now (could be background)
    try:
        # We need to await the pipeline method
        result = await pipeline.ingest_document(
            tmp_path,
            metadata={"original_filename": file.filename}
        )
        return result
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {tmp_path}: {e}")

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
