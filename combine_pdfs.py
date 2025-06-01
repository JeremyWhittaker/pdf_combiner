#!/usr/bin/env python3
"""
combine_pdfs.py

Combine every PDF, DOC, and DOCX in a given directory into one consolidated PDF, with optional
integrity checking and automatic OCR on image-only PDFs.

Usage
-----
Merge PDFs, DOCs, and DOCXs & OCR on-the-fly (writes ./combined.pdf):

    python combine_pdfs.py /path/to/dir

Same as above but pick an explicit output file:

    python combine_pdfs.py /path/to/dir -o /tmp/all_docs.pdf

Dry-run / health-check only (no merge, no OCR):

    python combine_pdfs.py /path/to/dir --check

Verify combined PDF contains all files from directory:

    python combine_pdfs.py --verify /path/to/combined.pdf /path/to/source_dir

Dependencies
------------
* PyPDF2 >= 3.0  (`pip install --upgrade PyPDF2`)
* ocrmypdf >= 15 (`pip install --upgrade ocrmypdf`)  – must also have Tesseract
  and Ghostscript installed on the host OS.
* python-docx (`pip install python-docx`)
* docx2pdf (`pip install docx2pdf`)  – Windows/macOS only
* For Linux: libreoffice (`sudo apt-get install libreoffice`)

The script logs to STDOUT at INFO level by default.  Use --verbose for DEBUG.
"""

from __future__ import annotations

import argparse
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterator, List, Tuple

try:
    from PyPDF2 import PdfReader, PdfMerger
    from PyPDF2.errors import PdfReadError
except ImportError:
    print("PyPDF2 is required. Install with: pip install PyPDF2")
    sys.exit(1)

try:
    from docx import Document
except ImportError:
    print("python-docx is required. Install with: pip install python-docx")
    sys.exit(1)

if platform.system() in ["Windows", "Darwin"]:
    try:
        from docx2pdf import convert
    except ImportError:
        print("docx2pdf is required on Windows/macOS. Install with: pip install docx2pdf")
        sys.exit(1)


# -----------------------------------------------------------------------------#
# Utility functions                                                            #
# -----------------------------------------------------------------------------#
SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx"}


def iter_documents(directory: Path) -> Iterator[Path]:
    """Yield PDF, DOC, and DOCX files in *directory* sorted alphabetically (non-recursive)."""
    if not directory.is_dir():
        raise NotADirectoryError(f"{directory} is not a directory")
    
    for p in sorted(directory.iterdir()):
        if p.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield p


def count_expected_files(directory: Path) -> int:
    """Count total number of supported files in directory."""
    return sum(1 for _ in iter_documents(directory))


def convert_doc_to_pdf(doc_path: Path, output_dir: Path) -> Path:
    """Convert DOC/DOCX file to PDF. Returns path to converted PDF."""
    pdf_path = output_dir / f"{doc_path.stem}.pdf"
    
    logging.info("Converting %s to PDF...", doc_path.name)
    
    if platform.system() in ["Windows", "Darwin"]:
        # Use docx2pdf on Windows/macOS
        convert(str(doc_path), str(pdf_path))
    else:
        # Use LibreOffice on Linux
        cmd = [
            "libreoffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(doc_path)
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logging.error("LibreOffice conversion failed for %s: %s", doc_path, e.stderr)
            raise RuntimeError(
                "LibreOffice is required for DOC/DOCX conversion on Linux. "
                "Install with: sudo apt-get install libreoffice"
            ) from e
        except FileNotFoundError:
            raise RuntimeError(
                "LibreOffice is required for DOC/DOCX conversion on Linux. "
                "Install with: sudo apt-get install libreoffice"
            )
    
    if not pdf_path.exists():
        raise RuntimeError(f"Failed to convert {doc_path} to PDF")
    
    return pdf_path


def pdf_has_text(path: Path, sample_pages: int = 3) -> bool:
    """
    Return True if *path* contains any extractable text on the first
    *sample_pages*.  Assumes PDFs that have *any* text are already searchable.
    """
    try:
        reader = PdfReader(str(path))
        for i, page in enumerate(reader.pages[:sample_pages]):
            if (text := page.extract_text()) and text.strip():
                return True
    except PdfReadError as err:
        logging.error("Corrupted PDF detected: %s – %s", path.name, err)
        return False
    return False  # no text found


def ocr_pdf(source: Path, dest_dir: Path) -> Path:
    """
    Run OCRmyPDF on *source* only when it is image-based.
    Returns the path to an OCR-processed copy (may be the original if no OCR).
    """
    if pdf_has_text(source):
        logging.debug("Text already present in %s; skipping OCR.", source.name)
        return source

    dest = dest_dir / source.name
    logging.info("Running OCR on image-only PDF: %s", source.name)

    cmd = [
        "ocrmypdf",
        "--skip-text",          # OCRmyPDF will skip pages that already have text
        "--quiet",
        str(source),
        str(dest),
    ]
    try:
        subprocess.run(cmd, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as err:
        logging.error("OCR failed for %s: %s", source, err)
        raise RuntimeError(
            "OCRmyPDF is required and must be installed & on PATH"
        ) from err
    return dest


def get_pdf_metadata(pdf_path: Path) -> List[str]:
    """Extract list of original filenames from PDF metadata if available."""
    try:
        reader = PdfReader(str(pdf_path))
        metadata = reader.metadata
        if metadata and hasattr(metadata, 'get'):
            # Check common metadata fields where we might store source files
            for field in ['/Subject', '/Keywords', '/Producer']:
                if field in metadata:
                    value = str(metadata[field])
                    if 'Combined from:' in value:
                        files_str = value.replace('Combined from:', '').strip()
                        return [f.strip() for f in files_str.split(',')]
    except Exception as e:
        logging.debug("Could not read metadata from %s: %s", pdf_path, e)
    return []


# -----------------------------------------------------------------------------#
# Core workflow                                                                #
# -----------------------------------------------------------------------------#
def check_only(directory: Path) -> None:
    """
    Verify that every document in *directory* is readable and report whether PDFs
    already contain text (searchable) or are image-based (needs OCR).
    """
    logging.info("Running integrity check on directory: %s", directory)
    ok: List[str] = []
    bad: List[str] = []
    doc_count = 0
    pdf_count = 0

    for doc in iter_documents(directory):
        if doc.suffix.lower() in ['.doc', '.docx']:
            doc_count += 1
            logging.info("%-45s  →  %s", doc.name, "DOC/DOCX (will convert to PDF)")
            ok.append(doc.name)
        else:  # PDF
            pdf_count += 1
            try:
                searchable = pdf_has_text(doc)
                status = "searchable text" if searchable else "image-only / needs OCR"
                logging.info("%-45s  →  %s", doc.name, status)
                ok.append(doc.name)
            except PdfReadError:
                bad.append(doc.name)

    total = len(ok) + len(bad)
    logging.info("Found %d files total: %d PDFs, %d DOC/DOCX files", total, pdf_count, doc_count)
    
    if bad:
        logging.warning("Unreadable or corrupted files: %s", ", ".join(bad))
    logging.info("Checked %d documents – readable: %d, unreadable: %d", total, len(ok), len(bad))


def merge_documents(directory: Path, output_file: Path) -> None:
    """Combine every document in *directory* (after conversion/OCR if required) into *output_file*."""
    logging.info("Processing documents from %s ...", directory)
    
    # Count expected files
    expected_count = count_expected_files(directory)
    logging.info("Found %d supported files to process", expected_count)
    
    merger = PdfMerger()
    processed_files = []
    failed_files = []
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        
        for doc in iter_documents(directory):
            try:
                if doc.suffix.lower() in ['.doc', '.docx']:
                    # Convert DOC/DOCX to PDF first
                    pdf_path = convert_doc_to_pdf(doc, tmp)
                else:
                    pdf_path = doc
                
                # Run OCR if necessary; returns either original or OCR'd copy
                ready_pdf = ocr_pdf(pdf_path, tmp)
                merger.append(str(ready_pdf))
                processed_files.append(doc.name)
                logging.debug("Appended %s", doc.name)
                
            except Exception as e:
                logging.error("Failed to process %s: %s", doc.name, e)
                failed_files.append(doc.name)
        
        # Add metadata about source files
        merger.add_metadata({
            '/Subject': f'Combined from: {", ".join(processed_files)}',
            '/Producer': 'PDF Combiner Script'
        })
        
        merger.write(str(output_file))
        merger.close()
    
    # Final report
    processed_count = len(processed_files)
    if processed_count != expected_count:
        logging.warning("⚠️  FILE COUNT MISMATCH: Expected %d files, but only processed %d", 
                       expected_count, processed_count)
        if failed_files:
            logging.warning("Failed to process: %s", ", ".join(failed_files))
    
    try:
        total_pages = len(PdfReader(str(output_file)).pages)
        logging.info("✓ Combined PDF written to %s (%d pages from %d documents)",
                     output_file, total_pages, processed_count)
    except:
        logging.info("✓ Combined PDF written to %s (from %d documents)",
                     output_file, processed_count)


def verify_combined_pdf(pdf_path: Path, source_dir: Path) -> None:
    """Verify that a combined PDF contains all files from the source directory."""
    logging.info("Verifying %s against directory %s", pdf_path, source_dir)
    
    # Get expected files from directory
    expected_files = set(doc.name for doc in iter_documents(source_dir))
    expected_count = len(expected_files)
    
    # Try to get source files from PDF metadata
    metadata_files = set(get_pdf_metadata(pdf_path))
    
    if metadata_files:
        logging.info("Found %d source files in PDF metadata", len(metadata_files))
        missing = expected_files - metadata_files
        extra = metadata_files - expected_files
        
        if not missing and not extra:
            logging.info("✓ VERIFIED: All %d files from directory are in the combined PDF", expected_count)
        else:
            if missing:
                logging.warning("⚠️  MISSING FILES: These files are in the directory but not in the PDF:")
                for f in sorted(missing):
                    logging.warning("  - %s", f)
            if extra:
                logging.warning("⚠️  EXTRA FILES: These files are in the PDF but not in the directory:")
                for f in sorted(extra):
                    logging.warning("  - %s", f)
    else:
        logging.warning("No metadata found in PDF. Cannot verify source files.")
        logging.info("Directory contains %d files", expected_count)
        
    # Also report PDF info
    try:
        reader = PdfReader(str(pdf_path))
        logging.info("PDF has %d pages", len(reader.pages))
    except Exception as e:
        logging.error("Could not read PDF: %s", e)


# -----------------------------------------------------------------------------#
# Argument parsing & entry point                                               #
# -----------------------------------------------------------------------------#
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """CLI argument parser."""
    # First check if 'verify' is in argv to determine which parser to use
    if argv and len(argv) > 0 and argv[0] == 'verify':
        # Use verify-specific parser
        parser = argparse.ArgumentParser(
            description="Verify combined PDF contains all files from source directory."
        )
        parser.add_argument(
            "mode",
            choices=['verify'],
            help="Operation mode",
        )
        parser.add_argument(
            "pdf_file",
            type=Path,
            help="Combined PDF file to verify",
        )
        parser.add_argument(
            "source_dir",
            type=Path,
            help="Source directory to compare against",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable DEBUG-level logging.",
        )
    else:
        # Use default merge parser
        parser = argparse.ArgumentParser(
            description="Combine PDFs, DOCs, and DOCXs in a directory (with optional OCR and checking)."
        )
        parser.add_argument(
            "source_dir",
            type=Path,
            help="Directory containing files to combine (non-recursive).",
        )
        parser.add_argument(
            "-o", "--output",
            type=Path,
            default=Path.cwd() / "combined.pdf",
            help="Path for the merged PDF (default: ./combined.pdf).",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Only verify documents exist, are readable, and report requirements.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable DEBUG-level logging.",
        )
        
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    # Handle verify mode separately
    if argv and len(argv) > 0 and argv[0] == 'verify':
        args = parse_args(argv)
    else:
        args = parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Check for required tools
    if not shutil.which("ocrmypdf"):
        logging.warning("ocrmypdf was not found on PATH – OCR will fail if needed.")
    
    if platform.system() == "Linux" and not shutil.which("libreoffice"):
        logging.warning("libreoffice was not found on PATH – DOC/DOCX conversion will fail.")

    # Handle verify mode
    if hasattr(args, 'mode') and args.mode == 'verify':
        verify_combined_pdf(args.pdf_file, args.source_dir)
        return

    # Handle check mode
    if hasattr(args, 'check') and args.check:
        check_only(args.source_dir)
        return

    # Default merge mode
    try:
        merge_documents(args.source_dir, args.output)
    except Exception:
        logging.exception("Failed to create combined PDF.")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])