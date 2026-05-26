#!/bin/bash

CONFIG_DEFAULT="${CONFIG_DEFAULT:-config/homelab.default.json}"
CONFIG_RUNTIME="${CONFIG_RUNTIME:-.local-state/homelab.runtime.json}"
CONFIG_EFFECTIVE="${CONFIG_EFFECTIVE:-.local-state/homelab.effective.json}"

ensure_config() {
  mkdir -p .local-state state logs
  if [ ! -f "$CONFIG_DEFAULT" ]; then
    echo "[FAIL] Missing default config: $CONFIG_DEFAULT"
    return 1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[FAIL] python3 is required for JSON config management"
    return 1
  fi
  if [ ! -f "$CONFIG_RUNTIME" ]; then
    printf '{\n  "runtime": {},\n  "tunnels": {}\n}\n' > "$CONFIG_RUNTIME"
  fi
  python3 - "$CONFIG_DEFAULT" "$CONFIG_RUNTIME" "$CONFIG_EFFECTIVE" <<'PY'
import json, sys
from pathlib import Path

def merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = merge(out.get(k), v)
        return out
    return b if b is not None else a

def load(path):
    p = Path(path)
    if not p.exists():
        return {}
    with p.open() as f:
        return json.load(f)

default = load(sys.argv[1])
runtime = load(sys.argv[2])
effective = merge(default, runtime)
Path(sys.argv[3]).write_text(json.dumps(effective, indent=2) + "\n")
PY
}

config_get() {
  ensure_config >/dev/null || return 1
  python3 - "$CONFIG_EFFECTIVE" "$1" <<'PY'
import json, sys
obj=json.load(open(sys.argv[1]))
cur=obj
for part in sys.argv[2].split('.'):
    if isinstance(cur, dict) and part in cur:
        cur=cur[part]
    else:
        sys.exit(1)
if isinstance(cur, (dict, list)):
    print(json.dumps(cur))
elif isinstance(cur, bool):
    print(str(cur).lower())
elif cur is None:
    print("")
else:
    print(cur)
PY
}

config_set() {
  ensure_config >/dev/null || return 1
  key="$1"
  value="$2"
  python3 - "$CONFIG_RUNTIME" "$key" "$value" <<'PY'
import json, sys
from pathlib import Path
path=Path(sys.argv[1])
key=sys.argv[2]
raw=sys.argv[3]
try:
    value=json.loads(raw)
except Exception:
    value=raw
obj=json.loads(path.read_text()) if path.exists() else {}
cur=obj
parts=key.split('.')
for p in parts[:-1]:
    cur=cur.setdefault(p,{})
cur[parts[-1]]=value
path.write_text(json.dumps(obj, indent=2)+"\n")
PY
  ensure_config >/dev/null
}

config_service_port() { config_get "services.$1.port"; }
config_service_compose() { config_get "services.$1.compose_service" 2>/dev/null || echo "$1"; }
config_group_services() {
  ensure_config >/dev/null || return 1
  python3 - "$CONFIG_EFFECTIVE" "$1" <<'PY'
import json, sys
obj=json.load(open(sys.argv[1]))
for item in obj.get('tunnel_groups', {}).get(sys.argv[2], []):
    print(item)
PY
}

config_save_tunnel_url() {
  service="$1"
  url="$2"
  generated_at="$(date -Iseconds)"
  config_set "tunnels.$service.url" "\"$url\"" >/dev/null
  config_set "tunnels.$service.generated_at" "\"$generated_at\"" >/dev/null
  python3 - "$CONFIG_RUNTIME" state/tunnels.json .local-state/current-urls.txt <<'PY'
import json, sys
from pathlib import Path
obj=json.load(open(sys.argv[1]))
tunnels=obj.get('tunnels', {})
Path(sys.argv[2]).write_text(json.dumps(tunnels, indent=2)+"\n")
lines=[]
for name, data in tunnels.items():
    if isinstance(data, dict) and data.get('url'):
        lines.append(f"{name}: {data['url']}")
Path(sys.argv[3]).write_text("\n".join(lines)+("\n" if lines else ""))
PY
}

config_show_tunnel_urls() {
  ensure_config >/dev/null || return 1
  python3 - "$CONFIG_EFFECTIVE" <<'PY'
import json, sys
obj=json.load(open(sys.argv[1]))
tunnels=obj.get('tunnels', {})
if not tunnels:
    print('No saved tunnel URLs. Run: homelab tunnel core')
    sys.exit(0)
for name, data in tunnels.items():
    if isinstance(data, dict) and data.get('url'):
        when=data.get('generated_at','unknown')
        print(f"{name}: {data['url']} ({when})")
PY
}
