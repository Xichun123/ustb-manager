# Deployment and rollback

## Release images

Use one immutable tag for both images. A date plus the short Git SHA is recommended.

```bash
export IMAGE_TAG="$(date +%Y.%m.%d)-$(git rev-parse --short HEAD)"

docker build -t "ghcr.io/xichun123/ustb-manager-backend:${IMAGE_TAG}" backend
docker build -t "ghcr.io/xichun123/ustb-manager-frontend:${IMAGE_TAG}" frontend

docker push "ghcr.io/xichun123/ustb-manager-backend:${IMAGE_TAG}"
docker push "ghcr.io/xichun123/ustb-manager-frontend:${IMAGE_TAG}"
```

Do not overwrite a published release tag. The backend build is frozen by `uv.lock`; the frontend build uses `npm ci` and `package-lock.json`.

## First deployment

```bash
mkdir -p /opt/ustb-manager
cd /opt/ustb-manager
cp /path/to/repository/docker-compose.yml .
cp /path/to/repository/.env.example .env
```

Set these values in `.env`:

- `IMAGE_TAG`: the immutable tag built above.
- `SESSION_ENCRYPTION_KEY`: a persistent Fernet key.
- `COOKIE_SECURE=true` when the public endpoint uses HTTPS.
- `APP_PORT`: loopback port consumed by Caddy or another reverse proxy.

Generate a Fernet key once:

```bash
python3 -c 'import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())'
```

Then deploy:

```bash
docker compose config --quiet
docker compose pull
docker compose up -d --wait
docker compose ps
```

The backend readiness check validates SQLite without contacting BYYT. Use:

- `/api/health/live` for process liveness.
- `/api/health/ready` for deployment readiness.

## Upgrade

Record the current tag before changing it:

```bash
cp .env ".env.before-$(date +%Y%m%d%H%M%S)"
```

Set the new immutable `IMAGE_TAG`, then run:

```bash
docker compose pull
docker compose up -d --wait
docker compose ps
docker compose logs --tail=100 backend frontend
```

Do not rotate `SESSION_ENCRYPTION_KEY` during a normal upgrade. The `backend-data` volume contains encrypted sessions and survives container replacement.

## Rollback

Restore the previous `IMAGE_TAG` while retaining the same encryption key and volume:

```bash
# Edit IMAGE_TAG in .env to the previous known-good tag.
docker compose pull
docker compose up -d --wait
docker compose ps
```

A rollback does not require BYYT availability. If readiness fails, inspect storage/configuration with `docker compose logs backend`; do not delete `backend-data` unless invalidating all persisted sessions is intentional.

## Reverse proxy

Caddy example:

```caddy
ustb.example.com {
    reverse_proxy 127.0.0.1:8032
}
```

Keep port 8032 bound to loopback as configured by Compose. Caddy provides public TLS, which is required when `COOKIE_SECURE=true`.

## Compatibility rollout

The backend temporarily retains legacy read/write route adapters for already-published miniapp versions. Remove them only after logs show old route usage has fallen to the accepted release threshold. New Web and miniapp code uses `/api/me`, `/api/academic/*`, `/api/grades`, `/api/schedule`, `/api/exams`, `/api/notices`, and `/api/course-selection/*`.
