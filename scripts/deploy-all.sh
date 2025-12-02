#!/bin/bash
# Full deployment: Lambda code + Skill metadata
# Run this after making changes to deploy everything

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "  Full Deployment: Mathe Quiz Alexa Skill"
echo "=========================================="
echo ""

# Deploy Lambda first
echo "Step 1/2: Deploying Lambda..."
"$SCRIPT_DIR/deploy-lambda.sh"

echo ""
echo "Step 2/2: Deploying Skill Metadata..."
"$SCRIPT_DIR/deploy-skill-metadata.sh"

echo ""
echo "=========================================="
echo "  ✅ Full deployment complete!"
echo "=========================================="
echo ""
echo "Test with: ask dialog --locale de-DE"
echo "Or say: \"Alexa, öffne Mathe Quiz\""
