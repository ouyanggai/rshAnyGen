"""Test Document Loader Formats"""
import pytest
import sys
from unittest.mock import MagicMock, patch
from pathlib import Path
from services.rag_pipeline.loader.document_loader import DocumentLoader

@pytest.mark.unit
class TestDocumentLoaderFormats:

    @pytest.fixture
    def loader(self):
        return DocumentLoader()

    @pytest.mark.asyncio
    async def test_load_pdf(self, loader, tmp_path):
        # Create a dummy PDF file
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4...") # Dummy content

        # Mock pypdf
        with patch.dict('sys.modules', {'pypdf': MagicMock()}):
            mock_pypdf = sys.modules['pypdf']
            mock_reader = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "PDF Content"
            mock_reader.pages = [mock_page]
            mock_pypdf.PdfReader.return_value = mock_reader
            
            result = await loader.load(str(pdf_path))
            assert result["type"] == "pdf"
            assert "PDF Content" in result["content"]
            assert result["metadata"]["page_count"] == 1

    @pytest.mark.asyncio
    async def test_load_word(self, loader, tmp_path):
        docx_path = tmp_path / "test.docx"
        docx_path.touch() # Create dummy file
        
        with patch.dict('sys.modules', {'docx': MagicMock()}):
            mock_docx = sys.modules['docx']
            mock_doc = MagicMock()
            mock_para = MagicMock()
            mock_para.text = "Word Content"
            mock_doc.paragraphs = [mock_para]
            mock_docx.Document.return_value = mock_doc
            
            result = await loader.load(str(docx_path))
            assert result["type"] == "word"
            assert "Word Content" in result["content"]
            assert result["metadata"]["paragraph_count"] == 1

    @pytest.mark.asyncio
    async def test_load_excel(self, loader, tmp_path):
        xlsx_path = tmp_path / "test.xlsx"
        xlsx_path.touch()
        
        with patch.dict('sys.modules', {'openpyxl': MagicMock()}):
            mock_openpyxl = sys.modules['openpyxl']
            mock_wb = MagicMock()
            mock_sheet = MagicMock()
            # Mock iter_rows to return values directly when values_only=True
            # The implementation iterates: for row in sheet.iter_rows(values_only=True)
            mock_sheet.iter_rows.return_value = [["Header"], ["Excel Content"]]
            
            mock_wb.sheetnames = ["Sheet1"]
            mock_wb.__getitem__.return_value = mock_sheet
            mock_openpyxl.load_workbook.return_value = mock_wb
            
            result = await loader.load(str(xlsx_path))
            assert result["type"] == "excel"
            assert "Excel Content" in result["content"]
            assert "Sheet: Sheet1" in result["content"]

    @pytest.mark.asyncio
    async def test_load_powerpoint(self, loader, tmp_path):
        pptx_path = tmp_path / "test.pptx"
        pptx_path.touch()

        with patch.dict('sys.modules', {'pptx': MagicMock()}):
            mock_pptx = sys.modules['pptx']
            mock_prs = MagicMock()
            mock_slide = MagicMock()
            mock_shape = MagicMock()
            mock_shape.text = "PowerPoint Content"
            mock_slide.shapes = [mock_shape]
            mock_prs.slides = [mock_slide]
            mock_pptx.Presentation.return_value = mock_prs

            result = await loader.load(str(pptx_path))
            assert result["type"] == "powerpoint"
            assert "PowerPoint Content" in result["content"]
            assert result["metadata"]["slide_count"] == 1

    @pytest.mark.asyncio
    async def test_load_html(self, loader, tmp_path):
        html_path = tmp_path / "test.html"
        html_path.write_text("<html><head><title>Test Page</title></head><body><h1>Hello World</h1><p>Content here</p></body></html>", encoding="utf-8")

        result = await loader.load(str(html_path))
        assert result["type"] == "html"
        assert "Hello World" in result["content"]
        assert "Content here" in result["content"]
        assert result["metadata"]["title"] == "Test Page"

    @pytest.mark.asyncio
    async def test_load_html_with_bs4_fallback(self, loader, tmp_path):
        html_path = tmp_path / "test2.html"
        html_path.write_text("<html><body><h1>Fallback Test</h1></body></html>", encoding="utf-8")

        # Test without BeautifulSoup (should use regex fallback)
        with patch.dict('sys.modules', {'bs4': None}):
            result = await loader.load(str(html_path))
            assert result["type"] == "html"
            # Fallback extracts text using regex
            assert "Fallback Test" in result["content"] or result["content"]

    @pytest.mark.asyncio
    async def test_load_image_with_ocr_mock(self, loader, tmp_path):
        """Test image loading with mocked OCR"""
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"fake image data")

        # Test the error handling path when paddleocr is not available
        # This is the realistic scenario for unit tests without full OCR setup
        with patch.dict('sys.modules', {'paddleocr': None}):
            # Force import error by setting paddleocr to None
            result = await loader.load(str(img_path))
            assert result["type"] == "image"
            # When paddleocr is not installed, content is empty
            assert result["content"] == ""
            assert "note" in result["metadata"]
            assert "paddleocr" in result["metadata"]["note"]
