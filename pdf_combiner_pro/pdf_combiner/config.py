"""Configuration management for PDF Combiner."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s [%(levelname)s] %(message)s",
        description="Log message format"
    )
    date_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Date format for logs"
    )
    file: Optional[Path] = Field(default=None, description="Log file path")
    
    @field_validator('level')
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid logging level: {v}. Must be one of {valid_levels}")
        return v


class OutputConfig(BaseSettings):
    """Output configuration."""
    
    default_name: str = Field(default="combined.pdf", description="Default output filename")
    add_metadata: bool = Field(default=True, description="Add metadata to merged PDF")
    compression: bool = Field(default=True, description="Enable PDF compression")
    overwrite: bool = Field(default=False, description="Overwrite existing output file")


class OCRConfig(BaseSettings):
    """OCR configuration."""
    
    enabled: bool = Field(default=True, description="Enable OCR processing")
    language: str = Field(default="eng", description="OCR language")
    dpi: int = Field(default=300, ge=72, le=600, description="OCR resolution in DPI")
    skip_text_pages: bool = Field(default=True, description="Skip pages that already have text")
    timeout: int = Field(default=300, ge=60, description="OCR timeout in seconds")
    extra_args: list[str] = Field(default_factory=list, description="Extra arguments for ocrmypdf")


class ProcessingConfig(BaseSettings):
    """Processing configuration."""
    
    temp_dir: Optional[Path] = Field(default=None, description="Temporary directory for processing")
    max_workers: int = Field(default=4, ge=1, le=16, description="Maximum parallel workers")
    batch_size: int = Field(default=10, ge=1, description="Batch size for processing")
    fail_fast: bool = Field(default=False, description="Stop on first error")


class Config(BaseSettings):
    """Main configuration class."""
    
    model_config = SettingsConfigDict(
        env_prefix="PDF_COMBINER_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )
    
    output: OutputConfig = Field(default_factory=OutputConfig)
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    @classmethod
    def from_yaml(cls, path: Path) -> "Config":
        """Load configuration from YAML file.
        
        Args:
            path: Path to YAML configuration file
            
        Returns:
            Config instance
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(**data)
    
    def to_yaml(self, path: Path) -> None:
        """Save configuration to YAML file.
        
        Args:
            path: Path to save YAML configuration
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)
    
    def setup_logging(self) -> None:
        """Configure logging based on settings."""
        handlers = [logging.StreamHandler()]
        
        if self.logging.file:
            self.logging.file.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(self.logging.file))
        
        logging.basicConfig(
            level=getattr(logging, self.logging.level),
            format=self.logging.format,
            datefmt=self.logging.date_format,
            handlers=handlers,
            force=True
        )
    
    def get_temp_dir(self) -> Path:
        """Get temporary directory, creating if necessary.
        
        Returns:
            Path to temporary directory
        """
        if self.processing.temp_dir:
            self.processing.temp_dir.mkdir(parents=True, exist_ok=True)
            return self.processing.temp_dir
        
        # Use system temp directory
        import tempfile
        return Path(tempfile.gettempdir()) / "pdf_combiner"


def get_default_config() -> Config:
    """Get default configuration instance.
    
    Returns:
        Default Config instance
    """
    return Config()


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file or environment.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Config instance
    """
    if config_path and config_path.exists():
        return Config.from_yaml(config_path)
    
    # Try to load from default locations
    default_paths = [
        Path.cwd() / "pdf_combiner.yaml",
        Path.cwd() / "config.yaml",
        Path.home() / ".config" / "pdf_combiner" / "config.yaml",
    ]
    
    for path in default_paths:
        if path.exists():
            logging.info(f"Loading configuration from {path}")
            return Config.from_yaml(path)
    
    # Return default configuration
    return Config()