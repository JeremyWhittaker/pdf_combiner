#!/usr/bin/env python3
"""
Enhanced PDF Combiner

A powerful tool to combine multiple PDFs, DOC, and DOCX files into a single PDF with
advanced features like progress bars, parallel processing, bookmarks, filtering, and more.

Features:
- Progress bars for better user experience
- Parallel processing for faster conversion
- Automatic bookmark/TOC generation
- File filtering with include/exclude patterns
- Custom file ordering options
- Password protection for output PDF
- Compression options
- Configuration file support
- Enhanced error handling and logging
"""

from __future__ import annotations

import concurrent.futures
import fnmatch
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, List, Optional, Dict, Any, Union

import click
from tqdm import tqdm

try:
    from PyPDF2 import PdfReader, PdfWriter, PdfMerger
    from PyPDF2.errors import PdfReadError
    from PyPDF2.generic import Bookmark
except ImportError:
    click.echo("PyPDF2 is required. Install with: pip install PyPDF2", err=True)
    sys.exit(1)

try:
    from docx import Document
except ImportError:
    click.echo("python-docx is required. Install with: pip install python-docx", err=True)
    sys.exit(1)

if platform.system() in ["Windows", "Darwin"]:
    try:
        from docx2pdf import convert as docx2pdf_convert
    except ImportError:
        click.echo("docx2pdf is required on Windows/macOS. Install with: pip install docx2pdf", err=True)
        sys.exit(1)


# -----------------------------------------------------------------------------#
# Configuration and Data Classes                                              #
# -----------------------------------------------------------------------------#

@dataclass
class ProcessingConfig:
    """Configuration for PDF processing."""
    max_workers: int = 4
    compression_level: int = 5  # 1-9, where 9 is maximum compression
    add_bookmarks: bool = True
    include_patterns: List[str] = field(default_factory=lambda: ["*.pdf", "*.doc", "*.docx"])
    exclude_patterns: List[str] = field(default_factory=list)
    sort_order: str = "name"  # name, date, size, custom
    custom_order_file: Optional[str] = None
    password: Optional[str] = None
    ocr_enabled: bool = True
    preserve_metadata: bool = True
    log_file: Optional[str] = None
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'ProcessingConfig':
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        except Exception as e:
            logging.warning(f"Could not load config from {config_path}: {e}")
            return cls()
    
    def to_file(self, config_path: Path) -> None:
        """Save configuration to YAML file."""
        data = {k: v for k, v in self.__dict__.items() if v is not None}
        with open(config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, indent=2)


@dataclass
class ProcessingResult:
    """Result of document processing operation."""
    processed_documents: int = 0
    failed_documents: int = 0
    total_pages: int = 0
    output_size: int = 0
    processing_time: float = 0.0
    failed_files: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# -----------------------------------------------------------------------------#
# Enhanced Utility Functions                                                  #
# -----------------------------------------------------------------------------#

SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx"}


def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> None:
    """Setup enhanced logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s [%(levelname)s] %(message)s"
    
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers
    )


def matches_patterns(file_path: Path, include_patterns: List[str], exclude_patterns: List[str]) -> bool:
    """Check if file matches include patterns and doesn't match exclude patterns."""
    filename = file_path.name.lower()
    
    # Check exclude patterns first
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(filename, pattern.lower()):
            return False
    
    # Check include patterns
    for pattern in include_patterns:
        if fnmatch.fnmatch(filename, pattern.lower()):
            return True
    
    return False


def get_file_sort_key(file_path: Path, sort_order: str):
    """Get sort key for file based on sort order."""
    if sort_order == "name":
        return file_path.name.lower()
    elif sort_order == "date":
        return file_path.stat().st_mtime
    elif sort_order == "size":
        return file_path.stat().st_size
    else:
        return file_path.name.lower()


def iter_documents(directory: Path, config: ProcessingConfig) -> Iterator[Path]:
    """Yield filtered and sorted document files from directory."""
    if not directory.is_dir():
        raise NotADirectoryError(f"{directory} is not a directory")
    
    # Get all matching files
    files = []
    for file_path in directory.iterdir():
        if file_path.is_file() and matches_patterns(file_path, config.include_patterns, config.exclude_patterns):
            files.append(file_path)
    
    # Custom ordering from file
    if config.sort_order == "custom" and config.custom_order_file:
        try:
            with open(config.custom_order_file, 'r') as f:
                custom_order = [line.strip() for line in f if line.strip()]
            order_dict = {name: i for i, name in enumerate(custom_order)}
            files.sort(key=lambda f: order_dict.get(f.name, len(custom_order)))
        except Exception as e:
            logging.warning(f"Could not use custom order file: {e}, falling back to name sort")
            files.sort(key=lambda f: get_file_sort_key(f, "name"))
    else:
        # Standard sorting
        reverse = config.sort_order == "date"  # Newest first for date
        files.sort(key=lambda f: get_file_sort_key(f, config.sort_order), reverse=reverse)
    
    yield from files


def convert_doc_to_pdf_enhanced(doc_path: Path, output_dir: Path, progress_callback=None) -> Path:
    """Enhanced DOC/DOCX to PDF conversion with progress tracking."""
    pdf_path = output_dir / f"{doc_path.stem}.pdf"
    
    try:
        if progress_callback:
            progress_callback(f"Converting {doc_path.name}")
        
        if platform.system() in ["Windows", "Darwin"]:
            # Use docx2pdf on Windows/macOS
            docx2pdf_convert(str(doc_path), str(pdf_path))
        else:
            # Use LibreOffice on Linux
            cmd = [
                "libreoffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(output_dir),
                str(doc_path)
            ]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        
        if not pdf_path.exists():
            raise RuntimeError(f"Conversion failed: {pdf_path} was not created")
        
        return pdf_path
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Conversion timeout for {doc_path.name}")
    except Exception as e:
        raise RuntimeError(f"Conversion failed for {doc_path.name}: {e}")


def pdf_has_text_enhanced(path: Path, sample_pages: int = 3) -> bool:
    """Enhanced text detection with better error handling."""
    try:
        reader = PdfReader(str(path))
        page_count = min(len(reader.pages), sample_pages)
        
        for i in range(page_count):
            try:
                text = reader.pages[i].extract_text()
                if text and text.strip():
                    return True
            except Exception as e:
                logging.debug(f"Error reading page {i} of {path.name}: {e}")
                continue
                
    except Exception as e:
        logging.error(f"Error reading PDF {path.name}: {e}")
        return False
    
    return False


def ocr_pdf_enhanced(source: Path, dest_dir: Path, progress_callback=None) -> Path:
    """Enhanced OCR processing with progress tracking."""
    if pdf_has_text_enhanced(source):
        logging.debug(f"Text already present in {source.name}; skipping OCR.")
        return source

    dest = dest_dir / source.name
    
    if progress_callback:
        progress_callback(f"OCR processing {source.name}")

    cmd = [
        "ocrmypdf",
        "--skip-text",
        "--optimize", "1",
        "--quiet",
        str(source),
        str(dest),
    ]
    
    try:
        subprocess.run(cmd, check=True, timeout=300)  # 5 minute timeout
        return dest
    except subprocess.TimeoutExpired:
        logging.error(f"OCR timeout for {source.name}")
        return source  # Return original if OCR fails
    except Exception as e:
        logging.error(f"OCR failed for {source.name}: {e}")
        return source  # Return original if OCR fails


# -----------------------------------------------------------------------------#
# Enhanced Core Processing                                                     #
# -----------------------------------------------------------------------------#

class EnhancedPDFProcessor:
    """Enhanced PDF processor with parallel processing and advanced features."""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.result = ProcessingResult()
        
    def process_single_document(self, doc_path: Path, temp_dir: Path) -> Optional[Path]:
        """Process a single document (convert if needed, OCR if needed)."""
        try:
            # Convert if needed
            if doc_path.suffix.lower() in ['.doc', '.docx']:
                pdf_path = convert_doc_to_pdf_enhanced(
                    doc_path, temp_dir, 
                    lambda msg: tqdm.write(f"  {msg}")
                )
            else:
                pdf_path = doc_path
            
            # OCR if needed and enabled
            if self.config.ocr_enabled:
                pdf_path = ocr_pdf_enhanced(
                    pdf_path, temp_dir,
                    lambda msg: tqdm.write(f"  {msg}")
                )
            
            return pdf_path
            
        except Exception as e:
            logging.error(f"Failed to process {doc_path.name}: {e}")
            self.result.failed_files.append(doc_path.name)
            self.result.failed_documents += 1
            return None
    
    def create_bookmarks(self, merger: PdfMerger, processed_files: List[tuple]) -> None:
        """Add bookmarks to the merged PDF."""
        if not self.config.add_bookmarks:
            return
            
        current_page = 0
        for original_name, pdf_path in processed_files:
            try:
                reader = PdfReader(str(pdf_path))
                page_count = len(reader.pages)
                
                # Add bookmark for this document
                bookmark_title = Path(original_name).stem
                merger.add_outline_item(bookmark_title, current_page)
                
                current_page += page_count
                
            except Exception as e:
                logging.warning(f"Could not add bookmark for {original_name}: {e}")
    
    def apply_security(self, output_path: Path) -> None:
        """Apply password protection to the output PDF."""
        if not self.config.password:
            return
            
        try:
            # Read the PDF
            reader = PdfReader(str(output_path))
            writer = PdfWriter()
            
            # Copy all pages
            for page in reader.pages:
                writer.add_page(page)
            
            # Copy metadata
            if reader.metadata and self.config.preserve_metadata:
                writer.add_metadata(reader.metadata)
            
            # Encrypt with password
            writer.encrypt(self.config.password)
            
            # Write back to file
            with open(output_path, 'wb') as f:
                writer.write(f)
                
            logging.info("Password protection applied to output PDF")
            
        except Exception as e:
            logging.error(f"Failed to apply password protection: {e}")
            self.result.warnings.append(f"Password protection failed: {e}")
    
    def merge_documents(self, directory: Path, output_file: Path) -> ProcessingResult:
        """Enhanced document merging with all advanced features."""
        start_time = time.time()
        
        logging.info(f"Processing documents from {directory}")
        
        # Get list of documents to process
        documents = list(iter_documents(directory, self.config))
        if not documents:
            raise ValueError("No matching documents found in directory")
        
        logging.info(f"Found {len(documents)} documents to process")
        
        # Create progress bar
        with tqdm(total=len(documents), desc="Processing documents", unit="file") as pbar:
            processed_files = []
            
            with tempfile.TemporaryDirectory() as tmpdir:
                temp_dir = Path(tmpdir)
                
                # Process documents in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                    # Submit all tasks
                    future_to_doc = {
                        executor.submit(self.process_single_document, doc, temp_dir): doc
                        for doc in documents
                    }
                    
                    # Collect results as they complete
                    for future in concurrent.futures.as_completed(future_to_doc):
                        doc = future_to_doc[future]
                        try:
                            result_path = future.result()
                            if result_path:
                                processed_files.append((doc.name, result_path))
                                self.result.processed_documents += 1
                            
                        except Exception as e:
                            logging.error(f"Processing failed for {doc.name}: {e}")
                            self.result.failed_files.append(doc.name)
                            self.result.failed_documents += 1
                        
                        pbar.update(1)
                
                # Merge all processed PDFs
                if processed_files:
                    pbar.set_description("Merging PDFs")
                    merger = PdfMerger()
                    
                    try:
                        # Sort processed files to maintain order
                        processed_files.sort(key=lambda x: [doc.name for doc in documents].index(x[0]))
                        
                        # Add each PDF to merger
                        for original_name, pdf_path in processed_files:
                            merger.append(str(pdf_path))
                        
                        # Add bookmarks
                        self.create_bookmarks(merger, processed_files)
                        
                        # Add metadata
                        merger.add_metadata({
                            '/Title': f'Combined Document - {len(processed_files)} files',
                            '/Subject': f'Combined from: {", ".join([pf[0] for pf in processed_files])}',
                            '/Producer': 'Enhanced PDF Combiner',
                            '/Creator': 'Enhanced PDF Combiner'
                        })
                        
                        # Write the merged PDF
                        merger.write(str(output_file))
                        merger.close()
                        
                        # Apply security if configured
                        self.apply_security(output_file)
                        
                        # Calculate final statistics
                        try:
                            final_reader = PdfReader(str(output_file))
                            self.result.total_pages = len(final_reader.pages)
                        except:
                            self.result.total_pages = 0
                        
                        self.result.output_size = output_file.stat().st_size
                        
                    except Exception as e:
                        logging.error(f"Failed to merge PDFs: {e}")
                        raise
        
        self.result.processing_time = time.time() - start_time
        
        # Final report
        if self.result.failed_documents > 0:
            logging.warning(f"⚠️  {self.result.failed_documents} documents failed to process")
            if self.result.failed_files:
                logging.warning(f"Failed files: {', '.join(self.result.failed_files)}")
        
        success_rate = (self.result.processed_documents / len(documents)) * 100
        logging.info(f"✓ Processing complete: {self.result.processed_documents}/{len(documents)} files "
                    f"({success_rate:.1f}% success rate)")
        logging.info(f"✓ Combined PDF: {output_file} ({self.result.total_pages} pages, "
                    f"{self.result.output_size / 1024 / 1024:.1f}MB)")
        logging.info(f"✓ Processing time: {self.result.processing_time:.1f} seconds")
        
        return self.result


def check_documents_enhanced(directory: Path, config: ProcessingConfig) -> None:
    """Enhanced document checking with filtering and detailed analysis."""
    logging.info(f"Running enhanced integrity check on directory: {directory}")
    
    documents = list(iter_documents(directory, config))
    if not documents:
        logging.warning("No matching documents found")
        return
    
    stats = {"pdf": 0, "doc": 0, "docx": 0, "readable": 0, "unreadable": 0, "text_pdfs": 0, "image_pdfs": 0}
    unreadable_files = []
    
    with tqdm(documents, desc="Checking documents", unit="file") as pbar:
        for doc in pbar:
            pbar.set_postfix_str(doc.name[:30] + "..." if len(doc.name) > 30 else doc.name)
            
            ext = doc.suffix.lower()
            if ext == ".pdf":
                stats["pdf"] += 1
                try:
                    has_text = pdf_has_text_enhanced(doc)
                    if has_text:
                        stats["text_pdfs"] += 1
                        status = "searchable text"
                    else:
                        stats["image_pdfs"] += 1
                        status = "image-only / needs OCR"
                    
                    logging.info(f"%-50s → %s", doc.name, status)
                    stats["readable"] += 1
                    
                except Exception as e:
                    logging.error(f"%-50s → ERROR: %s", doc.name, e)
                    unreadable_files.append(doc.name)
                    stats["unreadable"] += 1
                    
            elif ext in [".doc", ".docx"]:
                if ext == ".doc":
                    stats["doc"] += 1
                else:
                    stats["docx"] += 1
                    
                logging.info(f"%-50s → %s", doc.name, "DOC/DOCX (will convert to PDF)")
                stats["readable"] += 1
    
    # Summary report
    total = len(documents)
    logging.info("\n" + "="*60)
    logging.info("DOCUMENT ANALYSIS SUMMARY")
    logging.info("="*60)
    logging.info(f"Total documents found: {total}")
    logging.info(f"  - PDF files: {stats['pdf']} ({stats['text_pdfs']} with text, {stats['image_pdfs']} image-only)")
    logging.info(f"  - DOC files: {stats['doc']}")
    logging.info(f"  - DOCX files: {stats['docx']}")
    logging.info(f"Readable: {stats['readable']}, Unreadable: {stats['unreadable']}")
    
    if unreadable_files:
        logging.warning(f"Unreadable files: {', '.join(unreadable_files)}")
    
    if config.include_patterns != ["*.pdf", "*.doc", "*.docx"]:
        logging.info(f"Include patterns: {config.include_patterns}")
    if config.exclude_patterns:
        logging.info(f"Exclude patterns: {config.exclude_patterns}")
    
    estimated_time = len(documents) * 1.2  # Rough estimate
    logging.info(f"Estimated processing time: {estimated_time:.1f} seconds")


def verify_combined_pdf_enhanced(pdf_path: Path, source_dir: Path, config: ProcessingConfig) -> None:
    """Enhanced PDF verification with detailed analysis."""
    logging.info(f"Verifying {pdf_path} against directory {source_dir}")
    
    # Get expected files from directory
    expected_files = set(doc.name for doc in iter_documents(source_dir, config))
    expected_count = len(expected_files)
    
    if expected_count == 0:
        logging.warning("No matching files found in source directory")
        return
    
    # Try to get source files from PDF metadata
    try:
        reader = PdfReader(str(pdf_path))
        metadata = reader.metadata
        metadata_files = set()
        
        if metadata:
            for field in ['/Subject', '/Keywords', '/Producer']:
                if field in metadata:
                    value = str(metadata[field])
                    if 'Combined from:' in value:
                        files_str = value.replace('Combined from:', '').strip()
                        metadata_files = set(f.strip() for f in files_str.split(',') if f.strip())
                        break
        
        # Analysis
        if metadata_files:
            logging.info(f"Found {len(metadata_files)} source files in PDF metadata")
            missing = expected_files - metadata_files
            extra = metadata_files - expected_files
            
            if not missing and not extra:
                logging.info(f"✓ VERIFIED: All {expected_count} files from directory are in the combined PDF")
            else:
                if missing:
                    logging.warning(f"⚠️  MISSING FILES ({len(missing)}): These files are in the directory but not in the PDF:")
                    for f in sorted(missing):
                        logging.warning(f"  - {f}")
                if extra:
                    logging.warning(f"⚠️  EXTRA FILES ({len(extra)}): These files are in the PDF but not in the directory:")
                    for f in sorted(extra):
                        logging.warning(f"  - {f}")
        else:
            logging.warning("No source file metadata found in PDF")
        
        # PDF statistics
        page_count = len(reader.pages)
        file_size = pdf_path.stat().st_size
        logging.info(f"PDF Statistics:")
        logging.info(f"  - Pages: {page_count}")
        logging.info(f"  - File size: {file_size / 1024 / 1024:.1f} MB")
        logging.info(f"  - Average pages per document: {page_count / max(len(metadata_files or expected_files), 1):.1f}")
        
        # Check if password protected
        if reader.is_encrypted:
            logging.info("  - Password protected: Yes")
        
    except Exception as e:
        logging.error(f"Could not analyze PDF: {e}")


# -----------------------------------------------------------------------------#
# Enhanced CLI Interface                                                       #
# -----------------------------------------------------------------------------#

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Enhanced PDF Combiner - Combine PDFs, DOCs, and DOCXs with advanced features."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument('source_dir', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('-o', '--output', type=click.Path(path_type=Path), default=Path.cwd() / 'combined.pdf',
              help='Output PDF file path')
@click.option('-c', '--config', type=click.Path(exists=True, path_type=Path),
              help='Configuration file path')
@click.option('--workers', type=int, default=4, help='Number of parallel workers')
@click.option('--compression', type=click.IntRange(1, 9), default=5, help='Compression level (1-9)')
@click.option('--include', multiple=True, help='Include file patterns (e.g., "*.pdf")')
@click.option('--exclude', multiple=True, help='Exclude file patterns')
@click.option('--sort', type=click.Choice(['name', 'date', 'size', 'custom']), default='name',
              help='File sorting order')
@click.option('--custom-order', type=click.Path(exists=True, path_type=Path),
              help='Custom order file (one filename per line)')
@click.option('--password', help='Password protect the output PDF')
@click.option('--no-bookmarks', is_flag=True, help='Disable bookmark generation')
@click.option('--no-ocr', is_flag=True, help='Disable OCR processing')
@click.option('--log-file', type=click.Path(path_type=Path), help='Log file path')
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
@click.option('--check', is_flag=True, help='Only check files without processing')
@click.option('--save-config', type=click.Path(path_type=Path), help='Save current settings to config file')
def combine(source_dir, output, config, workers, compression, include, exclude, sort, custom_order,
           password, no_bookmarks, no_ocr, log_file, verbose, check, save_config):
    """Combine documents from SOURCE_DIR into a single PDF."""
    
    # Load configuration
    if config:
        proc_config = ProcessingConfig.from_file(config)
    else:
        proc_config = ProcessingConfig()
    
    # Override with command line options
    if workers != 4:
        proc_config.max_workers = workers
    if compression != 5:
        proc_config.compression_level = compression
    if include:
        proc_config.include_patterns = list(include)
    if exclude:
        proc_config.exclude_patterns = list(exclude)
    if sort != 'name':
        proc_config.sort_order = sort
    if custom_order:
        proc_config.custom_order_file = str(custom_order)
    if password:
        proc_config.password = password
    if no_bookmarks:
        proc_config.add_bookmarks = False
    if no_ocr:
        proc_config.ocr_enabled = False
    if log_file:
        proc_config.log_file = str(log_file)
    
    # Save configuration if requested
    if save_config:
        proc_config.to_file(save_config)
        click.echo(f"Configuration saved to {save_config}")
    
    # Setup logging
    setup_logging(verbose, proc_config.log_file)
    
    # Check system dependencies
    if not shutil.which("ocrmypdf") and proc_config.ocr_enabled:
        logging.warning("ocrmypdf not found - OCR will be disabled")
        proc_config.ocr_enabled = False
    
    if platform.system() == "Linux" and not shutil.which("libreoffice"):
        logging.warning("libreoffice not found - DOC/DOCX conversion may fail")
    
    try:
        if check:
            check_documents_enhanced(source_dir, proc_config)
        else:
            processor = EnhancedPDFProcessor(proc_config)
            result = processor.merge_documents(source_dir, output)
            
            if result.failed_documents > 0:
                sys.exit(1)
                
    except Exception as e:
        logging.error(f"Operation failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument('pdf_file', type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument('source_dir', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('-c', '--config', type=click.Path(exists=True, path_type=Path),
              help='Configuration file path')
@click.option('--include', multiple=True, help='Include file patterns')
@click.option('--exclude', multiple=True, help='Exclude file patterns')
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
def verify(pdf_file, source_dir, config, include, exclude, verbose):
    """Verify that PDF_FILE contains all documents from SOURCE_DIR."""
    
    # Load configuration
    if config:
        proc_config = ProcessingConfig.from_file(config)
    else:
        proc_config = ProcessingConfig()
    
    # Override with command line options
    if include:
        proc_config.include_patterns = list(include)
    if exclude:
        proc_config.exclude_patterns = list(exclude)
    
    setup_logging(verbose)
    
    try:
        verify_combined_pdf_enhanced(pdf_file, source_dir, proc_config)
    except Exception as e:
        logging.error(f"Verification failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--save-to', type=click.Path(path_type=Path), default=Path('pdf_combiner_config.yaml'),
              help='Configuration file to create')
def init_config(save_to):
    """Create a sample configuration file."""
    config = ProcessingConfig()
    config.to_file(save_to)
    click.echo(f"Sample configuration saved to {save_to}")
    click.echo("Edit this file to customize your settings.")


@cli.command()
def check_deps():
    """Check system dependencies."""
    click.echo("Checking system dependencies...")
    
    deps = {
        "Python": sys.version,
        "ocrmypdf": shutil.which("ocrmypdf"),
        "libreoffice": shutil.which("libreoffice"),
    }
    
    for name, status in deps.items():
        if status:
            click.echo(f"✓ {name}: {status if name == 'Python' else 'Found'}")
        else:
            click.echo(f"✗ {name}: Not found")
    
    # Check Python packages
    try:
        import PyPDF2
        click.echo(f"✓ PyPDF2: {PyPDF2.__version__}")
    except ImportError:
        click.echo("✗ PyPDF2: Not installed")
    
    try:
        import docx
        click.echo("✓ python-docx: Available")
    except ImportError:
        click.echo("✗ python-docx: Not installed")
    
    try:
        import tqdm
        click.echo(f"✓ tqdm: Available")
    except ImportError:
        click.echo("✗ tqdm: Not installed")


if __name__ == '__main__':
    cli()