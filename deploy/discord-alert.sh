#!/bin/sh
# Send a failure alert to Discord. Called by crontab on ETL errors.
# Requires DISCORD_WEBHOOK_URL env var (passed through docker-compose).
LABEL="${1:-unknown}"
[ -z "${DISCORD_WEBHOOK_URL:-}" ] && exit 0
python3 -c "
import urllib.request, json, os
data = json.dumps({'content': '❌ **${LABEL}** failed at $(date -Iseconds)'}).encode()
req = urllib.request.Request(os.environ['DISCORD_WEBHOOK_URL'],
    data=data, headers={'Content-Type': 'application/json'})
urllib.request.urlopen(req, timeout=10)
" 2>/dev/null || true
