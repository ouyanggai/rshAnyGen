"""Embedder - Generate embeddings for text chunks"""

import asyncio
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Embedder:
    """Generate embeddings for text using various providers"""

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
        self.batch_size = embedding_config.get("batch_size", 32)
        self.dimension = embedding_config.get("dimension", 1024)

        # Provider-specific configs
        self.qwen_config = embedding_config.get("qwen", {})
        self.openai_config = embedding_config.get("openai", {})

        self._llm_client = None

    def _load_llm_client(self):
        """Lazy load LLM client for embeddings

        Returns:
            Configured embeddings client
        """
        if self._llm_client is not None:
            return self._llm_client

        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError:
            logger.error("langchain-openai not installed")
            raise

        if self.provider == "qwen":
            self._llm_client = OpenAIEmbeddings(
                model=self.model,
                openai_api_base=self.qwen_config.get(
                    "base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"
                ),
                openai_api_key=self.qwen_config.get("api_key", ""),
            )
        elif self.provider == "openai":
            self._llm_client = OpenAIEmbeddings(
                model=self.model,
                openai_api_key=self.openai_config.get("api_key", ""),
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")

        return self._llm_client

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of documents

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        client = self._load_llm_client()
        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            logger.debug(f"Embedding batch {i // self.batch_size + 1}, size: {len(batch)}")

            try:
                # Use asyncio to run the sync embedding in a thread
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(None, client.embed_documents, batch)
                all_embeddings.extend(embeddings)
            except Exception as e:
                logger.error(f"Error embedding batch: {e}")
                # Return zero vectors for failed batches
                zero_vector = [0.0] * self.dimension
                all_embeddings.extend([zero_vector.copy() for _ in batch])

        return all_embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query

        Args:
            query: Query string to embed

        Returns:
            Embedding vector
        """
        embeddings = await self.embed_documents([query])
        return embeddings[0] if embeddings else [0.0] * self.dimension

    async def embed_chunks(
        self, chunks: List[Any], content_field: str = "content"
    ) -> List[Dict[str, Any]]:
        """Embed text chunks with their content

        Args:
            chunks: List of chunk objects (with content attribute or dict)
            content_field: Field name to get content from (if chunks are dicts)

        Returns:
            List of dicts with chunk_id, content, and embedding
        """
        # Extract text content
        texts = []
        for chunk in chunks:
            if hasattr(chunk, "content"):
                texts.append(chunk.content)
            elif isinstance(chunk, dict):
                texts.append(chunk.get(content_field, ""))
            else:
                texts.append(str(chunk))

        # Generate embeddings
        embeddings = await self.embed_documents(texts)

        # Combine with chunk info
        results = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            result = {
                "index": i,
                "embedding": embedding,
            }

            if hasattr(chunk, "chunk_id"):
                result["chunk_id"] = chunk.chunk_id
                result["content"] = chunk.content
                if chunk.metadata:
                    result["metadata"] = chunk.metadata
            elif isinstance(chunk, dict):
                result.update(chunk)
            else:
                result["content"] = str(chunk)

            results.append(result)

        return results

    def get_dimension(self) -> int:
        """Get the dimension of embeddings

        Returns:
            Embedding dimension
        """
        return self.dimension

    def verify_dimension(self, embedding: List[float]) -> bool:
        """Verify that an embedding has the correct dimension

        Args:
            embedding: Embedding vector to check

        Returns:
            True if dimension is correct
        """
        return len(embedding) == self.dimension
