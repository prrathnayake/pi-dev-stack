#!/bin/bash

mkdir -p logs

pkill -f 'cloudflared tunnel --url' || true

cloudflared tunnel --url http://localhost:5678 > logs/n8n.log 2>&1 &
cloudflared tunnel --url http://localhost:3000 > logs/open-webui.log 2>&1 &
cloudflared tunnel --url http://localhost:9000 > logs/portainer.log 2>&1 &

sleep 10

N8N_URL=$(grep -o 'https://[-0-9a-z]*\.trycloudflare\.com' logs/n8n.log | head -n 1)
WEBUI_URL=$(grep -o 'https://[-0-9a-z]*\.trycloudflare\.com' logs/open-webui.log | head -n 1)
PORTAINER_URL=$(grep -o 'https://[-0-9a-z]*\.trycloudflare\.com' logs/portainer.log | head -n 1)

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
