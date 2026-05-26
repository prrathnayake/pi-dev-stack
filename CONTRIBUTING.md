# Contributing

Thank you for contributing to Pi Dev Stack.

## Development workflow

```bash
git clone https://github.com/prrathnayake/pi-dev-stack.git
cd pi-dev-stack
chmod +x homelab pi-stack setup.sh stop.sh tunnel.sh validate.sh
```

Run validation:

```bash
./homelab doctor
./homelab validate
```

## Important rules

Do not store secrets in Git.

Do not modify local-only ignored files inside pull requests:

- .env
- .env.local
- data/
- logs/
- local/
- docker-compose.override.yml

## Local customization

Use:

```bash
cp docker-compose.override.example.yml docker-compose.override.yml
```

Store custom scripts under:

```text
local/
```

## Testing

CI validates:

- shell scripts
- Docker Compose config
- homelab CLI
- PostgreSQL
- Redis
- n8n startup
- cloudflared installation

## Pull requests

Please:

- keep scripts POSIX compatible when possible
- avoid breaking Raspberry Pi ARM64 support
- test with Docker Compose before submitting
- update documentation when adding features

## License

By contributing, you agree that your contributions are licensed under the MIT License.
