#!/bin/bash

# Example named Cloudflare Tunnel launcher
# Copy to:
# local/start-named-tunnel.sh

cloudflared tunnel --config cloudflared/config.yml run
