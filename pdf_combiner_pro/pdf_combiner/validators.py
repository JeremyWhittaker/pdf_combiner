"""Input validation functions for PDF Combiner."""

import logging
from pathlib import Path
from typing import List, Optional

from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

from pdf_combiner.exceptions import ValidationError
from pdf_combiner.models import DocumentInfo, DocumentType
from pdf_combiner.utils import SUPPORTED_EXTENSIONS, get_document_type


logger = logging.getLogger(__name__)


def validate_directory(directory: Path) -> None:
    """Validate that a directory exists and is accessible.
    
    Args:
        directory: Directory path to validate
        
    Raises:
        ValidationError: If directory is invalid
    """
    if not directory.exists():
        raise ValidationError(
            f"Directory does not exist: {directory}",
            field="directory",
            value=str(directory)
        )
    
    if not directory.is_dir():
        raise ValidationError(
            f"Path is not a directory: {directory}",
            field="directory",
            value=str(directory)
        )
    
    # Check read permissions
    try:
        list(directory.iterdir())
    except PermissionError:
        raise ValidationError(
            f"No read permission for directory: {directory}",
            field="directory",
            value=str(directory)
        )


def validate_output_path(path: Path, overwrite: bool = False) -> None:
    """Validate output path for writing.
    
    Args:
        path: Output file path
        overwrite: Whether to allow overwriting existing files
        
    Raises:
        ValidationError: If output path is invalid
    """
    # Check if parent directory exists
    if not path.parent.exists():
        raise ValidationError(
            f"Output directory does not exist: {path.parent}",
            field="output_path",
            value=str(path)
        )
    
    # Check if file already exists
    if path.exists() and not overwrite:
        raise ValidationError(
            f"Output file already exists: {path}. Use --overwrite to replace.",
            field="output_path",
            value=str(path)
        )
    
    # Check write permissions
    try:
        path.parent.resolve()
        # Try to create a temporary file to check write permissions
        temp_file = path.parent / f".{path.stem}_temp"
        temp_file.touch()
        temp_file.unlink()
    except (PermissionError, OSError):
        raise ValidationError(
            f"No write permission for directory: {path.parent}",
            field="output_path",
            value=str(path)
        )
    
    # Validate extension
    if path.suffix.lower() != ".pdf":
        raise ValidationError(
            f"Output file must have .pdf extension, got: {path.suffix}",
            field="output_path",
            value=str(path)
        )


def validate_document(path: Path) -> DocumentInfo:
    """Validate a single document file.
    
    Args:
        path: Path to document
        
    Returns:
        DocumentInfo with validation results
        
    Raises:
        ValidationError: If document is invalid
    """
    # Check if file exists
    if not path.exists():
        raise ValidationError(
            f"File does not exist: {path}",
            field="document",
            value=str(path)
        )
    
    # Check if it's a file
    if not path.is_file():
        raise ValidationError(
            f"Path is not a file: {path}",
            field="document",
            value=str(path)
        )
    
    # Check extension
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type: {path.suffix}. Supported types: {', '.join(SUPPORTED_EXTENSIONS)}",
            field="document",
            value=str(path)
        )
    
    # Get document info
    from pdf_combiner.utils import get_file_info
    doc_info = get_file_info(path)
    
    # Additional validation for PDFs
    if doc_info.type == DocumentType.PDF:
        try:
            reader = PdfReader(str(path))
            doc_info.page_count = len(reader.pages)
            
            # Check if PDF has text
            doc_info.has_text = False
            for page in reader.pages[:3]:  # Check first 3 pages
                if page.extract_text().strip():
                    doc_info.has_text = True
                    break
                    
        except PdfReadError as e:
            logger.warning(f"PDF validation failed for {path}: {e}")
            doc_info.error_message = str(e)
    
    return doc_info


def validate_documents(paths: List[Path]) -> List[DocumentInfo]:
    """Validate multiple documents.
    
    Args:
        paths: List of document paths
        
    Returns:
        List of DocumentInfo objects
        
    Raises:
        ValidationError: If no valid documents found
    """
    if not paths:
        raise ValidationError("No documents provided")
    
    valid_docs = []
    errors = []
    
    for path in paths:
        try:
            doc_info = validate_document(path)
            valid_docs.append(doc_info)
        except ValidationError as e:
            errors.append(f"{path.name}: {e.message}")
            logger.error(f"Validation failed for {path}: {e}")
    
    if not valid_docs:
        raise ValidationError(
            f"No valid documents found. Errors: {'; '.join(errors)}"
        )
    
    if errors:
        logger.warning(f"Some documents failed validation: {'; '.join(errors)}")
    
    return valid_docs


def validate_ocr_language(language: str) -> None:
    """Validate OCR language code.
    
    Args:
        language: OCR language code (e.g., 'eng', 'deu', 'fra')
        
    Raises:
        ValidationError: If language code is invalid
    """
    # Common language codes
    common_languages = {
        "eng", "deu", "fra", "spa", "ita", "por", "rus", "jpn", "chi_sim", "chi_tra",
        "ara", "hin", "kor", "nld", "pol", "tur", "vie", "ind", "tha", "heb"
    }
    
    # Check format (should be 3 letters or special format like chi_sim)
    parts = language.split('+')  # Support multiple languages like "eng+deu"
    
    for lang in parts:
        if len(lang) < 3 or (lang not in common_languages and '_' not in lang):
            logger.warning(f"Unusual OCR language code: {lang}. Common codes: {', '.join(sorted(common_languages))}")


def validate_config_file(path: Path) -> None:
    """Validate configuration file.
    
    Args:
        path: Path to configuration file
        
    Raises:
        ValidationError: If config file is invalid
    """
    if not path.exists():
        raise ValidationError(
            f"Configuration file does not exist: {path}",
            field="config",
            value=str(path)
        )
    
    if not path.is_file():
        raise ValidationError(
            f"Configuration path is not a file: {path}",
            field="config",
            value=str(path)
        )
    
    # Check extension
    if path.suffix.lower() not in [".yaml", ".yml"]:
        raise ValidationError(
            f"Configuration file must be YAML (.yaml or .yml), got: {path.suffix}",
            field="config",
            value=str(path)
        )
    
    # Try to read the file
    try:
        import yaml
        with open(path, 'r') as f:
            yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValidationError(
            f"Invalid YAML in configuration file: {e}",
            field="config",
            value=str(path)
        )
    except Exception as e:
        raise ValidationError(
            f"Cannot read configuration file: {e}",
            field="config",
            value=str(path)
        )