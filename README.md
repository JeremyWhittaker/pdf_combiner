# PDF Combiner

A Python tool to combine multiple PDFs, DOC, and DOCX files into a single PDF with automatic OCR support for image-based PDFs.

## Features

- 📄 Combine PDFs, DOC, and DOCX files from a directory
- 🔍 Automatic OCR for image-based PDFs
- ✅ File count verification and warnings
- 🔎 Verify mode to check if combined PDF contains all source files
- 📊 Progress tracking and detailed logging
- 🖥️ Cross-platform support (Windows, macOS, Linux)

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

### Basic Usage

```bash
# Combine all PDFs, DOCs, and DOCXs in a directory
python combine_pdfs.py /path/to/documents

# Specify output file
python combine_pdfs.py /path/to/documents -o my_combined.pdf

# Combine files from current directory
python combine_pdfs.py .
```

### Check Mode

Preview what files will be processed without combining:

```bash
python combine_pdfs.py /path/to/documents --check
```

### Verify Mode

Check if a combined PDF contains all files from a source directory:

```bash
python combine_pdfs.py verify combined.pdf /path/to/source/directory
```

### Advanced Options

```bash
# Enable verbose logging
python combine_pdfs.py /path/to/documents --verbose

# Show help
python combine_pdfs.py --help
```

## How It Works

1. **File Discovery**: Scans the specified directory for PDF, DOC, and DOCX files
2. **Conversion**: Converts DOC/DOCX files to PDF format
3. **OCR Processing**: Automatically detects and OCRs image-based PDFs
4. **Merging**: Combines all processed PDFs into a single output file
5. **Verification**: Adds metadata and provides file count verification

## Features in Detail

### Automatic OCR
- Detects image-based PDFs by checking for extractable text
- Uses OCRmyPDF to add searchable text layer
- Preserves original quality while adding text

### File Count Verification
- Warns if the number of processed files doesn't match expected count
- Lists any files that failed to process
- Provides detailed error messages

### Metadata Tracking
- Stores list of source files in PDF metadata
- Enables verification of combined PDFs
- Helps track document origins

## Troubleshooting

### OCR not working
- Ensure `ocrmypdf` is installed and in PATH
- Check that Tesseract and Ghostscript are installed

### DOC/DOCX conversion failing on Linux
- Install LibreOffice: `sudo apt-get install libreoffice`
- Ensure `libreoffice` command is available in PATH

### Permission errors
- Ensure you have read permissions for source directory
- Ensure you have write permissions for output location

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Jeremy Whittaker

## Acknowledgments

- [PyPDF2](https://github.com/py-pdf/pypdf2) for PDF manipulation
- [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) for OCR functionality
- [python-docx](https://github.com/python-openxml/python-docx) for DOCX handling
- [docx2pdf](https://github.com/AlJohri/docx2pdf) for DOC/DOCX conversion