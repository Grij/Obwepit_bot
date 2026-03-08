# 📋 СПЕЦІФІКЕЙШН: Модуль модерації Telegram-бота

**Версія:** 1.0  
**Дата:** 2026-03-08  
**Статус:** Ready for AI Implementation  
**Цільова платформа:** VPS (Linux Ubuntu/Debian)

---

## 1. ОГЛЯД МОДУЛЯ

### 1.1 Мета
Розробити універсальний модуль модерації для Telegram-групи, який автоматично детектує та блокує:
- **Спам** (повторювальні повідомлення, комерційні посилання)
- **Флуд** (масові повідомлення в короткий час)
- **Фейк-розсилки** (автоматичні розсилки, боти)
- **Токсичний контент** (чорний список слів)
- **Аномальну активність** (раптові стрибки в повідомленнях)

### 1.2 Архітектура
```
┌─────────────────────────────────────────────────────────┐
│                  Telegram Group                          │
└────────────────────────┬────────────────────────────────┘
                         │
                    (Updates via API)
                         │
        ┌────────────────▼────────────────┐
        │    Telegram Bot (python-telegram-bot v20+)      │
        └────────────────┬────────────────┘
                         │
    ┌────────┬───────────┼───────────┬────────┐
    │        │           │           │        │
    ▼        ▼           ▼           ▼        ▼
[Content]  [User]   [Flood]     [Pattern]  [Action]
[Detector] [Monitor] [Detector]  [Matcher]  [Executor]
    │        │           │           │        │
    └────────┴───────────┼───────────┴────────┘
                         │
        ┌────────────────▼────────────────┐
        │     SQLite/PostgreSQL Database  │
        │  (users, logs, rules, cache)    │
        └────────────────────────────────┘
```

### 1.3 Вимоги до системи
- **Python:** 3.10+
- **OS:** Linux (Ubuntu 22.04+ або Debian 12+)
- **Пам'ять:** Мінімум 512MB, рекомендовано 1GB+
- **Дисковий простір:** 2GB (для логів і БД)
- **Мережа:** Постійне інтернет-з'єднання (Telegram API)

---

## 2. ФУНКЦІОНАЛЬНІ МОДУЛІ

### 2.1 Detector: Спам-детектор

**Логіка:**
- Отримує повідомлення від користувача
- Перевіряє 5 критеріїв:
  1. Наявність у чорному списку слів (точне та нечітке збігання)
  2. Повтор того ж повідомлення від одного користувача (N разів за M секунд)
  3. Наявність комерційних URL (regex-паттерни)
  4. Кількість емодзі або символів капсу (>40%)
  5. Схожість на відомих спам-ботів (за паттернами)

**Конфіг:**
```json
{
  "spam_detector": {
    "blacklist_words": ["casino", "xxx", "кредит"],
    "repeat_threshold": {"count": 3, "time_window": 60},
    "caps_threshold": 0.4,
    "emoji_threshold": 0.5,
    "url_patterns": ["bit.ly", "t.me/+", "casino"],
    "bot_patterns": ["вітаю на", "підпишись", "заробляй"]
  }
}
```

**Вихід:**
```python
SpamDetectionResult(
    is_spam=bool,
    confidence=0.0-1.0,
    reason="blacklist_match | repeat_message | suspicious_urls | all_caps | emoji_spam | bot_pattern",
    details={"matched_word": "xxx", "count": 3}
)
```

---

### 2.2 FloodDetector: Детектор флуду

**Логіка:**
- Відстежує кількість повідомлень на користувача в часовому вікні
- Три рівні тривоги:
  1. **Warning** (≥5 повідомлень за 10 сек) → видалення повідомлень
  2. **Timeout** (≥10 за 30 сек) → муте на 5 хвилин
  3. **Ban** (≥20 за 60 сек) → видалення з групи

**Конфіг:**
```json
{
  "flood_detector": {
    "levels": [
      {"name": "warning", "messages": 5, "window": 10, "action": "delete"},
      {"name": "timeout", "messages": 10, "window": 30, "action": "mute", "duration": 300},
      {"name": "ban", "messages": 20, "window": 60, "action": "remove"}
    ],
    "exclude_admins": true,
    "grace_period": 5
  }
}
```

**Вихід:**
```python
FloodDetectionResult(
    is_flood=bool,
    level="warning | timeout | ban | none",
    action="delete | mute | remove | none"
)
```

---

### 2.3 FakeDistributionDetector: Детектор фейк-розсилок

**Логіка:**
- Аналізує метадані повідомлення: реферальні посилання, одне посилання, 100% однаковий текст від різних користувачів
- Визначає, чи повідомлення скопійоване (форвардоване) мільйон разів
- Перевіряє схожість на шаблони розсилок

**Сигнатури поганих розсилок:**
```json
{
  "fake_distribution": {
    "referral_domains": ["t.me/+", "ref.", "bonus", "app.link"],
    "copy_threshold": 5,
    "time_window": 300,
    "template_patterns": ["заробляй на дому", "клікни сюди", "обмежена пропозиція"]
  }
}
```

**Вихід:**
```python
FakeDistributionResult(
    is_fake=bool,
    detection_type="referral | copied | template | forwarded",
    similar_messages_count=5
)
```

---

### 2.4 UserMonitor: Моніторинг користувачів

**Логіка:**
- Ведить статистику на користувача:
  - Кількість повідомлень за день
  - Аномалії (раптовий стрибок)
  - Репутація (попередження, муте, бани)
  - IP/Device ID (якщо можливо визначити)

**Зберігання:**
```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    is_bot BOOLEAN,
    join_date TIMESTAMP,
    message_count INTEGER,
    warn_count INTEGER,
    mute_until TIMESTAMP,
    is_banned BOOLEAN,
    ban_reason TEXT,
    last_activity TIMESTAMP
);

CREATE TABLE user_messages (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    message_id INTEGER,
    text TEXT,
    timestamp TIMESTAMP,
    is_deleted BOOLEAN
);

CREATE TABLE incidents (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    incident_type TEXT,
    severity TEXT,
    action_taken TEXT,
    timestamp TIMESTAMP,
    resolved BOOLEAN
);
```

---

### 2.5 ActionExecutor: Виконавець дій

**Список доступних дій:**
1. **delete** — видалити повідомлення
2. **warn** — видати попередження (сповіщення в чаті)
3. **mute** — заблокувати можливість писати на N секунд
4. **restrict** — обмежити права (без посилань, медіа)
5. **remove** — видалити користувача з групи
6. **ban** — добавити в чорний список (на постійно)
7. **report_admin** — позначити для amministrator review

**Конфіг дій:**
```json
{
  "actions": {
    "delete": {"delay": 0, "notify": false},
    "warn": {"delay": 0, "notify": true, "message": "⚠️ Порушення правил групи!"},
    "mute": {"delay": 0, "notify": true},
    "restrict": {"delay": 0, "notify": true, "duration": 3600},
    "remove": {"delay": 5, "notify": true},
    "ban": {"delay": 0, "notify": false},
    "report_admin": {"delay": 0, "notify": false, "channel": "admin_logs"}
  }
}
```

---

### 2.6 RuleEngine: Система правил

**Структура правила:**
```python
Rule = {
    "id": "rule_1_spam_casino",
    "name": "Spam: Casino websites",
    "enabled": True,
    "priority": 100,
    "detectors": ["spam_detector"],
    "condition": {
        "detector": "spam_detector",
        "field": "reason",
        "operator": "equals",
        "value": "blacklist_match"
    },
    "actions": [
        {"action": "delete", "delay": 0},
        {"action": "warn", "delay": 1},
        {"action": "report_admin", "delay": 2}
    ],
    "exceptions": {
        "user_ids": [],
        "user_roles": ["admin", "moderator"],
        "channels": []
    }
}
```

**Приклад правил для базової конфігурації:**
```json
{
  "rules": [
    {
      "id": "spam_1",
      "name": "Чорний список слів",
      "detectors": ["spam_detector"],
      "condition": {"reason": "blacklist_match"},
      "actions": ["delete", "warn"],
      "priority": 100
    },
    {
      "id": "flood_1",
      "name": "Детектор флуду - Warning",
      "detectors": ["flood_detector"],
      "condition": {"level": "warning"},
      "actions": ["delete"],
      "priority": 90
    },
    {
      "id": "flood_2",
      "name": "Детектор флуду - Ban",
      "detectors": ["flood_detector"],
      "condition": {"level": "ban"},
      "actions": ["remove", "report_admin"],
      "priority": 95
    },
    {
      "id": "fake_1",
      "name": "Фейк-розсилки",
      "detectors": ["fake_distribution_detector"],
      "condition": {"is_fake": true},
      "actions": ["delete", "warn"],
      "priority": 90
    }
  ]
}
```

---

## 3. АРХІТЕКТУРА КОДОВОЇ БАЗИ

### 3.1 Структура проекту
```
telegram-moderation-bot/
├── config/
│   ├── config.yaml                 # Основна конфігурація
│   ├── rules.json                  # Правила модерації
│   └── blacklist.json              # Чорний список слів
├── src/
│   ├── __init__.py
│   ├── main.py                     # Точка входу
│   ├── bot.py                      # Основний обробник Telegram-апі
│   ├── database.py                 # SQLite операції
│   ├── detectors/
│   │   ├── __init__.py
│   │   ├── base.py                 # Базовий клас детектора
│   │   ├── spam_detector.py        # Спам-детектор
│   │   ├── flood_detector.py       # Флуд-детектор
│   │   └── fake_distribution.py    # Детектор розсилок
│   ├── actions/
│   │   ├── __init__.py
│   │   └── executor.py             # Виконавець дій
│   ├── rules/
│   │   ├── __init__.py
│   │   └── engine.py               # Rule engine
│   ├── user/
│   │   ├── __init__.py
│   │   └── monitor.py              # Моніторинг користувачів
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py               # Логування
│   │   └── cache.py                # In-memory кеш
│   └── handlers/
│       ├── __init__.py
│       ├── message_handler.py      # Обробник повідомлень
│       ├── admin_commands.py       # Команди адміна
│       └── callbacks.py            # Callback-обробники
├── migrations/
│   └── 001_init.sql                # Схема БД
├── logs/
│   └── bot.log                     # Лог-файл
├── .env.example                    # Приклад змінних оточення
├── requirements.txt                # Python залежності
├── docker-compose.yml              # Docker-конфігурація
├── Dockerfile                      # Docker-образ
└── README.md                       # Документація

```

### 3.2 Залежності (requirements.txt)
```
python-telegram-bot==20.7
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
sqlalchemy==2.0.23
aiofiles==23.2.1
aiohttp==3.9.1
regex==2023.12.25
apscheduler==3.10.4
structlog==23.3.0
```

---

## 4. ЛОГІКА ОБРОБКИ ПОВІДОМЛЕННЯ

### 4.1 Flow діаграма (текстова)
```
┌─ Нове повідомлення від користувача
│
├─→ [PreCheck]
│   ├─ Від адміна? → skip moderation → POST
│   └─ Від удалення? → skip → END
│
├─→ [ContentAnalysis]
│   ├─ SpamDetector → detect_spam()
│   ├─ FakeDistributionDetector → detect_fake()
│   └─ результати → cache
│
├─→ [UserAnalysis]
│   ├─ FloodDetector → detect_flood()
│   ├─ UserMonitor → record_message()
│   └─ results → cache
│
├─→ [RuleMatching]
│   ├─ Пройти усі правила по приоритету
│   ├─ Для кожного правила:
│   │  ├─ Перевірити умову
│   │  ├─ Перевірити винятки
│   │  └─ Якщо підходить → добавити дії
│   └─ Агрегувати дії
│
├─→ [ActionExecution]
│   ├─ Сортувати дії по затримці
│   ├─ Для кожної дії:
│   │  ├─ Виконати (delete, warn, mute, etc)
│   │  ├─ Логувати результат
│   │  └─ Ошибки → retry or report
│   └─ Зберегти інцидент в БД
│
└─→ END
```

### 4.2 Pseudocode обробника
```python
async def handle_new_message(message: Message):
    # 1. Pre-checks
    if is_admin(message.from_user):
        await store_message(message)
        return
    
    # 2. Detect spam & fake distribution
    spam_result = spam_detector.detect(message)
    fake_result = fake_dist_detector.detect(message)
    
    # 3. Detect flood
    flood_result = flood_detector.detect(message.from_user)
    
    # 4. Record user activity
    user_monitor.record_message(message)
    
    # 5. Find matching rules
    matched_rules = rule_engine.find_matching_rules(
        spam_result, fake_result, flood_result
    )
    
    # 6. Collect actions
    actions = []
    for rule in matched_rules:
        if should_apply_rule(rule, message):
            actions.extend(rule.actions)
    
    # 7. Execute actions
    if actions:
        await action_executor.execute(actions, message)
        await log_incident(message, actions)
    else:
        await store_message(message)
```

---

## 5. ІНТЕРФЕЙС ДЛЯ АДМІНІСТРАТОРА

### 5.1 Команди бота
```
/start - Інформація про бота
/status - Статус модерації
/stats - Статистика групи
/whitelist add @user - Добавити користувача у винятки
/whitelist remove @user - Видалити з винятків
/ban @user [reason] - Забанити користувача
/unban @user - Розбанити
/mute @user [seconds] - Замутити на N секунд
/unmute @user - Розмутити
/warn @user [reason] - Видати попередження
/warns @user - Переглянути попередження
/rules list - Список активних правил
/rules enable/disable [rule_id] - Увімкнути/вимкнути правило
/logs [N] - Останні N інцидентів
/export_logs - Експортувати логи за період
/reload_config - Перезавантажити конфіг
```

### 5.2 Admin Panel (опційно)
```
URL: https://your-vps-ip:8000/admin
├─ Dashboard
│  ├─ Статистика: messages/day, incidents, bans
│  ├─ Топ спамерів
│  └─ Здоров'я системи
├─ Users
│  ├─ Пошук користувача
│  ├─ Переглід історії
│  └─ Дії: ban/mute/warn
├─ Rules
│  ├─ Таблиця правил
│  ├─ Создание/редагування правил
│  └─ Тестування правила на історичних даних
├─ Logs
│  ├─ Фільтрація
│  ├─ Експорт в CSV/JSON
│  └─ Пошук
└─ Settings
   ├─ Конфіг детекторів
   ├─ Чорний список
   └─ Планування резервних копій
```

---

## 6. ДЕТАЛІ РЕАЛІЗАЦІЇ

### 6.1 Обробка помилок
```python
class ModeratorException(Exception):
    """Базова помилка модератора"""
    pass

class DetectorError(ModeratorException):
    """Помилка детектора"""
    pass

class ActionExecutionError(ModeratorException):
    """Помилка виконання дії"""
    pass

class DatabaseError(ModeratorException):
    """Помилка БД"""
    pass
```

**Стратегія:**
- Усі помилки логуються з контекстом
- Для критичних дій (ban, mute) → retry до 3 разів
- Якщо не вдалося → report_admin + log

### 6.2 Логування
```
2024-03-08 14:22:15 [INFO] Bot started. Group: -1001234567890
2024-03-08 14:22:45 [WARNING] User 123 detected: spam_match (confidence=0.95)
2024-03-08 14:22:46 [ACTION] Message 456 deleted (rule: spam_1)
2024-03-08 14:22:47 [ACTION] User 123 warned (spam_1)
2024-03-08 14:23:00 [ERROR] Failed to mute user 789 (API timeout)
2024-03-08 14:23:01 [RETRY] Retrying mute action... Attempt 2/3
2024-03-08 14:23:02 [SUCCESS] User 789 muted for 300s
```

### 6.3 Кеш
```python
class Cache:
    - user_activity[user_id] → {timestamps: [t1, t2...]}
    - message_hashes[hash] → {count: N, users: [id1, id2...]}
    - regex_patterns → compiled regex objects
    - TTL: 1 час для user_activity, 24 години для message_hashes
```

### 6.4 Deployment
```bash
# 1. Клонування репо
git clone https://github.com/your-org/telegram-moderation-bot.git
cd telegram-moderation-bot

# 2. Встановлення залежностей
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Конфігурація
cp .env.example .env
nano .env  # Додати TELEGRAM_BOT_TOKEN, DATABASE_URL

# 4. Ініціалізація БД
python3 -m src.database init

# 5. Запуск
python3 -m src.main

# ЛІ використовувати Docker:
docker-compose up -d
```

---

## 7. ТЕСТУВАННЯ

### 7.1 Юніт-тести
```python
# tests/test_spam_detector.py
def test_blacklist_word_detection():
    detector = SpamDetector(config)
    result = detector.detect("Привіт casino друзі")
    assert result.is_spam == True
    assert result.reason == "blacklist_match"
    assert result.confidence > 0.8

def test_caps_detection():
    detector = SpamDetector(config)
    result = detector.detect("КУПИ СЕЙЧАС!!!!")
    assert result.is_spam == True
```

### 7.2 Інтеграційні тести
```python
# tests/test_bot_integration.py
async def test_message_moderation_flow():
    bot = TelegramBot(config)
    message = create_test_message("casino")
    
    await bot.handle_message(message)
    
    # Перевірити:
    # 1. Повідомлення видалено
    # 2. Користувач отримав попередження
    # 3. Інцидент залогований
```

---

## 8. МОНІТОРИНГ І ОБСЛУГОВУВАННЯ

### 8.1 Метрики для моніторингу
```
- messages_processed/hour
- spam_detected/hour
- flood_incidents/hour
- api_errors/hour
- database_response_time_ms
- rule_evaluation_time_ms
- action_execution_success_rate
- uptime_%
```

### 8.2 Алерти
```
- Bot offline for >5 minutes
- Database error rate >5%
- API rate limit exceeded
- Unusual spike in spam/flood
- Rule execution time >1s
```

### 8.3 Резервна копія
```bash
# Щодня о 02:00
0 2 * * * /opt/telegram-bot/backup.sh
```

---

## 9. РОЗШИРЕННЯ (FUTURE)

- [ ] ML-модель для детектування фейк-аккаунтів (за поведінкою)
- [ ] Інтеграція з CaptCha для підтвердження користувачів
- [ ] Детектування мовою на основі NLP
- [ ] Вебхук для зовнішніх систем (Discord, Slack notifications)
- [ ] Графіки та аналітика в web-панелі
- [ ] A/B тестування правил

---

## 10. КРИТЕРІЇ УСПІХУ

✅ Бот запускається без помилок на VPS  
✅ Детектує спам-повідомлення за <500ms  
✅ Флуд детектується реал-тайм  
✅ Усі дії виконуються (delete, mute, warn, ban)  
✅ Логування повне і читаємо  
✅ Конфіг гарячо перезавантажується  
✅ Резервні копії БД діють  
✅ API rate limits не перевищуються  
✅ Документація повна й актуальна  

---

## 11. КОНТАКТИ І ПІДТРИМКА

**На випадок проблем:**
- Логи: `/var/log/telegram-bot/bot.log`
- Конфіг перевіряти: `config/config.yaml`
- БД відновлювати з backup: `./restore.sh`
- Рестарт: `systemctl restart telegram-bot`

---

**Готово для передачі AI-агенту. Цей спеціфікейшн містить усю інформацію для повної розробки модуля.**
