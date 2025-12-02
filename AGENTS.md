Use GitHub CLI. The project is managed through GitHub issues.
Use `uv` for python development.

## Workflow
1. Pick a task from GitHub issues
2. Implement it (with tests)
3. Run formatting, linting, and tests
4. Commit and push (it gets deployed automatically then)
5. Close the issue with a summary

## Hard Rules
- Always run formatting, linting, and tests before committing:
  ```bash
  cd lambda
  uv run ruff format .
  uv run ruff check .
  uv run pytest tests/
  ```

## Deployment

Some useful scripts are in `scripts/` and use the `math-quiz-dev` AWS profile by default.
