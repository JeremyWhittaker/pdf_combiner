"""Custom exceptions for the PDF Combiner package."""

from typing import Optional, List


class PDFCombinerError(Exception):
    """Base exception for all PDF Combiner errors."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        """Initialize the exception with a message and optional details.
        
        Args:
            message: The error message
            details: Optional dictionary with additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(PDFCombinerError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[str] = None) -> None:
        """Initialize validation error.
        
        Args:
            message: The error message
            field: The field that failed validation
            value: The invalid value
        """
        details = {}
        if field:
            details["field"] = field
        if value:
            details["value"] = value
        super().__init__(message, details)


class ConversionError(PDFCombinerError):
    """Raised when document conversion fails."""

    def __init__(self, message: str, source_file: Optional[str] = None, 
                 target_format: Optional[str] = None) -> None:
        """Initialize conversion error.
        
        Args:
            message: The error message
            source_file: The file that failed to convert
            target_format: The target format for conversion
        """
        details = {}
        if source_file:
            details["source_file"] = source_file
        if target_format:
            details["target_format"] = target_format
        super().__init__(message, details)


class OCRError(PDFCombinerError):
    """Raised when OCR processing fails."""

    def __init__(self, message: str, pdf_file: Optional[str] = None, 
                 ocr_engine: str = "ocrmypdf") -> None:
        """Initialize OCR error.
        
        Args:
            message: The error message
            pdf_file: The PDF file that failed OCR
            ocr_engine: The OCR engine being used
        """
        details = {"ocr_engine": ocr_engine}
        if pdf_file:
            details["pdf_file"] = pdf_file
        super().__init__(message, details)


class FileReadError(PDFCombinerError):
    """Raised when a file cannot be read."""

    def __init__(self, message: str, file_path: str) -> None:
        """Initialize file read error.
        
        Args:
            message: The error message
            file_path: The file that couldn't be read
        """
        super().__init__(message, {"file_path": file_path})


class MergeError(PDFCombinerError):
    """Raised when PDF merging fails."""

    def __init__(self, message: str, failed_files: Optional[List[str]] = None) -> None:
        """Initialize merge error.
        
        Args:
            message: The error message
            failed_files: List of files that failed to merge
        """
        details = {}
        if failed_files:
            details["failed_files"] = failed_files
        super().__init__(message, details)


class DependencyError(PDFCombinerError):
    """Raised when a required system dependency is missing."""

    def __init__(self, dependency: str, install_command: Optional[str] = None) -> None:
        """Initialize dependency error.
        
        Args:
            dependency: The missing dependency
            install_command: Command to install the dependency
        """
        message = f"Required dependency '{dependency}' is not installed"
        details = {"dependency": dependency}
        if install_command:
            message += f". Install with: {install_command}"
            details["install_command"] = install_command
        super().__init__(message, details)