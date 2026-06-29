#!/bin/bash
# commands/tunnel.sh — homelab tunnel [group|service] [start|stop|restart|status|urls]
#                       homelab urls

STATE_FILE="${STATE_FILE:-state/tunnels.env}"
URL_FILE="${URL_FILE:-.local-state/current-urls.txt}"

_tunnel_service_key() { echo "$1" | tr '[:lower:]-' '[:upper:]_'; }

_tunnel_wait_for_origin() {
  local scheme="$1" port="$2"
  local origin="${scheme}://127.0.0.1:${port}"
  for i in {1..30}; do
    curl -fsS --max-time 3 "$origin" >/dev/null 2>&1 && return 0
    curl -kfsS --max-time 3 "$origin" >/dev/null 2>&1 && return 0
    sleep 2
  done
  log_error "Origin not reachable: $origin"
  return 1
}

_tunnel_start_one() {
  local compose_name="$1"
  local port scheme key log
  port=$(registry_port "$compose_name") || { log_error "No port for $compose_name"; return 1; }
  scheme=$(registry_scheme "$compose_name")
  key=$(_tunnel_service_key "$compose_name")
  log="logs/tunnel-${compose_name}.log"

  [ "$OUTPUT_FORMAT" != "json" ] && echo "Ensuring $compose_name is running..."
  local compose; compose=$(compose_for_service "$compose_name")
  $compose up -d "$compose_name"

  _tunnel_wait_for_origin "$scheme" "$port" || return 1

  pkill -f "cloudflared tunnel --url ${scheme}://localhost:${port}" 2>/dev/null || true
  pkill -f "cloudflared tunnel --url ${scheme}://127.0.0.1:${port}" 2>/dev/null || true
  rm -f "$log"

  [ "$OUTPUT_FORMAT" != "json" ] && echo "Starting tunnel for $compose_name on ${scheme}://127.0.0.1:$port..."
  cloudflared tunnel --url "${scheme}://127.0.0.1:${port}" > "$log" 2>&1 &

  local url=""
  for i in {1..45}; do
    url=$(grep -o 'https://[-0-9a-z]*\.trycloudflare\.com' "$log" | head -n 1 || true)
    [ -n "$url" ] && break
    sleep 2
  done

  [ -z "$url" ] && { log_error "Failed to create tunnel for $compose_name. Check: $log"; return 1; }

  mkdir -p state .local-state
  grep -v "^${key}_URL=" "$STATE_FILE" 2>/dev/null > "${STATE_FILE}.tmp" || true
  echo "${key}_URL=${url}" >> "${STATE_FILE}.tmp"
  mv "${STATE_FILE}.tmp" "$STATE_FILE"

  if [ "$compose_name" = "n8n" ]; then
    [ "$OUTPUT_FORMAT" != "json" ] && echo "Updating n8n webhook URL in .env..."
    if grep -q '^N8N_WEBHOOK_URL=' .env 2>/dev/null; then
      sed -i "s|^N8N_WEBHOOK_URL=.*|N8N_WEBHOOK_URL=${url}/|" .env
    else
      echo "N8N_WEBHOOK_URL=${url}/" >> .env
    fi
    $DOCKER_CMD compose up -d n8n
  fi

  echo "$compose_name: $url"
}

_tunnel_stop_one() {
  local compose_name="$1"
  local port scheme
  port=$(registry_port "$compose_name" 2>/dev/null) || return 0
  scheme=$(registry_scheme "$compose_name" 2>/dev/null)
  pkill -f "cloudflared tunnel --url ${scheme}://localhost:${port}" 2>/dev/null || true
  pkill -f "cloudflared tunnel --url ${scheme}://127.0.0.1:${port}" 2>/dev/null || true
  [ "$OUTPUT_FORMAT" != "json" ] && echo "Stopped tunnel: $compose_name"
}

_tunnel_show_status() {
  if [ "$OUTPUT_FORMAT" = "json" ]; then
    local pids
    pids=$(pgrep -f 'cloudflared tunnel --url' 2>/dev/null | tr '\n' ',' | sed 's/,$//')
    printf '{"tunnels":[%s]}\n' "$pids"
  else
    echo "Running cloudflared quick tunnels:"
    pgrep -af 'cloudflared tunnel --url' || echo "No quick tunnels running."
  fi
}

_tunnel_show_urls() {
  if [ "$OUTPUT_FORMAT" = "json" ]; then
    if [ -f "$STATE_FILE" ]; then
      local first=1 key val
      printf '{'
      while IFS='=' read -r key val; do
        [ -z "$key" ] && continue
        [ $first -eq 0 ] && printf ','
        first=0
        printf '"%s":"%s"' "$(json_escape "$key")" "$(json_escape "$val")"
      done < "$STATE_FILE"
      printf '}\n'
    else
      echo '{}'
    fi
  else
    echo "Current saved tunnel URLs:"
    if [ -f "$STATE_FILE" ]; then
      sort "$STATE_FILE" | tee "$URL_FILE"
    else
      echo "No saved tunnel URLs. Run: homelab tunnel core"
    fi
  fi
}

_tunnel_resolve_target() {
  local input="$1"
  if resolve_alias "$input" >/dev/null 2>&1; then
    echo "service:$(resolve_alias "$input")"
    return 0
  fi
  case "$input" in
    all) echo "group:all" ;;
    *)
      if tunnel_group_services "$input" >/dev/null 2>&1 && [ -n "$(tunnel_group_services "$input" 2>/dev/null)" ]; then
        echo "group:$input"
        return 0
      fi
      return 1
      ;;
  esac
}

cmd_tunnel() {
  local target="${1:-core}"
  local action="${2:-start}"

  case "$target" in
    --help|-h)
      cat <<'EOF'
Usage: homelab tunnel [group|service] [start|stop|restart|status|urls]

Groups: core, monitoring, automation, ai, dev, storage, security, media, ops, all
EOF
      return 0
      ;;
  esac

  case "$action" in
    --help|-h)
      cat <<'EOF'
Usage: homelab tunnel [group|service] [start|stop|restart|status|urls]

Groups: core, monitoring, automation, ai, dev, storage, security, media, ops, all
EOF
      return 0
      ;;
  esac

  mkdir -p logs state .local-state

  case "$action" in
    status) _tunnel_show_status; return ;;
    urls)   _tunnel_show_urls; return ;;
  esac

  local resolved
  resolved=$(_tunnel_resolve_target "$target") || { log_error "Unknown tunnel target: $target"; return 1; }
  local kind="${resolved%%:*}"
  local name="${resolved#*:}"

  case "$action" in
    start)
      if [ "$kind" = "group" ] && [ "$name" = "all" ]; then
        local svc
        for svc in $(tunnelable); do _tunnel_start_one "$svc"; done
      elif [ "$kind" = "group" ]; then
        local svc
        for svc in $(tunnel_group_services "$name"); do _tunnel_start_one "$svc"; done
      else
        _tunnel_start_one "$name"
      fi
      _tunnel_show_urls
      ;;
    stop)
      if [ "$kind" = "group" ] && [ "$name" = "all" ]; then
        pkill -f 'cloudflared tunnel --url' 2>/dev/null || true
        [ "$OUTPUT_FORMAT" != "json" ] && echo "Stopped all quick tunnels."
      elif [ "$kind" = "group" ]; then
        local svc
        for svc in $(tunnel_group_services "$name"); do _tunnel_stop_one "$svc"; done
      else
        _tunnel_stop_one "$name"
      fi
      ;;
    restart)
      if [ "$kind" = "group" ] && [ "$name" = "all" ]; then
        pkill -f 'cloudflared tunnel --url' 2>/dev/null || true
        local svc
        for svc in $(tunnelable); do _tunnel_start_one "$svc"; done
      elif [ "$kind" = "group" ]; then
        local svc
        for svc in $(tunnel_group_services "$name"); do _tunnel_stop_one "$svc"; _tunnel_start_one "$svc"; done
      else
        _tunnel_stop_one "$name"
        _tunnel_start_one "$name"
      fi
      _tunnel_show_urls
      ;;
    *) log_error "Unknown tunnel action: $action"; return 1 ;;
  esac
}

cmd_urls() { _tunnel_show_urls; }
