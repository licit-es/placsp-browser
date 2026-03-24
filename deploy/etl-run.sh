#!/bin/sh
# Wrapper for ETL jobs: runs the module, measures duration, and notifies Discord.
# Usage: etl-run.sh <label> <python_module>
#
# Requires DISCORD_WEBHOOK_URL env var (passed through docker-compose).
set -u

LABEL="$1"
MODULE="$2"
LOG="/var/log/etl/${LABEL}.log"
START=$(date +%s)

cd /app && PYTHONPATH=src /usr/local/bin/uv run python -m "$MODULE" >> "$LOG" 2>&1
EXIT=$?

DURATION=$(( $(date +%s) - START ))
MINS=$(( DURATION / 60 ))
SECS=$(( DURATION % 60 ))

[ -z "${DISCORD_WEBHOOK_URL:-}" ] && exit "$EXIT"

# Parse last Result line from log
RESULT_LINE=$(grep "Result:" "$LOG" | tail -1)
PROCESSED=$(echo "$RESULT_LINE" | grep -o "'processed': [0-9]*" | grep -o '[0-9]*' || echo "?")
STALE=$(echo "$RESULT_LINE"     | grep -o "'skipped_stale': [0-9]*" | grep -o '[0-9]*' || echo "?")
FAILED=$(echo "$RESULT_LINE"    | grep -o "'failed': [0-9]*" | grep -o '[0-9]*' || echo "?")
PAGES=$(echo "$RESULT_LINE"     | grep -o "'pages': [0-9]*" | grep -o '[0-9]*' || echo "?")

if [ "$EXIT" -eq 0 ]; then
  ICON="✅"; TITLE="ETL ${LABEL} completado"; COLOR=3066993
else
  ICON="❌"; TITLE="ETL ${LABEL} FALLIDO"; COLOR=15158332
fi

jq -n \
  --arg title "${ICON} ${TITLE}" \
  --argjson color "$COLOR" \
  --arg duration "${MINS}m ${SECS}s" \
  --arg processed "$PROCESSED" \
  --arg stale "$STALE" \
  --arg failed "$FAILED" \
  --arg pages "$PAGES" \
  '{embeds: [{title: $title, color: $color, fields: [
    {name: "Duración",    value: $duration,  inline: true},
    {name: "Insertados",  value: $processed, inline: true},
    {name: "Sin cambios", value: $stale,     inline: true},
    {name: "Fallidos",    value: $failed,    inline: true},
    {name: "Páginas",     value: $pages,     inline: true}
  ]}]}' \
| curl -sf -H "Content-Type: application/json" -d @- "$DISCORD_WEBHOOK_URL" > /dev/null 2>&1 || true

exit "$EXIT"
