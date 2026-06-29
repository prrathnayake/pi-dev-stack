#!/bin/bash
# commands/up.sh — homelab up [service...] [--all]

cmd_up() {
  local all="" services=()
  while [ $# -gt 0 ]; do
    case "$1" in
      --all) all=1 ;;
      --help|-h) cat <<'EOF'; return 0 ;;
Usage: homelab up [service...] [--all]

Start core services, or specific services, or core + extras with --all.
EOF
      *) services+=("$1") ;;
    esac
    shift
  done

  ensure_executable

  if [ ${#services[@]} -gt 0 ]; then
    for svc in "${services[@]}"; do
      if ! is_service "$svc"; then log_error "Unknown service: $svc"; return 1; fi
    done
    for svc in "${services[@]}"; do
      local compose; compose=$(compose_for_service "$svc")
      $compose up -d "$svc"
    done
    if [ "$OUTPUT_FORMAT" = "json" ]; then
      printf '{"started":['
      local first=1
      for svc in "${services[@]}"; do [ $first -eq 0 ] && printf ','; first=0; printf '"%s"' "$svc"; done
      printf ']}\n'
    else
      echo "Started: ${services[*]}"
    fi
  elif [ -n "$all" ]; then
    $DOCKER_CMD compose --profile extras up -d
    [ "$OUTPUT_FORMAT" = "json" ] && echo '{"started":"all"}' || echo "Core + extras stack started."
  else
    $DOCKER_CMD compose up -d
    [ "$OUTPUT_FORMAT" = "json" ] && echo '{"started":"core"}' || echo "Core stack started."
  fi
}
