#!/bin/bash
# commands/doctor.sh — homelab doctor [--fix]

cmd_doctor() {
  local fix=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --fix) fix=1 ;;
      --help|-h) cat <<'EOF'; return 0 ;;
Usage: homelab doctor [--fix]

Check stack health. With --fix, attempt to repair common issues:
create .env from example, fix data directory permissions, ensure scripts executable.
EOF
      *) log_error "Unknown option: $1"; return 1 ;;
    esac
    shift
  done

  local issues=0

  if [ "$OUTPUT_FORMAT" = "json" ]; then
    _doctor_json "$fix"
    return
  fi

  system_info
  echo ""

  if command -v docker >/dev/null 2>&1; then log_ok "docker installed"; else log_fail "docker missing"; issues=$((issues+1)); fi
  if docker_available; then log_ok "docker accessible"; else log_fail "docker not accessible"; issues=$((issues+1)); fi
  if compose_available; then log_ok "docker compose available"; else log_fail "docker compose missing"; issues=$((issues+1)); fi

  if [ -f .env ]; then
    log_ok ".env exists"
  else
    log_fail ".env missing"
    issues=$((issues+1))
    if [ -n "$fix" ] && [ -f .env.example ]; then
      cp .env.example .env
      log_info "Created .env from .env.example — edit secrets before exposing services"
    fi
  fi

  if [ -f config/services.tsv ]; then
    log_ok "service registry found"
  else
    log_fail "service registry missing: config/services.tsv"
    issues=$((issues+1))
  fi

  if [ -n "$fix" ]; then
    ensure_executable
    log_info "Ensured scripts executable"
    mkdir -p data logs state .local-state
    log_info "Ensured runtime directories"
  fi

  echo ""
  if docker_available; then
    $DOCKER_CMD compose --profile extras ps 2>/dev/null || true
  fi

  [ $issues -eq 0 ]
}

_doctor_json() {
  local fix="$1" status checks=""
  _check() { checks+="\"$1\":\"$2\","; }
  command -v docker >/dev/null 2>&1 && _check "docker" "installed" || { _check "docker" "missing"; issues=$((issues+1)); }
  docker_available && _check "docker_daemon" "accessible" || { _check "docker_daemon" "inaccessible"; issues=$((issues+1)); }
  compose_available && _check "compose" "available" || { _check "compose" "missing"; issues=$((issues+1)); }
  [ -f .env ] && _check "env" "exists" || { _check "env" "missing"; issues=$((issues+1)); }
  [ -f config/services.tsv ] && _check "registry" "found" || { _check "registry" "missing"; issues=$((issues+1)); }
  [ $issues -eq 0 ] && status="healthy" || status="issues"
  printf '{"status":"%s","checks":{%s}}\n' "$status" "${checks%,}"
}
