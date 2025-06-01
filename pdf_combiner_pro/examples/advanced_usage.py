#!/usr/bin/env python3
"""
Advanced usage example for PDF Combiner Pro.

This script demonstrates advanced features including:
- Custom error handling
- Progress tracking
- Batch processing
- Configuration management
"""

import logging
import sys
from pathlib import Path
from typing import List

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from pdf_combiner import PDFMerger, PDFCombinerError
from pdf_combiner.config import Config
from pdf_combiner.models import DocumentInfo, ProcessingStatus
from pdf_combiner.utils import format_file_size, check_system_dependencies


console = Console()
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def check_dependencies():
    """Check and report system dependencies."""
    console.print("[bold blue]Checking system dependencies...[/bold blue]\n")
    
    available, missing = check_system_dependencies()
    
    if missing:
        console.print("[bold red]Missing dependencies:[/bold red]")
        for dep in missing:
            console.print(f"  - {dep}")
        console.print("\nPlease install missing dependencies to enable all features.")
        return False
    
    console.print("[bold green]All dependencies are installed![/bold green]\n")
    return True


def process_directory_batch(directories: List[Path], output_dir: Path, config: Config):
    """Process multiple directories in batch."""
    merger = PDFMerger(config)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        
        main_task = progress.add_task(
            f"Processing {len(directories)} directories...",
            total=len(directories)
        )
        
        for i, directory in enumerate(directories):
            progress.update(
                main_task,
                description=f"Processing {directory.name}..."
            )
            
            try:
                # Generate output filename
                output_file = output_dir / f"{directory.name}_combined.pdf"
                
                # Check directory first
                documents = merger.check_directory(directory)
                
                if not documents:
                    console.print(f"[yellow]No documents found in {directory}[/yellow]")
                    continue
                
                # Process documents
                result = merger.merge_directory(directory, output_file)
                results.append({
                    "directory": directory,
                    "result": result,
                    "status": "success"
                })
                
                console.print(
                    f"[green]✓[/green] {directory.name}: "
                    f"{result.processed_documents} files → {output_file.name}"
                )
                
            except PDFCombinerError as e:
                results.append({
                    "directory": directory,
                    "error": e,
                    "status": "failed"
                })
                console.print(
                    f"[red]✗[/red] {directory.name}: {e.message}"
                )
            
            progress.update(main_task, advance=1)
    
    return results


def display_summary(results: List[dict]):
    """Display processing summary."""
    console.print("\n[bold blue]Processing Summary[/bold blue]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Directory", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Files", justify="right")
    table.add_column("Pages", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Time", justify="right")
    
    total_files = 0
    total_pages = 0
    total_size = 0
    
    for item in results:
        if item["status"] == "success":
            result = item["result"]
            total_files += result.processed_documents
            total_pages += result.total_pages
            
            # Calculate output file size
            if result.output_path.exists():
                size = result.output_path.stat().st_size
                total_size += size
                size_str = format_file_size(size)
            else:
                size_str = "-"
            
            table.add_row(
                item["directory"].name,
                "[green]Success",
                str(result.processed_documents),
                str(result.total_pages),
                size_str,
                f"{result.processing_time_seconds:.1f}s"
            )
        else:
            table.add_row(
                item["directory"].name,
                "[red]Failed",
                "-",
                "-",
                "-",
                "-"
            )
    
    console.print(table)
    
    # Overall summary
    console.print(f"\n[bold]Total:[/bold]")
    console.print(f"  Directories processed: {len(results)}")
    console.print(f"  Successful: {sum(1 for r in results if r['status'] == 'success')}")
    console.print(f"  Failed: {sum(1 for r in results if r['status'] == 'failed')}")
    console.print(f"  Total files merged: {total_files}")
    console.print(f"  Total pages: {total_pages}")
    console.print(f"  Total output size: {format_file_size(total_size)}")


def main():
    """Main function demonstrating advanced usage."""
    setup_logging(verbose=True)
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    # Example configuration
    config = Config(
        output={
            "add_metadata": True,
            "compression": True,
            "overwrite": True
        },
        ocr={
            "enabled": True,
            "language": "eng",
            "dpi": 300,
            "skip_text_pages": True
        },
        processing={
            "max_workers": 4,
            "fail_fast": False
        }
    )
    
    # Example: Process multiple directories
    base_dir = Path("/path/to/documents")
    directories = [
        base_dir / "invoices",
        base_dir / "contracts",
        base_dir / "reports",
    ]
    
    output_dir = Path("/path/to/output")
    
    # Filter existing directories
    existing_dirs = [d for d in directories if d.exists() and d.is_dir()]
    
    if not existing_dirs:
        console.print("[red]No valid directories found![/red]")
        return
    
    console.print(f"[bold]Processing {len(existing_dirs)} directories...[/bold]\n")
    
    # Process in batch
    results = process_directory_batch(existing_dirs, output_dir, config)
    
    # Display summary
    display_summary(results)
    
    # Save configuration for future use
    config_file = output_dir / "pdf_combiner_config.yaml"
    config.to_yaml(config_file)
    console.print(f"\n[dim]Configuration saved to {config_file}[/dim]")


if __name__ == "__main__":
    main()