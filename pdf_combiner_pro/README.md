# PDF Combiner Pro

A professional-grade PDF combiner tool that merges PDFs, DOCs, and DOCX files with automatic OCR support for image-based PDFs.

## Features

- 📄 **Multi-format Support**: Combine PDF, DOC, and DOCX files seamlessly
- 🔍 **Automatic OCR**: Detects and processes image-only PDFs using OCRmyPDF
- 🔧 **Cross-platform**: Works on Windows, macOS, and Linux
- ✅ **Integrity Checking**: Verify document readability before processing
- 📊 **Verification Mode**: Confirm combined PDFs contain all source files
- 🎨 **Rich CLI**: Beautiful command-line interface with progress indicators
- ⚡ **High Performance**: Efficient processing with proper error handling
- 🔐 **Type-safe**: Full type hints and runtime validation with Pydantic
- 📝 **Comprehensive Logging**: Detailed logs with configurable verbosity
- 🧪 **Well-tested**: Extensive test coverage with pytest

## Installation

### From PyPI

```bash
pip install pdf-combiner-pro
```

### From Source

```bash
git clone https://github.com/yourusername/pdf-combiner-pro.git
cd pdf-combiner-pro
pip install -e ".[dev]"
```

### System Dependencies

#### All Platforms
- Python 3.8 or higher
- Tesseract OCR (for OCRmyPDF)
- Ghostscript (for OCRmyPDF)

#### Platform-specific

**Windows/macOS:**
```bash
# Tesseract
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
# macOS: brew install tesseract

# Ghostscript
# Windows: Download from https://www.ghostscript.com/download/gsdnld.html
# macOS: brew install ghostscript
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y tesseract-ocr ghostscript libreoffice

# Fedora/RHEL
sudo dnf install -y tesseract ghostscript libreoffice
```

## Usage

### Basic Usage

Combine all PDFs, DOCs, and DOCX files in a directory:

```bash
pdf-combiner combine /path/to/documents
```

Specify output file:

```bash
pdf-combiner combine /path/to/documents -o /path/to/output.pdf
```

### Advanced Options

```bash
# Dry run - check files without combining
pdf-combiner combine /path/to/documents --check

# Enable debug logging
pdf-combiner combine /path/to/documents --verbose

# Use configuration file
pdf-combiner combine /path/to/documents --config config.yaml

# Skip OCR processing
pdf-combiner combine /path/to/documents --skip-ocr

# Specify OCR language
pdf-combiner combine /path/to/documents --ocr-language eng+deu
```

### Verification Mode

Verify that a combined PDF contains all files from the source directory:

```bash
pdf-combiner verify /path/to/combined.pdf /path/to/source/directory
```

### Configuration File

Create a `config.yaml` file:

```yaml
# Output settings
output:
  default_name: "combined.pdf"
  add_metadata: true
  compression: true

# OCR settings  
ocr:
  enabled: true
  language: "eng"
  skip_text_pages: true
  dpi: 300

# Processing settings
processing:
  temp_dir: "/tmp/pdf_combiner"
  max_workers: 4
  
# Logging settings
logging:
  level: "INFO"
  format: "%(asctime)s [%(levelname)s] %(message)s"
  file: "pdf_combiner.log"
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/pdf-combiner-pro.git
cd pdf-combiner-pro

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pdf_combiner --cov-report=html

# Run specific test file
pytest tests/test_merger.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black pdf_combiner tests

# Sort imports
isort pdf_combiner tests

# Type checking
mypy pdf_combiner

# Linting
flake8 pdf_combiner tests

# Run all checks
pre-commit run --all-files
```

## Architecture

The project follows a modular architecture with clear separation of concerns:

```
pdf_combiner/
├── __init__.py          # Package initialization
├── __version__.py       # Version information
├── cli.py              # CLI interface using Click
├── config.py           # Configuration management with Pydantic
├── converters.py       # Document conversion logic
├── exceptions.py       # Custom exception classes
├── merger.py           # Core PDF merging functionality
├── models.py           # Pydantic models for data validation
├── ocr.py             # OCR processing logic
├── utils.py           # Utility functions
└── validators.py      # Input validation functions
```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [PyPDF2](https://github.com/py-pdf/pypdf2) for PDF manipulation
- [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) for OCR functionality
- [python-docx](https://github.com/python-openxml/python-docx) for DOCX handling
- [Click](https://click.palletsprojects.com/) for the CLI interface
- [Rich](https://github.com/Textualize/rich) for beautiful terminal output

## Support

- 📧 Email: support@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/pdf-combiner-pro/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/yourusername/pdf-combiner-pro/discussions)