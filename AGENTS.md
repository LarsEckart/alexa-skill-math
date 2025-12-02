Use GitHub CLI. The project is managed through GitHub issues.
Use `uv` for python development.

## Workflow
1. Pick a task from GitHub issues
2. Implement it (with tests)
3. Run formatting, linting, and tests
4. Commit and push
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

Scripts are in `scripts/` and use the `math-quiz-dev` AWS profile by default.

### Deploy Lambda code
```bash
./scripts/deploy-lambda.sh
```

### Deploy skill metadata (interaction model, manifest)
```bash
./scripts/deploy-skill-metadata.sh
```

### Deploy everything
```bash
./scripts/deploy-all.sh
```

### Check skill status
```bash
./scripts/get-skill-status.sh
```

### View Lambda logs
```bash
aws logs tail /aws/lambda/alexa-skill-math --region eu-west-1 --follow
```

### DynamoDB management
- `./scripts/create-dynamodb-table.sh` - Create table
- `./scripts/delete-dynamodb-table.sh` - Delete table (⚠️ destroys data)
- `./scripts/describe-dynamodb-table.sh` - Show table info
