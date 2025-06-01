"""Document conversion functionality."""

import logging
import platform
import tempfile
from pathlib import Path
from typing import Optional

from pdf_combiner.exceptions import ConversionError, DependencyError
from pdf_combiner.models import DocumentInfo, DocumentType
from pdf_combiner.utils import run_command, ensure_dependencies


logger = logging.getLogger(__name__)


class DocumentConverter:
    """Handles conversion of various document formats to PDF."""
    
    def __init__(self, temp_dir: Optional[Path] = None):
        """Initialize document converter.
        
        Args:
            temp_dir: Optional temporary directory for conversions
        """
        self.temp_dir = temp_dir
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Check for required conversion dependencies."""
        if platform.system() == "Linux":
            try:
                ensure_dependencies(["libreoffice"])
            except DependencyError:
                logger.warning("LibreOffice not found. DOC/DOCX conversion will fail.")
    
    def convert_to_pdf(self, document: DocumentInfo, output_dir: Optional[Path] = None) -> Path:
        """Convert a document to PDF format.
        
        Args:
            document: Document information
            output_dir: Optional output directory (uses temp if not specified)
            
        Returns:
            Path to converted PDF
            
        Raises:
            ConversionError: If conversion fails
        """
        if document.type == DocumentType.PDF:
            # Already a PDF, return as-is
            return document.path
        
        if document.type in [DocumentType.DOC, DocumentType.DOCX]:
            return self._convert_office_to_pdf(document, output_dir)
        
        raise ConversionError(
            f"Unsupported document type for conversion: {document.type}",
            source_file=str(document.path),
            target_format="pdf"
        )
    
    def _convert_office_to_pdf(self, document: DocumentInfo, output_dir: Optional[Path] = None) -> Path:
        """Convert DOC/DOCX to PDF.
        
        Args:
            document: Document information
            output_dir: Optional output directory
            
        Returns:
            Path to converted PDF
            
        Raises:
            ConversionError: If conversion fails
        """
        if output_dir is None:
            output_dir = self.temp_dir or Path(tempfile.gettempdir())
        
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{document.path.stem}.pdf"
        
        logger.info(f"Converting {document.name} to PDF...")
        
        if platform.system() in ["Windows", "Darwin"]:
            return self._convert_with_docx2pdf(document.path, output_path)
        else:
            return self._convert_with_libreoffice(document.path, output_dir)
    
    def _convert_with_docx2pdf(self, input_path: Path, output_path: Path) -> Path:
        """Convert using docx2pdf (Windows/macOS).
        
        Args:
            input_path: Input document path
            output_path: Output PDF path
            
        Returns:
            Path to converted PDF
            
        Raises:
            ConversionError: If conversion fails
        """
        try:
            from docx2pdf import convert
            
            convert(str(input_path), str(output_path))
            
            if not output_path.exists():
                raise ConversionError(
                    f"Conversion produced no output file",
                    source_file=str(input_path),
                    target_format="pdf"
                )
            
            logger.debug(f"Successfully converted {input_path.name} to PDF")
            return output_path
            
        except ImportError:
            raise ConversionError(
                "docx2pdf is required for DOC/DOCX conversion on Windows/macOS",
                source_file=str(input_path),
                target_format="pdf"
            )
        except Exception as e:
            raise ConversionError(
                f"Failed to convert document: {e}",
                source_file=str(input_path),
                target_format="pdf"
            )
    
    def _convert_with_libreoffice(self, input_path: Path, output_dir: Path) -> Path:
        """Convert using LibreOffice (Linux).
        
        Args:
            input_path: Input document path
            output_dir: Output directory
            
        Returns:
            Path to converted PDF
            
        Raises:
            ConversionError: If conversion fails
        """
        cmd = [
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(input_path)
        ]
        
        try:
            result = run_command(cmd, timeout=120)
            
            # LibreOffice creates the output file with the same name but .pdf extension
            output_path = output_dir / f"{input_path.stem}.pdf"
            
            if not output_path.exists():
                # Check if LibreOffice put it somewhere else
                possible_paths = list(output_dir.glob(f"{input_path.stem}*.pdf"))
                if possible_paths:
                    output_path = possible_paths[0]
                else:
                    raise ConversionError(
                        f"Conversion produced no output file",
                        source_file=str(input_path),
                        target_format="pdf"
                    )
            
            logger.debug(f"Successfully converted {input_path.name} to PDF")
            return output_path
            
        except FileNotFoundError:
            raise DependencyError(
                "libreoffice",
                "sudo apt-get install libreoffice"
            )
        except Exception as e:
            raise ConversionError(
                f"LibreOffice conversion failed: {e}",
                source_file=str(input_path),
                target_format="pdf"
            )


class BatchConverter:
    """Handles batch conversion of multiple documents."""
    
    def __init__(self, converter: Optional[DocumentConverter] = None, max_workers: int = 4):
        """Initialize batch converter.
        
        Args:
            converter: Document converter instance (creates one if not provided)
            max_workers: Maximum parallel conversion workers
        """
        self.converter = converter or DocumentConverter()
        self.max_workers = max_workers
    
    def convert_documents(self, documents: list[DocumentInfo], output_dir: Optional[Path] = None) -> dict[str, Path]:
        """Convert multiple documents to PDF.
        
        Args:
            documents: List of documents to convert
            output_dir: Optional output directory
            
        Returns:
            Dictionary mapping original paths to converted PDF paths
        """
        results = {}
        
        # Group by type for efficiency
        pdfs = [doc for doc in documents if doc.type == DocumentType.PDF]
        to_convert = [doc for doc in documents if doc.type != DocumentType.PDF]
        
        # PDFs don't need conversion
        for doc in pdfs:
            results[str(doc.path)] = doc.path
        
        # Convert other formats
        if len(to_convert) <= 3 or self.max_workers == 1:
            # Serial conversion for small batches
            for doc in to_convert:
                try:
                    converted_path = self.converter.convert_to_pdf(doc, output_dir)
                    results[str(doc.path)] = converted_path
                except ConversionError as e:
                    logger.error(f"Failed to convert {doc.name}: {e}")
                    raise
        else:
            # Parallel conversion for larger batches
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_doc = {
                    executor.submit(self.converter.convert_to_pdf, doc, output_dir): doc
                    for doc in to_convert
                }
                
                for future in as_completed(future_to_doc):
                    doc = future_to_doc[future]
                    try:
                        converted_path = future.result()
                        results[str(doc.path)] = converted_path
                    except Exception as e:
                        logger.error(f"Failed to convert {doc.name}: {e}")
                        raise ConversionError(
                            f"Batch conversion failed for {doc.name}: {e}",
                            source_file=str(doc.path),
                            target_format="pdf"
                        )
        
        return results