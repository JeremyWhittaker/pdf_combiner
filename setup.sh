#!/bin/bash

# PDF Combiner Setup Script

echo "Setting up PDF Combiner dependencies..."

# Install Python dependencies
pip install -r requirements.txt

# Check for system dependencies
if ! command -v ocrmypdf &> /dev/null; then
    echo "⚠️  ocrmypdf not found. Please install it:"
    echo "   Ubuntu/Debian: sudo apt-get install ocrmypdf"
    echo "   macOS: brew install ocrmypdf"
    echo "   Windows: pip install ocrmypdf"
fi

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! command -v libreoffice &> /dev/null; then
        echo "⚠️  LibreOffice not found (needed for DOC/DOCX conversion on Linux)"
        echo "   Install with: sudo apt-get install libreoffice"
    fi
fi

echo "✓ Setup complete! You can now run: python combine_pdfs.py --help"