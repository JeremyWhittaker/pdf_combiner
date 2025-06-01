# Contributing to PDF Combiner Pro

We love your input! We want to make contributing to PDF Combiner Pro as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Development Setup

1. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/pdf-combiner-pro.git
   cd pdf-combiner-pro
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Code Style

- We use [Black](https://github.com/psf/black) for Python code formatting
- We use [isort](https://github.com/PyCQA/isort) for import sorting
- We use [flake8](https://flake8.pycqa.org/) for linting
- We use [mypy](http://mypy-lang.org/) for type checking
- Maximum line length is 100 characters
- All functions and classes must have docstrings

## Testing

- Write tests for any new functionality
- Ensure all tests pass before submitting PR
- Aim for high test coverage (>90%)
- Run tests with: `pytest`
- Check coverage with: `pytest --cov=pdf_combiner`

## Pull Request Process

1. Update the README.md with details of changes to the interface, if applicable.
2. Update the CHANGELOG.md with notes on your changes.
3. The PR will be merged once you have the sign-off of at least one maintainer.

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](LICENSE) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using GitHub's [issue tracker](https://github.com/yourusername/pdf-combiner-pro/issues)

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/yourusername/pdf-combiner-pro/issues/new).

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## License

By contributing, you agree that your contributions will be licensed under its MIT License.