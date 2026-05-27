# Code Server

## Overview

Code Server provides VS Code in the browser.

Local URL:

```text
https://localhost:8443
```

## Start Service

```bash
docker compose --profile extras up -d code-server
```

Then:

```bash
homelab code-server status
```

## Restart Service

```bash
homelab code-server restart
```

## Logs

```bash
homelab code-server logs
```

## Open Shell

```bash
homelab code-server shell
```

## Persistent Data

```text
data/code-server/
```

## Workspace Mapping

The entire repository is mounted into:

```text
/workspace
```

## Troubleshooting

### Browser SSL Warning

Expected when using self-signed local HTTPS.

### Reset Password

Update `.env`:

```env
CODE_SERVER_PASSWORD=new_password
```

Then restart:

```bash
homelab code-server restart
```
