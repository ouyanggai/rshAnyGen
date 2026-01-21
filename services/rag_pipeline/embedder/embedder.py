"""Embedder - Generate embeddings for text using various providers"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
import httpx

from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)


class Embedder:
    """Embedding generator supporting multiple providers"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize embedder

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Get embedding settings
        embedding_config = self.config.get("embedding", self.config)
        self.provider = embedding_config.get("provider", "qwen")
        self.model = embedding_config.get("model", "text-embedding-v3")
        self.dimension = embedding_config.get("dimension", 1024)
        self.batch_size = embedding_config.get("batch_size", 32)

        # Provider-specific configs
        self.qwen_config = embedding_config.get("qwen", {})
        self.zhipu_config = embedding_config.get("zhipu", {})
        self.openai_config = embedding_config.get("openai", {})

        # Initialize LLM client for OpenAI-compatible providers
        self._llm_client = None

    def _load_llm_client(self) -> OpenAIEmbeddings:
        """Load LLM client for embedding generation

        Returns:
            OpenAIEmbeddings client instance
        """
        if self._llm_client is not None:
            return self._llm_client

        if self.provider == "qwen":
            self._llm_client = OpenAIEmbeddings(
                model=self.model,
                openai_api_base=self.qwen_config.get(
                    "base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"
                ),
                openai_api_key=self.qwen_config.get("api_key", ""),
            )
        elif self.provider == "zhipu":
            self._llm_client = OpenAIEmbeddings(
                model=self.model,
                openai_api_base=self.zhipu_config.get(
                    "base_url", "https://open.bigmodel.cn/api/paas/v4"
                ),
                openai_api_key=self.zhipu_config.get("api_key", ""),
            )
        elif self.provider == "openai":
            self._llm_client = OpenAIEmbeddings(
                model=self.model,
                openai_api_key=self.openai_config.get("api_key", ""),
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")

        return self._llm_client

    def get_dimension(self) -> int:
        """Get embedding dimension

        Returns:
            Embedding dimension
        """
        return self.dimension

    def verify_dimension(self, vector: List[float]) -> bool:
        """Verify if vector has correct dimension

        Args:
            vector: Vector to verify

        Returns:
            True if dimension matches
        """
        return len(vector) == self.dimension

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple documents

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Ensure all texts are strings and not empty/None
        valid_texts = []
        original_indices = []

        for i, text in enumerate(texts):
            if text and isinstance(text, str) and text.strip():
                valid_texts.append(text[:8000])
                original_indices.append(i)

        if not valid_texts:
            return [[0.0] * self.dimension for _ in texts]

        if self.provider == "zhipu":
            return await self._embed_documents_zhipu(texts, valid_texts, original_indices)
        elif self.provider == "qwen":
            return await self._embed_documents_qwen(texts, valid_texts, original_indices)
        elif self.provider == "openai":
            return await self._embed_documents_openai(texts, valid_texts, original_indices)
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")

    async def embed_chunks(self, chunks: List[Any]) -> List[Dict[str, Any]]:
        """Generate embeddings for chunk objects or dicts

        Args:
            chunks: List of Chunk objects or dicts

        Returns:
            List of dicts with embeddings and metadata
        """
        if not chunks:
            return []

        texts = []
        for chunk in chunks:
            if hasattr(chunk, "content"):
                texts.append(chunk.content)
            elif isinstance(chunk, dict):
                texts.append(chunk.get("content", ""))
            else:
                texts.append("")

        embeddings = await self.embed_documents(texts)

        results = []
        for idx, chunk in enumerate(chunks):
            embedding = embeddings[idx] if idx < len(embeddings) else [0.0] * self.dimension
            if hasattr(chunk, "content"):
                results.append(
                    {
                        "chunk_id": getattr(chunk, "chunk_id", f"chunk_{idx}"),
                        "parent_id": getattr(chunk, "parent_id", None),
                        "content": getattr(chunk, "content", ""),
                        "metadata": getattr(chunk, "metadata", None),
                        "embedding": embedding,
                    }
                )
            elif isinstance(chunk, dict):
                item = dict(chunk)
                if "chunk_id" not in item and "id" in item:
                    item["chunk_id"] = item["id"]
                item["embedding"] = embedding
                results.append(item)
            else:
                results.append({"chunk_id": f"chunk_{idx}", "content": "", "embedding": embedding})

        return results

    async def _embed_documents_zhipu(
        self, texts: List[str], valid_texts: List[str], original_indices: List[int]
    ) -> List[List[float]]:
        base_url = self.zhipu_config.get("base_url", "https://open.bigmodel.cn/api/paas/v4")
        api_key = self.zhipu_config.get("api_key", "")
        if not api_key:
            return [[0.0] * self.dimension for _ in texts]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        all_embeddings_map = {}
        async with httpx.AsyncClient(timeout=60.0) as client:
            for i in range(0, len(valid_texts), self.batch_size):
                batch = valid_texts[i : i + self.batch_size]
                batch_start_idx = i
                payload = {
                    "model": self.model,
                    "input": batch if len(batch) > 1 else batch[0],
                }
                try:
                    response = await client.post(f"{base_url}/embeddings", json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    embeddings = []
                    if isinstance(data, dict):
                        if isinstance(data.get("data"), list):
                            for item in data.get("data"):
                                if isinstance(item, dict) and "embedding" in item:
                                    embeddings.append(item["embedding"])
                        elif isinstance(data.get("embeddings"), list):
                            embeddings = data.get("embeddings")

                    for j, emb in enumerate(embeddings):
                        all_embeddings_map[batch_start_idx + j] = emb
                except Exception as e:
                    logger.error(f"Error embedding batch: {e}")

        final_embeddings = []
        for i in range(len(texts)):
            if i in original_indices:
                valid_idx = original_indices.index(i)
                if valid_idx in all_embeddings_map:
                    final_embeddings.append(all_embeddings_map[valid_idx])
                else:
                    final_embeddings.append([0.0] * self.dimension)
            else:
                final_embeddings.append([0.0] * self.dimension)

        return final_embeddings

    async def _embed_documents_qwen(
        self, texts: List[str], valid_texts: List[str], original_indices: List[int]
    ) -> List[List[float]]:
        client = self._load_llm_client()
        all_embeddings_map = {}
        
        # Process in batches
        for i in range(0, len(valid_texts), self.batch_size):
            batch = valid_texts[i : i + self.batch_size]
            batch_start_idx = i
            logger.debug(f"Embedding batch {i // self.batch_size + 1}, size: {len(batch)}")

            try:
                # Use asyncio to run the sync embedding in a thread
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(None, client.embed_documents, batch)
                
                for j, emb in enumerate(embeddings):
                    all_embeddings_map[batch_start_idx + j] = emb
                    
            except Exception as e:
                logger.error(f"Error embedding batch: {e}")
                # Don't fail completely, just leave holes which will be filled with zeros
        
        # Reconstruct result list matching input texts
        final_embeddings = []
        for i in range(len(texts)):
            if i in original_indices:
                # Find where this original index maps to in valid_texts
                valid_idx = original_indices.index(i)
                if valid_idx in all_embeddings_map:
                    final_embeddings.append(all_embeddings_map[valid_idx])
                else:
                    final_embeddings.append([0.0] * self.dimension)
            else:
                final_embeddings.append([0.0] * self.dimension)

        return final_embeddings

    async def _embed_documents_openai(
        self, texts: List[str], valid_texts: List[str], original_indices: List[int]
    ) -> List[List[float]]:
        client = self._load_llm_client()
        all_embeddings_map = {}
        
        # Process in batches
        for i in range(0, len(valid_texts), self.batch_size):
            batch = valid_texts[i : i + self.batch_size]
            batch_start_idx = i
            logger.debug(f"Embedding batch {i // self.batch_size + 1}, size: {len(batch)}")

            try:
                # Use asyncio to run the sync embedding in a thread
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(None, client.embed_documents, batch)
                
                for j, emb in enumerate(embeddings):
                    all_embeddings_map[batch_start_idx + j] = emb
                    
            except Exception as e:
                logger.error(f"Error embedding batch: {e}")
                # Don't fail completely, just leave holes which will be filled with zeros
        
        # Reconstruct result list matching input texts
        final_embeddings = []
        for i in range(len(texts)):
            if i in original_indices:
                # Find where this original index maps to in valid_texts
                valid_idx = original_indices.index(i)
                if valid_idx in all_embeddings_map:
                    final_embeddings.append(all_embeddings_map[valid_idx])
                else:
                    final_embeddings.append([0.0] * self.dimension)
            else:
                final_embeddings.append([0.0] * self.dimension)

        return final_embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query

        Args:
            query: Query string to embed

        Returns:
            Embedding vector
        """
        if not query or not isinstance(query, str) or not query.strip():
            return [0.0] * self.dimension

        if self.provider == "zhipu":
            return await self._embed_query_zhipu(query)
        else:
            client = self._load_llm_client()
            try:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, client.embed_query, query)
            except Exception as e:
                logger.error(f"Error embedding query: {e}")
                return [0.0] * self.dimension

    async def _embed_query_zhipu(self, query: str) -> List[float]:
        base_url = self.zhipu_config.get("base_url", "https://open.bigmodel.cn/api/paas/v4")
        api_key = self.zhipu_config.get("api_key", "")
        if not api_key:
            return [0.0] * self.dimension

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "input": query,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{base_url}/embeddings", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, dict):
                    if isinstance(data.get("data"), list) and data["data"]:
                        return data["data"][0].get("embedding", [0.0] * self.dimension)
                    elif isinstance(data.get("embeddings"), list) and data["embeddings"]:
                        return data["embeddings"][0]
                
                return [0.0] * self.dimension
                
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            return [0.0] * self.dimension
