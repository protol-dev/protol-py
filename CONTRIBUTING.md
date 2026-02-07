# Contributing to Protol Python SDK

Thank you for your interest in contributing to the Protol Python SDK! This guide will help you get started.

## Development Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/protol-dev/protol-py.git
   cd protol-py
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in development mode:**

   ```bash
   pip install -e ".[dev,all]"
   ```

## Running Tests

```bash
pytest tests/ -v
```

## Code Quality

We use `ruff` for linting and `mypy` for type checking:

```bash
ruff check src/ tests/
mypy src/protol/
```

## Pull Request Process

1. Fork the repository and create a feature branch from `main`.
2. Write tests for any new functionality.
3. Ensure all tests pass and there are no lint/type errors.
4. Update the `CHANGELOG.md` with your changes.
5. Submit a pull request with a clear description of the changes.

## Code Style

- All public methods and classes must have type annotations.
- All public methods must have docstrings.
- Follow existing code patterns and naming conventions.
- Keep line length ≤ 100 characters.

## Reporting Issues

Use [GitHub Issues](https://github.com/protol-dev/protol-py/issues) to report bugs or suggest features. Include:

- Python version
- SDK version
- Minimal reproduction steps
- Expected vs actual behavior

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
