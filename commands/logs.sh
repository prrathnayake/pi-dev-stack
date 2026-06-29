#!/bin/bash
# commands/logs.sh — homelab logs [service] [--tail N] [--since T]

cmd_logs() {
  local svc="" tail_args=()
  while [ $# -gt 0 ]; do
    case "$1" in
      --help|-h) cat <<'EOF'; return 0 ;;
Usage: homelab logs [service] [--tail N] [--since T]

Follow logs for all services or one service.
  --tail N     Show last N lines per service
  --since T    Show logs since time (e.g. 5m, 1h, 2024-01-01T00:00:00)
EOF
      --tail) shift; tail_args+=(--tail "$1") ;;
      --since) shift; tail_args+=(--since "$1") ;;
      *) svc="$1" ;;
    esac
    shift
  done

  if [ -n "$svc" ]; then
    if ! is_service "$svc"; then log_error "Unknown service: $svc"; return 1; fi
    local compose; compose=$(compose_for_service "$svc")
    $compose logs -f "${tail_args[@]}" "$svc"
  else
    $DOCKER_CMD compose --profile extras logs -f "${tail_args[@]}"
  fi
}
