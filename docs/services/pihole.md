# Pi-hole

## Overview

Pi-hole provides DNS-level ad blocking and local network DNS filtering.

Admin URL:

```text
http://localhost:8081/admin
```

## Start Pi-hole

```bash
homelab service start pihole
```

## Stop Pi-hole

```bash
homelab service stop pihole
```

## Restart Pi-hole

```bash
homelab service restart pihole
```

## Check Status

```bash
homelab service status pihole
```

## View Logs

```bash
homelab service logs pihole --follow
```

## Open Shell

```bash
homelab service shell pihole
```

## Show URL

```bash
homelab service url pihole
```

## Block Domain

```bash
homelab pihole block ads.example.com
```

## Allow Domain

```bash
homelab pihole allow google.com
```

## Temporarily Disable Blocking

```bash
homelab pihole disable 300
```

## Re-enable Blocking

```bash
homelab pihole enable-blocking
```

## Update Gravity Lists

```bash
homelab pihole gravity
```

## View Stats

```bash
homelab pihole stats
```

## Change Password

```bash
homelab pihole password '<new-password>'
```

## Persistent Data

```text
data/pihole/etc-pihole
data/pihole/etc-dnsmasq.d
```

## Troubleshooting

### Port 53 Conflict

```bash
sudo ss -tulpn | grep ':53'
```

### DNS Not Working

Check:

- router DNS settings
- firewall rules
- DNS bind configuration
