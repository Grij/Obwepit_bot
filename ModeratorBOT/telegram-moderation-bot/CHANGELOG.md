# Changelog

## [1.0.0] - В розробці (MVP)

### Додано
- **Base Infrastructure**: 
  - Налаштовано `python-telegram-bot` v20+ для асинхронної обробки.
  - SQLite база даних (`users`, `user_messages`, `incidents`).
  - In-memory `cache` для відстеження флуду і повторів (MD5).
- **Detectors**:
  - `SpamDetector`: Реагує на чорний список (`config/blacklist.json`), патерни ботів, капс. Має білий список для ігнорування `whitelisted_urls`.
  - `FloodDetector`: Спрацьовує на лімітовані часові вікна (`warning`, `timeout`, `ban`).
  - `FakeDistributionDetector`: Відстежує спам однаковими повідомленнями і реферальними лінками.
- **Rule Engine**:
  - Обробка JSON-умов (`rules.json`).
- **Commands**:
  - `/ban`, `/mute`, `/status`, `/rules`.
- **Deployment**:
  - `Dockerfile` та `docker-compose.yml` готові до роботи на VPS.
  - Bash-скрипти `setup.sh`, `backup.sh`, `restore.sh`.
