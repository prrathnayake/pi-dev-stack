#!/bin/bash
# commands/pihole.sh — homelab pihole <action>

cmd_pihole() {
  local action="${1:-status}"
  case "$action" in
    --help|-h) cat <<'EOF'; return 0 ;;
Usage: homelab pihole <action>

Service actions:
  start|stop|restart|status|logs|inspect|shell|url

Pi-hole specific:
  allow|whitelist|enable <domain>     Whitelist a domain
  block|blacklist <domain>            Blacklist a domain
  disable [seconds]                   Disable blocking (default 60s)
  enable-blocking                     Re-enable blocking
  update-gravity|gravity              Update gravity
  stats                               Show Pi-hole stats
  password <new-password>             Change web password
EOF
    start|stop|restart|status|ps|logs|inspect|shell|url) service_alias pihole "$action" ;;
    allow|whitelist|enable)
      local domain="${2:-}"
      [ -n "$domain" ] || { log_error "Usage: homelab pihole allow <domain>"; return 1; }
      $DOCKER_CMD exec pi-pihole pihole whitelist "$domain" ;;
    block|blacklist)
      local domain="${2:-}"
      [ -n "$domain" ] || { log_error "Usage: homelab pihole block <domain>"; return 1; }
      $DOCKER_CMD exec pi-pihole pihole blacklist "$domain" ;;
    disable)
      local seconds="${2:-60}"
      $DOCKER_CMD exec pi-pihole pihole disable "$seconds" ;;
    enable-blocking)
      $DOCKER_CMD exec pi-pihole pihole enable ;;
    update-gravity|gravity)
      $DOCKER_CMD exec pi-pihole pihole -g ;;
    stats)
      $DOCKER_CMD exec pi-pihole pihole -c || true ;;
    password)
      local pass="${2:-}"
      [ -n "$pass" ] || { log_error "Usage: homelab pihole password <new-password>"; return 1; }
      $DOCKER_CMD exec pi-pihole pihole setpassword "$pass" ;;
    *) log_error "Usage: homelab pihole <start|stop|restart|status|logs|shell|url|allow|block|disable|enable-blocking|gravity|stats|password>"; return 1 ;;
  esac
}
