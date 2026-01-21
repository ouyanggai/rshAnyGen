"""Text Chunker - Split documents into chunks for embedding"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A text chunk with metadata"""

    content: str
    chunk_id: str
    parent_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TextChunker:
    """Split documents into chunks for embedding and retrieval"""

    DEFAULT_SEPARATORS = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize text chunker

        Args:
            config: Configuration dictionary with chunking settings
        """
        self.config = config or {}
        chunking_config = self.config.get("chunking", {})

        self.strategy = chunking_config.get("strategy", "parent_child")

        # Parent chunk settings
        parent_config = chunking_config.get("parent", {})
        self.parent_size = parent_config.get("size", 1000)
        self.parent_overlap = parent_config.get("overlap", 200)

        # Child chunk settings
        child_config = chunking_config.get("child", {})
        self.child_size = child_config.get("size", 300)
        self.child_overlap = child_config.get("overlap", 100)

        # Separators
        self.separators = chunking_config.get("separators", self.DEFAULT_SEPARATORS)

    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split text into chunks based on configured strategy

        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of Chunk objects
        """
        if self.strategy == "parent_child":
            return self._chunk_parent_child(text, metadata)
        elif self.strategy == "simple":
            return self._chunk_simple(text, metadata)
        else:
            logger.warning(f"Unknown strategy {self.strategy}, falling back to simple")
            return self._chunk_simple(text, metadata)

    def _chunk_parent_child(
        self, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Create parent-child chunks

        Parent chunks are larger for context, child chunks are smaller for precise retrieval.

        Args:
            text: Input text
            metadata: Optional metadata

        Returns:
            List of parent and child chunks
        """
        if not text or not text.strip():
            return []

        chunks = []

        # First create parent chunks
        parent_chunks = self._split_recursive(text, self.parent_size, self.parent_overlap)

        # Then create child chunks from each parent
        for i, parent_content in enumerate(parent_chunks):
            parent_id = f"parent_{i}"

            # Add parent chunk
            chunks.append(
                Chunk(
                    content=parent_content,
                    chunk_id=parent_id,
                    metadata={**(metadata or {}), "chunk_type": "parent", "parent_index": i},
                )
            )

            # Create child chunks from this parent
            child_chunks = self._split_recursive(
                parent_content, self.child_size, self.child_overlap
            )
            
            # If split recursive returned empty or only one chunk same as parent
            # we should still keep at least one child if it makes sense, 
            # but usually we want smaller chunks.
            # If parent is small enough, it might be its own child.
            if not child_chunks and parent_content:
                 child_chunks = [parent_content]

            for j, child_content in enumerate(child_chunks):
                chunks.append(
                    Chunk(
                        content=child_content,
                        chunk_id=f"child_{i}_{j}",
                        parent_id=parent_id,
                        metadata={
                            **(metadata or {}),
                            "chunk_type": "child",
                            "parent_index": i,
                            "child_index": j,
                        },
                    )
                )

        return chunks

    def _chunk_simple(
        self, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Simple chunking strategy

        Args:
            text: Input text
            metadata: Optional metadata

        Returns:
            List of chunks
        """
        chunks_text = self._split_recursive(text, self.child_size, self.child_overlap)

        return [
            Chunk(
                content=chunk,
                chunk_id=f"chunk_{i}",
                metadata={**(metadata or {}), "chunk_type": "simple", "index": i},
            )
            for i, chunk in enumerate(chunks_text)
        ]

    def _split_recursive(
        self, text: str, chunk_size: int, overlap: int
    ) -> List[str]:
        """Recursively split text using separators

        Args:
            text: Input text
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        chunks = []
        remaining = text

        while remaining:
            # If remaining text is short enough, take it all
            if len(remaining) <= chunk_size:
                chunks.append(remaining)
                break

            # Find best split point
            split_point = self._find_split_point(remaining[:chunk_size])

            if split_point == 0:
                # No good split point, force split at chunk_size
                split_point = chunk_size

            chunks.append(remaining[:split_point].strip())

            # Calculate next start with overlap
            if split_point > overlap:
                raw_next_start = split_point - overlap
            else:
                raw_next_start = split_point
            
            # Adjust next_start to align with sentence boundaries
            # Find the best split point in the overlap region
            adjusted_start = raw_next_start
            if split_point > overlap and raw_next_start > 0:
                # Look for separators in the text before raw_next_start
                # This ensures the next chunk starts after a separator
                boundary_search_text = remaining[:raw_next_start]
                # Reuse find_split_point which finds the last separator
                best_boundary = self._find_split_point(boundary_search_text)
                if best_boundary > 0:
                    adjusted_start = best_boundary
            
            # Ensure we make progress to avoid infinite loop
            if adjusted_start == 0:
                adjusted_start = split_point

            remaining = remaining[adjusted_start:]

        return [c for c in chunks if c.strip()]

    def _find_split_point(self, text: str) -> int:
        """Find the best split point in text using separators

        Args:
            text: Text to find split point in

        Returns:
            Index of best split point
        """
        # Try each separator in order
        for separator in self.separators:
            if not separator:
                continue

            # Find last occurrence of separator
            idx = text.rfind(separator)
            if idx != -1:
                # Split after the separator
                return idx + len(separator)

        # No separator found, return 0 to indicate force split
        return 0

    def merge_chunks(self, chunks: List[Chunk], max_size: int = 4000) -> List[str]:
        """Merge chunks back together (useful for context reconstruction)

        Args:
            chunks: Chunks to merge
            max_size: Maximum size for merged text

        Returns:
            List of merged text segments
        """
        if not chunks:
            return []

        # Group by parent if parent-child chunks
        parent_groups: Dict[str, List[Chunk]] = {}
        standalone_chunks = []

        for chunk in chunks:
            if chunk.parent_id:
                if chunk.parent_id not in parent_groups:
                    parent_groups[chunk.parent_id] = []
                parent_groups[chunk.parent_id].append(chunk)
            else:
                standalone_chunks.append(chunk)

        # Merge each group
        merged = []

        for parent_id, group in parent_groups.items():
            # Sort by child index if available
            group.sort(
                key=lambda c: (
                    c.metadata.get("child_index", 0) if c.metadata else 0
                )
            )
            content = "\n\n".join(c.content for c in group)
            merged.append(content)

        # Add standalone chunks
        merged.extend(c.content for c in standalone_chunks)

        # Further merge if needed
        if max_size:
            result = []
            current = ""

            for text in merged:
                if len(current) + len(text) <= max_size:
                    current += "\n\n" + text if current else text
                else:
                    if current:
                        result.append(current)
                    current = text

            if current:
                result.append(current)

            return result

        return merged
