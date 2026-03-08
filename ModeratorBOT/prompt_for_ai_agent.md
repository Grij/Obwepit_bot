# 🤖 ПРОМПТ ДЛЯ AI-АГЕНТА: Розробка модуля модерації Telegram-бота

**ІНСТРУКЦІЯ:** Скопіюй цей текст повністю, передай AI-моделі (Claude, ChatGPT, Grok, тощо) як окремий промпт. AI виконає повну розробку без додаткових запитань.

---

## КОНТЕКСТ

Тобі потрібно розробити **повноцінний модуль модерації для Telegram-групи** на основі доданого спеціфікейшну.

**Результат:** Git-готовий проект для VPS (Linux), який можна розгорнути за 5 хвилин.

---

## ЗАДАЧА

### Етап 1: Створення структури проекту
1. Створи папку `telegram-moderation-bot/` з точною структурою з розділу 3.1 спеціфікейшну
2. Ініціалізуй Git репозиторій
3. Створи `.gitignore` (исключить: venv, .env, *.pyc, __pycache__, logs/*, db.sqlite3)

### Етап 2: Основні файли конфігурації
1. **config/config.yaml** - Основна конфігурація з усіма параметрами детекторів (розділ 2.1-2.6)
2. **config/rules.json** - Базові 4 правила для спаму, флуду та розсилок
3. **config/blacklist.json** - Стартовий чорний список (мінімум 50 слів для російської/української)
4. **.env.example** - Шаблон змінних оточення
5. **requirements.txt** - Усі залежності (розділ 3.2)

### Етап 3: Реалізація детекторів
Для кожного детектора створи окремий файл:

#### `src/detectors/base.py`
- Абстрактний клас `BaseDetector` з методом `detect()`
- Загальна логіка для кеширування, логування

#### `src/detectors/spam_detector.py`
- Клас `SpamDetector`
- Методи:
  - `_check_blacklist(text)` - перевірка чорного списку
  - `_check_repeat(user_id, text)` - перевірка повторів
  - `_check_urls(text)` - детектування комерційних URL
  - `_check_caps(text)` - перевірка капсу/емодзі
  - `_check_bot_patterns(text)` - виявлення ботів
  - `detect(message)` - основна логіка
- Вихідні дані: `SpamDetectionResult`

#### `src/detectors/flood_detector.py`
- Клас `FloodDetector`
- Методи:
  - `_count_messages_in_window(user_id, window)` - лічильник
  - `_determine_level(count, window)` - визначити рівень (warning/timeout/ban)
  - `detect(user_id)` - основна логіка
- Вихідні дані: `FloodDetectionResult`

#### `src/detectors/fake_distribution.py`
- Клас `FakeDistributionDetector`
- Методи:
  - `_check_referral_links(text)` - реферальні посилання
  - `_check_message_copy(message)` - однакові повідомлення від різних людей
  - `_check_forwarded(message)` - чи це форвард розсилки
  - `detect(message)` - основна логіка
- Вихідні дані: `FakeDistributionResult`

### Етап 4: Система управління правилами
#### `src/rules/engine.py`
- Клас `RuleEngine`
- Методи:
  - `load_rules(config_path)` - завантажити правила з JSON
  - `find_matching_rules(spam_result, fake_result, flood_result)` - знайти застосовні правила
  - `should_apply_rule(rule, message, user)` - перевірити винятки
  - `reload_rules()` - гарячої перезавантаження
- Логіка: пройти усі правила, перевірити умови, застосувати з урахуванням пріоритету

### Етап 5: Виконавець дій
#### `src/actions/executor.py`
- Клас `ActionExecutor`
- Методи для кожної дії:
  - `delete_message(message)` - видалити повідомлення
  - `warn_user(user, reason)` - видати попередження
  - `mute_user(user, duration)` - замутити
  - `restrict_user(user, permissions, duration)` - обмежити права
  - `remove_user(user, reason)` - видалити з групи
  - `ban_user(user, reason)` - забанити
  - `report_admin(user, incident, details)` - повідомити адміна
- Загальна методика `execute(actions, message)` - виконати послідовність дій
- Обробка помилок: retry до 3 разів, логування

### Етап 6: Моніторинг користувачів
#### `src/user/monitor.py`
- Клас `UserMonitor`
- Методи:
  - `record_message(message)` - записати повідомлення
  - `get_user_stats(user_id)` - статистика користувача
  - `get_anomalies(user_id)` - виявити аномалії (стрибки активності)
  - `add_warning(user_id, reason)` - добавити попередження
  - `get_warnings(user_id)` - отримати попередження
- Інтеграція з БД

### Етап 7: База даних
#### `src/database.py`
- Клас `Database`
- Методи:
  - `init()` - створити таблиці (schema з розділу 2.4)
  - `add_user(user_data)` - новий користувач
  - `update_user(user_id, data)` - оновити
  - `log_incident(user_id, incident_type, action, reason)` - залогувати інцидент
  - `get_user_history(user_id, limit)` - історія користувача
  - `backup()` - резервна копія БД
- SQLAlchemy ORM або сирі SQL
- Підтримка SQLite за замовчуванням (можна легко переключитись на PostgreSQL)

### Етап 8: Основна логіка бота
#### `src/bot.py`
- Клас `TelegramBot`
- Ініціалізація з Telegram Bot API (python-telegram-bot v20+)
- Методи:
  - `start()` - запуск бота
  - `stop()` - зупинка
  - Підписка на оновлення повідомлень
- Делегування обробки повідомлень до обробників

#### `src/handlers/message_handler.py`
- Функція `handle_message(update, context)` - асинхрона
- Реалізація flow-діаграми з розділу 4.1
- Послідовний виклик:
  1. Pre-checks (адміни, видалення)
  2. Детектори (spam, flood, fake_dist)
  3. RuleEngine
  4. ActionExecutor
  5. Логування в БД

#### `src/handlers/admin_commands.py`
- Обробники команд (розділ 5.1):
  - `/ban @user`
  - `/mute @user`
  - `/warn @user`
  - `/status`
  - `/stats`
  - `/rules list`
  - `/logs`
  - `/reload_config`
- Перевірка прав (тільки адміни)

#### `src/handlers/callbacks.py`
- Callback-обробники для інтерактивних кнопок (якщо потрібні)

### Етап 9: Утиліти
#### `src/utils/logger.py`
- Налаштування логування (structlog або стандартний logging)
- Рівні: INFO, WARNING, ERROR
- Формат з timestamp, module, level, message

#### `src/utils/cache.py`
- In-memory кеш для:
  - Користувацької активності (TTL 1 год)
  - Хешів повідомлень (TTL 24 год)
  - Скомпільованих regex (постійно)

### Етап 10: Точка входу
#### `src/main.py`
- Завантаження .env змінних
- Ініціалізація логування
- Завантаження конфігів
- Створення БД
- Запуск бота
- Обробка сигналів (SIGINT, SIGTERM) для коректного завершення

### Етап 11: Docker
#### `Dockerfile`
- Base: `python:3.11-slim`
- Встановлення залежностей
- Copy проекту
- ENV для конфігурації
- CMD: `python -m src.main`
- Expose: 8000 (для можливого API панелі)

#### `docker-compose.yml`
- Сервіс для бота
- Volumes для config, logs, db
- Restart policy: always
- Environment variables з .env

### Етап 12: Документація
#### `README.md`
1. **Огляд** - що робить бот
2. **Вимоги** - OS, Python, залежності
3. **Встановлення** - покроково
4. **Конфігурація** - як налаштувати
5. **Запуск** - локально vs Docker
6. **Команди** - список адміністратора
7. **Логи** - де шукати, як читати
8. **Розробка** - тестування, контрибюції
9. **Проблеми** - FAQ та рішення

#### `ARCHITECTURE.md`
- Детальна архітектура (flow-діаграми ASCII)
- Взаємодія компонентів
- Порядок виклику методів

### Етап 13: Тестування
#### `tests/test_spam_detector.py`
- Юніт-тести для спам-детектора
- Приклади для кожного критерію (blacklist, repeat, urls, caps, bot_patterns)
- Assertion на результати

#### `tests/test_flood_detector.py`
- Тести для флуд-детектора
- Різні рівні (warning, timeout, ban)

#### `tests/test_rule_engine.py`
- Тести для системи правил
- Перевірка умов та винятків

#### `conftest.py`
- Fixtures для тестів
- Mock telegram messages

### Етап 14: Скрипти розгортання
#### `scripts/setup.sh`
```bash
#!/bin/bash
# 1. Клонування репо
# 2. Встановлення Python залежностей
# 3. Ініціалізація БД
# 4. Запуск бота
```

#### `scripts/backup.sh`
```bash
#!/bin/bash
# Щоденна резервна копія БД (date-stamped)
# Upload на зовнішнє сховище (опційно)
```

#### `scripts/restore.sh`
```bash
#!/bin/bash
# Відновлення БД з резервної копії
```

---

## ВИМОГИ ДО ЯКОСТІ КОДУ

1. **Типізація:** Використовуй type hints на всі функції
2. **Докстринги:** Кожна функція та клас повинна мати описання
3. **Помилки:** Користувацькі exceptions для кожного модуля
4. **Логування:** Логуй входи/виходи критичних функцій
5. **Асинхронність:** Використовуй async/await для I/O операцій
6. **Конфіг:** Жодних hardcoded значень - все з config.yaml
7. **DRY:** Не повторюй код - виділяй в утиліти

---

## КРИТЕРІЇ ПРИЙНЯТТЯ

Проект готовий, коли:

- ✅ Можна запустити `python -m src.main` без помилок
- ✅ Бот підключується до Telegram API
- ✅ Обробляє повідомлення без затримок
- ✅ Детектує спам/флуд/розсилки за <500ms
- ✅ Виконує дії (delete, warn, mute, ban) моментально
- ✅ БД записує усі інциденти
- ✅ Команди адміна працюють
- ✅ Docker-образ збирається без помилок
- ✅ Логи читаємі й повні
- ✅ README зрозумілий для newbie
- ✅ Конфіг можна редагувати без перезапуску (окрім команд `/reload_config`)
- ✅ Усі тести проходять (`pytest`)

---

## ДОДАТКОВІ ВИМОГИ

1. Напиши **CHANGELOG.md** зі списком реалізованих функцій
2. Додай **LICENSE** (MIT рекомендовано)
3. Файли мають UTF-8 кодування
4. Коментарі на англійській (код + коментарі)
5. Git commits мають бути atomic та з інформативними повідомленнями

---

## СТРУКТУРА ВИХІДНИХ ФАЙЛІВ

Усе повинно бути в одній папці `telegram-moderation-bot/` готове до:
```bash
cd telegram-moderation-bot
pip install -r requirements.txt
python -m src.main
```

Без додаткових кроків!

---

**ПОЧИН РОЗРОБКУ. УСПІХУ! 🚀**
