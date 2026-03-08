# Obwepit_bot

Production repository for the `ОБЩЕПІТ` ecosystem:
- Telegram approval bot
- FastAPI web dashboard
- Feedback bot
- Moderator module integration

## Repository Layout
- `src/` — main bot + web dashboard + feedback service
- `ModeratorBOT/` — moderator module source and related docs
- `docs/` — development process and operational standards
- `.github/workflows/` — CI checks

## Branch Strategy
- `main` — production only
- `staging` — pre-production verification
- `develop` — integration branch for completed features
- `feature/*` — short-lived feature branches
- `hotfix/*` — urgent fixes from `main`

Detailed rules: `docs/BRANCHING.md`
New team onboarding flow: `docs/FOLLOWER_GUIDE.md`

## Quick Start (Local)
```bash
cd src
cp .env.example .env
# fill real secrets in .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn web:app --reload --port 8000
```

## Deploy (VPS)
```bash
cd /opt/gemini/services/obwepit_bot
docker compose up -d --build web
```

Full deploy procedure: `docs/DEPLOYMENT.md`

## Current Docs
- `CHANGELOG.md`
- `PRD_Общепіт.md`
- `Інструкція_по_деплою.md`
- `docs/FOLLOWER_GUIDE.md`
- `docs/MODERATOR_CAPABILITIES.md`
