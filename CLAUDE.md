# CLAUDE.md - Notebook Panopticon

## Build/Test/Lint Commands

- Setup environment: `uv venv`
- Run application: `uv run streamlit run app.py`
- Run tests: `uv run pytest`
- Run single test: `uv run pytest tests/test_file.py::test_function`
- Format code: `uv run black .`
- Lint: `uv run flake8`
- Type check: `uv run mypy .`

## Code Style Guidelines
- Follow PEP 8
- Python 3.7+ with type annotations
- Use nbformat for parsing notebooks
- Use Streamlit for UI components
