# Pi-hole

Pi-hole is included as the local DNS sinkhole and network ad-blocking service for the Raspberry Pi homelab stack.

## Service

Docker Compose service name:

```bash
pihole
```

Container name:

```bash
pi-pihole
```

## Start Pi-hole

```bash
homelab service start pihole
```

or:

```bash
docker compose up -d pihole
```

## Admin UI

```text
http://localhost:8081/admin
```

If you access the Pi over Tailscale or LAN, replace `localhost` with the Pi IP address, depending on your bind configuration.

## Ports

| Port | Protocol | Purpose |
|---:|---|---|
| 53 | TCP/UDP | DNS server |
| 8081 | TCP | Pi-hole admin web UI |

By default, DNS listens on all interfaces so other devices on your network can use the Pi as their DNS server. The admin web UI is bound to localhost by default for safer access.

## Environment Variables

Set these in `.env` when needed:

```env
PIHOLE_WEBPASSWORD=change_this_pihole_password
PIHOLE_HOSTNAME=pi-hole
PIHOLE_DNS_BIND=0.0.0.0
PIHOLE_WEB_BIND=127.0.0.1
PIHOLE_DNS_LISTENING_MODE=all
PIHOLE_DNS_UPSTREAMS=1.1.1.1;1.0.0.1
TIMEZONE=Australia/Melbourne
```

### Recommended First-Time Password Change

```bash
homelab pihole password '<new-password>'
```

## CLI Commands

| Command | Purpose |
|---|---|
| `homelab service status pihole` | Show Pi-hole container status |
| `homelab service start pihole` | Start Pi-hole |
| `homelab service stop pihole` | Stop Pi-hole |
| `homelab service restart pihole` | Restart Pi-hole |
| `homelab service logs pihole --follow` | Follow Pi-hole logs |
| `homelab service shell pihole` | Open a shell inside the Pi-hole container |
| `homelab service url pihole` | Show local admin URL |
| `homelab pihole block <domain>` | Add a domain to Pi-hole blacklist |
| `homelab pihole enable <domain>` | Add a domain to Pi-hole whitelist |
| `homelab pihole disable [seconds]` | Temporarily disable blocking |
| `homelab pihole enable-blocking` | Re-enable blocking |
| `homelab pihole update-gravity` | Update gravity/adlists |
| `homelab pihole stats` | Show Pi-hole terminal stats |
| `homelab pihole password <new-password>` | Set the admin password |

## Use Pi-hole as Network DNS

After Pi-hole is running, point your router or individual devices to the Raspberry Pi IP address as DNS.

Example:

```text
DNS server: <raspberry-pi-ip>
```

For safer testing, first configure one laptop or phone manually before changing router-wide DNS.

## Persistent Data

Pi-hole data is stored in:

```text
data/pihole/etc-pihole
data/pihole/etc-dnsmasq.d
```

These folders are ignored by Git and should be included in local backups.

## Troubleshooting

### Port 53 Already in Use

Check what is using DNS port 53:

```bash
sudo ss -tulpn | grep ':53'
```

Common conflicts include `systemd-resolved`, another DNS service, or an existing Pi-hole install.

### Admin UI Not Loading

Check container status and logs:

```bash
homelab service status pihole
homelab service logs pihole --follow
```

### DNS Not Working From Other Devices

Check that:

- the Pi has a stable LAN or Tailscale IP
- port 53 is not blocked by firewall rules
- `PIHOLE_DNS_BIND=0.0.0.0`
- the client device is using the Pi IP as DNS
