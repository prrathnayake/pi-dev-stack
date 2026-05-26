#!/bin/bash

set -e

mkdir -p logs state .local-state

DOCKER_CMD="${DOCKER_CMD:-docker}"
if ! $DOCKER_CMD ps >/dev/null 2>&1; then
  if sudo docker ps >/dev/null 2>&1; then
    DOCKER_CMD="sudo docker"
  fi
fi

SERVICE="${1:-core}"
ACTION="${2:-start}"
STATE_FILE="state/tunnels.env"
URL_FILE=".local-state/current-urls.txt"

service_port() {
  case "$1" in
    n8n) echo "5678" ;;
    webui|open-webui) echo "3000" ;;
    portainer) echo "9000" ;;
    dozzle|logs) echo "9999" ;;
    uptime|uptime-kuma|status) echo "3001" ;;
    homepage|home) echo "8088" ;;
    glances) echo "61208" ;;
    desktop|novnc|kicad) echo "6080" ;;
    *) echo "" ;;
  esac
}

service_key() {
  echo "$1" | tr '[:lower:]-' '[:upper:]_'
}

start_one() {
  name="$1"
  port="$(service_port "$name")"
  if [ -z "$port" ]; then
    echo "Unknown tunnel service: $name"
    exit 1
  fi

  key="$(service_key "$name")"
  log="logs/tunnel-${name}.log"

  pkill -f "cloudflared tunnel --url http://localhost:${port}" || true
  rm -f "$log"

  echo "Starting tunnel for $name on localhost:$port..."
  cloudflared tunnel --url "http://localhost:${port}" > "$log" 2>&1 &

  url=""
  for i in {1..45}; do
    url=$(grep -o 'https://[-0-9a-z]*\.trycloudflare\.com' "$log" | head -n 1 || true)
    if [ -n "$url" ]; then
      break
    fi
    sleep 2
  done

  if [ -z "$url" ]; then
    echo "Failed to create tunnel for $name. Check: $log"
    return 1
  fi

  grep -v "^${key}_URL=" "$STATE_FILE" 2>/dev/null > "${STATE_FILE}.tmp" || true
  echo "${key}_URL=${url}" >> "${STATE_FILE}.tmp"
  mv "${STATE_FILE}.tmp" "$STATE_FILE"

  if [ "$name" = "n8n" ]; then
    echo "Updating n8n webhook URL in .env..."
    if grep -q '^N8N_WEBHOOK_URL=' .env 2>/dev/null; then
      sed -i "s|^N8N_WEBHOOK_URL=.*|N8N_WEBHOOK_URL=${url}/|" .env
    else
      echo "N8N_WEBHOOK_URL=${url}/" >> .env
    fi
    $DOCKER_CMD compose up -d n8n
  fi

  echo "$name: $url"
}

start_group() {
  case "$1" in
    n8n|webui|open-webui|portainer|dozzle|logs|uptime|uptime-kuma|status|homepage|home|glances|desktop|novnc|kicad)
      start_one "$1"
      ;;
    core)
      start_one n8n
      start_one webui
      start_one portainer
      ;;
    monitoring)
      start_one homepage
      start_one uptime
      start_one dozzle
      start_one glances
      ;;
    desktop)
      start_one desktop
      ;;
    all)
      start_one n8n
      start_one webui
      start_one portainer
      start_one homepage
      start_one uptime
      start_one dozzle
      start_one glances
      start_one desktop
      ;;
    *)
      echo "Unknown tunnel group: $1"
      exit 1
      ;;
  esac
}

stop_tunnels() {
  target="${1:-all}"
  if [ "$target" = "all" ]; then
    pkill -f 'cloudflared tunnel --url' || true
    echo "Stopped all quick tunnels."
  else
    port="$(service_port "$target")"
    [ -n "$port" ] && pkill -f "cloudflared tunnel --url http://localhost:${port}" || true
    echo "Stopped tunnel: $target"
  fi
}

show_status() {
  echo "Running cloudflared quick tunnels:"
  pgrep -af 'cloudflared tunnel --url' || echo "No quick tunnels running."
}

show_urls() {
  echo "Current saved tunnel URLs:"
  if [ -f "$STATE_FILE" ]; then
    cat "$STATE_FILE" | tee "$URL_FILE"
  else
    echo "No saved tunnel URLs. Run: homelab tunnel core"
  fi
}

case "$ACTION" in
  start) start_group "$SERVICE"; show_urls ;;
  stop) stop_tunnels "$SERVICE" ;;
  restart) stop_tunnels "$SERVICE"; start_group "$SERVICE"; show_urls ;;
  status) show_status ;;
  urls) show_urls ;;
  *)
    echo "Usage: ./tunnel.sh [core|all|monitoring|n8n|webui|portainer|homepage|uptime|dozzle|glances|desktop] [start|stop|restart|status|urls]"
    exit 1
    ;;
esac
