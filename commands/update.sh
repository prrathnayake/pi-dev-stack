#!/bin/bash
# commands/update.sh — homelab update

cmd_update() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --help|-h) cat <<'EOF'; return 0 ;;
Usage: homelab update

Pull latest changes from git and ensure scripts are executable.
EOF
      *) log_error "Unknown option: $1"; return 1 ;;
    esac
    shift
  done

  git pull
  ensure_executable
  if [ "$OUTPUT_FORMAT" = "json" ]; then
    echo '{"updated":true}'
  else
    echo "Updated."
  fi
}
