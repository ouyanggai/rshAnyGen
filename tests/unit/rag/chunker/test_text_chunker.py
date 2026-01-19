"""Text Chunker Unit Tests"""

import pytest
from pathlib import Path
from services.rag_pipeline.chunker.text_chunker import TextChunker, Chunk


@pytest.mark.unit
class TestTextChunker:
    """Test TextChunker"""

    def test_init_default_config(self):
        """Test initialization with default config"""
        chunker = TextChunker()
        assert chunker.strategy == "parent_child"
        assert chunker.parent_size == 1000
        assert chunker.child_size == 300

    def test_init_custom_config(self):
        """Test initialization with custom config"""
        config = {
            "chunking": {
                "strategy": "simple",
                "parent": {"size": 500, "overlap": 100},
                "child": {"size": 200, "overlap": 50}
            }
        }
        chunker = TextChunker(config)

        assert chunker.strategy == "simple"
        assert chunker.parent_size == 500
        assert chunker.parent_overlap == 100
        assert chunker.child_size == 200
        assert chunker.child_overlap == 50

    def test_chunk_empty_text(self):
        """Test chunking empty text"""
        chunker = TextChunker()
        chunks = chunker.chunk("")

        assert chunks == []

    def test_chunk_whitespace_only(self):
        """Test chunking whitespace-only text"""
        chunker = TextChunker()
        chunks = chunker.chunk("   \n\n   ")

        assert chunks == []

    def test_chunk_short_text(self):
        """Test chunking text shorter than chunk size"""
        chunker = TextChunker()
        chunks = chunker.chunk("Short text")

        assert len(chunks) > 0

    def test_chunk_with_metadata(self):
        """Test chunking with metadata"""
        chunker = TextChunker()
        metadata = {"source": "test.txt", "page": 1}

        chunks = chunker.chunk("Some text here", metadata=metadata)

        assert len(chunks) > 0
        assert chunks[0].metadata.get("source") == "test.txt"
        assert chunks[0].metadata.get("page") == 1

    def test_simple_strategy(self):
        """Test simple chunking strategy"""
        config = {"chunking": {"strategy": "simple", "child": {"size": 50}}}
        chunker = TextChunker(config)

        text = "This is a test. " * 20
        chunks = chunker.chunk(text)

        assert len(chunks) > 1
        assert all(c.metadata.get("chunk_type") == "simple" for c in chunks)

    def test_parent_child_strategy(self):
        """Test parent-child chunking strategy"""
        config = {
            "chunking": {
                "strategy": "parent_child",
                "parent": {"size": 200, "overlap": 20},
                "child": {"size": 50, "overlap": 10}
            }
        }
        chunker = TextChunker(config)

        text = "This is a test. " * 50
        chunks = chunker.chunk(text)

        parent_chunks = [c for c in chunks if c.metadata.get("chunk_type") == "parent"]
        child_chunks = [c for c in chunks if c.metadata.get("chunk_type") == "child"]

        assert len(parent_chunks) > 0
        assert len(child_chunks) > 0
        assert all(c.parent_id for c in child_chunks)

    def test_merge_chunks(self):
        """Test merging chunks"""
        chunker = TextChunker()

        chunks = [
            Chunk(content="Part 1", chunk_id="c1", metadata={"index": 0}),
            Chunk(content="Part 2", chunk_id="c2", metadata={"index": 1}),
        ]

        merged = chunker.merge_chunks(chunks)

        # With default max_size, small chunks should be merged
        assert len(merged) == 1
        assert "Part 1" in merged[0]
        assert "Part 2" in merged[0]

    def test_merge_parent_child_chunks(self):
        """Test merging parent-child chunks"""
        chunker = TextChunker()

        chunks = [
            Chunk(content="Parent 1", chunk_id="p1", metadata={"chunk_type": "parent"}),
            Chunk(content="Child 1.1", chunk_id="c1", parent_id="p1",
                  metadata={"chunk_type": "child", "child_index": 0}),
            Chunk(content="Child 1.2", chunk_id="c2", parent_id="p1",
                  metadata={"chunk_type": "child", "child_index": 1}),
        ]

        merged = chunker.merge_chunks(chunks)

        # Should group children by parent
        assert len(merged) >= 1

    def test_find_split_point(self):
        """Test finding split point in text"""
        chunker = TextChunker()

        # Text with separator
        text = "First part\n\nSecond part"
        split_point = chunker._find_split_point(text)
        assert split_point > 0

        # Text without separator
        text = "nosseparatorhere"
        split_point = chunker._find_split_point(text)
        assert split_point == 0

    def test_split_recursive(self):
        """Test recursive splitting"""
        chunker = TextChunker()

        text = "a" * 100
        chunks = chunker._split_recursive(text, chunk_size=30, overlap=5)

        assert len(chunks) > 1
        assert all(len(c) <= 35 for c in chunks)  # Allow some buffer
