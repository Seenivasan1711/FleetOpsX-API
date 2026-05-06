#!/usr/bin/env bash
# Renew Render free-tier PostgreSQL:
#   1. Dump the expiring DB
#   2. Delete it on Render
#   3. Create a fresh DB with the same name
#   4. Restore the dump
#
# Usage:
#   export RENDER_API_KEY="rnd_xxxx"
#   export RENDER_OWNER_ID="usr_xxxx"          # or "tea_xxxx" for a team
#   export OLD_DB_SERVICE_ID="dpg_xxxx"        # Render database service ID
#   export NEW_DB_NAME="fleetopsx-db"          # name for the new database
#   ./scripts/render_db_renew.sh

set -euo pipefail

# ── config ────────────────────────────────────────────────────────────────────
RENDER_API_KEY="${RENDER_API_KEY:?Set RENDER_API_KEY}"
RENDER_OWNER_ID="${RENDER_OWNER_ID:?Set RENDER_OWNER_ID}"
OLD_DB_SERVICE_ID="${OLD_DB_SERVICE_ID:?Set OLD_DB_SERVICE_ID}"
# OLD_DB_CONN: paste the External Connection String from the Render dashboard.
# The Render API does not expose it — you must set this manually.
OLD_DB_CONN="${OLD_DB_CONN:?Set OLD_DB_CONN — copy the External Connection String from Render dashboard → your DB → Connect}"
NEW_DB_NAME="${NEW_DB_NAME:-fleetopsx-db}"
REGION="${RENDER_REGION:-oregon}"          # oregon | frankfurt | singapore | ohio
PLAN="${RENDER_DB_PLAN:-free}"             # free | starter | standard | pro …
PG_VERSION="${RENDER_PG_VERSION:-18}"      # 14 | 15 | 16 | 18 — match your Render dashboard version
DUMP_FILE="${DUMP_FILE:-/tmp/fleetopsx_$(date +%Y%m%d_%H%M%S).dump}"
API="https://api.render.com/v1"

# pg_dump/pg_restore must be >= server version.
# Override if Homebrew installed a versioned copy, e.g.:
#   export PG_BIN=/opt/homebrew/opt/postgresql@18/bin
PG_BIN="${PG_BIN:-}"
PG_DUMP="${PG_BIN:+${PG_BIN}/}pg_dump"
PG_RESTORE="${PG_BIN:+${PG_BIN}/}pg_restore"

# ── helpers ───────────────────────────────────────────────────────────────────

# render_api: exits on HTTP error and prints the response body for debugging.
render_api() {
  local response http_code
  response=$(curl -sS -w "\n__HTTP_CODE__:%{http_code}" \
    -H "Authorization: Bearer ${RENDER_API_KEY}" \
    -H "Content-Type: application/json" "$@")
  http_code=$(echo "$response" | grep -o '__HTTP_CODE__:[0-9]*' | cut -d: -f2)
  body=$(echo "$response" | sed 's/__HTTP_CODE__:[0-9]*$//')
  if [[ "$http_code" -ge 400 ]]; then
    echo "ERROR: Render API returned HTTP ${http_code}" >&2
    echo "Response: ${body}" >&2
    exit 1
  fi
  echo "$body"
}

wait_for_db() {
  local svc_id="$1"
  echo "Waiting for new database to become available..."
  for i in $(seq 1 40); do
    status=$(render_api "${API}/postgres/${svc_id}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || true)
    echo "  [${i}/40] status: ${status}"
    [[ "$status" == "available" ]] && return 0
    sleep 15
  done
  echo "ERROR: database did not become available in time." >&2
  exit 1
}

# ── 1. use provided connection string ────────────────────────────────────────
OLD_CONN="${OLD_DB_CONN}"
echo "==> Using connection string for ${OLD_DB_SERVICE_ID}."

# ── 2. dump ──────────────────────────────────────────────────────────────────
echo "==> Dumping database to ${DUMP_FILE} ..."
"${PG_DUMP}" --format=custom --no-acl --no-owner -d "${OLD_CONN}" -f "${DUMP_FILE}"
echo "    Dump complete ($(du -sh "${DUMP_FILE}" | cut -f1))."

# ── 3. delete old database ───────────────────────────────────────────────────
echo "==> Deleting old database ${OLD_DB_SERVICE_ID} ..."
render_api -X DELETE "${API}/postgres/${OLD_DB_SERVICE_ID}"
echo "    Deleted."

# ── 4. create new database ───────────────────────────────────────────────────
echo "==> Creating new database '${NEW_DB_NAME}' ..."
NEW_DB_JSON=$(render_api -X POST "${API}/postgres" -d "{
  \"name\": \"${NEW_DB_NAME}\",
  \"ownerId\": \"${RENDER_OWNER_ID}\",
  \"plan\": \"${PLAN}\",
  \"region\": \"${REGION}\",
  \"version\": \"${PG_VERSION}\",
  \"databaseName\": \"fleetopsx\",
  \"databaseUser\": \"fleetuser\"
}")
NEW_DB_ID=$(echo "$NEW_DB_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "    New DB service ID: ${NEW_DB_ID}"

# ── 5. wait until ready ───────────────────────────────────────────────────────
wait_for_db "${NEW_DB_ID}"

# ── 6. fetch new connection string ────────────────────────────────────────────
NEW_CONN=$(render_api "${API}/postgres/${NEW_DB_ID}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('connectionInfo', {}).get('externalConnectionString', ''))")

# ── 7. restore ────────────────────────────────────────────────────────────────
echo "==> Restoring dump into new database ..."
"${PG_RESTORE}" --no-acl --no-owner -d "${NEW_CONN}" "${DUMP_FILE}"
echo "    Restore complete."

# ── 8. print new DATABASE_URL ─────────────────────────────────────────────────
echo ""
echo "======================================================"
echo " Done! Update your Render service env var:"
echo "   DATABASE_URL=${NEW_CONN}"
echo " New DB service ID: ${NEW_DB_ID}"
echo " Dump saved at:     ${DUMP_FILE}"
echo "======================================================"
