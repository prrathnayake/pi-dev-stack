#!/bin/bash
# commands/service.sh — homelab service <action> [service]
#                        homelab <service> <action>  (direct alias)

cmd_service() {
  local action="${1:-list}"
  local svc="${2:-}"
  local compose="$DOCKER_CMD compose"
  [ -n "$svc" ] && compose=$(compose_for_service "$svc")

  case "$action" in
    --help|-h) cat <<'EOF'; return 0 ;;
Usage: homelab service <action> [service]

Actions:
  list     List all services
  core     List core services
  extras   List extras services
  start|stop|restart|status|logs|inspect|shell|url  <service>
EOF
    list)
      if [ "$OUTPUT_FORMAT" = "json" ]; then all_services | json_string_array; else all_services; fi ;;
    core)
      if [ "$OUTPUT_FORMAT" = "json" ]; then core_services | json_string_array; else core_services; fi ;;
    extras)
      if [ "$OUTPUT_FORMAT" = "json" ]; then extra_services | json_string_array; else extra_services; fi ;;
    start)
      [ -n "$svc" ] || { log_error "Usage: homelab service start <service>"; return 1; }
      is_service "$svc" || { log_error "Unknown service: $svc"; return 1; }
      $compose up -d "$svc" ;;
    stop)
      [ -n "$svc" ] || { log_error "Usage: homelab service stop <service>"; return 1; }
      is_service "$svc" || { log_error "Unknown service: $svc"; return 1; }
      $compose stop "$svc" ;;
    restart)
      [ -n "$svc" ] || { log_error "Usage: homelab service restart <service>"; return 1; }
      is_service "$svc" || { log_error "Unknown service: $svc"; return 1; }
      $compose restart "$svc" ;;
    status|ps)
      [ -n "$svc" ] || { log_error "Usage: homelab service status <service>"; return 1; }
      is_service "$svc" || { log_error "Unknown service: $svc"; return 1; }
      if [ "$OUTPUT_FORMAT" = "json" ]; then
        $compose ps --format json "$svc" | json_objects_array
      else
        $compose ps "$svc"
      fi ;;
    logs)
      [ -n "$svc" ] || { log_error "Usage: homelab service logs <service>"; return 1; }
      is_service "$svc" || { log_error "Unknown service: $svc"; return 1; }
      $compose logs -f "$svc" ;;
    inspect)
      [ -n "$svc" ] || { log_error "Usage: homelab service inspect <service>"; return 1; }
      is_service "$svc" || { log_error "Unknown service: $svc"; return 1; }
      $DOCKER_CMD inspect "$(container_name "$svc")" ;;
    shell)
      [ -n "$svc" ] || { log_error "Usage: homelab service shell <service>"; return 1; }
      is_service "$svc" || { log_error "Unknown service: $svc"; return 1; }
      $DOCKER_CMD exec -it "$(container_name "$svc")" sh ;;
    url)
      [ -n "$svc" ] || { log_error "Usage: homelab service url <service>"; return 1; }
      is_service "$svc" || { log_error "Unknown service: $svc"; return 1; }
      if [ "$OUTPUT_FORMAT" = "json" ]; then
        local u; u=$(service_url "$svc")
        printf '{"service":"%s","url":"%s"}\n' "$svc" "$(json_escape "$u")"
      else
        service_url "$svc"
      fi
      ;;
    *) log_error "Usage: homelab service <list|core|extras|start|stop|restart|status|logs|inspect|shell|url> [service]"; return 1 ;;
  esac
}

service_alias() {
  local svc="$1"
  local action="${2:-status}"
  is_service "$svc" || { log_error "Unknown service: $svc"; log_info "Run: homelab service list"; return 1; }
  case "$action" in
    start|stop|restart|status|ps|logs|inspect|shell) cmd_service "$action" "$svc" ;;
    url)
      if [ "$OUTPUT_FORMAT" = "json" ]; then
        local u; u=$(service_url "$svc")
        printf '{"service":"%s","url":"%s"}\n' "$svc" "$(json_escape "$u")"
      else
        service_url "$svc"
      fi
      ;;
    --help|-h) service_url "$svc" ;;
    *) log_error "Usage: homelab $svc <start|stop|restart|status|logs|inspect|shell|url>"; return 1 ;;
  esac
}
