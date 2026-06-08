import sqlite3
import threading
import asyncio
import os
import requests
import time
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.error import TelegramError

TOKEN = "8571936857:AAFb0c4snxxNaNPh46txsbpNhfiR2st-tGg"
ADMIN_ID = 8767998937  # Aapki sahi numerical Telegram ID

REGISTER_LINK = "https://4yaarwin.com/#/register?invitationCode=18426755757"
SUPPORT_ID = "@hackii_sureshote"

# Render URL yahan daalein taaki anti-sleep ping kaam kare (e.g., "https://your-app.onrender.com")
RENDER_APP_URL = "https://yaarwingiftcode-94p2.onrender.com" 

app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is running 24/7!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

# SITE KO SLEEP HONE SE BACHANE KE LIYE PING LOGIC (PIN SYSTEM)
def ping_server():
    if not RENDER_APP_URL or "your-bot-link" in RENDER_APP_URL:
        print("⚠️ Anti-Sleep active karne ke liye RENDER_APP_URL set karein.")
        return
    time.sleep(30) # Bot chalu hone ke thodi der baad shuru karein
    while True:
        try:
            requests.get(RENDER_APP_URL)
            print("🚀 Anti-Sleep Ping Sent! Site is Awake.")
        except Exception as e:
            print(f"❌ Ping failed: {e}")
        time.sleep(300) # Har 5 minute (300 seconds) me ping karega

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY, 
            uid TEXT,
            status TEXT DEFAULT 'active'
        )
    """)
    conn.commit()
    conn.close()
    
    # RESTART SE BACHNE KA JUGAAD: Text file se purane users wapas database me load karein
    if os.path.exists("backup_users.txt"):
        conn = sqlite3.connect("bot.db")
        c = conn.cursor()
        with open("backup_users.txt", "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(",")
                    tid = int(parts[0])
                    uid = parts[1] if len(parts) > 1 else ""
                    c.execute("INSERT OR IGNORE INTO users (telegram_id, uid, status) VALUES (?, ?, 'active')", (tid, uid))
        conn.commit()
        conn.close()

# ---------------- USER SIDE FLOW ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # 1. Sabse pehle strict check ki kya user admin hai
    if int(user_id) == int(ADMIN_ID):
        await update.message.reply_text(
            "📊 *WELCOME TO ADMIN DASHBOARD*\n\n"
            "Aapka admin panel active hai.\n\n"
            "Commands:\n"
            "🔹 `/stats` - Total Active/Blocked Members dekhne ke liye\n"
            "🔹 `/broadcast` - Sabhi ko media/text bhejne ke liye\n\n"
            "ℹ️ _Kisi bhi member ke message par Reply karke use direct msg bhej sakte hain._",
            parse_mode="Markdown"
        )
        return

    # 2. Agar normal member hai to data save karein (Database + Text File backup)
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO users (telegram_id, uid, status) VALUES (?, '', 'active') ON CONFLICT(telegram_id) DO UPDATE SET status='active'", (user_id,))
    conn.commit()
    conn.close()

    # Backup text file me entry karein agar pehle se nahi hai
    is_new = True
    if os.path.exists("backup_users.txt"):
        with open("backup_users.txt", "r") as f:
            if str(user_id) in f.read():
                is_new = False
                
    if is_new:
        with open("backup_users.txt", "a") as f:
            f.write(f"{user_id},\n")

    kb = [[InlineKeyboardButton("📝 Register ID", url=REGISTER_LINK)]]
    await update.message.reply_text(
        "🎁 YAAR WIN GIFT CENTER 🎁\n\n"
        "Pehle upar diye gaye button se Register karein, "
        "phir register karne ke baad apni UID yahan send karein.",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def uid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Admin reply filter
    if update.effective_user.id == ADMIN_ID and update.message.reply_to_message:
        await handle_admin_reply(update, context)
        return

    uid = update.message.text.strip()
    user = update.effective_user

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO users (telegram_id, uid, status) VALUES (?, ?, 'active') ON CONFLICT(telegram_id) DO UPDATE SET uid=?, status='active'", (user.id, uid, uid))
    conn.commit()
    conn.close()

    # Text backup me UID update karne ka logic
    if os.path.exists("backup_users.txt"):
        with open("backup_users.txt", "r") as f:
            lines = f.readlines()
        with open("backup_users.txt", "w") as f:
            for line in lines:
                if line.startswith(f"{user.id},"):
                    f.write(f"{user.id},{uid}\n")
                else:
                    f.write(line)

    context.user_data["user_uid"] = uid
    await update.message.reply_text("✅ UID Saved Successfully.")

    gifts = [
        [InlineKeyboardButton("₹10", callback_data="amt_10"), InlineKeyboardButton("₹20", callback_data="amt_20")],
        [InlineKeyboardButton("₹30", callback_data="amt_30"), InlineKeyboardButton("₹50", callback_data="amt_50")],
        [InlineKeyboardButton("₹100", callback_data="amt_100"), InlineKeyboardButton("₹200", callback_data="amt_200")],
        [InlineKeyboardButton("₹500", callback_data="amt_500")]
    ]
    await update.message.reply_text("Ab apna Gift Amount select karein:", reply_markup=InlineKeyboardMarkup(gifts))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data.startswith("amt_"):
        amt = q.data.split("_")[1]
        user = update.effective_user
        uid = context.user_data.get("user_uid", "Unknown")

        await q.message.reply_text(f"🎁 Selected ₹{amt}\n\nAapka request admin ke paas bhej diya gaya hai!")

        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"📩 *New Request*\n\n"
                f"👤 User: {user.full_name}\n"
                f"🆔 Telegram ID: `{user.id}`\n"
                f"🆔 Game UID: `{uid}`\n"
                f"💰 Gift: ₹{amt}\n\n"
                f"ℹ️ _Is message par Reply karke aap user ko sidha msg bhej sakte hain._",
                parse_mode="Markdown"
            )
        except Exception:
            pass

# ---------------- ADMIN FEATURES ----------------

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_to = update.message.reply_to_message
    reply_text = update.message.text
    
    target_user_id = None
    try:
        if "Telegram ID:" in reply_to.text:
            lines = reply_to.text.split("\n")
            for line in lines:
                if "Telegram ID:" in line:
                    target_user_id = int(line.split(":")[1].replace("`", "").strip())
    except Exception:
        pass

    if target_user_id:
        try:
            await context.bot.send_message(target_user_id, f"💬 *Admin Reply:*\n\n{reply_text}", parse_mode="Markdown")
            await update.message.reply_text("✅ Message user tak pahunch gaya!")
        except TelegramError as e:
            await update.message.reply_text(f"❌ Message nahi bheja ja saka: {e}")
    else:
        await update.message.reply_text("❌ Main user ki Telegram ID nahi dhoondh paya.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
        
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE status='active'")
    active = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE status='blocked'")
    blocked = c.fetchone()[0]
    conn.close()
    
    dashboard = (
        "📊 *LIVE ADMIN DASHBOARD*\n\n"
        f"👥 Total Backup Members: `{total}`\n"
        f"🟢 Active Members: `{active}`\n"
        f"🔴 Blocked Members: `{blocked}`\n\n"
        f"🚀 _Anti-Sleep System Running: True_"
    )
    await update.message.reply_text(dashboard, parse_mode="Markdown")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    msg = update.message
    media_type = None
    
    if msg.reply_to_message:
        target_msg = msg.reply_to_message
    else:
        target_msg = msg
        
    if target_msg.photo:
        media_type = "photo"
        file_id = target_msg.photo[-1].file_id
        caption = target_msg.caption or ""
    elif target_msg.video:
        media_type = "video"
        file_id = target_msg.video.file_id
        caption = target_msg.caption or ""
    elif target_msg.voice:
        media_type = "voice"
        file_id = target_msg.voice.file_id
    elif target_msg.audio:
        media_type = "audio"
        file_id = target_msg.audio.file_id
        caption = target_msg.caption or ""
    else:
        if msg.text.startswith("/broadcast "):
            media_type = "text"
            text_to_send = msg.text.replace("/broadcast ", "", 1)
        elif msg.reply_to_message and msg.reply_to_message.text:
            media_type = "text"
            text_to_send = msg.reply_to_message.text
        else:
            await update.message.reply_text("❌ *Format Galat Hai!* Use: `/broadcast text` ya kisi media par reply karke `/broadcast` likhein.")
            return

    await update.message.reply_text("⏳ Broadcast shuru ho raha hai... Sabhi purane aur naye users ko bheja ja raha hai.")

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT telegram_id FROM users")
    user_rows = c.fetchall()
    
    success = 0
    failed_blocked = 0

    for row in user_rows:
        tid = row[0]
        try:
            if media_type == "text":
                await context.bot.send_message(chat_id=tid, text=text_to_send)
            elif media_type == "photo":
                await context.bot.send_photo(chat_id=tid, photo=file_id, caption=caption)
            elif media_type == "video":
                await context.bot.send_video(chat_id=tid, video=file_id, caption=caption)
            elif media_type == "voice":
                await context.bot.send_voice(chat_id=tid, voice=file_id)
            elif media_type == "audio":
                await context.bot.send_audio(chat_id=tid, audio=file_id, caption=caption)
            
            c.execute("UPDATE users SET status='active' WHERE telegram_id=?", (tid,))
            success += 1
        except TelegramError:
            c.execute("UPDATE users SET status='blocked' WHERE telegram_id=?", (tid,))
            failed_blocked += 1
        
        await asyncio.sleep(0.05)

    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"📢 *Broadcast Completed!*\n\n"
        f"✅ Total Sent: `{success}`\n"
        f"❌ Blocked/Failed: `{failed_blocked}`",
        parse_mode="Markdown"
    )

def main():
    init_db()
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Anti-sleep ping thread ko piche background me chalayein
    threading.Thread(target=ping_server, daemon=True).start()

    bot_app = ApplicationBuilder().token(TOKEN).build()
    
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("stats", stats))
    bot_app.add_handler(CommandHandler("broadcast", broadcast))
    bot_app.add_handler(CallbackQueryHandler(buttons))
    bot_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, uid_handler))
    
    bot_app.run_polling()

if __name__ == "__main__":
    asyncio.set_event_loop(asyncio.new_event_loop())
    main()
