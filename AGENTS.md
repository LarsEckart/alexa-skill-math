Use GitHub CLI. The project is managed through GitHub issues.
Use `uv` for python development.

## Hard Rules
- Always run formatting, linting, and tests before committing:
  ```bash
  cd lambda
  uv run ruff format .
  uv run ruff check .
  uv run pytest tests/
  ```
