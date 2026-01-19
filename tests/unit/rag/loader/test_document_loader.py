"""Document Loader Unit Tests"""

import pytest
import tempfile
from pathlib import Path
from services.rag_pipeline.loader.document_loader import DocumentLoader


@pytest.mark.unit
class TestDocumentLoader:
    """Test DocumentLoader"""

    def test_init_default_config(self):
        """Test initialization with default config"""
        loader = DocumentLoader()
        assert loader.config == {}

    def test_init_with_config(self):
        """Test initialization with config"""
        config = {"test": "value"}
        loader = DocumentLoader(config)
        assert loader.config == config

    @pytest.mark.asyncio
    async def test_load_txt_file(self):
        """Test loading a text file"""
        loader = DocumentLoader()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello World\nThis is a test")
            temp_path = f.name

        try:
            result = await loader.load(temp_path)

            assert result["type"] == "text"
            assert "Hello World" in result["content"]
            assert result["metadata"]["format"] == ".txt"
            assert "file_name" in result["metadata"]
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_load_md_file(self):
        """Test loading a markdown file"""
        loader = DocumentLoader()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Header\n\nContent here")
            temp_path = f.name

        try:
            result = await loader.load(temp_path)

            assert result["type"] == "text"
            assert "# Header" in result["content"]
            assert result["metadata"]["format"] == ".md"
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_load_unsupported_extension(self):
        """Test loading file with unsupported extension"""
        loader = DocumentLoader()

        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported file type"):
                await loader.load(temp_path)
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self):
        """Test loading non-existent file"""
        loader = DocumentLoader()

        with pytest.raises(FileNotFoundError):
            await loader.load("/nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_load_batch(self):
        """Test loading multiple files in batch"""
        loader = DocumentLoader()

        temp_files = []
        try:
            for i in range(3):
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                    f.write(f"File {i} content")
                    temp_files.append(f.name)

            results = await loader.load_batch(temp_files)

            assert len(results) == 3
            assert all(r["type"] == "text" for r in results)
        finally:
            for f in temp_files:
                Path(f).unlink()

    def test_supported_extensions(self):
        """Test supported file extensions"""
        assert ".txt" in DocumentLoader.TEXT_EXTENSIONS
        assert ".md" in DocumentLoader.TEXT_EXTENSIONS
        assert ".pdf" in DocumentLoader.PDF_EXTENSIONS
        assert ".jpg" in DocumentLoader.IMAGE_EXTENSIONS
        assert ".docx" in DocumentLoader.WORD_EXTENSIONS
        assert ".xlsx" in DocumentLoader.EXCEL_EXTENSIONS
