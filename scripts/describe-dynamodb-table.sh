#!/bin/bash
#
# Describe the DynamoDB table for the Math Quiz Alexa Skill
#
# Usage: ./describe-dynamodb-table.sh [--region REGION]
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

echo "DynamoDB Table Info"
echo "==================="
echo "  Region: $REGION"
echo "  Table:  $TABLE_NAME"
echo ""

# Check if table exists and describe it
if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" 2>/dev/null; then
    echo ""
    echo "Item count (approximate):"
    aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" \
        --query 'Table.ItemCount' --output text
else
    echo "❌ Table '$TABLE_NAME' does not exist in region '$REGION'."
    exit 1
fi
