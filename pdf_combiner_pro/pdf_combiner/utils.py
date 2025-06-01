"""Utility functions for PDF Combiner."""

import logging
import platform
import shutil
import subprocess
from pathlib import Path
from typing import List, Iterator, Set, Optional, Tuple

from pdf_combiner.exceptions import DependencyError
from pdf_combiner.models import DocumentType, DocumentInfo


logger = logging.getLogger(__name__)


# Supported file extensions
SUPPORTED_EXTENSIONS: Set[str] = {".pdf", ".doc", ".docx"}


def get_document_type(path: Path) -> Optional[DocumentType]:
    """Get document type from file extension.
    
    Args:
        path: Path to document
        
    Returns:
        DocumentType or None if not supported
    """
    extension = path.suffix.lower().lstrip('.')
    
    if extension == "pdf":
        return DocumentType.PDF
    elif extension == "doc":
        return DocumentType.DOC
    elif extension == "docx":
        return DocumentType.DOCX
    
    return None


def iter_documents(directory: Path, recursive: bool = False) -> Iterator[Path]:
    """Iterate over supported documents in a directory.
    
    Args:
        directory: Directory to scan
        recursive: Whether to scan subdirectories
        
    Yields:
        Path objects for each supported document
        
    Raises:
        NotADirectoryError: If directory doesn't exist or isn't a directory
    """
    if not directory.exists():
        raise NotADirectoryError(f"Directory does not exist: {directory}")
    
    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory}")
    
    if recursive:
        pattern = "**/*"
    else:
        pattern = "*"
    
    for path in sorted(directory.glob(pattern)):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def count_documents(directory: Path, recursive: bool = False) -> int:
    """Count supported documents in a directory.
    
    Args:
        directory: Directory to scan
        recursive: Whether to scan subdirectories
        
    Returns:
        Number of supported documents
    """
    return sum(1 for _ in iter_documents(directory, recursive))


def get_file_info(path: Path) -> DocumentInfo:
    """Get information about a document file.
    
    Args:
        path: Path to document
        
    Returns:
        DocumentInfo instance
        
    Raises:
        ValueError: If document type is not supported
    """
    doc_type = get_document_type(path)
    if not doc_type:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    
    stat = path.stat()
    
    return DocumentInfo(
        path=path,
        name=path.name,
        type=doc_type,
        size_bytes=stat.st_size,
        created_at=stat.st_ctime,
        modified_at=stat.st_mtime,
    )


def check_system_dependencies() -> Tuple[List[str], List[str]]:
    """Check for required system dependencies.
    
    Returns:
        Tuple of (available_deps, missing_deps)
    """
    available = []
    missing = []
    
    # Check for OCRmyPDF
    if shutil.which("ocrmypdf"):
        available.append("ocrmypdf")
    else:
        missing.append("ocrmypdf")
    
    # Check for Tesseract
    if shutil.which("tesseract"):
        available.append("tesseract")
    else:
        missing.append("tesseract")
    
    # Check for Ghostscript
    gs_commands = ["gs", "gswin32c", "gswin64c", "ghostscript"]
    if any(shutil.which(cmd) for cmd in gs_commands):
        available.append("ghostscript")
    else:
        missing.append("ghostscript")
    
    # Check for LibreOffice on Linux
    if platform.system() == "Linux":
        if shutil.which("libreoffice"):
            available.append("libreoffice")
        else:
            missing.append("libreoffice")
    
    return available, missing


def get_dependency_install_command(dependency: str) -> str:
    """Get installation command for a dependency.
    
    Args:
        dependency: Name of the dependency
        
    Returns:
        Installation command string
    """
    system = platform.system()
    
    commands = {
        "Windows": {
            "ocrmypdf": "pip install ocrmypdf",
            "tesseract": "Download from https://github.com/UB-Mannheim/tesseract/wiki",
            "ghostscript": "Download from https://www.ghostscript.com/download/gsdnld.html",
        },
        "Darwin": {  # macOS
            "ocrmypdf": "pip install ocrmypdf",
            "tesseract": "brew install tesseract",
            "ghostscript": "brew install ghostscript",
        },
        "Linux": {
            "ocrmypdf": "pip install ocrmypdf",
            "tesseract": "sudo apt-get install tesseract-ocr",
            "ghostscript": "sudo apt-get install ghostscript",
            "libreoffice": "sudo apt-get install libreoffice",
        },
    }
    
    return commands.get(system, {}).get(dependency, f"Install {dependency} for your system")


def ensure_dependencies(required: List[str]) -> None:
    """Ensure required dependencies are available.
    
    Args:
        required: List of required dependencies
        
    Raises:
        DependencyError: If any required dependency is missing
    """
    available, missing = check_system_dependencies()
    
    missing_required = [dep for dep in required if dep in missing]
    
    if missing_required:
        for dep in missing_required:
            install_cmd = get_dependency_install_command(dep)
            logger.error(f"Missing dependency: {dep}. Install with: {install_cmd}")
        
        raise DependencyError(
            missing_required[0],
            get_dependency_install_command(missing_required[0])
        )


def run_command(
    cmd: List[str],
    timeout: Optional[int] = None,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """Run a command with proper error handling.
    
    Args:
        cmd: Command and arguments as list
        timeout: Command timeout in seconds
        check: Whether to check return code
        capture_output: Whether to capture stdout/stderr
        
    Returns:
        CompletedProcess instance
        
    Raises:
        subprocess.CalledProcessError: If command fails and check=True
        subprocess.TimeoutExpired: If command times out
    """
    logger.debug(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
        )
        
        if result.returncode != 0 and not check:
            logger.warning(f"Command failed with code {result.returncode}: {' '.join(cmd)}")
            if result.stderr:
                logger.warning(f"Error output: {result.stderr}")
        
        return result
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {' '.join(cmd)}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        raise
    except FileNotFoundError:
        logger.error(f"Command not found: {cmd[0]}")
        raise


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} PB"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Ensure filename is not empty
    if not filename:
        filename = "unnamed"
    
    return filename