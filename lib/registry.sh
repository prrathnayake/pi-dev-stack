#!/bin/bash
# lib/registry.sh — service registry loaded from config/services.tsv
# Pipe-delimited fields: name|profile|group|port|scheme|path|aliases|tunnel|url_note

REGISTRY_FILE="${REGISTRY_FILE:-$ROOT_DIR/config/services.tsv}"
_REGISTRY_LOADED=""

declare -a _REG_NAMES _REG_PROFILE _REG_GROUP _REG_PORT _REG_SCHEME _REG_PATH _REG_ALIASES _REG_TUNNEL _REG_TUNNEL_GROUPS _REG_URLNOTE

_load_registry() {
  [ -n "$_REGISTRY_LOADED" ] && return 0
  _REGISTRY_LOADED=1
  [ -f "$REGISTRY_FILE" ] || { log_error "Registry not found: $REGISTRY_FILE"; return 1; }
  local name profile group port scheme path aliases tunnel tunnel_groups urlnote
  while IFS='|' read -r name profile group port scheme path aliases tunnel tunnel_groups urlnote || [ -n "$name" ]; do
    case "$name" in ''|'#'*) continue ;; esac
    _REG_NAMES+=("$name")
    _REG_PROFILE+=("$profile")
    _REG_GROUP+=("$group")
    _REG_PORT+=("$port")
    _REG_SCHEME+=("$scheme")
    _REG_PATH+=("$path")
    _REG_ALIASES+=("$aliases")
    _REG_TUNNEL+=("$tunnel")
    _REG_TUNNEL_GROUPS+=("$tunnel_groups")
    _REG_URLNOTE+=("$urlnote")
  done < "$REGISTRY_FILE"
}

_reg_idx() {
  _load_registry || return 1
  local i
  for i in "${!_REG_NAMES[@]}"; do
    [ "${_REG_NAMES[$i]}" = "$1" ] && { echo "$i"; return 0; }
  done
  return 1
}

is_service() { _reg_idx "$1" >/dev/null 2>&1; }

is_extra() {
  _load_registry || return 1
  local i; i=$(_reg_idx "$1") || return 1
  [ "${_REG_PROFILE[$i]}" = "extras" ]
}

registry_profile() { _load_registry || return 1; local i; i=$(_reg_idx "$1") || return 1; echo "${_REG_PROFILE[$i]}"; }
registry_group()   { _load_registry || return 1; local i; i=$(_reg_idx "$1") || return 1; echo "${_REG_GROUP[$i]}"; }
registry_port()    { _load_registry || return 1; local i; i=$(_reg_idx "$1") || return 1; echo "${_REG_PORT[$i]}"; }
registry_scheme()  { _load_registry || return 1; local i; i=$(_reg_idx "$1") || return 1; echo "${_REG_SCHEME[$i]}"; }
registry_path()    { _load_registry || return 1; local i; i=$(_reg_idx "$1") || return 1; echo "${_REG_PATH[$i]}"; }
registry_tunnel()  { _load_registry || return 1; local i; i=$(_reg_idx "$1") || return 1; echo "${_REG_TUNNEL[$i]}"; }
registry_urlnote() { _load_registry || return 1; local i; i=$(_reg_idx "$1") || return 1; echo "${_REG_URLNOTE[$i]}"; }

all_services()   { _load_registry; printf '%s\n' "${_REG_NAMES[@]}"; }
core_services()  { _load_registry; local i; for i in "${!_REG_NAMES[@]}"; do [ "${_REG_PROFILE[$i]}" = "core" ] && echo "${_REG_NAMES[$i]}"; done; }
extra_services() { _load_registry; local i; for i in "${!_REG_NAMES[@]}"; do [ "${_REG_PROFILE[$i]}" = "extras" ] && echo "${_REG_NAMES[$i]}"; done; }
tunnelable()     { _load_registry; local i; for i in "${!_REG_NAMES[@]}"; do [ "${_REG_TUNNEL[$i]}" = "yes" ] && echo "${_REG_NAMES[$i]}"; done; }
group_services() { _load_registry; local i; for i in "${!_REG_NAMES[@]}"; do [ "${_REG_GROUP[$i]}" = "$1" ] && echo "${_REG_NAMES[$i]}"; done; }
tunnel_group_services() {
  _load_registry
  local i groups g
  for i in "${!_REG_NAMES[@]}"; do
    IFS=',' read -ra groups <<< "${_REG_TUNNEL_GROUPS[$i]}"
    for g in "${groups[@]}"; do
      [ "$g" = "$1" ] && { echo "${_REG_NAMES[$i]}"; break; }
    done
  done
}
tunnel_groups_list() {
  _load_registry
  local i groups g seen=""
  for i in "${!_REG_NAMES[@]}"; do
    IFS=',' read -ra groups <<< "${_REG_TUNNEL_GROUPS[$i]}"
    for g in "${groups[@]}"; do
      case " $seen " in *" $g "*) ;; *) seen="$seen $g"; echo "$g" ;; esac
    done
  done
}

resolve_alias() {
  _load_registry || return 1
  local i a alias_list
  for i in "${!_REG_NAMES[@]}"; do
    [ "${_REG_NAMES[$i]}" = "$1" ] && { echo "$1"; return 0; }
    IFS=',' read -ra alias_list <<< "${_REG_ALIASES[$i]}"
    for a in "${alias_list[@]}"; do
      [ "$a" = "$1" ] && { echo "${_REG_NAMES[$i]}"; return 0; }
    done
  done
  return 1
}

service_url() {
  _load_registry || return 1
  local i; i=$(_reg_idx "$1") || { echo "No URL registered for service: $1"; return 1; }
  local note="${_REG_URLNOTE[$i]}"
  [ -n "$note" ] && { echo "$note"; return 0; }
  local port="${_REG_PORT[$i]}" scheme="${_REG_SCHEME[$i]}" path="${_REG_PATH[$i]}" name="${_REG_NAMES[$i]}"
  [ -z "$port" ] && { echo "$name has no web UI"; return 0; }
  echo "${name}: ${scheme}://localhost:${port}${path}"
}
