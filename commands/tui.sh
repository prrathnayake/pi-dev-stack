#!/bin/bash
# commands/tui.sh — homelab tui
# Launches the Textual-based TUI, auto-creating a venv on first run.

cmd_tui() {
  local venv_dir="$ROOT_DIR/tui/.venv"
  local py="$venv_dir/bin/python"

  while [ $# -gt 0 ]; do
    case "$1" in
      --help|-h) cat <<'EOF'; return 0 ;;
Usage: homelab tui

Launch the interactive TUI for monitoring Docker services and system state.

A Python virtual environment is created at tui/.venv on first run with
textual and psutil installed. Subsequent launches reuse the venv.

Keybindings:
  1-4   Switch tabs (Containers, System, Logs, Registry)
  s     Start selected service
  x     Stop selected service
  r     Restart selected service
  u     Show service URL
  l     Jump to logs for selected service
  c     Clear log output (on Logs tab)
  ?     Show help
  q     Quit
EOF
      *) log_error "Unknown option: $1"; return 1 ;;
    esac
    shift
  done

  if ! command -v python3 >/dev/null 2>&1; then
    log_error "python3 is required for the TUI"
    log_info "Install with: sudo apt install -y python3 python3-venv"
    return 1
  fi

  if [ ! -x "$py" ]; then
    log_info "First run: creating TUI virtual environment at tui/.venv"
    if ! python3 -m venv "$venv_dir" 2>/dev/null; then
      log_error "Failed to create virtual environment"
      log_info "Ensure python3-venv is installed: sudo apt install -y python3-venv"
      return 1
    fi
    log_info "Installing textual and psutil (one-time)..."
    if ! "$py" -m pip install --quiet --upgrade pip 2>/dev/null; then
      log_warn "pip self-upgrade failed, continuing"
    fi
    if ! "$py" -m pip install --quiet -r "$ROOT_DIR/tui/requirements.txt" 2>&1; then
      log_error "Failed to install TUI dependencies"
      log_info "Try manually: $py -m pip install -r tui/requirements.txt"
      return 1
    fi
    log_ok "TUI environment ready"
  fi

  cd "$ROOT_DIR" || return 1
  exec "$py" -m tui
}
