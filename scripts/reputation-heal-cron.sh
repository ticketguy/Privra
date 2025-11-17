#!/bin/bash
# Cron script to heal reputation scores daily
# Add to crontab: 0 2 * * * /path/to/reputation-heal-cron.sh

cd "$(dirname "$0")/.."

# Run healing process
docker compose exec -T postfix python3 /app/reputation_service.py heal

# Log result
echo "[$(date)] Reputation healing completed" >> /var/log/privra-reputation.log
