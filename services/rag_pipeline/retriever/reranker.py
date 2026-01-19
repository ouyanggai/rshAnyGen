"""Reranker - Reorder search results for better relevance"""

import asyncio
from typing import List, Dict, Any, Optional
import logging

from ..store.vector_store import SearchResult

logger = logging.getLogger(__name__)


class Reranker:
    """Rerank search results using various methods"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize reranker

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        rerank_config = self.config.get("reranker", self.config)

        self.provider = rerank_config.get("provider", "qwen")
        self.model = rerank_config.get("model", "rerank-v2")
        self.top_n = rerank_config.get("top_n", 5)
        self.api_key = rerank_config.get("api_key", "")

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_n: Optional[int] = None,
    ) -> List[SearchResult]:
        """Rerank search results

        Args:
            query: Original search query
            results: Search results to rerank
            top_n: Number of top results to return

        Returns:
            Reranked search results
        """
        if not results:
            return results

        n = top_n or self.top_n
        n = min(n, len(results))

        if self.provider == "qwen":
            return await self._rerank_qwen(query, results, n)
        elif self.provider == "openai":
            return await self._rerank_openai(query, results, n)
        else:
            # Fallback to original scores
            logger.warning(f"Unknown rerank provider {self.provider}, using original scores")
            return results[:n]

    async def _rerank_qwen(
        self,
        query: str,
        results: List[SearchResult],
        top_n: int,
    ) -> List[SearchResult]:
        """Rerank using Qwen rerank API

        Args:
            query: Search query
            results: Search results
            top_n: Number of results to return

        Returns:
            Reranked results
        """
        try:
            import httpx

            # Prepare documents
            documents = [r.content for r in results if r.content]

            if not documents:
                return results[:top_n]

            # Call Qwen rerank API
            api_url = "https://dashscope.aliyuncs.com/api/v1/services/rerank/rerank/v1"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_n": top_n,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            # Extract reranked results
            if "output" in data and "results" in data["output"]:
                rerank_indices = [r["index"] for r in data["output"]["results"]]
                rerank_scores = [r.get("relevance_score", 0.0) for r in data["output"]["results"]]

                # Reorder results
                reranked = []
                for idx, score in zip(rerank_indices, rerank_scores):
                    if idx < len(results):
                        result = results[idx]
                        # Update score with rerank score
                        result.score = score
                        reranked.append(result)

                return reranked

        except ImportError:
            logger.warning("httpx not installed")
        except Exception as e:
            logger.error(f"Error reranking with Qwen: {e}")

        # Fallback to original results
        return results[:top_n]

    async def _rerank_openai(
        self,
        query: str,
        results: List[SearchResult],
        top_n: int,
    ) -> List[SearchResult]:
        """Rerank using OpenAI (not yet supported, fallback to original)

        Args:
            query: Search query
            results: Search results
            top_n: Number of results to return

        Returns:
            Reranked results
        """
        # OpenAI doesn't have a native rerank API yet
        # Could implement a custom one using embeddings
        logger.warning("OpenAI rerank not implemented, using original scores")
        return results[:top_n]


class NoOpReranker:
    """No-op reranker that just returns top N results by score"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize no-op reranker

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.top_n = self.config.get("top_n", 5)

    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_n: Optional[int] = None,
    ) -> List[SearchResult]:
        """Return top N results by original score

        Args:
            query: Search query (unused)
            results: Search results
            top_n: Number of results to return

        Returns:
            Top N results
        """
        n = top_n or self.top_n
        n = min(n, len(results))
        return results[:n]
