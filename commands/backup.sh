#!/bin/bash
# commands/backup.sh — homelab backup | homelab restore <file>

cmd_backup() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --help|-h) cat <<'EOF'; return 0 ;;
Usage: homelab backup

Create a gzipped tarball of data, .env, homepage, cloudflared, and local config.
Note: media/ is excluded (typically large and backed up separately).
EOF
      *) log_error "Unknown option: $1"; return 1 ;;
    esac
    shift
  done

  mkdir -p backups
  local file="backups/pi-dev-stack-$(date +%Y%m%d-%H%M%S).tar.gz"
  tar -czf "$file" data .env homepage cloudflared local docker-compose.override.yml 2>/dev/null || true
  if [ "$OUTPUT_FORMAT" = "json" ]; then
    printf '{"backup":"%s"}\n' "$file"
  else
    echo "Backup created: $file"
  fi
}

cmd_restore() {
  local file="${1:-}"
  [ -n "$file" ] || { log_error "Usage: homelab restore <file>"; return 1; }
  [ -f "$file" ] || { log_error "Backup file not found: $file"; return 1; }

  if [ "$OUTPUT_FORMAT" != "json" ]; then
    echo "Restoring from: $file"
    echo "This will overwrite ./data, .env, and local config. Continue? [y/N]"
    read -r reply
    [ "$reply" = "y" ] || [ "$reply" = "Y" ] || { echo "Aborted."; return 1; }
  fi

  tar -xzf "$file"
  if [ "$OUTPUT_FORMAT" = "json" ]; then
    printf '{"restored":"%s"}\n' "$file"
  else
    echo "Restored from: $file"
    echo "Run: homelab up"
  fi
}
