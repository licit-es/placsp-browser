#!/bin/sh
# Daily API stats → Discord embed.
# Usage: stats-daily.sh
#
# Requires DATABASE_URL and DISCORD_WEBHOOK_URL env vars.
set -u

[ -z "${DISCORD_WEBHOOK_URL:-}" ] && { echo "DISCORD_WEBHOOK_URL not set, skipping"; exit 0; }

cd /app || exit 1
STATS=$(PYTHONPATH=src /usr/local/bin/uv run python -m api.stats 2>/dev/null)
EXIT=$?

if [ "$EXIT" -ne 0 ] || [ -z "$STATS" ]; then
  jq -n '{embeds: [{title: "❌ Stats diarias fallidas", color: 15158332, description: "El script de stats no pudo conectar a la BD o falló."}]}' \
  | curl -sf -H "Content-Type: application/json" -d @- "$DISCORD_WEBHOOK_URL" > /dev/null 2>&1 || true
  exit "$EXIT"
fi

# Extract values with jq
TOTAL=$(echo "$STATS"       | jq -r '.total_requests')
ACTIVE=$(echo "$STATS"      | jq -r '.active_users')
MEAN_PER=$(echo "$STATS"    | jq -r '.mean_per_user')
LATENCY=$(echo "$STATS"     | jq -r '.mean_latency_ms')
P95=$(echo "$STATS"         | jq -r '.p95_latency_ms')
ERRORS_4XX=$(echo "$STATS"  | jq -r '.client_errors')
ERRORS_5XX=$(echo "$STATS"  | jq -r '.server_errors')
ERR_RATE=$(echo "$STATS"    | jq -r '.error_rate_pct')
AUTH_FAIL=$(echo "$STATS"   | jq -r '.auth_failures')
NEW_USERS=$(echo "$STATS"   | jq -r '.new_users_24h')
TOTAL_USERS=$(echo "$STATS" | jq -r '.total_users')
PEAK=$(echo "$STATS"        | jq -r '.peak_hour')
PEAK_HITS=$(echo "$STATS"   | jq -r '.peak_hour_hits')

# Top endpoints as a compact list
TOP_EP=$(echo "$STATS" | jq -r '.top_endpoints[] | "`\(.hits)` \(.path)"' | head -5)
[ -z "$TOP_EP" ] && TOP_EP="-"

# Top users
TOP_USR=$(echo "$STATS" | jq -r '.top_users[] | "`\(.hits)` \(.email)"' | head -3)
[ -z "$TOP_USR" ] && TOP_USR="-"

# Color: green if no 5xx, yellow if some, red if many
if [ "$ERRORS_5XX" -eq 0 ]; then
  COLOR=3066993   # green
elif [ "$ERRORS_5XX" -lt 10 ]; then
  COLOR=16776960  # yellow
else
  COLOR=15158332  # red
fi

DATE=$(date -u +%Y-%m-%d)

jq -n \
  --arg date "$DATE" \
  --argjson color "$COLOR" \
  --arg total "$TOTAL" \
  --arg active "$ACTIVE" \
  --arg mean "$MEAN_PER" \
  --arg latency "${LATENCY}ms" \
  --arg p95 "${P95}ms" \
  --arg errors "4xx: ${ERRORS_4XX}  ·  5xx: ${ERRORS_5XX}  (${ERR_RATE}%)" \
  --arg auth_fail "$AUTH_FAIL" \
  --arg users "${TOTAL_USERS} total  ·  ${NEW_USERS} nuevos" \
  --arg peak "${PEAK} (${PEAK_HITS} req)" \
  --arg top_ep "$TOP_EP" \
  --arg top_usr "$TOP_USR" \
  '{embeds: [{
    title: ("📊 Stats API — " + $date),
    color: $color,
    fields: [
      {name: "Peticiones (24h)",     value: $total,     inline: true},
      {name: "Usuarios activos",     value: $active,    inline: true},
      {name: "Media/usuario",        value: $mean,      inline: true},
      {name: "Latencia media",       value: $latency,   inline: true},
      {name: "Latencia p95",         value: $p95,       inline: true},
      {name: "Hora pico",            value: $peak,      inline: true},
      {name: "Errores",              value: $errors,     inline: false},
      {name: "Auth rechazados",      value: $auth_fail, inline: true},
      {name: "Usuarios",             value: $users,     inline: true},
      {name: "Top endpoints",        value: $top_ep,    inline: false},
      {name: "Top usuarios",         value: $top_usr,   inline: false}
    ]
  }]}' \
| curl -sf -H "Content-Type: application/json" -d @- "$DISCORD_WEBHOOK_URL" > /dev/null 2>&1 || true
