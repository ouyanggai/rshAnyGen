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
