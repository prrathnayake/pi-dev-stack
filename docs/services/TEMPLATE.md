# SERVICE_NAME

## Overview

Describe what the service does.

## Start Service

```bash
homelab SERVICE_NAME start
```

## Stop Service

```bash
homelab SERVICE_NAME stop
```

## Restart Service

```bash
homelab SERVICE_NAME restart
```

## Check Status

```bash
homelab SERVICE_NAME status
```

## View Logs

```bash
homelab SERVICE_NAME logs
```

## Open Shell

```bash
homelab SERVICE_NAME shell
```

## Show URL

```bash
homelab SERVICE_NAME url
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
homelab SERVICE_NAME logs
```

### Restart Service

```bash
homelab SERVICE_NAME restart
```

### Inspect Container

```bash
homelab service inspect SERVICE_NAME
```
