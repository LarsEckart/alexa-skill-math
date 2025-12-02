# Infrastructure Scripts

Simple bash scripts for managing AWS resources for the Math Quiz Alexa Skill.

## CI/CD

The project uses GitHub Actions for continuous deployment. On every push to `main` that changes files in `lambda/`:

1. **Test job**: Runs linting and unit tests
2. **Deploy job**: Packages and deploys to AWS Lambda

### Required GitHub Secrets

Configure these secrets in your repository settings (Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS access key for the `math-quiz-dev` IAM user |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for the `math-quiz-dev` IAM user |

## Local Development

### Prerequisites

- AWS CLI installed and configured
- The scripts use the `math-quiz-dev` AWS profile by default

## AWS Profile Setup

The project uses a dedicated IAM user `math-quiz-dev` with limited permissions.
If you need to recreate it:

```bash
# Create IAM user and policy (run with admin/root credentials)
aws iam create-user --user-name math-quiz-dev
# Then create and attach the MathQuizDevPolicy (see policy in repo)
aws iam create-access-key --user-name math-quiz-dev
aws configure --profile math-quiz-dev
```

## Scripts

### create-dynamodb-table.sh

Creates the DynamoDB table for storing user data.

```bash
./create-dynamodb-table.sh
```

Options:
- `--region REGION` - AWS region (default: eu-west-1)
- `--table-name NAME` - Table name (default: MathQuizUserData)

### delete-dynamodb-table.sh

Deletes the DynamoDB table. **Warning: This deletes all user data!**

```bash
./delete-dynamodb-table.sh
```

### describe-dynamodb-table.sh

Shows information about the DynamoDB table.

```bash
./describe-dynamodb-table.sh
```

## Environment Variables

You can also set these environment variables instead of using command-line options:

- `AWS_REGION` - AWS region
- `TABLE_NAME` - DynamoDB table name

## Table Schema

The table uses a single-table design:

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | String (PK) | User ID from Alexa |
| `attributes` | Map | User profile, SRS stats, session stats |

Billing mode is set to **on-demand** (pay-per-request), which is cost-effective for low-to-moderate traffic.
