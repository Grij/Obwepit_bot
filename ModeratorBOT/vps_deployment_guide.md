# 🚀 ШПАРГАЛКА: Запуск модуля модерації на VPS

**Коли AI-агент завершить розробку, виконай ці кроки на VPS:**

---

## Крок 1: Підготовка VPS

```bash
# Підключитись до VPS
ssh root@your-vps-ip

# Оновити систему
apt update && apt upgrade -y

# Встановити Python 3.11+ та необхідні пакети
apt install -y python3.11 python3.11-venv python3.11-dev git curl

# Встановити Docker (опційно, але рекомендовано)
apt install -y docker.io docker-compose
systemctl start docker
systemctl enable docker
```

---

## Крок 2: Клонування репо (або завантаження файлів)

### Варіант A: Git
```bash
cd /opt
git clone https://github.com/your-username/telegram-moderation-bot.git
cd telegram-moderation-bot
```

### Варіант B: Завантаження ZIP
```bash
cd /opt
wget https://link-to-your-repo/telegram-moderation-bot.zip
unzip telegram-moderation-bot.zip
cd telegram-moderation-bot
```

---

## Крок 3: Налаштування конфігурації

```bash
# Копіюємо .env.example
cp .env.example .env

# Редагуємо .env
nano .env
```

**Що додати в .env:**
```env
# Telegram Bot Token (отримай від @BotFather)
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh

# Telegram Group ID (отримай через @get_id_bot або через API)
TELEGRAM_GROUP_ID=-1001234567890

# Database URL (SQLite за замовчуванням)
DATABASE_URL=sqlite:///./data/moderation.db

# Telegram Admin ID (твій телеграм ID для команд)
ADMIN_ID=987654321

# Log level
LOG_LEVEL=INFO

# Port для API панелі (опційно)
API_PORT=8000
```

---

## Крок 4: Запуск (Варіант 1: Без Docker)

```bash
# Створюємо virtual environment
python3.11 -m venv venv

# Активуємо venv
source venv/bin/activate

# Встановлюємо залежності
pip install -r requirements.txt

# Ініціалізуємо БД
python -m src.database init

# Запускаємо бота
python -m src.main
```

**Очікуємий вихід:**
```
2024-03-08 14:22:15 [INFO] Bot started. Group: -1001234567890
2024-03-08 14:22:16 [INFO] Rules loaded: 4 active rules
2024-03-08 14:22:17 [INFO] Listening for updates...
```

Якщо вибачиш цей вихід - ✅ бот запустився!

---

## Крок 5: Запуск (Варіант 2: Docker)

```bash
# Запускаємо контейнер
docker-compose up -d

# Перевіряємо логи
docker-compose logs -f bot

# Зупинка
docker-compose down
```

---

## Крок 6: Запуск як системний сервіс (Systemd)

Це дозволяє боту автоматично стартувати при перезавантаженні VPS.

```bash
# Створюємо systemd service
sudo nano /etc/systemd/system/telegram-bot.service
```

**Вставляємо:**
```ini
[Unit]
Description=Telegram Moderation Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/telegram-moderation-bot
ExecStart=/opt/telegram-moderation-bot/venv/bin/python -m src.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Активуємо сервіс:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot

# Перевіряємо статус
sudo systemctl status telegram-bot

# Переглядаємо логи
sudo journalctl -u telegram-bot -f
```

---

## Крок 7: Налаштування правил

```bash
# Открываем конфіг правил
nano config/rules.json

# Додаємо свої правила або редагуємо існуючі
# Формат описаний у спеціфікейшні (розділ 2.6)
```

**Основні параметри для налаштування:**
- `priority` - вищий номер = важливіше
- `condition` - що детектується
- `actions` - що робити

**Приклад нового правила:**
```json
{
  "id": "custom_1",
  "name": "Блокувати слово 'BADWORD'",
  "enabled": true,
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
    {"action": "warn", "delay": 1}
  ]
}
```

**Перезавантажуємо правила:**
```bash
# Команда в Telegram групі від адміна:
/reload_config

# Або перезапускаємо бота:
sudo systemctl restart telegram-bot
```

---

## Крок 8: Перевірка роботи

### 8.1 Тест спам-детектора
Напиши в групі: "casino" (додайте до чорного списку)

**Очікуємо:**
- ❌ Повідомлення видалено
- ⚠️ Ви отримали попередження

### 8.2 Тест флуд-детектора
Напиши в групі 10 повідомлень за 5 секунд

**Очікуємо:**
- ❌ Повідомлення видалені
- 🔇 Вас замутили на 5 хвилин

### 8.3 Перевірка команд адміна
```
/status
/stats
/logs 5
```

Мають вивести інформацію без помилок.

---

## Крок 9: Резервна копія БД

### Щоденна резервна копія (Cron)

```bash
# Відкриваємо crontab
crontab -e

# Додаємо строку для резервної копії о 02:00 кожної ночі
0 2 * * * /opt/telegram-moderation-bot/scripts/backup.sh

# Перевіряємо
crontab -l
```

### Ручна резервна копія
```bash
cd /opt/telegram-moderation-bot

# Створити backup
./scripts/backup.sh

# Перевірити резервні копії
ls -lh data/backups/
```

### Відновлення з резервної копії
```bash
# Якщо БД пошкоджена, відновити:
./scripts/restore.sh data/backups/moderation_2024-03-08_020000.db
```

---

## Крок 10: Моніторинг

### 10.1 Логи в реальному часі
```bash
# Якщо використовуєш systemd
sudo journalctl -u telegram-bot -f

# Якщо запущено в tmux/screen
tail -f logs/bot.log
```

### 10.2 Статистика роботи
```bash
# Скільки повідомлень оброблено
grep "ACTION" logs/bot.log | wc -l

# Кількість спам-детекцій
grep "spam_match" logs/bot.log | wc -l

# Кількість флудів
grep "flood_detected" logs/bot.log | wc -l
```

### 10.3 Здоров'я системи
```bash
# Розмір БД
du -h data/moderation.db

# Розмір логів
du -h logs/

# Використання пам'яті ботом
ps aux | grep "python -m src.main"
```

---

## Крок 11: Розширення функціональності

### Додавання нових слів до чорного списку
```bash
nano config/blacklist.json

# Додаємо слово, зберігаємо
# Перезавантажуємо /reload_config або системний сервіс
```

### Додавання нового правила
```bash
nano config/rules.json

# Додаємо об'єкт правила
# Перевіряємо JSON синтаксис
python -m json.tool config/rules.json

# Перезавантажуємо
/reload_config
```

---

## Типові проблеми й рішення

### Проблема: "Bot offline"
```bash
# Перевіркаємо статус
sudo systemctl status telegram-bot

# Переглядаємо помилки
sudo journalctl -u telegram-bot -n 50

# Рестартуємо
sudo systemctl restart telegram-bot
```

### Проблема: "Database locked"
```bash
# Закриває усі процеси ботів
pkill -f "python -m src.main"

# Очищуємо lock-файл БД (якщо є)
rm -f data/moderation.db-wal data/moderation.db-shm

# Перезапускаємо
sudo systemctl start telegram-bot
```

### Проблема: "Telegram API rate limit"
Трапляється при масовій модерації. Рішення:
- Зменш кількість дій в правилах
- Збільш `delay` між діями в конфігу
- Використай пулінг замість вебхуків

### Проблема: "Out of memory"
```bash
# Перевір процес
top

# Очисти кеш логів
echo > logs/bot.log

# Переклад на меншу кількість логування (LOG_LEVEL=WARNING)
nano .env
```

---

## Корисні команди

```bash
# Статус сервісу
sudo systemctl status telegram-bot

# Перезапуск
sudo systemctl restart telegram-bot

# Зупинка
sudo systemctl stop telegram-bot

# Старт
sudo systemctl start telegram-bot

# Логи (50 останніх рядків)
sudo journalctl -u telegram-bot -n 50

# Логи в реальному часі
sudo journalctl -u telegram-bot -f

# Перевірити конфіг (синтаксис YAML)
python -m yaml config/config.yaml

# Перевірити правила (синтаксис JSON)
python -m json.tool config/rules.json

# Перезавантажити правила в Telegram групі
/reload_config
```

---

## Finito! 🎉

Бот готовий до роботи. Тепер він буде автоматично:
- ✅ Детектувати спам
- ✅ Ловити флуд
- ✅ Видаляти фейк-розсилки
- ✅ Видавати попередження
- ✅ Мутити й банити порушників

**Успіху! Модерація групи тепер автоматична. 🚀**
