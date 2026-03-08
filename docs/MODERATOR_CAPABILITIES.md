# Moderator Capabilities

## Scope
This document describes what the `ModeratorBOT` module can do today in production:
- Telegram moderation bot behavior
- Dashboard moderation tab behavior
- Data/storage behavior

## Telegram Bot Capabilities

### Automatic moderation pipeline
- Processes incoming chat messages.
- Runs detectors for spam/flood/pattern-based abuse.
- Applies configured actions in sequence (rules engine + action executor).

### Actions supported
- `delete` — deletes offending message.
- `warn` — records warning incident.
- `mute` — restricts user for configured duration.
- `kick` — bans and immediately unbans (remove from chat).
- `ban` — permanent ban.
- `report` — logs/reporting action path (through incident logging pipeline).

### Persistent side effects
- Every handled incident is written to `incidents`.
- Permanent bans set `users.is_banned = 1` with `ban_reason`.
- Every successful delete increments `daily_stats.deleted_count` per `(date, chat_id)`.

## Telegram Admin Commands

All commands require chat admin rights.

- `/status` — bot health ping.
- `/ban [reason]` — ban replied user and log incident.
- `/mute [seconds]` — mute replied user for duration (default 300s).
- `/rules` — confirms rules engine is active.
- `/blacklist_add <word|phrase>` — add global blacklist item.
- `/blacklist_remove <word|phrase>` — remove global blacklist item.
- `/blacklist_list` — show global blacklist.
- `/stats` — show today's deleted totals (global + per chat).

## Dashboard Capabilities (`/moderator`)

### Read-only analytics
- Today's deleted message total.
- Today's per-chat deletion breakdown.
- Banned users list (`users.is_banned = 1`).

### Management UI
- Add blacklist word/phrase.
- Remove blacklist word/phrase.

### Reliability behavior
- If moderator DB file is missing: page renders with safe fallback message.
- If required tables are missing: dashboard auto-creates `daily_stats` and `global_blacklist`.
- If DB read still fails: page returns controlled error message instead of HTTP 500.

## Database Objects Used

- `users` (source for banned users)
- `incidents` (logged moderation incidents)
- `daily_stats` (per-day/per-chat deleted counters)
- `global_blacklist` (shared blacklist store)
- `user_messages` (message history)

## Integration Contract

- Dashboard reads moderator DB from:
  - `/opt/telegram-moderation-bot/data/db.sqlite3` (inside web service mount path).
- Moderator bot writes the same DB through its `/app/data/db.sqlite3` volume.
- Shared-file strategy requires schema consistency and write permissions on mounted volume.
