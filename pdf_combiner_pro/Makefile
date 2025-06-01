.PHONY: help install install-dev test test-cov lint format type-check clean build docs

help:
	@echo "Available commands:"
	@echo "  make install       Install package in production mode"
	@echo "  make install-dev   Install package in development mode with all dependencies"
	@echo "  make test          Run tests"
	@echo "  make test-cov      Run tests with coverage report"
	@echo "  make lint          Run linting checks"
	@echo "  make format        Format code with black and isort"
	@echo "  make type-check    Run type checking with mypy"
	@echo "  make clean         Clean build artifacts"
	@echo "  make build         Build distribution packages"
	@echo "  make docs          Build documentation"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest -v

test-cov:
	pytest -v --cov=pdf_combiner --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

lint:
	flake8 pdf_combiner tests
	black --check pdf_combiner tests
	isort --check-only pdf_combiner tests

format:
	black pdf_combiner tests
	isort pdf_combiner tests

type-check:
	mypy pdf_combiner

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

docs:
	@echo "Documentation can be built with Sphinx if needed"
	@echo "Install sphinx and sphinx-rtd-theme, then run:"
	@echo "  cd docs && make html"

# Development workflow shortcuts
check: lint type-check test

pre-commit:
	pre-commit run --all-files

# Installation shortcuts for different platforms
install-deps-ubuntu:
	sudo apt-get update
	sudo apt-get install -y tesseract-ocr ghostscript libreoffice

install-deps-macos:
	brew install tesseract ghostscript

install-deps-windows:
	@echo "Please install the following manually:"
	@echo "1. Tesseract: https://github.com/UB-Mannheim/tesseract/wiki"
	@echo "2. Ghostscript: https://www.ghostscript.com/download/gsdnld.html"