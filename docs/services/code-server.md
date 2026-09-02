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
homelab service status code-server
```

## Restart Service

```bash
homelab service restart code-server
```

## Logs

```bash
homelab service logs code-server --follow
```

## Open Shell

```bash
homelab service shell code-server
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
homelab service restart code-server
```
