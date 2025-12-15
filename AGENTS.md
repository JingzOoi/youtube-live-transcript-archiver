# AGENTS.md

## Build/Test Commands
- Run tests: `python -m unittest tests.py`
- Run single test: `python -m unittest tests.TestClassName.test_method_name`
- Install dependencies: `uv sync` or `pip install -e .`
- Run main application: `python main.py`

## Code Style Guidelines
- Use UTF-8 encoding with `# -*- coding: utf-8 -*-` header
- Import order: standard library, third-party, local modules
- Type hints required for function signatures (use `str`, `pd.DataFrame` etc.)
- Use pandas DataFrames for data processing
- Error handling: print descriptive messages, return empty DataFrames on failure
- Naming: snake_case for variables/functions, UPPER_CASE for constants
- File organization: one module per major functionality (parsers, storage, youtube_client)
- Use docstrings for all functions following Google style
- Print statements for progress tracking in long-running operations
- Temporary files handled with tempfile module
- Configuration via config.py module