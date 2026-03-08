# Гайд Для Послідовників (Obwepit_bot)

## Мета
Цей документ описує єдиний робочий процес команди: від доступу до репозиторію до безпечного деплою у production.

## 1) Доступи
- GitHub org/user: `Grij`
- Репозиторій: `https://github.com/Grij/Obwepit_bot`
- Доступ до VPS: `evohub-vps` (`~/.ssh/config`)

## 2) Бранч-модель (обов'язково)
- `main` — тільки production
- `staging` — передпрод перевірка
- `develop` — інтеграція змін
- `feature/*` — новий функціонал
- `hotfix/*` — критичні правки з `main`

## 3) Правила merge
1. Розробка: `feature/*` -> `develop` (PR).
2. Підготовка релізу: `develop` -> `staging` (PR).
3. Прод-реліз: `staging` -> `main` (PR).
4. Критичний фікс: `hotfix/*` -> `main`, потім back-merge у `develop`.

## 4) Захист гілок (вже ввімкнено)
Для `main` і `staging`:
- мінімум 1 approval у PR
- `required linear history`
- `required conversation resolution`
- force push/delete заборонені

## 5) Локальний старт
```bash
git clone git@github.com:Grij/Obwepit_bot.git
cd Obwepit_bot
git checkout develop

cd src
cp .env.example .env
# Заповни реальні значення в .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn web:app --reload --port 8000
```

## 6) Мінімальний quality gate перед PR
```bash
python3 -m py_compile src/web.py
```
- Перевірити, що в diff немає секретів (`.env`, токени, ключі).
- Оновити docs/changelog, якщо змінена поведінка.

## 7) Production deploy
```bash
ssh evohub-vps
cd /opt/gemini/services/obwepit_bot
docker compose up -d --build web
```

## 8) Smoke-check після деплою
1. `/login` відкривається.
2. `/auth/google` дає `302` з `client_id`.
3. На дашборді видно графік `Динаміка Апрувів`.
4. Вкладка `Модератор` видима і `/moderator` відкривається.

## 9) Обов'язкові артефакти релізу
- Оновлений `CHANGELOG.md`
- PR з коротким test plan
- За потреби: оновлення `docs/DEPLOYMENT.md` і `docs/RELEASE.md`
- Для змін модуля модерації: оновлення `docs/MODERATOR_CAPABILITIES.md`
