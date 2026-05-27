# Pi-hole

## Overview

Pi-hole provides DNS-level ad blocking and local network DNS filtering.

Admin URL:

```text
http://localhost:8081/admin
```

## Start Pi-hole

```bash
homelab pihole start
```

## Stop Pi-hole

```bash
homelab pihole stop
```

## Restart Pi-hole

```bash
homelab pihole restart
```

## Check Status

```bash
homelab pihole status
```

## View Logs

```bash
homelab pihole logs
```

## Open Shell

```bash
homelab pihole shell
```

## Show URL

```bash
homelab pihole url
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
