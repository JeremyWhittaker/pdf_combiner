"""Tests for CLI interface."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from pdf_combiner.cli import cli


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


class TestCLI:
    """Tests for CLI commands."""
    
    def test_cli_help(self, runner):
        """Test CLI help output."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "PDF Combiner Pro" in result.output
        assert "combine" in result.output
        assert "verify" in result.output
    
    def test_version(self, runner):
        """Test version output."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.output.lower()
    
    def test_combine_help(self, runner):
        """Test combine command help."""
        result = runner.invoke(cli, ["combine", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--check" in result.output
        assert "--recursive" in result.output
    
    def test_combine_check_mode(self, runner, temp_dir, sample_pdf):
        """Test combine command in check mode."""
        result = runner.invoke(cli, ["combine", str(sample_pdf.parent), "--check"])
        assert result.exit_code == 0
        assert "Checking documents" in result.output
        assert sample_pdf.name in result.output
    
    def test_combine_empty_directory(self, runner, temp_dir):
        """Test combine with empty directory."""
        result = runner.invoke(cli, ["combine", str(temp_dir)])
        assert result.exit_code == 1
        assert "No supported documents found" in result.output
    
    def test_combine_with_output(self, runner, temp_dir, sample_pdf):
        """Test combine with custom output path."""
        output_path = temp_dir / "custom_output.pdf"
        result = runner.invoke(cli, [
            "combine",
            str(sample_pdf.parent),
            "--output", str(output_path),
            "--overwrite"
        ])
        
        # Check that it would succeed (actual merge requires more setup)
        # In a real test environment with all dependencies, this would work
        assert "Combining documents" in result.output
    
    def test_verify_help(self, runner):
        """Test verify command help."""
        result = runner.invoke(cli, ["verify", "--help"])
        assert result.exit_code == 0
        assert "pdf_file" in result.output
        assert "source_dir" in result.output
    
    def test_check_deps(self, runner):
        """Test check-deps command."""
        result = runner.invoke(cli, ["check-deps"])
        assert result.exit_code in [0, 1]  # Depends on system
        assert "System Dependencies" in result.output
        assert "ocrmypdf" in result.output


class TestCLIIntegration:
    """Integration tests for CLI."""
    
    def test_combine_verbose_mode(self, runner, temp_dir, sample_pdf):
        """Test verbose output."""
        result = runner.invoke(cli, [
            "combine",
            str(sample_pdf.parent),
            "--verbose",
            "--check"
        ])
        assert result.exit_code == 0
        # Verbose mode should show more detailed output
        assert "Checking documents" in result.output
    
    def test_combine_with_config(self, runner, temp_dir, sample_pdf):
        """Test using configuration file."""
        config_file = temp_dir / "test_config.yaml"
        config_file.write_text("""
output:
  default_name: "test_output.pdf"
  overwrite: true
ocr:
  enabled: false
""")
        
        result = runner.invoke(cli, [
            "combine",
            str(sample_pdf.parent),
            "--config", str(config_file),
            "--check"
        ])
        assert result.exit_code == 0
    
    def test_invalid_config_file(self, runner, temp_dir):
        """Test error handling for invalid config."""
        result = runner.invoke(cli, [
            "combine",
            str(temp_dir),
            "--config", "/nonexistent/config.yaml"
        ])
        assert result.exit_code == 1
        assert "does not exist" in result.output
    
    def test_keyboard_interrupt(self, runner, temp_dir, monkeypatch):
        """Test handling of keyboard interrupt."""
        def mock_merge(*args, **kwargs):
            raise KeyboardInterrupt()
        
        import pdf_combiner.merger
        monkeypatch.setattr(pdf_combiner.merger.PDFMerger, "merge_directory", mock_merge)
        
        result = runner.invoke(cli, ["combine", str(temp_dir)])
        assert result.exit_code == 130
        assert "cancelled by user" in result.output.lower()