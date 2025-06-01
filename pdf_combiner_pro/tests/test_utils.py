"""Tests for utility functions."""

from pathlib import Path

import pytest

from pdf_combiner.exceptions import DependencyError
from pdf_combiner.models import DocumentType
from pdf_combiner.utils import (
    get_document_type,
    iter_documents,
    count_documents,
    format_file_size,
    sanitize_filename,
    get_file_info,
)


class TestGetDocumentType:
    """Tests for get_document_type function."""
    
    def test_pdf_extension(self):
        """Test PDF file detection."""
        assert get_document_type(Path("test.pdf")) == DocumentType.PDF
        assert get_document_type(Path("test.PDF")) == DocumentType.PDF
    
    def test_doc_extension(self):
        """Test DOC file detection."""
        assert get_document_type(Path("test.doc")) == DocumentType.DOC
        assert get_document_type(Path("test.DOC")) == DocumentType.DOC
    
    def test_docx_extension(self):
        """Test DOCX file detection."""
        assert get_document_type(Path("test.docx")) == DocumentType.DOCX
        assert get_document_type(Path("test.DOCX")) == DocumentType.DOCX
    
    def test_unsupported_extension(self):
        """Test unsupported file types."""
        assert get_document_type(Path("test.txt")) is None
        assert get_document_type(Path("test.jpg")) is None
        assert get_document_type(Path("test")) is None


class TestIterDocuments:
    """Tests for iter_documents function."""
    
    def test_empty_directory(self, temp_dir):
        """Test iteration over empty directory."""
        docs = list(iter_documents(temp_dir))
        assert len(docs) == 0
    
    def test_non_recursive(self, temp_dir):
        """Test non-recursive document iteration."""
        # Create files in root
        (temp_dir / "doc1.pdf").touch()
        (temp_dir / "doc2.docx").touch()
        (temp_dir / "ignore.txt").touch()
        
        # Create files in subdirectory
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "doc3.pdf").touch()
        
        docs = list(iter_documents(temp_dir, recursive=False))
        assert len(docs) == 2
        assert all(d.parent == temp_dir for d in docs)
    
    def test_recursive(self, temp_dir):
        """Test recursive document iteration."""
        # Create files in root
        (temp_dir / "doc1.pdf").touch()
        
        # Create files in subdirectory
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "doc2.pdf").touch()
        (subdir / "doc3.docx").touch()
        
        docs = list(iter_documents(temp_dir, recursive=True))
        assert len(docs) == 3
    
    def test_sorted_order(self, temp_dir):
        """Test that documents are returned in sorted order."""
        files = ["zebra.pdf", "alpha.docx", "beta.doc"]
        for f in files:
            (temp_dir / f).touch()
        
        docs = list(iter_documents(temp_dir))
        names = [d.name for d in docs]
        assert names == ["alpha.docx", "beta.doc", "zebra.pdf"]
    
    def test_nonexistent_directory(self):
        """Test error handling for non-existent directory."""
        with pytest.raises(NotADirectoryError):
            list(iter_documents(Path("/nonexistent")))
    
    def test_file_instead_of_directory(self, temp_dir):
        """Test error handling when path is a file."""
        file_path = temp_dir / "file.txt"
        file_path.touch()
        
        with pytest.raises(NotADirectoryError):
            list(iter_documents(file_path))


class TestCountDocuments:
    """Tests for count_documents function."""
    
    def test_count_matches_iteration(self, temp_dir):
        """Test that count matches iteration results."""
        for i in range(5):
            (temp_dir / f"doc{i}.pdf").touch()
        
        count = count_documents(temp_dir)
        docs = list(iter_documents(temp_dir))
        assert count == len(docs) == 5


class TestFormatFileSize:
    """Tests for format_file_size function."""
    
    def test_bytes(self):
        """Test formatting bytes."""
        assert format_file_size(0) == "0.0 B"
        assert format_file_size(100) == "100.0 B"
        assert format_file_size(1023) == "1023.0 B"
    
    def test_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
        assert format_file_size(1024 * 100) == "100.0 KB"
    
    def test_megabytes(self):
        """Test formatting megabytes."""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 5.5) == "5.5 MB"
    
    def test_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_file_size(1024 ** 3) == "1.0 GB"
        assert format_file_size(1024 ** 3 * 2.5) == "2.5 GB"


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""
    
    def test_valid_filename(self):
        """Test that valid filenames are unchanged."""
        assert sanitize_filename("document.pdf") == "document.pdf"
        assert sanitize_filename("my-file_123.docx") == "my-file_123.docx"
    
    def test_invalid_characters(self):
        """Test removal of invalid characters."""
        assert sanitize_filename('doc<>:"|?*.pdf') == "doc_______.pdf"
        assert sanitize_filename("file:name.pdf") == "file_name.pdf"
    
    def test_leading_trailing_spaces_dots(self):
        """Test removal of leading/trailing spaces and dots."""
        assert sanitize_filename("  document.pdf  ") == "document.pdf"
        assert sanitize_filename("...file...") == "file"
        assert sanitize_filename(".hidden.pdf.") == "hidden.pdf"
    
    def test_empty_filename(self):
        """Test handling of empty filename."""
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("   ") == "unnamed"
        assert sanitize_filename("...") == "unnamed"


class TestGetFileInfo:
    """Tests for get_file_info function."""
    
    def test_pdf_file_info(self, sample_pdf):
        """Test getting info for PDF file."""
        info = get_file_info(sample_pdf)
        
        assert info.path == sample_pdf
        assert info.name == "sample.pdf"
        assert info.type == DocumentType.PDF
        assert info.size_bytes > 0
        assert info.extension == "pdf"
    
    def test_docx_file_info(self, sample_docx):
        """Test getting info for DOCX file."""
        info = get_file_info(sample_docx)
        
        assert info.path == sample_docx
        assert info.name == "sample.docx"
        assert info.type == DocumentType.DOCX
        assert info.size_bytes > 0
        assert info.extension == "docx"
    
    def test_unsupported_file_type(self, temp_dir):
        """Test error for unsupported file type."""
        txt_file = temp_dir / "test.txt"
        txt_file.touch()
        
        with pytest.raises(ValueError, match="Unsupported file type"):
            get_file_info(txt_file)