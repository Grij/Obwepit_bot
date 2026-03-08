from fastapi import FastAPI, Request, Form, UploadFile, File, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import aiosqlite
import json
import os
import secrets
import uuid
from config import BOT_TOKEN

app = FastAPI(title="Общепіт Дашборд")

APP_VERSION = "1.4.3"
APP_LAST_UPDATE = "2026-03-08 08:00"

# --- Сесії (cookie-based, 30 днів) ---
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=30 * 24 * 60 * 60)

# --- Google OAuth ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
ALLOWED_EMAIL = os.getenv("ALLOWED_EMAIL", "")
OAUTH_READY = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# --- Налаштування шаблонів ---
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

DB_NAME = "data/users.db"
FEEDBACK_DB = "data/feedback.db"
MODERATOR_DB = "/opt/telegram-moderation-bot/data/db.sqlite3"
POST_SIGNATURE_LINK = os.getenv("POST_SIGNATURE_LINK", "https://t.me/obwepit")
UPLOADS_DIR = "data/uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)


# --- Auth helpers ---
def get_current_user(request: Request):
    """Повертає email користувача з сесії, або None."""
    return request.session.get("user")


def require_auth(request: Request):
    """Якщо не авторизовано — редірект на /login."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return None


# --- Auth routes ---
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    # Якщо вже авторизовано — одразу на дашборд
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
        "oauth_ready": OAUTH_READY,
        "app_version": APP_VERSION,
        "app_last_update": APP_LAST_UPDATE
    })


@app.get("/auth/google")
async def auth_google(request: Request):
    if not OAUTH_READY:
        return RedirectResponse(url="/login?error=oauth_not_configured", status_code=status.HTTP_302_FOUND)
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return RedirectResponse(url="/login?error=auth_failed")

    user_info = token.get("userinfo")
    if not user_info:
        return RedirectResponse(url="/login?error=no_user_info")

    email = user_info.get("email", "")
    name = user_info.get("name", email)

    # Перевірка whitelist
    if ALLOWED_EMAIL and email.lower() != ALLOWED_EMAIL.lower():
        return RedirectResponse(url="/login?error=access_denied")

    # Зберігаємо в сесію
    request.session["user"] = email
    request.session["user_name"] = name

    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


# --- Dashboard ---
@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request, period: str = "week"):
    redirect = require_auth(request)
    if redirect:
        return redirect

    if period not in ("week", "month"):
        period = "week"
    days_back = 7 if period == "week" else 30
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # Метрики: Всього підписників у базі боту
        cursor = await db.execute("SELECT COUNT(*) as total FROM users")
        total_bot_users = (await cursor.fetchone())['total']
        
        # Метрики: Апрувів за сьогодні (загалом)
        cursor = await db.execute("SELECT COUNT(*) as total FROM approvals WHERE date(timestamp) = date('now')")
        today_approvals = (await cursor.fetchone())['total']
        
        # Метрики: Апрувів за сьогодні по каналах
        cursor = await db.execute('''
            SELECT COALESCE(c.title, a.chat_id) as channel_name, COUNT(a.id) as count
            FROM approvals a
            LEFT JOIN channels c ON a.chat_id = c.chat_id
            WHERE date(a.timestamp) = date('now')
            GROUP BY channel_name
            ORDER BY count DESC
        ''')
        today_channel_approvals = await cursor.fetchall()
        
        # Графік: Апруви по днях по каналах
        date_filter = f"date('now', '-{days_back} days')"
        cursor = await db.execute(f"SELECT DISTINCT date(timestamp) as day FROM approvals WHERE timestamp >= {date_filter} ORDER BY day ASC")
        days = [row['day'] for row in await cursor.fetchall()]

        cursor = await db.execute(f'''
            SELECT date(a.timestamp) as day, COALESCE(c.title, a.chat_id) as channel_name, COUNT(a.id) as count 
            FROM approvals a
            LEFT JOIN channels c ON a.chat_id = c.chat_id
            WHERE a.timestamp >= {date_filter}
            GROUP BY day, channel_name ORDER BY day ASC
        ''')
        approvals_data = await cursor.fetchall()

        # Загальні додавання по днях (сума)
        daily_totals = {d: 0 for d in days}

        datasets_dict = {}
        for row in approvals_data:
            day = row['day']
            channel = row['channel_name']
            count = row['count']
            
            daily_totals[day] = daily_totals.get(day, 0) + count
            
            if channel not in datasets_dict:
                datasets_dict[channel] = {d: 0 for d in days}
            datasets_dict[channel][day] = count
            
        chart_datasets = []
        colors = [
            'rgba(59, 130, 246, 0.8)',   # Blue
            'rgba(139, 92, 246, 0.8)',   # Purple
            'rgba(16, 185, 129, 0.8)',   # Green
            'rgba(245, 158, 11, 0.8)',   # Yellow
            'rgba(239, 68, 68, 0.8)',    # Red
            'rgba(14, 165, 233, 0.8)'    # Sky
        ]
        
        for idx, (channel, counts_by_day) in enumerate(datasets_dict.items()):
            chart_datasets.append({
                "label": channel,
                "data": [counts_by_day[d] for d in days],
                "backgroundColor": colors[idx % len(colors)],
                "borderRadius": 4,
            })
        
        # Канали
        cursor = await db.execute("SELECT * FROM channels")
        channels = await cursor.fetchall()
        
        # Історія розсилок
        cursor = await db.execute("SELECT * FROM broadcasts ORDER BY timestamp DESC LIMIT 5")
        broadcasts = await cursor.fetchall()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "active_page": "dashboard",
        "user_email": get_current_user(request),
        "user_name": request.session.get("user_name", ""),
        "total_bot_users": total_bot_users,
        "today_approvals": today_approvals,
        "today_channel_approvals": today_channel_approvals,
        "chart_labels": days,
        "chart_datasets": chart_datasets,
        "daily_totals": [daily_totals[d] for d in days],
        "channels": channels,
        "broadcasts": broadcasts,
        "period": period,
        "app_version": APP_VERSION,
        "app_last_update": APP_LAST_UPDATE
    })

@app.get("/users", response_class=HTMLResponse)
async def read_users(request: Request):
    redirect = require_auth(request)
    if redirect:
        return redirect

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # Отримуємо всіх користувачів
        cursor = await db.execute("SELECT * FROM users ORDER BY joined_at DESC")
        users = await cursor.fetchall()
        
    return templates.TemplateResponse("users.html", {
        "request": request,
        "active_page": "users",
        "user_email": get_current_user(request),
        "user_name": request.session.get("user_name", ""),
        "users": users,
        "app_version": APP_VERSION,
        "app_last_update": APP_LAST_UPDATE
    })

@app.post("/channels/add")
async def add_channel(
    request: Request,
    title: str = Form(...),
    link: str = Form(...),
    chat_id: str = Form(...),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO channels (chat_id, title, link)
            VALUES (?, ?, ?)
        ''', (chat_id, title, link))
        await db.commit()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/broadcast/test")
async def send_broadcast(
    request: Request,
    message_text: str = Form(...),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO broadcasts (text, status)
            VALUES (?, 'pending')
        ''', (message_text,))
        await db.commit()
        
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


# --- Feedback Bot Dashboard ---
@app.get("/feedback", response_class=HTMLResponse)
async def read_feedback(request: Request):
    redirect = require_auth(request)
    if redirect:
        return redirect

    async with aiosqlite.connect(FEEDBACK_DB) as db:
        db.row_factory = aiosqlite.Row

        # Метрики: повідомлення сьогодні
        cursor = await db.execute("SELECT COUNT(*) as c FROM feedback_stats WHERE date(timestamp) = date('now') AND direction = 'incoming'")
        today_incoming = (await cursor.fetchone())['c']

        cursor = await db.execute("SELECT COUNT(*) as c FROM feedback_stats WHERE date(timestamp) = date('now') AND direction = 'outgoing'")
        today_outgoing = (await cursor.fetchone())['c']

        today_messages = today_incoming + today_outgoing

        # Всього юзерів
        cursor = await db.execute("SELECT COUNT(*) as c FROM feedback_users")
        total_users = (await cursor.fetchone())['c']

        # Заблоковані
        cursor = await db.execute("SELECT COUNT(*) as c FROM feedback_blacklist")
        banned_count = (await cursor.fetchone())['c']

        # Чорний список
        cursor = await db.execute("SELECT * FROM feedback_blacklist ORDER BY banned_at DESC")
        blacklist = await cursor.fetchall()

        # Список юзерів бота
        cursor = await db.execute("SELECT * FROM feedback_users ORDER BY joined_at DESC")
        feedback_users = await cursor.fetchall()

        # Розсилки
        cursor = await db.execute("SELECT * FROM feedback_broadcasts ORDER BY timestamp DESC LIMIT 5")
        broadcasts = await cursor.fetchall()

    return templates.TemplateResponse("feedback.html", {
        "request": request,
        "active_page": "feedback",
        "user_email": get_current_user(request),
        "user_name": request.session.get("user_name", ""),
        "today_messages": today_messages,
        "today_incoming": today_incoming,
        "today_outgoing": today_outgoing,
        "total_users": total_users,
        "banned_count": banned_count,
        "blacklist": blacklist,
        "feedback_users": feedback_users,
        "broadcasts": broadcasts,
        "app_version": APP_VERSION,
        "app_last_update": APP_LAST_UPDATE
    })


@app.post("/feedback/broadcast")
async def send_feedback_broadcast(
    request: Request,
    message_text: str = Form(...),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    async with aiosqlite.connect(FEEDBACK_DB) as db:
        await db.execute('''
            INSERT INTO feedback_broadcasts (text, status)
            VALUES (?, 'pending')
        ''', (message_text,))
        await db.commit()

    return RedirectResponse(url="/feedback", status_code=status.HTTP_303_SEE_OTHER)


# --- Posting ---
@app.get("/posting", response_class=HTMLResponse)
async def read_posting(request: Request):
    redirect = require_auth(request)
    if redirect:
        return redirect

    # Канали з captcha DB
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM channels")
        channels = await cursor.fetchall()
        
        # Create channels map
        channels_map = {str(c['chat_id']): c['title'] for c in channels}

    # Історія постів
    async with aiosqlite.connect(FEEDBACK_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM scheduled_posts ORDER BY id DESC LIMIT 50")
        raw_posts = await cursor.fetchall()
        
        posts = []
        for p in raw_posts:
            p_dict = dict(p)
            try:
                ch_list = json.loads(p_dict['channels'])
                readable_names = [channels_map.get(str(ch), str(ch)) for ch in ch_list]
                p_dict['channels_str'] = ", ".join(readable_names)
            except Exception:
                p_dict['channels_str'] = p_dict['channels']
            posts.append(p_dict)
        
    return templates.TemplateResponse("posting.html", {
        "request": request,
        "active_page": "posting",
        "user_email": get_current_user(request),
        "user_name": request.session.get("user_name", ""),
        "channels": channels,
        "channels_map": channels_map,
        "posts": posts,
        "signature_link": POST_SIGNATURE_LINK,
        "app_version": APP_VERSION,
        "app_last_update": APP_LAST_UPDATE
    })


from typing import Optional, List

@app.post("/posting/create")
async def create_post(
    request: Request,
    post_text: str = Form(...),
    channels: List[str] = Form(default=[]),
    schedule_type: str = Form("now"),
    scheduled_at: Optional[str] = Form(None),
    pin_after: Optional[str] = Form(None),
    delete_after: int = Form(0),
    media: Optional[UploadFile] = File(None),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    if not channels:
        return RedirectResponse(url="/posting?error=no_channels", status_code=status.HTTP_303_SEE_OTHER)

    # Медіа
    media_path = None
    media_type = None
    if media and media.filename:
        ext = os.path.splitext(media.filename)[1].lower()
        filename = f"{uuid.uuid4().hex}{ext}"
        media_path = os.path.join(UPLOADS_DIR, filename)
        content = await media.read()
        with open(media_path, "wb") as f:
            f.write(content)
        if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
            media_type = 'photo'
        elif ext in ('.mp4', '.mov', '.avi', '.mkv'):
            media_type = 'video'

    # Розклад
    sched_dt = None
    if schedule_type == 'scheduled' and scheduled_at:
        sched_dt = scheduled_at.replace('T', ' ')

    # Підпис
    signature = f'<a href="{POST_SIGNATURE_LINK}">[\u041e\u0411\u0429\u0415\u041F\u0406\u0422]</a>'

    # Зберігаємо
    async with aiosqlite.connect(FEEDBACK_DB) as db:
        await db.execute('''
            INSERT INTO scheduled_posts (text, media_path, media_type, channels, scheduled_at, pin_after, delete_after, signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post_text,
            media_path,
            media_type,
            json.dumps(channels),
            sched_dt,
            1 if pin_after else 0,
            delete_after,
            signature
        ))
        await db.commit()

    return RedirectResponse(url="/posting", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/posting/delete/{post_id}")
async def delete_post(request: Request, post_id: int):
    redirect = require_auth(request)
    if redirect:
        return redirect

    async with aiosqlite.connect(FEEDBACK_DB) as db:
        # Тільки pending пости можна видаляти
        await db.execute("DELETE FROM scheduled_posts WHERE id = ? AND status = 'pending'", (post_id,))
        await db.commit()
    
    return RedirectResponse(url="/posting", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/posting/edit/{post_id}")
async def edit_post_page(request: Request, post_id: int):
    redirect = require_auth(request)
    if redirect:
        return redirect

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM channels")
        channels = await cursor.fetchall()
        channels_map = {str(c['chat_id']): c['title'] for c in channels}
        
    async with aiosqlite.connect(FEEDBACK_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM scheduled_posts WHERE id = ?", (post_id,))
        post = await cursor.fetchone()
        
    if not post or post['status'] != 'pending':
        return RedirectResponse(url="/posting", status_code=status.HTTP_303_SEE_OTHER)
        
    post_channels = json.loads(post['channels'])
    
    post_date_str = ""
    if post['scheduled_at']:
        dt_parts = post['scheduled_at'].split(':')
        post_date_str = ':'.join(dt_parts[:2]).replace(' ', 'T')
        
    return templates.TemplateResponse("posting_edit.html", {
        "request": request,
        "active_page": "posting",
        "user_email": get_current_user(request),
        "user_name": request.session.get("user_name", ""),
        "channels": channels,
        "channels_map": channels_map,
        "post": post,
        "post_channels": post_channels,
        "post_date_str": post_date_str,
        "signature_link": POST_SIGNATURE_LINK,
        "app_version": APP_VERSION,
        "app_last_update": APP_LAST_UPDATE
    })

@app.post("/posting/edit/{post_id}")
async def edit_post_submit(
    request: Request,
    post_id: int,
    post_text: str = Form(...),
    channels: List[str] = Form(default=[]),
    schedule_type: str = Form("now"),
    scheduled_at: Optional[str] = Form(None),
    pin_after: Optional[str] = Form(None),
    delete_after: int = Form(0),
    media: Optional[UploadFile] = File(None),
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    if not channels:
        return RedirectResponse(url=f"/posting/edit/{post_id}?error=no_channels", status_code=status.HTTP_303_SEE_OTHER)

    async with aiosqlite.connect(FEEDBACK_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM scheduled_posts WHERE id = ?", (post_id,))
        old_post = await cursor.fetchone()
        
    if not old_post or old_post['status'] != 'pending':
        return RedirectResponse(url="/posting", status_code=status.HTTP_303_SEE_OTHER)
        
    media_path = old_post['media_path']
    media_type = old_post['media_type']
    if media and media.filename:
        ext = os.path.splitext(media.filename)[1].lower()
        filename = f"{uuid.uuid4().hex}{ext}"
        media_path = os.path.join(UPLOADS_DIR, filename)
        content = await media.read()
        with open(media_path, "wb") as f:
            f.write(content)
        if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
            media_type = 'photo'
        elif ext in ('.mp4', '.mov', '.avi', '.mkv'):
            media_type = 'video'
            
    sched_dt = None
    if schedule_type == 'scheduled' and scheduled_at:
        sched_dt = scheduled_at.replace('T', ' ')
        
    signature = f'<a href="{POST_SIGNATURE_LINK}">[\u041e\u0411\u0429\u0415\u041f\u0406\u0422]</a>'
    
    async with aiosqlite.connect(FEEDBACK_DB) as db:
        await db.execute('''
            UPDATE scheduled_posts 
            SET text=?, media_path=?, media_type=?, channels=?, scheduled_at=?, pin_after=?, delete_after=?, signature=?
            WHERE id=?
        ''', (
            post_text,
            media_path,
            media_type,
            json.dumps(channels),
            sched_dt,
            1 if pin_after else 0,
            delete_after,
            signature,
            post_id
        ))
        await db.commit()

    return RedirectResponse(url="/posting", status_code=status.HTTP_303_SEE_OTHER)


# --- Moderator Dashboard ---
@app.get("/moderator", response_class=HTMLResponse)
async def read_moderator(request: Request):
    redirect = require_auth(request)
    if redirect:
        return redirect

    # Safe fallback if DB doesn't exist yet
    if not os.path.exists(MODERATOR_DB):
        return templates.TemplateResponse("moderator.html", {
            "request": request,
            "active_page": "moderator",
            "user_email": get_current_user(request),
            "user_name": request.session.get("user_name", ""),
            "today_deleted": 0,
            "today_breakdown": [],
            "blacklist": [],
            "banned_users": [],
            "app_version": APP_VERSION,
            "app_last_update": APP_LAST_UPDATE,
            "error_msg": "База даних модератора ще не підключена."
        })

    async with aiosqlite.connect(MODERATOR_DB) as db:
        db.row_factory = aiosqlite.Row

        # Deleted stats for today
        from datetime import datetime
        today = datetime.now().date().isoformat()
        cursor = await db.execute("SELECT SUM(deleted_count) as c FROM daily_stats WHERE date = ?", (today,))
        row = await cursor.fetchone()
        today_deleted = row['c'] if row and row['c'] else 0

        # Breakdown by chat
        cursor = await db.execute("SELECT chat_id, deleted_count FROM daily_stats WHERE date = ?", (today,))
        today_breakdown = await cursor.fetchall()
        
        # We can map chat_id to names if they exist in DB_NAME
        async with aiosqlite.connect(DB_NAME) as main_db:
            main_db.row_factory = aiosqlite.Row
            c_cursor = await main_db.execute("SELECT * FROM channels")
            channels = await c_cursor.fetchall()
            channels_map = {str(c['chat_id']): c['title'] for c in channels}
            
        enriched_breakdown = []
        for r in today_breakdown:
            chat_id_str = str(r['chat_id'])
            enriched_breakdown.append({
                "chat_name": channels_map.get(chat_id_str, chat_id_str),
                "deleted_count": r["deleted_count"]
            })

        # Global Blacklist
        cursor = await db.execute("SELECT * FROM global_blacklist ORDER BY added_at DESC")
        blacklist = await cursor.fetchall()

        # Banned Users
        cursor = await db.execute("SELECT * FROM users WHERE is_banned = 1 ORDER BY last_activity DESC")
        banned_users = await cursor.fetchall()

    return templates.TemplateResponse("moderator.html", {
        "request": request,
        "active_page": "moderator",
        "user_email": get_current_user(request),
        "user_name": request.session.get("user_name", ""),
        "today_deleted": today_deleted,
        "today_breakdown": enriched_breakdown,
        "blacklist": blacklist,
        "banned_users": banned_users,
        "app_version": APP_VERSION,
        "app_last_update": APP_LAST_UPDATE
    })


@app.post("/moderator/blacklist/add")
async def add_moderator_blacklist(
    request: Request,
    word: str = Form(...)
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    if os.path.exists(MODERATOR_DB):
        async with aiosqlite.connect(MODERATOR_DB) as db:
            try:
                # 0 for dashboard user ID 
                from datetime import datetime
                await db.execute('''
                    INSERT INTO global_blacklist (word, added_by, added_at)
                    VALUES (?, ?, ?)
                ''', (word.lower().strip(), 0, datetime.now()))
                await db.commit()
            except aiosqlite.IntegrityError:
                pass # Already exists

    return RedirectResponse(url="/moderator", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/moderator/blacklist/remove")
async def remove_moderator_blacklist(
    request: Request,
    word: str = Form(...)
):
    redirect = require_auth(request)
    if redirect:
        return redirect

    if os.path.exists(MODERATOR_DB):
        async with aiosqlite.connect(MODERATOR_DB) as db:
            await db.execute('DELETE FROM global_blacklist WHERE word = ?', (word.lower().strip(),))
            await db.commit()

    return RedirectResponse(url="/moderator", status_code=status.HTTP_303_SEE_OTHER)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web:app", host="0.0.0.0", port=8000, reload=True)
