# n8n

## Overview

n8n provides workflow automation, webhook handling, AI pipelines, cron jobs, and integrations.

Local URL:

```text
http://localhost:5678
```

## Start n8n

```bash
homelab n8n start
```

## Stop n8n

```bash
homelab n8n stop
```

## Restart n8n

```bash
homelab n8n restart
```

## Check Status

```bash
homelab n8n status
```

## View Logs

```bash
homelab n8n logs
```

## Open Shell

```bash
homelab n8n shell
```

## Show URL

```bash
homelab n8n url
```

## Common Workflows

### Restart After Environment Changes

```bash
homelab n8n restart
```

### Validate Container

```bash
homelab n8n logs
```

### Open Database Shell

```bash
homelab postgres shell
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
homelab n8n restart
```

### Webhooks Not Working

Check:

- Cloudflare Tunnel
- `N8N_WEBHOOK_URL`
- exposed HTTPS endpoint
