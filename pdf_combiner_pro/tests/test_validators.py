"""Tests for validation functions."""

from pathlib import Path

import pytest
from PyPDF2 import PdfWriter

from pdf_combiner.exceptions import ValidationError
from pdf_combiner.validators import (
    validate_directory,
    validate_output_path,
    validate_document,
    validate_documents,
    validate_ocr_language,
    validate_config_file,
)


class TestValidateDirectory:
    """Tests for validate_directory function."""
    
    def test_valid_directory(self, temp_dir):
        """Test validation of valid directory."""
        # Should not raise any exception
        validate_directory(temp_dir)
    
    def test_nonexistent_directory(self):
        """Test validation of non-existent directory."""
        with pytest.raises(ValidationError) as exc_info:
            validate_directory(Path("/nonexistent/directory"))
        
        assert "does not exist" in str(exc_info.value)
        assert exc_info.value.details["field"] == "directory"
    
    def test_file_instead_of_directory(self, temp_dir):
        """Test validation when path is a file."""
        file_path = temp_dir / "file.txt"
        file_path.touch()
        
        with pytest.raises(ValidationError) as exc_info:
            validate_directory(file_path)
        
        assert "not a directory" in str(exc_info.value)


class TestValidateOutputPath:
    """Tests for validate_output_path function."""
    
    def test_valid_output_path(self, temp_dir):
        """Test validation of valid output path."""
        output_path = temp_dir / "output.pdf"
        validate_output_path(output_path)
    
    def test_existing_file_no_overwrite(self, temp_dir):
        """Test validation when file exists and overwrite is False."""
        output_path = temp_dir / "existing.pdf"
        output_path.touch()
        
        with pytest.raises(ValidationError) as exc_info:
            validate_output_path(output_path, overwrite=False)
        
        assert "already exists" in str(exc_info.value)
    
    def test_existing_file_with_overwrite(self, temp_dir):
        """Test validation when file exists and overwrite is True."""
        output_path = temp_dir / "existing.pdf"
        output_path.touch()
        
        # Should not raise exception
        validate_output_path(output_path, overwrite=True)
    
    def test_nonexistent_parent_directory(self):
        """Test validation when parent directory doesn't exist."""
        output_path = Path("/nonexistent/directory/output.pdf")
        
        with pytest.raises(ValidationError) as exc_info:
            validate_output_path(output_path)
        
        assert "does not exist" in str(exc_info.value)
    
    def test_invalid_extension(self, temp_dir):
        """Test validation with non-PDF extension."""
        output_path = temp_dir / "output.txt"
        
        with pytest.raises(ValidationError) as exc_info:
            validate_output_path(output_path)
        
        assert "must have .pdf extension" in str(exc_info.value)


class TestValidateDocument:
    """Tests for validate_document function."""
    
    def test_valid_pdf(self, sample_pdf):
        """Test validation of valid PDF."""
        doc_info = validate_document(sample_pdf)
        
        assert doc_info.path == sample_pdf
        assert doc_info.page_count is not None
        assert doc_info.has_text is not None
    
    def test_valid_docx(self, sample_docx):
        """Test validation of valid DOCX."""
        doc_info = validate_document(sample_docx)
        
        assert doc_info.path == sample_docx
        assert doc_info.type.value == "docx"
    
    def test_nonexistent_file(self):
        """Test validation of non-existent file."""
        with pytest.raises(ValidationError) as exc_info:
            validate_document(Path("/nonexistent/file.pdf"))
        
        assert "does not exist" in str(exc_info.value)
    
    def test_unsupported_file_type(self, temp_dir):
        """Test validation of unsupported file type."""
        txt_file = temp_dir / "test.txt"
        txt_file.touch()
        
        with pytest.raises(ValidationError) as exc_info:
            validate_document(txt_file)
        
        assert "Unsupported file type" in str(exc_info.value)
    
    def test_corrupted_pdf(self, temp_dir):
        """Test validation of corrupted PDF."""
        corrupted_pdf = temp_dir / "corrupted.pdf"
        corrupted_pdf.write_text("This is not a valid PDF")
        
        doc_info = validate_document(corrupted_pdf)
        assert doc_info.error_message is not None
        assert "Corrupted PDF" in doc_info.error_message


class TestValidateDocuments:
    """Tests for validate_documents function."""
    
    def test_valid_documents(self, sample_pdf, sample_docx):
        """Test validation of multiple valid documents."""
        docs = validate_documents([sample_pdf, sample_docx])
        assert len(docs) == 2
    
    def test_empty_list(self):
        """Test validation with empty document list."""
        with pytest.raises(ValidationError) as exc_info:
            validate_documents([])
        
        assert "No documents provided" in str(exc_info.value)
    
    def test_mixed_valid_invalid(self, sample_pdf, temp_dir):
        """Test validation with mix of valid and invalid documents."""
        invalid_file = temp_dir / "invalid.txt"
        invalid_file.touch()
        
        docs = validate_documents([sample_pdf, invalid_file])
        assert len(docs) == 1  # Only valid document returned
    
    def test_all_invalid(self, temp_dir):
        """Test validation when all documents are invalid."""
        invalid_file = temp_dir / "invalid.txt"
        invalid_file.touch()
        
        with pytest.raises(ValidationError) as exc_info:
            validate_documents([invalid_file])
        
        assert "No valid documents found" in str(exc_info.value)


class TestValidateOCRLanguage:
    """Tests for validate_ocr_language function."""
    
    def test_common_languages(self):
        """Test validation of common language codes."""
        # Should not raise exceptions
        validate_ocr_language("eng")
        validate_ocr_language("deu")
        validate_ocr_language("fra")
        validate_ocr_language("spa")
    
    def test_multiple_languages(self):
        """Test validation of multiple language codes."""
        validate_ocr_language("eng+deu")
        validate_ocr_language("eng+fra+spa")
    
    def test_special_language_codes(self):
        """Test validation of special language codes."""
        validate_ocr_language("chi_sim")  # Simplified Chinese
        validate_ocr_language("chi_tra")  # Traditional Chinese
    
    def test_unusual_language_code(self, caplog):
        """Test warning for unusual language codes."""
        validate_ocr_language("xyz")
        assert "Unusual OCR language code" in caplog.text


class TestValidateConfigFile:
    """Tests for validate_config_file function."""
    
    def test_valid_yaml_config(self, temp_dir):
        """Test validation of valid YAML config."""
        config_file = temp_dir / "config.yaml"
        config_file.write_text("""
output:
  default_name: "test.pdf"
ocr:
  enabled: true
""")
        
        # Should not raise exception
        validate_config_file(config_file)
    
    def test_nonexistent_config(self):
        """Test validation of non-existent config."""
        with pytest.raises(ValidationError) as exc_info:
            validate_config_file(Path("/nonexistent/config.yaml"))
        
        assert "does not exist" in str(exc_info.value)
    
    def test_invalid_extension(self, temp_dir):
        """Test validation with invalid config extension."""
        config_file = temp_dir / "config.txt"
        config_file.touch()
        
        with pytest.raises(ValidationError) as exc_info:
            validate_config_file(config_file)
        
        assert "must be YAML" in str(exc_info.value)
    
    def test_invalid_yaml(self, temp_dir):
        """Test validation of invalid YAML content."""
        config_file = temp_dir / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")
        
        with pytest.raises(ValidationError) as exc_info:
            validate_config_file(config_file)
        
        assert "Invalid YAML" in str(exc_info.value)