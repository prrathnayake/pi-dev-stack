# Service CLI Documentation

Every service in Pi Dev Stack can be managed through the `homelab` CLI.

## Common Command Pattern

Use either the generic service command:

```bash
homelab service <action> <service>
```

or the direct service alias:

```bash
homelab <service> <action>
```

## Common Actions

| Action | Purpose |
|---|---|
| `start` | Start the service container |
| `stop` | Stop the service container |
| `restart` | Restart the service container |
| `status` | Show service status |
| `logs` | Follow service logs |
| `shell` | Open shell inside the container |
| `inspect` | Inspect container metadata |
| `url` | Show the local URL when available |

## Service Guides

| Service | Guide |
|---|---|
| PostgreSQL | [postgres.md](postgres.md) |
| Redis | [redis.md](redis.md) |
| n8n | [n8n.md](n8n.md) |
| Ollama | [ollama.md](ollama.md) |
| Open WebUI | [open-webui.md](open-webui.md) |
| Portainer | [portainer.md](portainer.md) |
| Dozzle | [dozzle.md](dozzle.md) |
| Uptime Kuma | [uptime-kuma.md](uptime-kuma.md) |
| Homepage | [homepage.md](homepage.md) |
| Glances | [glances.md](glances.md) |
| Home Assistant | [home-assistant.md](home-assistant.md) |
| Pi-hole | [pihole.md](pihole.md) |
| Watchtower | [watchtower.md](watchtower.md) |
| Traefik | [traefik.md](traefik.md) |
| Vaultwarden | [vaultwarden.md](vaultwarden.md) |
| Gitea | [gitea.md](gitea.md) |
| MinIO | [minio.md](minio.md) |
| Syncthing | [syncthing.md](syncthing.md) |
| FileBrowser | [filebrowser.md](filebrowser.md) |
| Netdata | [netdata.md](netdata.md) |
| Prometheus | [prometheus.md](prometheus.md) |
| Grafana | [grafana.md](grafana.md) |
| Mosquitto | [mosquitto.md](mosquitto.md) |
| Node-RED | [nodered.md](nodered.md) |
| Code Server | [code-server.md](code-server.md) |

## Extra Profile Services

Some services are in the Docker Compose `extras` profile. Start them with:

```bash
docker compose --profile extras up -d <service>
```

After they are running, the `homelab <service> <action>` pattern can control them.
