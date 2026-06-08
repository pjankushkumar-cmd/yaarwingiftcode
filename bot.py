import sqlite3
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# --- CONFIGURATION ---
TOKEN = "8571936857:AAFb0c4snxxNaNPh46txsbpNhfiR2st-tGg"
ADMIN_ID = 8767998937
REGISTER_LINK = "https://4yaarwin.com/#/register?invitationCode=18426755757"
SUPPORT_ID = "@hackii_sureshote"

# --- FLASK SERVER (TO PREVENT SLEEP) ---
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

# --- BOT LOGIC ---
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY, uid TEXT)")
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📝 Register ID", url=REGISTER_LINK)],
        [InlineKeyboardButton("🎁 Work Gift Code", callback_data="gift")],
        [InlineKeyboardButton("📞 Support", callback_data="support")]
    ]
    await update.message.reply_text(
        "🎁 YAAR WIN GIFT CENTER 🎁\n\nCreate New ID To Work Gift Code",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "support":
        await q.message.reply_text(f"Support: {SUPPORT_ID}")

    elif q.data == "gift":
        gifts = [
            [InlineKeyboardButton("₹10", callback_data="amt_10"), InlineKeyboardButton("₹20", callback_data="amt_20")],
            [InlineKeyboardButton("₹30", callback_data="amt_30"), InlineKeyboardButton("₹50", callback_data="amt_50")],
            [InlineKeyboardButton("₹100", callback_data="amt_100"), InlineKeyboardButton("₹200", callback_data="amt_200")],
            [InlineKeyboardButton("₹500", callback_data="amt_500")]
        ]
        await q.message.reply_text("Select Gift Amount", reply_markup=InlineKeyboardMarkup(gifts))

    elif q.data.startswith("amt_"):
        amt = q.data.split("_")[1]
        context.user_data["gift_amount"] = amt
        await q.message.reply_text(f"Selected ₹{amt}\n\nNow send your UID.")

async def uid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.text.strip()
    user = update.effective_user

    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (user.id, uid))
    conn.commit()
    conn.close()

    amt = context.user_data.get("gift_amount", "Not Selected")

    await update.message.reply_text("✅ UID Saved Successfully")

    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"New Request\nUser: {user.full_name}\nID: {user.id}\nUID: {uid}\nGift: ₹{amt}"
        )
    except:
        pass

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    conn.close()
    await update.message.reply_text(f"Total Users: {total}")

def main():
    init_db()
    
    # Start Flask in a separate thread
    threading.Thread(target=run_flask).start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, uid_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
