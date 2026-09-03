# n8n

## Overview

n8n provides workflow automation, webhook handling, AI pipelines, cron jobs, and integrations.

Local URL:

```text
http://localhost:5678
```

## Start n8n

```bash
homelab service start n8n
```

## Stop n8n

```bash
homelab service stop n8n
```

## Restart n8n

```bash
homelab service restart n8n
```

## Check Status

```bash
homelab service status n8n
```

## View Logs

```bash
homelab service logs n8n --follow
```

## Open Shell

```bash
homelab service shell n8n
```

## Show URL

```bash
homelab service url n8n
```

## Common Workflows

### Restart After Environment Changes

```bash
homelab service restart n8n
```

### Validate Container

```bash
homelab service logs n8n --follow
```

### Open Database Shell

```bash
homelab service shell postgres
```

## Persistent Data

```text
data/n8n/
```

## Backup Notes

n8n data is included in:

```bash
homelab backup
```

## Troubleshooting

### Permission Errors

```bash
sudo chown -R 1000:1000 data/n8n
homelab service restart n8n
```

### Webhooks Not Working

Check:

- Cloudflare Tunnel
- `N8N_WEBHOOK_URL`
- exposed HTTPS endpoint
