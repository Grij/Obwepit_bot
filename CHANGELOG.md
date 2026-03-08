# CHANGELOG — ОБЩЕПІТ

## 2026-03-08

### v1.4.4 — Dashboard Stability Hotfix
- Виправлено регресію рендеру графіка `Динаміка Апрувів`:
  - причина: у `templates/base.html` не рендерився блок `{% block scripts %}`, через що JS із `templates/index.html` не виконувався.
  - fix: додано `{% block scripts %}{% endblock %}` перед `</body>`.
- Виправлено видимість пункту меню `Модератор`:
  - причина: навігація могла не вміщатися на частині екранів.
  - fix: додано адаптивний wrapper (`.top-bar`) та `flex-wrap` для `.nav-links`.
- Деплой виконано на VPS:
  - `/opt/gemini/services/obwepit_bot`
  - `docker compose up -d --build web`

### v1.4.3 — OAuth Recovery Hotfix
- Відновлено авторизацію Google OAuth для web-дашборду.
- Додано guard у `web.py`: якщо `GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET` відсутні, маршрут `/auth/google` повертає редірект на `/login?error=oauth_not_configured` замість невалідного запиту в Google.
- Оновлено `templates/login.html`:
  - повідомлення про помилку `oauth_not_configured`;
  - блокування кнопки Google Login при відсутній OAuth-конфігурації.
- Розширено `src/.env.example` обов'язковими змінними:
  - `SECRET_KEY`
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - `ALLOWED_EMAIL`
  - `POST_SIGNATURE_LINK`

## Post-Deploy Smoke Checklist
- `GET /login` повертає `200`.
- `GET /auth/google` повертає `302` з query-параметром `client_id=...`.
- На головній сторінці видно графік `Динаміка Апрувів`.
- У верхній навігації є вкладка `Модератор`.
- `GET /moderator` відкривається без `500`.
