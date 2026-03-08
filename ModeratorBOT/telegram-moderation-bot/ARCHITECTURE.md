# Архітектура ModeratorBOT

## 1. Flow Обробки

1. **Telegram API (python-telegram-bot)** отримує повідомлення і відправляє в `src.handlers.message_handler:MessageHandler`.
2. **PreCheck**: Перевірка чи відправник є адміном. Якщо адмін — скіпаємо сувору модерацію.
3. **Detectors**:
   - `spam_detector` перевіряє текст на чорний список (`config/blacklist.json`), URL-патерни, капс, ботів. Білий список посилань (`bio.site/obwepit` тощо) ігнорується.
   - `fake_distribution` рахує MD5-хеш повідомлення та записує в in-memory `Cache`. Якщо хеш зустрічається N разів — це дублікат-розсилка.
   - `flood_detector` рахує активність `user_id` через кеш і повертає рівень загрози (`warning`, `timeout`, `ban`).
4. **User Monitor**:
   - Заносить користувача та саме повідомлення до таблиць `users` і `user_messages` у `SQLite` бази.
5. **Rule Engine**:
   - Бере результати від Dectors та проганяє їх через правила описані в `config/rules.json`.
   - Знаходить збіги (наприклад: `SpamResult.reason == 'blacklist_match'`).
6. **Action Executor**:
   - Читає масив дій від Rule Engine (видалити, замутити, кинути warning).
   - Транслює їх у виклики Telegram API (`deleteMessage`, `restrictChatMember`, `sendMessage` тощо).
7. **Incident Logging**:
   - Якщо спрацювало правило, записує інцидент в базу даних `db.log_incident(...)` для подальшої статистики.

## 2. Схема Бази Даних (SQLite)

- `users`: Профілі, лічильники повідомлень і варнів, дати.
- `user_messages`: Журнал всіх текстів (для ретроспективного аналізу або пошуку).
- `incidents`: Таблиця спрацювання правил, яка зберігає, що саме бот зробив із порушником.
