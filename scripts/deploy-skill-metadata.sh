#!/bin/bash
# Deploy skill metadata (interaction model, skill.json) to Alexa Developer Console
# This does NOT deploy Lambda code - use deploy-lambda.sh for that

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Deploying skill metadata..."
ask deploy --target skill-metadata

echo ""
echo "Checking skill status..."
SKILL_ID="amzn1.ask.skill.1c020f8e-1f5f-4262-98fc-0cf207884f3d"
ask smapi get-skill-status --skill-id "$SKILL_ID"

echo ""
echo "✅ Skill metadata deployed successfully!"
