#!/bin/bash
# commands/down.sh — homelab down [--volumes] [--wipe-data]

cmd_down() {
  local volumes="" wipe=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --volumes) volumes=1 ;;
      --wipe-data) wipe=1 ;;
      --help|-h) cat <<'EOF'; return 0 ;;
Usage: homelab down [--volumes] [--wipe-data]

Stop all services and cloudflared quick tunnels.
  --volumes    Also remove named volumes
  --wipe-data  Also delete ./data and ./logs
EOF
      *) log_error "Unknown option: $1"; return 1 ;;
    esac
    shift
  done

  ensure_executable

  if [ "$OUTPUT_FORMAT" != "json" ]; then
    echo "Stopping Cloudflare quick tunnels..."
  fi
  pkill -f 'cloudflared tunnel --url' 2>/dev/null || true

  if [ "$OUTPUT_FORMAT" != "json" ]; then
    echo "Stopping Docker services..."
  fi
  if docker_available; then
    $DOCKER_CMD compose down --remove-orphans
  fi

  if [ -n "$volumes" ]; then
    [ "$OUTPUT_FORMAT" != "json" ] && echo "Removing Compose volumes..."
    $DOCKER_CMD compose down -v --remove-orphans 2>/dev/null || true
  fi

  if [ -n "$wipe" ]; then
    [ "$OUTPUT_FORMAT" != "json" ] && echo "WARNING: wiping ./data and ./logs"
    $DOCKER_CMD compose down -v --remove-orphans 2>/dev/null || true
    sudo rm -rf data logs media
    [ "$OUTPUT_FORMAT" != "json" ] && echo "Local data wiped."
  fi

  if [ "$OUTPUT_FORMAT" = "json" ]; then
    printf '{"stopped":true,"volumes":%s,"wipe":%s}\n' \
      "$([ -n "$volumes" ] && echo true || echo false)" \
      "$([ -n "$wipe" ] && echo true || echo false)"
  else
    echo "Stack stopped."
  fi
}
