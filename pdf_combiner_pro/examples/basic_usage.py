#!/usr/bin/env python3
"""
Basic usage example for PDF Combiner Pro.

This script demonstrates how to use the PDF Combiner Pro library
programmatically in your own Python code.
"""

from pathlib import Path

from pdf_combiner import PDFMerger
from pdf_combiner.config import Config
from pdf_combiner.models import ProcessingOptions


def main():
    """Demonstrate basic usage of PDF Combiner Pro."""
    
    # Example 1: Simple merge with default settings
    print("Example 1: Simple merge")
    print("-" * 50)
    
    merger = PDFMerger()
    
    # Specify input directory and output file
    input_dir = Path("/path/to/documents")
    output_file = Path("/path/to/combined.pdf")
    
    try:
        result = merger.merge_directory(input_dir, output_file)
        print(f"Successfully merged {result.processed_documents} documents")
        print(f"Output: {result.output_path}")
        print(f"Total pages: {result.total_pages}")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # Example 2: Custom configuration
    print("Example 2: Custom configuration")
    print("-" * 50)
    
    config = Config(
        output={"add_metadata": True, "compression": True},
        ocr={"enabled": True, "language": "eng+deu"},  # English + German
        processing={"max_workers": 2}
    )
    
    merger = PDFMerger(config)
    
    # Merge with custom options
    options = ProcessingOptions(
        enable_ocr=True,
        ocr_language="eng+fra",  # Override config with English + French
        compression=False
    )
    
    try:
        documents = merger.check_directory(input_dir)
        print(f"Found {len(documents)} documents:")
        for doc in documents[:5]:  # Show first 5
            print(f"  - {doc.name} ({doc.type.value.upper()}, {doc.size_mb:.1f} MB)")
        
        # Perform merge
        result = merger.merge_documents(documents, output_file, options)
        print(f"\nMerge completed in {result.processing_time_seconds:.2f} seconds")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # Example 3: Verification
    print("Example 3: Verify merged PDF")
    print("-" * 50)
    
    try:
        verification = merger.verify_merged_pdf(output_file, input_dir)
        print(f"Verification result: {'VALID' if verification.is_valid else 'INVALID'}")
        print(f"Match percentage: {verification.match_percentage:.1f}%")
        
        if verification.missing_files:
            print(f"Missing files: {', '.join(verification.missing_files)}")
        if verification.extra_files:
            print(f"Extra files: {', '.join(verification.extra_files)}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()