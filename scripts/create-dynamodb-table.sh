#!/bin/bash
#
# Create the DynamoDB table for the Math Quiz Alexa Skill
#
# Usage: ./create-dynamodb-table.sh [--region REGION]
#
# Environment variables:
#   AWS_REGION - AWS region (default: eu-west-1)
#   TABLE_NAME - DynamoDB table name (default: MathQuizUserData)
#

set -e

# Configuration
AWS_PROFILE="${AWS_PROFILE:-math-quiz-dev}"
REGION="${AWS_REGION:-eu-west-1}"
TABLE_NAME="${TABLE_NAME:-MathQuizUserData}"

export AWS_PROFILE

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            REGION="$2"
            shift 2
            ;;
        --table-name)
            TABLE_NAME="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--region REGION] [--table-name TABLE_NAME]"
            echo ""
            echo "Options:"
            echo "  --region      AWS region (default: eu-west-1)"
            echo "  --table-name  DynamoDB table name (default: MathQuizUserData)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Creating DynamoDB table..."
echo "  Region: $REGION"
echo "  Table:  $TABLE_NAME"
echo ""

# Check if table already exists
if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" &>/dev/null; then
    echo "Table '$TABLE_NAME' already exists."
    exit 0
fi

# Create the table
aws dynamodb create-table \
    --table-name "$TABLE_NAME" \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$REGION"

echo ""
echo "Waiting for table to become active..."
aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$REGION"

echo ""
echo "✅ Table '$TABLE_NAME' created successfully!"
