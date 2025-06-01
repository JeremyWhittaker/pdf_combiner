# Enhanced PDF Combiner

A powerful Python tool to combine multiple PDFs, DOC, and DOCX files into a single PDF with advanced features like progress bars, parallel processing, bookmarks, filtering, and more.

## 🚀 New Enhanced Features

### ⚡ Performance & User Experience
- **Progress bars** with real-time processing updates
- **Parallel processing** for faster document conversion
- **Smart error handling** - continues processing even if some files fail
- **Detailed statistics** and success rate reporting

### 🎯 Advanced Processing Options
- **File filtering** with include/exclude patterns (e.g., `"*.pdf"`, `"*draft*"`)
- **Custom file ordering** (name, date, size, or custom list)
- **Automatic bookmarks/TOC** generation for easy navigation
- **Password protection** for output PDFs
- **Compression control** for output file size optimization

### ⚙️ Configuration & Management
- **YAML configuration files** for saving settings
- **Enhanced verification** with detailed analysis
- **Dependency checking** to ensure all tools are available
- **Comprehensive logging** with optional file output

## Installation

### Prerequisites

1. Python 3.8 or higher
2. System dependencies:
   - **All platforms**: Tesseract OCR and Ghostscript for OCR functionality
   - **Linux**: LibreOffice for DOC/DOCX conversion
   - **Windows/macOS**: No additional requirements for DOC/DOCX

### Quick Setup

```bash
# Clone the repository
git clone git@github.com:JeremyWhittaker/pdf_combiner.git
cd pdf_combiner

# Run the setup script
chmod +x setup.sh
./setup.sh

# Or manually install dependencies
pip install -r requirements.txt
```

### System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y ocrmypdf libreoffice
```

#### macOS
```bash
brew install ocrmypdf
```

#### Windows
```bash
# OCR support comes with pip install
pip install ocrmypdf
```

## Usage

### Both Versions Available

The repository includes two versions:

1. **`combine_pdfs.py`** - Original simple version
2. **`combine_pdfs_enhanced.py`** - New enhanced version with all advanced features

### Enhanced Version (Recommended)

#### Basic Commands

```bash
# Check system dependencies
python combine_pdfs_enhanced.py check-deps

# Create a configuration file
python combine_pdfs_enhanced.py init-config

# Basic combine operation
python combine_pdfs_enhanced.py combine /path/to/documents

# Combine with custom output
python combine_pdfs_enhanced.py combine /path/to/documents -o combined.pdf
```

#### Advanced Usage

```bash
# Filter files with patterns
python combine_pdfs_enhanced.py combine /path/to/docs --include "*.pdf" "report_*.docx"
python combine_pdfs_enhanced.py combine /path/to/docs --exclude "*draft*" "*temp*"

# Control processing
python combine_pdfs_enhanced.py combine /path/to/docs --workers 8 --compression 9

# Sort files by different criteria
python combine_pdfs_enhanced.py combine /path/to/docs --sort date  # newest first
python combine_pdfs_enhanced.py combine /path/to/docs --sort size  # largest first

# Add password protection
python combine_pdfs_enhanced.py combine /path/to/docs --password "mypassword"

# Disable features if needed
python combine_pdfs_enhanced.py combine /path/to/docs --no-ocr --no-bookmarks

# Check files without processing
python combine_pdfs_enhanced.py combine /path/to/docs --check

# Verify existing PDF
python combine_pdfs_enhanced.py verify combined.pdf /path/to/source/docs

# Use configuration file
python combine_pdfs_enhanced.py combine /path/to/docs -c my_config.yaml
```

#### Configuration File Example

```yaml
# pdf_combiner_config.yaml
max_workers: 6
compression_level: 7
add_bookmarks: true
include_patterns:
  - "*.pdf"
  - "*.docx"
  - "report_*.doc"
exclude_patterns:
  - "*draft*"
  - "*temp*"
sort_order: "date"
password: "optional_password"
log_file: "processing.log"
```

### Original Version

```bash
# Basic usage
python combine_pdfs.py /path/to/documents

# With options
python combine_pdfs.py /path/to/documents -o output.pdf --check --verbose

# Verify mode
python combine_pdfs.py verify combined.pdf /path/to/source/directory
```

## Feature Comparison

| Feature | Original | Enhanced |
|---------|----------|----------|
| Combine PDFs/DOCs/DOCX | ✅ | ✅ |
| OCR Processing | ✅ | ✅ |
| File Verification | ✅ | ✅ |
| Progress Bars | ❌ | ✅ |
| Parallel Processing | ❌ | ✅ |
| File Filtering | ❌ | ✅ |
| Custom Ordering | ❌ | ✅ |
| Bookmarks/TOC | ❌ | ✅ |
| Password Protection | ❌ | ✅ |
| Configuration Files | ❌ | ✅ |
| Enhanced Error Handling | ❌ | ✅ |
| Detailed Statistics | ❌ | ✅ |

## How It Works

1. **File Discovery**: Scans directory for matching files based on patterns
2. **Parallel Processing**: Converts multiple documents simultaneously
3. **Conversion**: Converts DOC/DOCX files to PDF format using LibreOffice or docx2pdf
4. **OCR Processing**: Automatically detects and OCRs image-based PDFs
5. **Merging**: Combines all processed PDFs with bookmarks and metadata
6. **Security**: Applies password protection if configured
7. **Verification**: Provides detailed success/failure statistics

## Performance

The enhanced version offers significant performance improvements:

- **Parallel processing**: 2-4x faster on multi-core systems
- **Smart error handling**: Continues processing even if some files fail
- **Progress tracking**: Real-time updates on processing status
- **Memory efficiency**: Processes files in batches to manage memory usage

Example benchmark (292 DOCX files):
- Original version: ~5-6 minutes sequential processing
- Enhanced version: ~2-3 minutes with 4 parallel workers

## Troubleshooting

### OCR not working
- Ensure `ocrmypdf` is installed and in PATH
- Check that Tesseract and Ghostscript are installed
- Run `python combine_pdfs_enhanced.py check-deps` to verify

### DOC/DOCX conversion failing
- **Linux**: Install LibreOffice: `sudo apt-get install libreoffice`
- **Windows/macOS**: Ensure docx2pdf is installed: `pip install docx2pdf`
- Some corrupted files may fail - check the detailed error logs

### Performance Issues
- Reduce `max_workers` if system becomes unresponsive
- Increase `compression_level` to reduce output file size
- Use `--no-ocr` flag if OCR is not needed

### Memory Issues
- Process smaller batches of files
- Reduce parallel workers
- Check available disk space in temp directory

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

```bash
git clone git@github.com:JeremyWhittaker/pdf_combiner.git
cd pdf_combiner
pip install -r requirements.txt
python combine_pdfs_enhanced.py check-deps
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Jeremy Whittaker

## Acknowledgments

- [PyPDF2](https://github.com/py-pdf/pypdf2) for PDF manipulation
- [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) for OCR functionality
- [python-docx](https://github.com/python-openxml/python-docx) for DOCX handling
- [docx2pdf](https://github.com/AlJohri/docx2pdf) for DOC/DOCX conversion
- [Click](https://click.palletsprojects.com/) for the enhanced CLI interface
- [tqdm](https://github.com/tqdm/tqdm) for progress bars
- [PyYAML](https://pyyaml.org/) for configuration file support