import sqlite3
import threading
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.error import TelegramError

TOKEN = "8571936857:AAFb0c4snxxNaNPh46txsbpNhfiR2st-tGg"
ADMIN_ID = 8767998937  # Aapki Telegram User ID

REGISTER_LINK = "https://4yaarwin.com/#/register?invitationCode=18426755757"
SUPPORT_ID = "@hackii_sureshote"

app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is running!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    # Users table me status column add kiya hai (active / blocked)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY, 
            uid TEXT,
            status TEXT DEFAULT 'active'
        )
    """)
    conn.commit()
    conn.close()

# ---------------- USER SIDE FLOW ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # User ko database me active insert/update karein
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO users (telegram_id, uid, status) VALUES (?, '', 'active') ON CONFLICT(telegram_id) DO UPDATE SET status='active'", (user_id,))
    conn.commit()
    conn.close()

    kb = [[InlineKeyboardButton("📝 Register ID", url=REGISTER_LINK)]]
    await update.message.reply_text(
        "🎁 YAAR WIN GIFT CENTER 🎁\n\n"
        "Pehle upar diye gaye button se Register karein, "
        "phir register karne ke baad apni UID yahan send karein.",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def uid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Agar admin kisi ke message par reply kar raha hai, to ise user ki UID na samjhein
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

        # Admin ko alert text bhejte hain jisme user ki internal Telegram ID chhupi hogi (For Reply feature)
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

# ---------------- ADMIN EXCLUSIVE FEATURES ----------------

# 1. Easy Reply Feature: Admin kisi bhi message par Telegram ka official 'Reply' use karega
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_to = update.message.reply_to_message
    reply_text = update.message.text
    
    # Reply text me se user ki Telegram ID dhoondhte hain
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
            await update.message.reply_text(f"❌ Message nahi bheja ja saka. Shayad user ne bot block kiya hai. Error: {e}")
    else:
        await update.message.reply_text("❌ Main user ki Telegram ID nahi dhoondh paya. Kripya naye request format par hi reply karein.")

# 2. Live Stats Dashboard (/stats)
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
        "📊 *ADMIN DASHBOARD*\n\n"
        f"👥 Total Members: `{total}`\n"
        f"🟢 Active Members: `{active}`\n"
        f"🔴 Blocked Members: `{blocked}`\n\n"
        f"ℹ️ _Note: Jab aap broadcast karenge, tab blocked list automatic update ho jayegi._"
    )
    await update.message.reply_text(dashboard, parse_mode="Markdown")

# 3. All-Media Broadcast Command (/broadcast)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    # Check karein ki admin ne kisi photo/video/voice message ke sath /broadcast likha hai ya nahi
    msg = update.message
    has_media = False
    media_type = None
    
    # Check media type
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
        # Simple text broadcast ke liye command ke aage ka text check karein
        if msg.text.startswith("/broadcast "):
            media_type = "text"
            text_to_send = msg.text.replace("/broadcast ", "", 1)
        elif msg.reply_to_message and msg.reply_to_message.text:
            media_type = "text"
            text_to_send = msg.reply_to_message.text
        else:
            await update.message.reply_text(
                "❌ *Galat Tarika!*\n\n"
                "1. Normal Text ke liye likhein: `/broadcast Hello Users`\n"
                "2. Photo/Video/Voice bhejne ke liye, use upload karein aur caption me likhein `/broadcast` ya us par reply karke `/broadcast` likhein.",
                parse_mode="Markdown"
            )
            return

    await update.message.reply_text("⏳ Broadcast shuru ho raha hai... Sabhi users ko bheja ja raha hai.")

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
            
            # Agar successfully chala gaya to active mark karein
            c.execute("UPDATE users SET status='active' WHERE telegram_id=?", (tid,))
            success += 1
        except TelegramError as e:
            # Agar bot block ho chuka hai, to status update karein
            c.execute("UPDATE users SET status='blocked' WHERE telegram_id=?", (tid,))
            failed_blocked += 1
        
        # Rate limit se bachne ke liye chota sa pause
        await asyncio.sleep(0.05)

    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"📢 *Broadcast Completed!*\n\n"
        f"✅ Safalta se bheja: `{success}` users ko\n"
        f"❌ Blocked/Failed mila: `{failed_blocked}` users",
        parse_mode="Markdown"
    )

def main():
    init_db()
    threading.Thread(target=run_flask, daemon=True).start()

    bot_app = ApplicationBuilder().token(TOKEN).build()
    
    # Base Handlers
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("stats", stats))
    bot_app.add_handler(CommandHandler("broadcast", broadcast))
    bot_app.add_handler(CallbackQueryHandler(buttons))
    
    # Catch-all message handler text/media ke liye
    bot_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, uid_handler))
    
    bot_app.run_polling()

if __name__ == "__main__":
    asyncio.set_event_loop(asyncio.new_event_loop())
    main()
