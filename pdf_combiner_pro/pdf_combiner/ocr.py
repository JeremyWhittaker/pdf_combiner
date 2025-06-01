"""OCR processing functionality."""

import logging
import tempfile
from pathlib import Path
from typing import Optional, List

from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

from pdf_combiner.exceptions import OCRError, DependencyError
from pdf_combiner.models import DocumentInfo, OCRStatus
from pdf_combiner.utils import run_command, ensure_dependencies


logger = logging.getLogger(__name__)


class OCRProcessor:
    """Handles OCR processing for PDF files."""
    
    def __init__(
        self,
        language: str = "eng",
        dpi: int = 300,
        skip_text_pages: bool = True,
        timeout: int = 300,
        extra_args: Optional[List[str]] = None
    ):
        """Initialize OCR processor.
        
        Args:
            language: OCR language code (e.g., 'eng', 'deu', 'fra')
            dpi: Resolution for OCR processing
            skip_text_pages: Skip pages that already have text
            timeout: OCR timeout in seconds
            extra_args: Additional arguments for ocrmypdf
        """
        self.language = language
        self.dpi = dpi
        self.skip_text_pages = skip_text_pages
        self.timeout = timeout
        self.extra_args = extra_args or []
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Check for required OCR dependencies."""
        try:
            ensure_dependencies(["ocrmypdf", "tesseract", "ghostscript"])
        except DependencyError as e:
            logger.warning(f"OCR dependency missing: {e.message}")
            raise
    
    def needs_ocr(self, pdf_path: Path, sample_pages: int = 3) -> bool:
        """Check if a PDF needs OCR processing.
        
        Args:
            pdf_path: Path to PDF file
            sample_pages: Number of pages to sample for text
            
        Returns:
            True if PDF needs OCR, False otherwise
        """
        try:
            reader = PdfReader(str(pdf_path))
            total_pages = len(reader.pages)
            pages_to_check = min(sample_pages, total_pages)
            
            # Check if any of the sampled pages have text
            for i in range(pages_to_check):
                page = reader.pages[i]
                text = page.extract_text()
                if text and text.strip():
                    logger.debug(f"Found text on page {i+1} of {pdf_path.name}")
                    return False
            
            logger.debug(f"No text found in first {pages_to_check} pages of {pdf_path.name}")
            return True
            
        except PdfReadError as e:
            logger.warning(f"Could not read PDF for OCR check: {pdf_path.name} - {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking PDF for OCR: {pdf_path.name} - {e}")
            return False
    
    def process_pdf(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """Process a PDF with OCR if needed.
        
        Args:
            input_path: Input PDF path
            output_path: Output PDF path (uses temp file if not specified)
            
        Returns:
            Path to processed PDF (may be original if no OCR needed)
            
        Raises:
            OCRError: If OCR processing fails
        """
        # Check if OCR is needed
        if not self.needs_ocr(input_path):
            logger.info(f"PDF already has text, skipping OCR: {input_path.name}")
            return input_path
        
        # Prepare output path
        if output_path is None:
            temp_dir = Path(tempfile.gettempdir())
            output_path = temp_dir / f"ocr_{input_path.name}"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Running OCR on: {input_path.name}")
        
        # Build OCR command
        cmd = [
            "ocrmypdf",
            "--language", self.language,
            "--dpi", str(self.dpi),
            "--quiet",
        ]
        
        if self.skip_text_pages:
            cmd.append("--skip-text")
        
        # Add extra arguments
        cmd.extend(self.extra_args)
        
        # Add input and output
        cmd.extend([str(input_path), str(output_path)])
        
        try:
            run_command(cmd, timeout=self.timeout)
            
            if not output_path.exists():
                raise OCRError(
                    "OCR produced no output file",
                    pdf_file=str(input_path)
                )
            
            logger.info(f"OCR completed successfully: {input_path.name}")
            return output_path
            
        except FileNotFoundError:
            raise DependencyError(
                "ocrmypdf",
                "pip install ocrmypdf"
            )
        except Exception as e:
            raise OCRError(
                f"OCR processing failed: {e}",
                pdf_file=str(input_path)
            )
    
    def get_ocr_info(self, pdf_path: Path) -> dict:
        """Get OCR-related information about a PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with OCR information
        """
        info = {
            "needs_ocr": False,
            "has_text": False,
            "page_count": 0,
            "text_pages": 0,
            "image_pages": 0,
        }
        
        try:
            reader = PdfReader(str(pdf_path))
            info["page_count"] = len(reader.pages)
            
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    info["text_pages"] += 1
                else:
                    info["image_pages"] += 1
            
            info["has_text"] = info["text_pages"] > 0
            info["needs_ocr"] = info["image_pages"] > 0 and self.skip_text_pages
            
        except Exception as e:
            logger.error(f"Error getting OCR info for {pdf_path.name}: {e}")
        
        return info


class BatchOCRProcessor:
    """Handles batch OCR processing of multiple PDFs."""
    
    def __init__(self, ocr_processor: Optional[OCRProcessor] = None, max_workers: int = 2):
        """Initialize batch OCR processor.
        
        Args:
            ocr_processor: OCR processor instance (creates one if not provided)
            max_workers: Maximum parallel OCR workers (default 2 due to resource intensity)
        """
        self.ocr_processor = ocr_processor or OCRProcessor()
        self.max_workers = max_workers
    
    def process_documents(self, documents: List[DocumentInfo], output_dir: Optional[Path] = None) -> dict[str, Path]:
        """Process multiple documents with OCR.
        
        Args:
            documents: List of documents to process
            output_dir: Optional output directory for OCR results
            
        Returns:
            Dictionary mapping original paths to processed paths
        """
        results = {}
        pdfs = [doc for doc in documents if doc.path.suffix.lower() == '.pdf']
        
        # First pass: check which PDFs need OCR
        need_ocr = []
        for doc in pdfs:
            if self.ocr_processor.needs_ocr(doc.path):
                need_ocr.append(doc)
                doc.ocr_status = OCRStatus.REQUIRED
            else:
                results[str(doc.path)] = doc.path
                doc.ocr_status = OCRStatus.NOT_NEEDED
        
        if not need_ocr:
            logger.info("No PDFs require OCR processing")
            return results
        
        logger.info(f"Processing {len(need_ocr)} PDFs with OCR")
        
        # Process PDFs that need OCR
        if len(need_ocr) <= 2 or self.max_workers == 1:
            # Serial processing for small batches
            for doc in need_ocr:
                try:
                    output_path = None
                    if output_dir:
                        output_path = output_dir / f"ocr_{doc.name}"
                    
                    processed_path = self.ocr_processor.process_pdf(doc.path, output_path)
                    results[str(doc.path)] = processed_path
                    doc.ocr_status = OCRStatus.COMPLETED
                except OCRError as e:
                    logger.error(f"OCR failed for {doc.name}: {e}")
                    doc.ocr_status = OCRStatus.FAILED
                    doc.error_message = str(e)
                    raise
        else:
            # Parallel processing for larger batches
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_doc = {}
                
                for doc in need_ocr:
                    output_path = None
                    if output_dir:
                        output_path = output_dir / f"ocr_{doc.name}"
                    
                    future = executor.submit(self.ocr_processor.process_pdf, doc.path, output_path)
                    future_to_doc[future] = doc
                
                for future in as_completed(future_to_doc):
                    doc = future_to_doc[future]
                    try:
                        processed_path = future.result()
                        results[str(doc.path)] = processed_path
                        doc.ocr_status = OCRStatus.COMPLETED
                    except Exception as e:
                        logger.error(f"OCR failed for {doc.name}: {e}")
                        doc.ocr_status = OCRStatus.FAILED
                        doc.error_message = str(e)
                        raise OCRError(
                            f"Batch OCR failed for {doc.name}: {e}",
                            pdf_file=str(doc.path)
                        )
        
        # Add non-PDF documents to results (they don't need OCR)
        for doc in documents:
            if doc.path.suffix.lower() != '.pdf':
                results[str(doc.path)] = doc.path
                doc.ocr_status = OCRStatus.NOT_NEEDED
        
        return results