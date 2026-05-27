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

WEB_TUNNEL_SERVICES="n8n open-webui portainer dozzle uptime-kuma homepage glances home-assistant pihole traefik vaultwarden gitea minio syncthing filebrowser netdata prometheus grafana nodered code-server"

service_port() {
  case "$1" in
    n8n) echo "5678" ;;
    webui|open-webui) echo "3000" ;;
    portainer) echo "9000" ;;
    dozzle|logs) echo "9999" ;;
    uptime|uptime-kuma|status) echo "3001" ;;
    homepage|home) echo "8088" ;;
    glances) echo "61208" ;;
    home-assistant|ha) echo "8123" ;;
    pihole|pi-hole) echo "8081" ;;
    traefik|proxy) echo "8082" ;;
    vaultwarden|vault) echo "8083" ;;
    gitea|git) echo "3002" ;;
    minio) echo "9001" ;;
    syncthing|sync) echo "8384" ;;
    filebrowser|files) echo "8084" ;;
    netdata) echo "19999" ;;
    prometheus) echo "9090" ;;
    grafana) echo "3003" ;;
    nodered|node-red) echo "1880" ;;
    code-server|code) echo "8443" ;;
    desktop|novnc|kicad) echo "6080" ;;
    *) echo "" ;;
  esac
}

service_scheme() {
  case "$1" in
    code-server|code) echo "https" ;;
    *) echo "http" ;;
  esac
}

service_key() {
  echo "$1" | tr '[:lower:]-' '[:upper:]_'
}

service_compose_name() {
  case "$1" in
    webui) echo "open-webui" ;;
    uptime|status) echo "uptime-kuma" ;;
    home|homepage) echo "homepage" ;;
    ha) echo "home-assistant" ;;
    pi-hole) echo "pihole" ;;
    proxy) echo "traefik" ;;
    vault) echo "vaultwarden" ;;
    git) echo "gitea" ;;
    sync) echo "syncthing" ;;
    files) echo "filebrowser" ;;
    node-red) echo "nodered" ;;
    code) echo "code-server" ;;
    *) echo "$1" ;;
  esac
}

start_service_if_needed() {
  name="$(service_compose_name "$1")"
  case "$name" in
    traefik|vaultwarden|gitea|minio|syncthing|filebrowser|netdata|prometheus|grafana|nodered|code-server)
      $DOCKER_CMD compose --profile extras up -d "$name"
      ;;
    *)
      $DOCKER_CMD compose up -d "$name"
      ;;
  esac
}

start_one() {
  name="$1"
  port="$(service_port "$name")"
  scheme="$(service_scheme "$name")"
  if [ -z "$port" ]; then
    echo "Unknown tunnel service: $name"
    exit 1
  fi

  compose_name="$(service_compose_name "$name")"
  key="$(service_key "$compose_name")"
  log="logs/tunnel-${compose_name}.log"

  echo "Ensuring $compose_name is running..."
  start_service_if_needed "$name" >/dev/null 2>&1 || true

  pkill -f "cloudflared tunnel --url ${scheme}://localhost:${port}" || true
  pkill -f "cloudflared tunnel --url http://localhost:${port}" || true
  pkill -f "cloudflared tunnel --url https://localhost:${port}" || true
  rm -f "$log"

  echo "Starting tunnel for $compose_name on ${scheme}://localhost:$port..."
  cloudflared tunnel --url "${scheme}://localhost:${port}" > "$log" 2>&1 &

  url=""
  for i in {1..45}; do
    url=$(grep -o 'https://[-0-9a-z]*\.trycloudflare\.com' "$log" | head -n 1 || true)
    if [ -n "$url" ]; then
      break
    fi
    sleep 2
  done

  if [ -z "$url" ]; then
    echo "Failed to create tunnel for $compose_name. Check: $log"
    return 1
  fi

  grep -v "^${key}_URL=" "$STATE_FILE" 2>/dev/null > "${STATE_FILE}.tmp" || true
  echo "${key}_URL=${url}" >> "${STATE_FILE}.tmp"
  mv "${STATE_FILE}.tmp" "$STATE_FILE"

  if [ "$compose_name" = "n8n" ]; then
    echo "Updating n8n webhook URL in .env..."
    if grep -q '^N8N_WEBHOOK_URL=' .env 2>/dev/null; then
      sed -i "s|^N8N_WEBHOOK_URL=.*|N8N_WEBHOOK_URL=${url}/|" .env
    else
      echo "N8N_WEBHOOK_URL=${url}/" >> .env
    fi
    $DOCKER_CMD compose up -d n8n
  fi

  echo "$compose_name: $url"
}

start_group() {
  case "$1" in
    n8n|webui|open-webui|portainer|dozzle|logs|uptime|uptime-kuma|status|homepage|home|glances|home-assistant|ha|pihole|pi-hole|traefik|proxy|vaultwarden|vault|gitea|git|minio|syncthing|sync|filebrowser|files|netdata|prometheus|grafana|nodered|node-red|code-server|code|desktop|novnc|kicad)
      start_one "$1"
      ;;
    core)
      start_one n8n
      start_one open-webui
      start_one portainer
      start_one homepage
      ;;
    monitoring)
      start_one homepage
      start_one uptime-kuma
      start_one dozzle
      start_one glances
      start_one netdata
      start_one prometheus
      start_one grafana
      ;;
    automation)
      start_one n8n
      start_one nodered
      ;;
    ai)
      start_one open-webui
      ;;
    dev)
      start_one gitea
      start_one code-server
      start_one filebrowser
      ;;
    storage)
      start_one minio
      start_one syncthing
      start_one filebrowser
      ;;
    security)
      start_one pihole
      start_one vaultwarden
      ;;
    all)
      for service in $WEB_TUNNEL_SERVICES; do
        start_one "$service"
      done
      ;;
    *)
      echo "Unknown tunnel group: $1"
      echo "Available: core, monitoring, automation, ai, dev, storage, security, all"
      echo "Services: $WEB_TUNNEL_SERVICES"
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
    scheme="$(service_scheme "$target")"
    [ -n "$port" ] && pkill -f "cloudflared tunnel --url ${scheme}://localhost:${port}" || true
    [ -n "$port" ] && pkill -f "cloudflared tunnel --url http://localhost:${port}" || true
    [ -n "$port" ] && pkill -f "cloudflared tunnel --url https://localhost:${port}" || true
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
    cat "$STATE_FILE" | sort | tee "$URL_FILE"
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
    echo "Usage: ./tunnel.sh [core|monitoring|automation|ai|dev|storage|security|all|service-name] [start|stop|restart|status|urls]"
    exit 1
    ;;
esac
