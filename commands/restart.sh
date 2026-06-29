#!/bin/bash
# commands/restart.sh — homelab restart [service]

cmd_restart() {
  local svc=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --help|-h) cat <<'EOF'; return 0 ;;
Usage: homelab restart [service]

Restart the whole stack or a single service.
EOF
      *) svc="$1" ;;
    esac
    shift
  done

  if [ -n "$svc" ]; then
    if ! is_service "$svc"; then log_error "Unknown service: $svc"; return 1; fi
    local compose; compose=$(compose_for_service "$svc")
    $compose restart "$svc"
    [ "$OUTPUT_FORMAT" = "json" ] && echo "{\"restarted\":\"$svc\"}" || echo "Restarted: $svc"
  else
    $DOCKER_CMD compose --profile extras down --remove-orphans 2>/dev/null || true
    $DOCKER_CMD compose up -d
    [ "$OUTPUT_FORMAT" = "json" ] && echo '{"restarted":"core"}' || echo "Core stack restarted."
  fi
}
