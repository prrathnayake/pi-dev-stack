#!/bin/bash

set -e

mkdir -p logs

DOCKER_CMD="${DOCKER_CMD:-docker}"
if ! $DOCKER_CMD ps >/dev/null 2>&1; then
  if sudo docker ps >/dev/null 2>&1; then
    DOCKER_CMD="sudo docker"
  fi
fi

pkill -f 'cloudflared tunnel --url' || true

cloudflared tunnel --url http://localhost:5678 > logs/n8n.log 2>&1 &
cloudflared tunnel --url http://localhost:3000 > logs/open-webui.log 2>&1 &
cloudflared tunnel --url http://localhost:9000 > logs/portainer.log 2>&1 &

N8N_URL=""
WEBUI_URL=""
PORTAINER_URL=""

for i in {1..30}; do
  N8N_URL=$(grep -o 'https://[-0-9a-z]*\.trycloudflare\.com' logs/n8n.log | head -n 1 || true)
  WEBUI_URL=$(grep -o 'https://[-0-9a-z]*\.trycloudflare\.com' logs/open-webui.log | head -n 1 || true)
  PORTAINER_URL=$(grep -o 'https://[-0-9a-z]*\.trycloudflare\.com' logs/portainer.log | head -n 1 || true)

  if [ -n "$N8N_URL" ]; then
    break
  fi

  sleep 2
done

if [ -n "$N8N_URL" ]; then
  echo "Updating n8n webhook URL in .env..."
  if grep -q '^N8N_WEBHOOK_URL=' .env; then
    sed -i "s|^N8N_WEBHOOK_URL=.*|N8N_WEBHOOK_URL=${N8N_URL}/|" .env
  else
    echo "N8N_WEBHOOK_URL=${N8N_URL}/" >> .env
  fi

  $DOCKER_CMD compose up -d n8n
  sleep 5
fi

echo ""
echo "======================================="
echo " Public URLs"
echo "======================================="
echo "n8n:"
echo "$N8N_URL"
echo ""
echo "Open WebUI:"
echo "$WEBUI_URL"
echo ""
echo "Portainer:"
echo "$PORTAINER_URL"
echo "======================================="

echo ""
echo "For Telegram nodes, use the n8n HTTPS URL above."
echo "If Telegram still says HTTPS is required, restart n8n:"
echo "  $DOCKER_CMD compose restart n8n"
