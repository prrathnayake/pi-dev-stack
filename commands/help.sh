#!/bin/bash
# commands/help.sh — homelab help [topic]

cmd_help() {
  local topic="${1:-}"

  if [ -n "$topic" ] && [ "$topic" != "help" ] && [ "$topic" != "--help" ] && [ "$topic" != "-h" ]; then
    _help_topic "$topic"
    return 0
  fi

  if [ "$OUTPUT_FORMAT" = "json" ]; then
    local core_json extras_json groups_json
    core_json=$(core_services | json_string_array)
    extras_json=$(extra_services | json_string_array)
    groups_json=$(tunnel_groups_list | json_string_array)
    printf '{"commands":["up","down","restart","status","logs","service","tunnel","urls","doctor","validate","install","update","backup","restore","pihole","help"],"core_services":%s,"extras_services":%s,"tunnel_groups":%s}\n' "$core_json" "$extras_json" "$groups_json"
    return
  fi

  cat <<EOF
Usage:
  homelab <command> [options]
  homelab <service> <action>

Lifecycle:
  homelab up [service...]    Start core services (or specific services)
  homelab up --all           Start core + extras
  homelab down [--volumes]   Stop stack (--volumes removes named volumes)
  homelab down --wipe-data   Stop stack and delete ./data and ./logs
  homelab restart [service]  Restart stack or a single service
  homelab status [service]   Show container status
  homelab logs [service]     Follow logs (--tail N, --since T)

Service management:
  homelab service list       List all services
  homelab service core       List core services
  homelab service extras     List extras services
  homelab service <action> <service>
    actions: start stop restart status logs inspect shell url

Tunnels:
  homelab tunnel [group|service] [start|stop|restart|status|urls]
  homelab urls                Show saved tunnel URLs

System:
  homelab install [--global]  Install dependencies and start stack
  homelab doctor [--fix]      Check health (--fix attempts repairs)
  homelab validate            Validate config and environment
  homelab update              git pull and refresh
  homelab backup              Create a tarball backup
  homelab restore <file>      Restore from a backup tarball

Domain:
  homelab pihole <action>     Pi-hole specific commands

Direct service alias:
  homelab n8n start           Same as: homelab service start n8n
  homelab plex url            Show Plex URL

Tunnel groups:
  $(tunnel_groups_list | tr '\n' ' ')

Flags:
  --json                      Machine-readable JSON output
  --help, -h                  Show help

Core services:
  $(core_services | tr '\n' ' ')

Extras services:
  $(extra_services | tr '\n' ' ')
EOF
}

_help_topic() {
  case "$1" in
    up)
      cat <<'EOF'
homelab up [service...] [--all]

Start core services, specific named services, or core + extras with --all.
EOF
      ;;
    down)
      cat <<'EOF'
homelab down [--volumes] [--wipe-data]

Stop all services and cloudflared tunnels.
  --volumes    Remove named volumes
  --wipe-data  Delete ./data, ./logs, and ./media
EOF
      ;;
    restart)
      cat <<'EOF'
homelab restart [service]

Restart the entire core stack or a single service.
EOF
      ;;
    status)   echo "homelab status [service] — show container status"; ;;
    logs)     echo "homelab logs [service] [--tail N] [--since T] — follow logs"; ;;
    service)  cmd_service --help ;;
    tunnel)   cmd_tunnel --help ;;
    urls)     echo "homelab urls — show saved tunnel URLs"; ;;
    doctor)   cmd_doctor --help ;;
    validate) cmd_validate --help ;;
    install)  cmd_install --help ;;
    update)   cmd_update --help ;;
    backup)   cmd_backup --help ;;
    restore)  echo "homelab restore <file> — restore from a backup tarball"; ;;
    pihole)   cmd_pihole --help ;;
    *) echo "No help for: $1"; echo "Run: homelab help"; return 1 ;;
  esac
}
