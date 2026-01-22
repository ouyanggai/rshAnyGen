"""RAG Pipeline Client"""
import httpx
from typing import Dict, Any, List, Optional
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

logger = LogManager("orchestrator").get_logger()
config = ConfigLoader().load_defaults()

class RAGPipelineClient:
    """Client for RAG Pipeline Service"""
    
    def __init__(self):
        self.base_url = f"http://localhost:{config.get('ports', {}).get('rag_pipeline', 9305)}"
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)

    async def search(self, query: str, top_k: int = 5, rerank: bool = True, kb_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search knowledge base"""
        try:
            payload = {
                "query": query,
                "top_k": top_k,
                "rerank": rerank,
                "kb_ids": kb_ids
            }
            response = await self.client.post("/api/v1/search", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error searching RAG: {e}")
            # Fallback or re-raise
            return []

    async def close(self):
        await self.client.aclose()
