# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - Enhanced Version - 2025-01-06

### 🚀 Major New Features

#### Performance & User Experience
- **Progress bars** with real-time processing updates using tqdm
- **Parallel processing** for 2-4x faster document conversion
- **Smart error handling** - continues processing even if some files fail
- **Detailed statistics** and success rate reporting

#### Advanced Processing Options
- **File filtering** with include/exclude patterns (e.g., `"*.pdf"`, `"*draft*"`)
- **Custom file ordering** (name, date, size, or custom list from file)
- **Automatic bookmarks/TOC** generation for easy navigation
- **Password protection** for output PDFs
- **Compression control** for output file size optimization (levels 1-9)

#### Configuration & Management
- **YAML configuration files** for saving and reusing settings
- **Enhanced verification** with detailed analysis and statistics
- **Dependency checking** command to ensure all tools are available
- **Comprehensive logging** with optional file output
- **Click-based CLI** for better command-line interface

### 🛠️ Technical Improvements

- **Enhanced PDF Processor** class with better architecture
- **Concurrent processing** using ThreadPoolExecutor
- **Better error handling** with detailed failure reporting
- **Metadata preservation** and enhanced metadata tracking
- **Memory efficiency** improvements for large file batches
- **Timeout handling** for OCR and conversion operations

### 📝 New Commands

#### Enhanced Version (`combine_pdfs_enhanced.py`)
- `check-deps` - Check system dependencies
- `init-config` - Create sample configuration file
- `combine` - Enhanced combine with all new features
- `verify` - Enhanced verification with detailed analysis

### 🔧 Configuration Options

New configuration file support with options for:
- Worker count for parallel processing
- Compression levels
- File filtering patterns
- Sorting preferences
- Security settings
- Logging configuration

### 📊 Performance Benchmarks

Real-world testing with 292 DOCX files:
- **Original version**: ~5-6 minutes sequential processing
- **Enhanced version**: ~2-3 minutes with 4 parallel workers
- **Success rate tracking**: Detailed reporting of processed vs failed files

### 🧪 Testing

- Comprehensive testing on 292 real-world DOCX files
- Validation of all new features
- Cross-platform compatibility verification
- Error handling validation

### 📚 Documentation

- Completely rewritten README with feature comparison
- Comprehensive usage examples
- Configuration file documentation
- Troubleshooting guide
- Performance guidelines

## [1.0.0] - Initial Release

### Features

- Basic PDF, DOC, and DOCX combination
- Automatic OCR for image-based PDFs
- File count verification and warnings
- Verify mode to check combined PDFs
- Cross-platform support (Windows, macOS, Linux)
- Basic CLI interface
- Error handling for corrupted files
- Metadata tracking in combined PDFs

### Supported Operations

- Combine documents from directory
- Check mode for previewing operations
- Verify mode for validating combined PDFs
- Verbose logging option
- Custom output file specification

### System Requirements

- Python 3.8+
- OCRmyPDF for OCR functionality
- LibreOffice (Linux) or docx2pdf (Windows/macOS) for DOC/DOCX conversion
- PyPDF2 for PDF manipulation
- python-docx for DOCX handling