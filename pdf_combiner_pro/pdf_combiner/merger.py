"""Core PDF merging functionality."""

import logging
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from PyPDF2 import PdfReader, PdfMerger as PyPDF2Merger
from PyPDF2.errors import PdfReadError

from pdf_combiner.config import Config, ProcessingConfig
from pdf_combiner.converters import BatchConverter, DocumentConverter
from pdf_combiner.exceptions import MergeError, ValidationError
from pdf_combiner.models import (
    DocumentInfo,
    ProcessingOptions,
    ProcessingResult,
    ProcessingStatus,
    VerificationResult,
)
from pdf_combiner.ocr import BatchOCRProcessor, OCRProcessor
from pdf_combiner.utils import get_file_info, iter_documents
from pdf_combiner.validators import validate_directory, validate_output_path, validate_documents


logger = logging.getLogger(__name__)


class PDFMerger:
    """Main class for merging PDFs with conversion and OCR support."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize PDF merger.
        
        Args:
            config: Configuration instance (uses defaults if not provided)
        """
        self.config = config or Config()
        self._temp_dir: Optional[Path] = None
        
        # Initialize processors
        self.converter = DocumentConverter(temp_dir=self.config.get_temp_dir())
        self.batch_converter = BatchConverter(
            self.converter,
            max_workers=self.config.processing.max_workers
        )
        
        if self.config.ocr.enabled:
            self.ocr_processor = OCRProcessor(
                language=self.config.ocr.language,
                dpi=self.config.ocr.dpi,
                skip_text_pages=self.config.ocr.skip_text_pages,
                timeout=self.config.ocr.timeout,
                extra_args=self.config.ocr.extra_args
            )
            self.batch_ocr = BatchOCRProcessor(
                self.ocr_processor,
                max_workers=min(2, self.config.processing.max_workers)  # OCR is resource-intensive
            )
        else:
            self.ocr_processor = None
            self.batch_ocr = None
    
    def merge_directory(
        self,
        directory: Path,
        output_path: Path,
        recursive: bool = False,
        options: Optional[ProcessingOptions] = None
    ) -> ProcessingResult:
        """Merge all documents in a directory.
        
        Args:
            directory: Directory containing documents
            output_path: Output PDF path
            recursive: Whether to scan subdirectories
            options: Processing options (uses config defaults if not provided)
            
        Returns:
            ProcessingResult with details
            
        Raises:
            ValidationError: If inputs are invalid
            MergeError: If merging fails
        """
        start_time = time.time()
        
        # Validate inputs
        validate_directory(directory)
        validate_output_path(output_path, overwrite=self.config.output.overwrite)
        
        # Get documents
        document_paths = list(iter_documents(directory, recursive))
        if not document_paths:
            raise ValidationError(f"No supported documents found in {directory}")
        
        logger.info(f"Found {len(document_paths)} documents to process")
        
        # Create document info objects
        documents = []
        for path in document_paths:
            try:
                doc_info = get_file_info(path)
                documents.append(doc_info)
            except Exception as e:
                logger.error(f"Failed to get info for {path}: {e}")
                if self.config.processing.fail_fast:
                    raise
        
        # Process documents
        result = self.merge_documents(documents, output_path, options)
        result.processing_time_seconds = time.time() - start_time
        
        return result
    
    def merge_documents(
        self,
        documents: List[DocumentInfo],
        output_path: Path,
        options: Optional[ProcessingOptions] = None
    ) -> ProcessingResult:
        """Merge multiple documents into a single PDF.
        
        Args:
            documents: List of documents to merge
            output_path: Output PDF path
            options: Processing options
            
        Returns:
            ProcessingResult with details
        """
        if not documents:
            raise ValidationError("No documents provided")
        
        options = options or ProcessingOptions(
            enable_ocr=self.config.ocr.enabled,
            ocr_language=self.config.ocr.language,
            compression=self.config.output.compression,
            add_metadata=self.config.output.add_metadata,
            max_workers=self.config.processing.max_workers,
            temp_dir=self.config.get_temp_dir()
        )
        
        # Initialize result
        result = ProcessingResult(
            output_path=output_path,
            total_documents=len(documents),
            processed_documents=0,
            failed_documents=0,
            skipped_documents=0,
            total_pages=0,
            processing_time_seconds=0,
            documents=documents
        )
        
        # Process in temp directory
        with tempfile.TemporaryDirectory(dir=options.temp_dir) as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                # Step 1: Convert non-PDF documents
                logger.info("Converting documents to PDF...")
                pdf_paths = self._convert_documents(documents, temp_path, result)
                
                # Step 2: OCR processing if enabled
                if options.enable_ocr and self.batch_ocr:
                    logger.info("Processing PDFs with OCR...")
                    pdf_paths = self._ocr_documents(documents, pdf_paths, temp_path, result)
                
                # Step 3: Merge PDFs
                logger.info("Merging PDFs...")
                self._merge_pdfs(pdf_paths, output_path, documents, options, result)
                
            except Exception as e:
                logger.error(f"Merge failed: {e}")
                result.errors.append({
                    "type": "merge_error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                raise MergeError(f"Failed to merge documents: {e}", result.get_failed_files())
        
        return result
    
    def _convert_documents(
        self,
        documents: List[DocumentInfo],
        temp_dir: Path,
        result: ProcessingResult
    ) -> Dict[str, Path]:
        """Convert documents to PDF format.
        
        Returns:
            Dictionary mapping original paths to PDF paths
        """
        try:
            pdf_paths = self.batch_converter.convert_documents(documents, temp_dir)
            
            # Update document statuses
            for doc in documents:
                if str(doc.path) in pdf_paths:
                    doc.status = ProcessingStatus.PROCESSING
                else:
                    doc.status = ProcessingStatus.FAILED
                    result.failed_documents += 1
            
            return pdf_paths
            
        except Exception as e:
            logger.error(f"Document conversion failed: {e}")
            for doc in documents:
                if doc.status == ProcessingStatus.PENDING:
                    doc.status = ProcessingStatus.FAILED
                    doc.error_message = str(e)
            raise
    
    def _ocr_documents(
        self,
        documents: List[DocumentInfo],
        pdf_paths: Dict[str, Path],
        temp_dir: Path,
        result: ProcessingResult
    ) -> Dict[str, Path]:
        """Process PDFs with OCR.
        
        Returns:
            Updated dictionary mapping original paths to processed PDF paths
        """
        try:
            # Get PDF documents
            pdf_docs = []
            for doc in documents:
                if str(doc.path) in pdf_paths:
                    # Create a temporary DocumentInfo for the converted PDF
                    pdf_path = pdf_paths[str(doc.path)]
                    temp_doc = DocumentInfo(
                        path=pdf_path,
                        name=pdf_path.name,
                        type=doc.type,
                        size_bytes=pdf_path.stat().st_size,
                        created_at=datetime.now(),
                        modified_at=datetime.now()
                    )
                    pdf_docs.append(temp_doc)
            
            # Process with OCR
            ocr_results = self.batch_ocr.process_documents(pdf_docs, temp_dir)
            
            # Update paths with OCR results
            updated_paths = {}
            for orig_path, pdf_path in pdf_paths.items():
                if str(pdf_path) in ocr_results:
                    updated_paths[orig_path] = ocr_results[str(pdf_path)]
                else:
                    updated_paths[orig_path] = pdf_path
            
            return updated_paths
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            result.warnings.append(f"OCR processing failed: {e}")
            return pdf_paths  # Return original paths if OCR fails
    
    def _merge_pdfs(
        self,
        pdf_paths: Dict[str, Path],
        output_path: Path,
        documents: List[DocumentInfo],
        options: ProcessingOptions,
        result: ProcessingResult
    ) -> None:
        """Merge PDFs into final output file."""
        merger = PyPDF2Merger()
        processed_files = []
        
        try:
            # Add PDFs to merger in order
            for doc in documents:
                orig_path = str(doc.path)
                if orig_path not in pdf_paths:
                    logger.warning(f"Skipping {doc.name} - no PDF available")
                    doc.status = ProcessingStatus.SKIPPED
                    result.skipped_documents += 1
                    continue
                
                pdf_path = pdf_paths[orig_path]
                
                try:
                    # Add to merger
                    merger.append(str(pdf_path))
                    processed_files.append(doc.name)
                    
                    # Update page count
                    reader = PdfReader(str(pdf_path))
                    page_count = len(reader.pages)
                    doc.page_count = page_count
                    result.total_pages += page_count
                    
                    doc.status = ProcessingStatus.COMPLETED
                    result.processed_documents += 1
                    
                    logger.debug(f"Added {doc.name} ({page_count} pages)")
                    
                except PdfReadError as e:
                    logger.error(f"Failed to add {doc.name}: {e}")
                    doc.status = ProcessingStatus.FAILED
                    doc.error_message = str(e)
                    result.failed_documents += 1
                    
                    if self.config.processing.fail_fast:
                        raise
            
            # Add metadata if requested
            if options.add_metadata and processed_files:
                metadata = {
                    '/Title': f'Combined PDF - {len(processed_files)} documents',
                    '/Subject': f'Combined from: {", ".join(processed_files)}',
                    '/Producer': 'PDF Combiner Pro',
                    '/Creator': 'PDF Combiner Pro',
                    '/CreationDate': datetime.now().isoformat(),
                }
                merger.add_metadata(metadata)
            
            # Write output file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            merger.write(str(output_path))
            merger.close()
            
            logger.info(
                f"Successfully created {output_path} "
                f"({result.total_pages} pages from {result.processed_documents} documents)"
            )
            
        except Exception as e:
            logger.error(f"Failed to create merged PDF: {e}")
            raise
        finally:
            merger.close()
    
    def check_directory(self, directory: Path, recursive: bool = False) -> List[DocumentInfo]:
        """Check documents in a directory without processing.
        
        Args:
            directory: Directory to check
            recursive: Whether to scan subdirectories
            
        Returns:
            List of DocumentInfo objects with validation status
        """
        validate_directory(directory)
        
        document_paths = list(iter_documents(directory, recursive))
        documents = []
        
        for path in document_paths:
            try:
                doc_info = get_file_info(path)
                
                # Check if it's a valid PDF
                if doc_info.type.value == "pdf":
                    try:
                        reader = PdfReader(str(path))
                        doc_info.page_count = len(reader.pages)
                        
                        # Check for text
                        doc_info.has_text = False
                        for page in reader.pages[:3]:
                            if page.extract_text().strip():
                                doc_info.has_text = True
                                break
                        
                        # Determine OCR status
                        if self.ocr_processor:
                            doc_info.ocr_status = "required" if not doc_info.has_text else "not_needed"
                        
                    except PdfReadError as e:
                        doc_info.error_message = f"Corrupted PDF: {e}"
                
                documents.append(doc_info)
                
            except Exception as e:
                logger.error(f"Failed to check {path}: {e}")
        
        return documents
    
    def verify_merged_pdf(self, pdf_path: Path, source_dir: Path) -> VerificationResult:
        """Verify that a merged PDF contains all expected files.
        
        Args:
            pdf_path: Path to merged PDF
            source_dir: Source directory to compare against
            
        Returns:
            VerificationResult with details
        """
        # Get expected files
        expected_files = [p.name for p in iter_documents(source_dir)]
        
        # Try to extract source files from metadata
        found_files = []
        try:
            reader = PdfReader(str(pdf_path))
            metadata = reader.metadata
            
            if metadata and '/Subject' in metadata:
                subject = str(metadata['/Subject'])
                if 'Combined from:' in subject:
                    files_str = subject.replace('Combined from:', '').strip()
                    found_files = [f.strip() for f in files_str.split(',')]
            
            page_count = len(reader.pages)
            
        except Exception as e:
            logger.error(f"Failed to read PDF metadata: {e}")
            page_count = 0
        
        # Calculate differences
        expected_set = set(expected_files)
        found_set = set(found_files)
        
        missing_files = sorted(expected_set - found_set)
        extra_files = sorted(found_set - expected_set)
        
        return VerificationResult(
            pdf_path=pdf_path,
            source_dir=source_dir,
            expected_files=expected_files,
            found_files=found_files,
            missing_files=missing_files,
            extra_files=extra_files,
            page_count=page_count,
            is_valid=len(missing_files) == 0 and len(extra_files) == 0
        )