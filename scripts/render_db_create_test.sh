#!/usr/bin/env bash
set -euo pipefail

RENDER_API_KEY="${RENDER_API_KEY:?Set RENDER_API_KEY}"
RENDER_OWNER_ID="${RENDER_OWNER_ID:?Set RENDER_OWNER_ID}"

curl -sS -X POST "https://api.render.com/v1/postgres" \
  -H "Authorization: Bearer ${RENDER_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @- <<EOF | python3 -m json.tool
{
  "name": "fleetopsx-db",
  "ownerId": "${RENDER_OWNER_ID}",
  "plan": "free",
  "region": "oregon",
  "version": "18",
  "databaseName": "fleetopsx",
  "databaseUser": "fleetuser"
}
EOF
