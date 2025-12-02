#!/bin/bash
# Deploy Lambda function code to AWS
# Uses the math-quiz-dev AWS profile and uv for dependency management

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LAMBDA_DIR="$PROJECT_ROOT/lambda"

AWS_PROFILE="${AWS_PROFILE:-math-quiz-dev}"
AWS_REGION="${AWS_REGION:-eu-west-1}"
FUNCTION_NAME="alexa-skill-math"

echo "Deploying Lambda function: $FUNCTION_NAME"
echo "Using AWS profile: $AWS_PROFILE"
echo "Region: $AWS_REGION"
echo ""

cd "$LAMBDA_DIR"

echo "Creating deployment package..."
TEMP_DIR=$(mktemp -d)
ZIP_FILE="$TEMP_DIR/lambda.zip"
PACKAGE_DIR="$TEMP_DIR/package"
mkdir -p "$PACKAGE_DIR"

# Export dependencies using uv (production only, no dev deps)
echo "Installing dependencies..."
uv export --no-dev --no-hashes --frozen | uv pip install \
    --quiet \
    --python 3.14 \
    --target "$PACKAGE_DIR" \
    --requirement -

# Copy lambda code
echo "Copying application code..."
cp lambda_function.py "$PACKAGE_DIR/"
cp -r alexa "$PACKAGE_DIR/" 2>/dev/null || true

# Create zip
echo "Creating zip file..."
cd "$PACKAGE_DIR"
zip -q -r "$ZIP_FILE" .

ZIP_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo "Package size: $ZIP_SIZE"

echo "Uploading to AWS Lambda..."
RESULT=$(aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --output json)

echo "$RESULT" | grep -E '"FunctionArn"|"LastModified"|"CodeSize"' | head -5

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo "✅ Lambda deployed successfully!"
