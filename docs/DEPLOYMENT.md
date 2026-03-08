# Deployment (VPS)

## Target
- Host path: `/opt/gemini/services/obwepit_bot`
- Main service for dashboard: `web`

## Required ENV
In `src/.env`:
- `BOT_TOKEN`
- `SECRET_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `ALLOWED_EMAIL`
- `POST_SIGNATURE_LINK`

## Deploy Commands
```bash
cd /opt/gemini/services/obwepit_bot
docker compose up -d --build web
```

## Smoke Check
1. `docker compose ps` -> `obwepit_web` is `Up`
2. `/login` loads
3. `/auth/google` returns 302 with `client_id`
4. Approvals chart visible on dashboard
5. `Модератор` tab visible and `/moderator` opens
