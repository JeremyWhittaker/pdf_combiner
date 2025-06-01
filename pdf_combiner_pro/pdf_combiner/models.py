"""Data models for the PDF Combiner package."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator


class DocumentType(str, Enum):
    """Supported document types."""
    
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"


class ProcessingStatus(str, Enum):
    """Document processing status."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class OCRStatus(str, Enum):
    """OCR processing status."""
    
    NOT_NEEDED = "not_needed"
    REQUIRED = "required"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DocumentInfo(BaseModel):
    """Information about a document to be processed."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    path: Path
    name: str
    type: DocumentType
    size_bytes: int
    created_at: datetime
    modified_at: datetime
    status: ProcessingStatus = ProcessingStatus.PENDING
    ocr_status: Optional[OCRStatus] = None
    page_count: Optional[int] = None
    has_text: Optional[bool] = None
    error_message: Optional[str] = None
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        """Ensure path exists and is a file."""
        if not v.exists():
            raise ValueError(f"File does not exist: {v}")
        if not v.is_file():
            raise ValueError(f"Path is not a file: {v}")
        return v
    
    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.size_bytes / (1024 * 1024)
    
    @property
    def extension(self) -> str:
        """Get file extension without dot."""
        return self.path.suffix.lower().lstrip('.')


class ProcessingOptions(BaseModel):
    """Options for document processing."""
    
    enable_ocr: bool = Field(default=True, description="Enable OCR for image-only PDFs")
    ocr_language: str = Field(default="eng", description="OCR language code")
    ocr_dpi: int = Field(default=300, description="DPI for OCR processing")
    skip_text_pages: bool = Field(default=True, description="Skip OCR on pages with text")
    compression: bool = Field(default=True, description="Enable PDF compression")
    add_metadata: bool = Field(default=True, description="Add source file metadata to merged PDF")
    max_workers: int = Field(default=4, ge=1, description="Maximum parallel workers")
    temp_dir: Optional[Path] = Field(default=None, description="Custom temporary directory")
    

class ProcessingResult(BaseModel):
    """Result of processing documents."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    output_path: Path
    total_documents: int
    processed_documents: int
    failed_documents: int
    skipped_documents: int
    total_pages: int
    processing_time_seconds: float
    documents: List[DocumentInfo]
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_documents == 0:
            return 0.0
        return (self.processed_documents / self.total_documents) * 100
    
    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return self.failed_documents > 0 or len(self.errors) > 0
    
    def get_failed_files(self) -> List[str]:
        """Get list of failed file names."""
        return [
            doc.name for doc in self.documents 
            if doc.status == ProcessingStatus.FAILED
        ]


class VerificationResult(BaseModel):
    """Result of PDF verification."""
    
    pdf_path: Path
    source_dir: Path
    expected_files: List[str]
    found_files: List[str]
    missing_files: List[str]
    extra_files: List[str]
    page_count: int
    is_valid: bool
    
    @property
    def match_percentage(self) -> float:
        """Calculate percentage of expected files found."""
        if not self.expected_files:
            return 100.0
        found_count = len(set(self.expected_files) & set(self.found_files))
        return (found_count / len(self.expected_files)) * 100