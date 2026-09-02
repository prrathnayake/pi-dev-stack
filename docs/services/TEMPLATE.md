# SERVICE_NAME

## Overview

Describe what the service does.

## Start Service

```bash
homelab service start SERVICE_NAME
```

## Stop Service

```bash
homelab service stop SERVICE_NAME
```

## Restart Service

```bash
homelab service restart SERVICE_NAME
```

## Check Status

```bash
homelab service status SERVICE_NAME
```

## View Logs

```bash
homelab service logs SERVICE_NAME --follow
```

## Open Shell

```bash
homelab service shell SERVICE_NAME
```

## Show URL

```bash
homelab service url SERVICE_NAME
```

## Docker Compose Alternative

```bash
docker compose up -d SERVICE_NAME
docker compose stop SERVICE_NAME
```

## Persistent Data

```text
data/SERVICE_NAME/
```

## Common Troubleshooting

### Service Not Starting

```bash
homelab service logs SERVICE_NAME --follow
```

### Restart Service

```bash
homelab service restart SERVICE_NAME
```

### Inspect Container

```bash
homelab service inspect SERVICE_NAME
```
