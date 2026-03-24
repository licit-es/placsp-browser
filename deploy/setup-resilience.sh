#!/bin/bash
# One-time setup for monitoring and resilience on the Hetzner server.
# Run as your deploy user (adf): ./deploy/setup-resilience.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_DIR="$PROJECT_DIR/deploy"

echo "==> Ensuring Docker starts on boot"
sudo systemctl enable docker

echo "==> Installing watchdog cron (every 5 min)"
echo "*/5 * * * * adf $DEPLOY_DIR/watchdog.sh" | sudo tee /etc/cron.d/placsp-watchdog > /dev/null
sudo chmod 0644 /etc/cron.d/placsp-watchdog

echo "==> Installing watchdog logrotate"
sudo tee /etc/logrotate.d/placsp-watchdog > /dev/null << 'EOF'
/var/log/placsp-watchdog.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
}
EOF

echo "==> Rebuilding etl-cron (persistent log volume)"
cd "$PROJECT_DIR"
COMPOSE="docker compose --project-directory $PROJECT_DIR -f $DEPLOY_DIR/docker-compose.yml"

$COMPOSE up -d --build etl-cron

echo "==> Running ETL feed_reader now (catch up today)"
$COMPOSE exec etl-cron /app/deploy/etl-run.sh feed_reader etl.handlers.feed_reader

echo "==> Done. Verify:"
echo "  - Watchdog: cat /etc/cron.d/placsp-watchdog"
echo "  - Docker on boot: systemctl is-enabled docker"
echo "  - ETL logs: $COMPOSE exec etl-cron ls -la /var/log/etl/"
