#!/bin/bash
# commands/tunnel.sh — homelab tunnel [group|service] [start|stop|restart|status|urls]
#                       homelab urls

STATE_FILE="${STATE_FILE:-state/tunnels.env}"
URL_FILE="${URL_FILE:-.local-state/current-urls.txt}"
TUNNEL_PID_DIR="${TUNNEL_PID_DIR:-state/tunnel-pids}"

_tunnel_service_key() { echo "$1" | tr '[:lower:]-' '[:upper:]_'; }

_tunnel_pid_file() { echo "$TUNNEL_PID_DIR/$1.pid"; }

_tunnel_pid_running() {
  local compose_name="$1" pid_file pid args port scheme
  pid_file=$(_tunnel_pid_file "$compose_name")
  [ -s "$pid_file" ] || return 1
  read -r pid < "$pid_file"
  case "$pid" in ''|*[!0-9]*) return 1 ;; esac
  kill -0 "$pid" 2>/dev/null || return 1
  port=$(registry_port "$compose_name") || return 1
  scheme=$(registry_scheme "$compose_name") || return 1
  args=$(ps -p "$pid" -o args= 2>/dev/null) || return 1
  case "$args" in
    *"cloudflared tunnel --url ${scheme}://127.0.0.1:${port}"*) return 0 ;;
    *) return 1 ;;
  esac
}

_tunnel_remove_state() {
  local compose_name="$1" key tmp
  key=$(_tunnel_service_key "$compose_name")
  [ -f "$STATE_FILE" ] || return 0
  tmp="${STATE_FILE}.tmp.$$"
  grep -v "^${key}_URL=" "$STATE_FILE" > "$tmp" || true
  mv "$tmp" "$STATE_FILE"
}

_tunnel_wait_for_origin() {
  local scheme="$1" port="$2"
  local origin="${scheme}://127.0.0.1:${port}"
  for i in {1..30}; do
    # Any HTTP response proves that the origin is accepting connections. Some
    # services legitimately return 401/403 at their root path.
    curl -ksS --max-time 3 -o /dev/null "$origin" >/dev/null 2>&1 && return 0
    sleep 2
  done
  log_error "Origin not reachable: $origin"
  return 1
}

_tunnel_start_one() {
  local compose_name="$1"
  local port scheme key log pid pid_file
  command -v cloudflared >/dev/null 2>&1 || { log_error "cloudflared is not installed"; return 1; }
  port=$(registry_port "$compose_name") || { log_error "No port for $compose_name"; return 1; }
  scheme=$(registry_scheme "$compose_name")
  key=$(_tunnel_service_key "$compose_name")
  log="logs/tunnel-${compose_name}.log"

  [ "$OUTPUT_FORMAT" != "json" ] && echo "Ensuring $compose_name is running..."
  local compose; compose=$(compose_for_service "$compose_name")
  $compose up -d "$compose_name" || { log_error "Failed to start service: $compose_name"; return 1; }

  _tunnel_wait_for_origin "$scheme" "$port" || return 1

  _tunnel_stop_one "$compose_name" quiet
  rm -f "$log"

  [ "$OUTPUT_FORMAT" != "json" ] && echo "Starting tunnel for $compose_name on ${scheme}://127.0.0.1:$port..."
  cloudflared tunnel --url "${scheme}://127.0.0.1:${port}" > "$log" 2>&1 &
  pid=$!
  mkdir -p "$TUNNEL_PID_DIR"
  pid_file=$(_tunnel_pid_file "$compose_name")
  echo "$pid" > "$pid_file"

  local url="" connected=""
  for i in {1..45}; do
    url=$(grep -o 'https://[-0-9a-z]*\.trycloudflare\.com' "$log" | head -n 1 || true)
    connected=$(grep -m1 'Registered tunnel connection' "$log" 2>/dev/null || true)
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid" 2>/dev/null || true
      rm -f "$pid_file"
      log_error "cloudflared exited before connecting for $compose_name. Check: $log"
      return 1
    fi
    [ -n "$url" ] && [ -n "$connected" ] && break
    sleep 2
  done

  if [ -z "$url" ] || [ -z "$connected" ]; then
    kill "$pid" 2>/dev/null || true
    rm -f "$pid_file"
    log_error "Failed to establish tunnel for $compose_name. Check: $log"
    return 1
  fi

  mkdir -p state .local-state
  grep -v "^${key}_URL=" "$STATE_FILE" 2>/dev/null > "${STATE_FILE}.tmp.$$" || true
  echo "${key}_URL=${url}" >> "${STATE_FILE}.tmp.$$"
  mv "${STATE_FILE}.tmp.$$" "$STATE_FILE"

  if [ "$compose_name" = "n8n" ]; then
    [ "$OUTPUT_FORMAT" != "json" ] && echo "Updating n8n webhook URL in .env..."
    if grep -q '^N8N_WEBHOOK_URL=' .env 2>/dev/null; then
      sed -i "s|^N8N_WEBHOOK_URL=.*|N8N_WEBHOOK_URL=${url}/|" .env
    else
      echo "N8N_WEBHOOK_URL=${url}/" >> .env
    fi
    if ! $DOCKER_CMD compose up -d n8n || ! _tunnel_wait_for_origin "$scheme" "$port"; then
      _tunnel_stop_one "$compose_name" quiet
      log_error "Failed to apply n8n webhook URL"
      return 1
    fi
  fi

  [ "$OUTPUT_FORMAT" = "json" ] || echo "$compose_name: $url"
}

_tunnel_stop_one() {
  local compose_name="$1" quiet="${2:-}"
  local port scheme pid_file pid
  port=$(registry_port "$compose_name" 2>/dev/null) || return 0
  scheme=$(registry_scheme "$compose_name" 2>/dev/null)
  pid_file=$(_tunnel_pid_file "$compose_name")
  if [ -s "$pid_file" ]; then
    read -r pid < "$pid_file"
    _tunnel_pid_running "$compose_name" && kill "$pid" 2>/dev/null || true
  else
    # Compatibility cleanup for tunnels started by older releases.
    pkill -f "cloudflared tunnel --url ${scheme}://localhost:${port}" 2>/dev/null || true
    pkill -f "cloudflared tunnel --url ${scheme}://127.0.0.1:${port}" 2>/dev/null || true
  fi
  rm -f "$pid_file"
  _tunnel_remove_state "$compose_name"
  [ "$quiet" = "quiet" ] || [ "$OUTPUT_FORMAT" = "json" ] || echo "Stopped tunnel: $compose_name"
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
  local svc
  for svc in $(tunnelable); do
    _tunnel_pid_running "$svc" || _tunnel_remove_state "$svc"
  done
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
    local service
    service=$(resolve_alias "$input")
    [ "$(registry_tunnel "$service")" = "yes" ] || return 1
    echo "service:$service"
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
        local failed=0
        for svc in $(tunnelable); do _tunnel_start_one "$svc" || failed=1; done
      elif [ "$kind" = "group" ]; then
        local svc
        local failed=0
        for svc in $(tunnel_group_services "$name"); do _tunnel_start_one "$svc" || failed=1; done
      else
        local failed=0
        _tunnel_start_one "$name" || failed=1
      fi
      _tunnel_show_urls
      [ "$failed" -eq 0 ]
      ;;
    stop)
      if [ "$kind" = "group" ] && [ "$name" = "all" ]; then
        local svc
        for svc in $(tunnelable); do _tunnel_stop_one "$svc" quiet; done
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
        local svc failed=0
        for svc in $(tunnelable); do _tunnel_stop_one "$svc" quiet; done
        for svc in $(tunnelable); do _tunnel_start_one "$svc" || failed=1; done
      elif [ "$kind" = "group" ]; then
        local svc failed=0
        for svc in $(tunnel_group_services "$name"); do _tunnel_stop_one "$svc"; _tunnel_start_one "$svc" || failed=1; done
      else
        local failed=0
        _tunnel_stop_one "$name"
        _tunnel_start_one "$name" || failed=1
      fi
      _tunnel_show_urls
      [ "$failed" -eq 0 ]
      ;;
    *) log_error "Unknown tunnel action: $action"; return 1 ;;
  esac
}

cmd_urls() { _tunnel_show_urls; }
