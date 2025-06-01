"""Command-line interface for PDF Combiner."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table

from pdf_combiner import __version__
from pdf_combiner.config import Config, load_config
from pdf_combiner.exceptions import PDFCombinerError
from pdf_combiner.merger import PDFMerger
from pdf_combiner.models import ProcessingOptions, ProcessingStatus
from pdf_combiner.utils import format_file_size, check_system_dependencies
from pdf_combiner.validators import validate_config_file, validate_ocr_language


console = Console()
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, log_file: Optional[Path] = None) -> None:
    """Configure logging with rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    
    handlers = [
        RichHandler(
            console=console,
            show_time=True,
            show_path=verbose,
            markup=True,
            rich_tracebacks=True,
        )
    ]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=handlers,
        force=True
    )


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="pdf-combiner")
def cli(ctx):
    """PDF Combiner Pro - Merge PDFs, DOCs, and DOCX files with OCR support."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=Path.cwd() / "combined.pdf",
    help="Output PDF file path"
)
@click.option(
    "--check",
    is_flag=True,
    help="Only check files without combining"
)
@click.option(
    "--recursive", "-r",
    is_flag=True,
    help="Scan subdirectories recursively"
)
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Configuration file path"
)
@click.option(
    "--skip-ocr",
    is_flag=True,
    help="Skip OCR processing"
)
@click.option(
    "--ocr-language",
    default="eng",
    help="OCR language (e.g., eng, deu, fra)"
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing output file"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
def combine(
    directory: Path,
    output: Path,
    check: bool,
    recursive: bool,
    config: Optional[Path],
    skip_ocr: bool,
    ocr_language: str,
    overwrite: bool,
    verbose: bool
):
    """Combine documents from a directory into a single PDF."""
    setup_logging(verbose)
    
    try:
        # Load configuration
        if config:
            validate_config_file(config)
            cfg = Config.from_yaml(config)
        else:
            cfg = load_config()
        
        # Override config with CLI options
        if skip_ocr:
            cfg.ocr.enabled = False
        if ocr_language != "eng":
            validate_ocr_language(ocr_language)
            cfg.ocr.language = ocr_language
        if overwrite:
            cfg.output.overwrite = True
        
        # Initialize merger
        merger = PDFMerger(cfg)
        
        if check:
            # Check mode
            console.print(f"\n[bold blue]Checking documents in {directory}[/bold blue]\n")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Scanning documents...", total=None)
                documents = merger.check_directory(directory, recursive)
                progress.update(task, completed=True)
            
            # Display results
            table = Table(title=f"Document Check Results ({len(documents)} files)")
            table.add_column("File", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Size", style="green")
            table.add_column("Pages", style="yellow")
            table.add_column("Has Text", style="blue")
            table.add_column("Status", style="red")
            
            for doc in documents:
                status = "✓ OK" if not doc.error_message else f"✗ {doc.error_message}"
                has_text = "Yes" if doc.has_text else "No" if doc.has_text is not None else "-"
                pages = str(doc.page_count) if doc.page_count else "-"
                
                table.add_row(
                    doc.name,
                    doc.type.value.upper(),
                    format_file_size(doc.size_bytes),
                    pages,
                    has_text,
                    status
                )
            
            console.print(table)
            
            # Summary
            console.print(f"\n[bold]Summary:[/bold]")
            console.print(f"  Total files: {len(documents)}")
            console.print(f"  Valid files: {sum(1 for d in documents if not d.error_message)}")
            console.print(f"  Need OCR: {sum(1 for d in documents if d.has_text is False)}")
            
        else:
            # Merge mode
            console.print(f"\n[bold blue]Combining documents from {directory}[/bold blue]\n")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                # Create a task
                task = progress.add_task("Processing documents...", total=100)
                
                # Merge documents
                result = merger.merge_directory(directory, output, recursive)
                
                # Update progress
                progress.update(task, completed=100)
            
            # Display results
            if result.has_errors:
                console.print(f"\n[bold yellow]⚠️  Completed with errors[/bold yellow]")
            else:
                console.print(f"\n[bold green]✓ Successfully combined documents[/bold green]")
            
            console.print(f"\nOutput: [cyan]{result.output_path}[/cyan]")
            console.print(f"Total pages: [yellow]{result.total_pages}[/yellow]")
            console.print(f"Processing time: [blue]{result.processing_time_seconds:.2f}s[/blue]")
            
            # Summary table
            table = Table(title="Processing Summary")
            table.add_column("Status", style="bold")
            table.add_column("Count", style="bold")
            
            table.add_row("[green]Processed", str(result.processed_documents))
            if result.skipped_documents > 0:
                table.add_row("[yellow]Skipped", str(result.skipped_documents))
            if result.failed_documents > 0:
                table.add_row("[red]Failed", str(result.failed_documents))
            table.add_row("Total", str(result.total_documents))
            
            console.print(table)
            
            # Show errors if any
            if result.failed_documents > 0:
                console.print("\n[bold red]Failed files:[/bold red]")
                for doc in result.documents:
                    if doc.status == ProcessingStatus.FAILED:
                        console.print(f"  - {doc.name}: {doc.error_message}")
            
            # Show warnings if any
            if result.warnings:
                console.print("\n[bold yellow]Warnings:[/bold yellow]")
                for warning in result.warnings:
                    console.print(f"  - {warning}")
    
    except PDFCombinerError as e:
        console.print(f"\n[bold red]Error:[/bold red] {e.message}")
        if e.details:
            for key, value in e.details.items():
                console.print(f"  {key}: {value}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
        logger.exception("Unexpected error occurred")
        sys.exit(1)


@cli.command()
@click.argument("pdf_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("source_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
def verify(pdf_file: Path, source_dir: Path, verbose: bool):
    """Verify that a combined PDF contains all files from source directory."""
    setup_logging(verbose)
    
    try:
        console.print(f"\n[bold blue]Verifying {pdf_file}[/bold blue]\n")
        
        # Initialize merger with default config
        merger = PDFMerger()
        
        # Verify PDF
        with console.status("Analyzing PDF..."):
            result = merger.verify_merged_pdf(pdf_file, source_dir)
        
        # Display results
        console.print(f"PDF: [cyan]{result.pdf_path}[/cyan]")
        console.print(f"Source directory: [cyan]{result.source_dir}[/cyan]")
        console.print(f"Pages: [yellow]{result.page_count}[/yellow]")
        console.print(f"Match percentage: [blue]{result.match_percentage:.1f}%[/blue]\n")
        
        # Create comparison table
        table = Table(title="File Comparison")
        table.add_column("Category", style="bold")
        table.add_column("Count", style="bold")
        table.add_column("Files")
        
        table.add_row(
            "[green]Expected",
            str(len(result.expected_files)),
            ", ".join(result.expected_files[:5]) + ("..." if len(result.expected_files) > 5 else "")
        )
        
        if result.found_files:
            table.add_row(
                "[blue]Found",
                str(len(result.found_files)),
                ", ".join(result.found_files[:5]) + ("..." if len(result.found_files) > 5 else "")
            )
        
        if result.missing_files:
            table.add_row(
                "[red]Missing",
                str(len(result.missing_files)),
                ", ".join(result.missing_files[:5]) + ("..." if len(result.missing_files) > 5 else "")
            )
        
        if result.extra_files:
            table.add_row(
                "[yellow]Extra",
                str(len(result.extra_files)),
                ", ".join(result.extra_files[:5]) + ("..." if len(result.extra_files) > 5 else "")
            )
        
        console.print(table)
        
        # Final verdict
        if result.is_valid:
            console.print("\n[bold green]✓ VERIFIED:[/bold green] All expected files are in the PDF")
        else:
            console.print("\n[bold red]✗ MISMATCH:[/bold red] PDF does not contain all expected files")
            
            if result.missing_files:
                console.print(f"\n[red]Missing {len(result.missing_files)} files from directory[/red]")
            if result.extra_files:
                console.print(f"\n[yellow]Found {len(result.extra_files)} unexpected files in PDF[/yellow]")
    
    except PDFCombinerError as e:
        console.print(f"\n[bold red]Error:[/bold red] {e.message}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
        logger.exception("Unexpected error occurred")
        sys.exit(1)


@cli.command()
def check_deps():
    """Check system dependencies."""
    console.print("\n[bold blue]Checking system dependencies...[/bold blue]\n")
    
    available, missing = check_system_dependencies()
    
    # Display results
    table = Table(title="System Dependencies")
    table.add_column("Dependency", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Notes")
    
    all_deps = set(available + missing)
    
    for dep in sorted(all_deps):
        if dep in available:
            status = "[green]✓ Installed"
            notes = ""
        else:
            status = "[red]✗ Missing"
            from pdf_combiner.utils import get_dependency_install_command
            notes = get_dependency_install_command(dep)
        
        table.add_row(dep, status, notes)
    
    console.print(table)
    
    if missing:
        console.print(f"\n[bold red]Missing {len(missing)} dependencies[/bold red]")
        console.print("Install the missing dependencies to enable all features.")
        sys.exit(1)
    else:
        console.print("\n[bold green]All dependencies are installed![/bold green]")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()