#!/bin/bash
# Check the current status of the Alexa skill

SKILL_ID="amzn1.ask.skill.1c020f8e-1f5f-4262-98fc-0cf207884f3d"

echo "Skill ID: $SKILL_ID"
echo ""
echo "Skill Status:"
ask smapi get-skill-status --skill-id "$SKILL_ID"
