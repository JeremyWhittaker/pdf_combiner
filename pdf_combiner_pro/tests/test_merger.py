"""Tests for PDF merger functionality."""

from pathlib import Path

import pytest
from PyPDF2 import PdfReader

from pdf_combiner.exceptions import ValidationError, MergeError
from pdf_combiner.merger import PDFMerger
from pdf_combiner.models import ProcessingOptions, ProcessingStatus


class TestPDFMerger:
    """Tests for PDFMerger class."""
    
    def test_initialization(self, config):
        """Test PDFMerger initialization."""
        merger = PDFMerger(config)
        assert merger.config == config
        assert merger.converter is not None
        assert merger.batch_converter is not None
    
    def test_merge_empty_directory(self, temp_dir, config):
        """Test merging with empty directory."""
        merger = PDFMerger(config)
        output_path = temp_dir / "output.pdf"
        
        with pytest.raises(ValidationError) as exc_info:
            merger.merge_directory(temp_dir, output_path)
        
        assert "No supported documents found" in str(exc_info.value)
    
    def test_merge_single_pdf(self, temp_dir, sample_pdf, config):
        """Test merging a single PDF."""
        merger = PDFMerger(config)
        output_path = temp_dir / "output.pdf"
        
        result = merger.merge_directory(sample_pdf.parent, output_path)
        
        assert result.output_path == output_path
        assert output_path.exists()
        assert result.total_documents == 1
        assert result.processed_documents == 1
        assert result.failed_documents == 0
    
    def test_merge_multiple_documents(self, temp_dir, sample_pdf, sample_docx, config, mock_libreoffice):
        """Test merging multiple documents."""
        merger = PDFMerger(config)
        output_path = temp_dir / "output.pdf"
        
        # Put both files in same directory
        target_dir = temp_dir / "docs"
        target_dir.mkdir()
        
        import shutil
        shutil.copy(sample_pdf, target_dir / sample_pdf.name)
        shutil.copy(sample_docx, target_dir / sample_docx.name)
        
        result = merger.merge_directory(target_dir, output_path)
        
        assert result.output_path == output_path
        assert output_path.exists()
        assert result.total_documents == 2
        assert result.processed_documents == 2
        assert result.failed_documents == 0
    
    def test_merge_with_metadata(self, temp_dir, sample_pdf, config):
        """Test that metadata is added to merged PDF."""
        config.output.add_metadata = True
        merger = PDFMerger(config)
        output_path = temp_dir / "output.pdf"
        
        result = merger.merge_directory(sample_pdf.parent, output_path)
        
        # Check metadata
        reader = PdfReader(str(output_path))
        metadata = reader.metadata
        
        assert metadata is not None
        assert "/Producer" in metadata
        assert metadata["/Producer"] == "PDF Combiner Pro"
        assert "/Subject" in metadata
        assert "Combined from:" in str(metadata["/Subject"])
    
    def test_check_directory(self, temp_dir, sample_pdf, config):
        """Test checking directory without merging."""
        merger = PDFMerger(config)
        
        documents = merger.check_directory(sample_pdf.parent)
        
        assert len(documents) == 1
        assert documents[0].name == sample_pdf.name
        assert documents[0].page_count is not None
    
    def test_verify_merged_pdf(self, temp_dir, sample_pdf, config):
        """Test PDF verification."""
        merger = PDFMerger(config)
        output_path = temp_dir / "output.pdf"
        
        # First merge
        merger.merge_directory(sample_pdf.parent, output_path)
        
        # Then verify
        result = merger.verify_merged_pdf(output_path, sample_pdf.parent)
        
        assert result.pdf_path == output_path
        assert result.is_valid
        assert len(result.missing_files) == 0
        assert result.page_count > 0


class TestProcessingOptions:
    """Tests for processing options."""
    
    def test_default_options(self):
        """Test default processing options."""
        options = ProcessingOptions()
        
        assert options.enable_ocr is True
        assert options.ocr_language == "eng"
        assert options.compression is True
        assert options.add_metadata is True
    
    def test_custom_options(self, temp_dir):
        """Test custom processing options."""
        options = ProcessingOptions(
            enable_ocr=False,
            ocr_language="deu",
            compression=False,
            add_metadata=False,
            temp_dir=temp_dir
        )
        
        assert options.enable_ocr is False
        assert options.ocr_language == "deu"
        assert options.compression is False
        assert options.add_metadata is False
        assert options.temp_dir == temp_dir


class TestErrorHandling:
    """Tests for error handling in merger."""
    
    def test_fail_fast_mode(self, temp_dir, config):
        """Test fail-fast mode stops on first error."""
        config.processing.fail_fast = True
        merger = PDFMerger(config)
        
        # Create an invalid PDF
        invalid_pdf = temp_dir / "invalid.pdf"
        invalid_pdf.write_text("This is not a valid PDF")
        
        output_path = temp_dir / "output.pdf"
        
        with pytest.raises(Exception):
            merger.merge_directory(temp_dir, output_path)
    
    def test_continue_on_error(self, temp_dir, sample_pdf, config):
        """Test continuing after errors when fail-fast is disabled."""
        config.processing.fail_fast = False
        merger = PDFMerger(config)
        
        # Create a valid and invalid PDF
        valid_dir = temp_dir / "docs"
        valid_dir.mkdir()
        
        import shutil
        shutil.copy(sample_pdf, valid_dir / "valid.pdf")
        
        invalid_pdf = valid_dir / "invalid.pdf"
        invalid_pdf.write_text("This is not a valid PDF")
        
        output_path = temp_dir / "output.pdf"
        
        result = merger.merge_directory(valid_dir, output_path)
        
        assert output_path.exists()
        assert result.processed_documents == 1
        assert result.failed_documents == 0  # Invalid PDF is skipped in iteration
        assert result.total_documents >= 1