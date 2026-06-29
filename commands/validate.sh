#!/bin/bash
# commands/validate.sh — homelab validate

cmd_validate() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --help|-h) cat <<'EOF'; return 0 ;;
Usage: homelab validate

Validate Docker, Compose, cloudflared, and docker-compose.yml config.
EOF
      *) log_error "Unknown option: $1"; return 1 ;;
    esac
    shift
  done

  if [ "$OUTPUT_FORMAT" = "json" ]; then
    _validate_json
    return
  fi

  echo "Running validation checks..."
  command -v docker >/dev/null 2>&1 && log_ok "Docker installed" || log_fail "Docker missing"
  docker_available && log_ok "Docker accessible" || log_fail "Docker not accessible"
  compose_available && log_ok "Docker Compose installed" || log_fail "Docker Compose missing"
  command -v cloudflared >/dev/null 2>&1 && log_ok "cloudflared installed" || log_fail "cloudflared missing"

  if $DOCKER_CMD compose config >/dev/null 2>&1; then
    log_ok "docker-compose.yml valid"
  else
    log_fail "docker-compose.yml invalid"
  fi

  if $DOCKER_CMD compose --profile extras config >/dev/null 2>&1; then
    log_ok "docker-compose.yml valid (with extras profile)"
  else
    log_fail "docker-compose.yml invalid (with extras profile)"
  fi

  echo ""
  echo "Core services:"
  core_services | tr '\n' ' '
  echo ""
  echo "Extras services:"
  extra_services | tr '\n' ' '
  echo ""
}

_validate_json() {
  local results=""
  _v() { results+="\"$1\":\"$2\","; }
  command -v docker >/dev/null 2>&1 && _v "docker" "ok" || _v "docker" "missing"
  docker_available && _v "docker_daemon" "ok" || _v "docker_daemon" "fail"
  compose_available && _v "compose" "ok" || _v "compose" "missing"
  command -v cloudflared >/dev/null 2>&1 && _v "cloudflared" "ok" || _v "cloudflared" "missing"
  $DOCKER_CMD compose config >/dev/null 2>&1 && _v "compose_config" "valid" || _v "compose_config" "invalid"
  printf '{"results":{%s}}\n' "${results%,}"
}
