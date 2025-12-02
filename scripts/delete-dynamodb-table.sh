#!/bin/bash
#
# Delete the DynamoDB table for the Math Quiz Alexa Skill
#
# Usage: ./delete-dynamodb-table.sh [--region REGION]
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
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "⚠️  This will delete the DynamoDB table and ALL user data!"
echo "  Region: $REGION"
echo "  Table:  $TABLE_NAME"
echo ""
read -p "Are you sure? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Check if table exists
if ! aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" &>/dev/null; then
    echo "Table '$TABLE_NAME' does not exist."
    exit 0
fi

# Delete the table
aws dynamodb delete-table --table-name "$TABLE_NAME" --region "$REGION"

echo ""
echo "✅ Table '$TABLE_NAME' deleted."
