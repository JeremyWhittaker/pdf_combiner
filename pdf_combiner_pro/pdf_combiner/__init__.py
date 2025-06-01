"""
PDF Combiner Pro - A professional PDF combiner with OCR support.

This package provides functionality to combine PDFs, DOCs, and DOCX files
with automatic OCR support for image-based PDFs.
"""

from pdf_combiner.__version__ import (
    __author__,
    __email__,
    __license__,
    __title__,
    __version__,
)
from pdf_combiner.exceptions import (
    PDFCombinerError,
    ConversionError,
    OCRError,
    ValidationError,
)
from pdf_combiner.merger import PDFMerger
from pdf_combiner.models import ProcessingResult, DocumentInfo

__all__ = [
    "__title__",
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "PDFCombinerError",
    "ConversionError",
    "OCRError",
    "ValidationError",
    "PDFMerger",
    "ProcessingResult",
    "DocumentInfo",
]