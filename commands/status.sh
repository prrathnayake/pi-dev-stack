#!/bin/bash
# commands/status.sh — homelab status [service]

cmd_status() {
  local svc=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --help|-h) cat <<'EOF'; return 0 ;;
Usage: homelab status [service]

Show container status for the whole stack or a single service.
EOF
      *) svc="$1" ;;
    esac
    shift
  done

  if [ -n "$svc" ]; then
    if ! is_service "$svc"; then log_error "Unknown service: $svc"; return 1; fi
    local compose; compose=$(compose_for_service "$svc")
    if [ "$OUTPUT_FORMAT" = "json" ]; then
      $compose ps --format json "$svc" | json_objects_array
    else
      $compose ps "$svc"
    fi
  else
    if [ "$OUTPUT_FORMAT" = "json" ]; then
      $DOCKER_CMD compose --profile extras ps --format json | json_objects_array
    else
      $DOCKER_CMD compose --profile extras ps
    fi
  fi
}
