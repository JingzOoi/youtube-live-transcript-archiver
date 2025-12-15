# AGENTS.md - Development Guidelines

## Commands
- **Run tests**: `python -m unittest tests.py`
- **Run single test**: `python -m unittest tests.TestClassName.test_method_name`
- **Install dependencies**: `uv sync` or `pip install -r requirements.txt`
- **Run main**: `python main.py`

## Code Style Guidelines

### Imports & Structure
- Use `# -*- coding: utf-8 -*-` at top of all Python files
- Group imports: stdlib, third-party, local modules
- Use absolute imports for src modules: `from src.module import function`

### Formatting & Types
- Use snake_case for variables and functions
- Use PascalCase for classes
- Add docstrings for all functions and classes
- Use type hints where beneficial (pandas DataFrames, function signatures)

### Error Handling
- Handle subprocess errors gracefully (yt-dlp failures)
- Use try/except blocks for file operations
- Log errors with descriptive messages
- Return None for expected failures (e.g., missing transcripts)

### Data Processing
- Use pandas for data manipulation
- Filter out invalid data (negative timestamps, empty text)
- Consolidate related data entries when appropriate
- Use temporary files for processing, clean up afterwards

### Testing
- Use unittest framework
- Mock external dependencies (subprocess, file I/O)
- Test with realistic fixtures
- Verify DataFrame structure and content