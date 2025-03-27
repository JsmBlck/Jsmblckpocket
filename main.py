import os
import random
import asyncio
import threading 
import requests
import time
import json
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
USER_STARTED_LOG_ID = int(os.getenv("USER_STARTED_LOG_ID", "0"))


# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
import json
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("TelegramBotMembers").sheet1

# Load authorized users from Google Sheets
def load_users():
    try:
        users = sheet.col_values(1)
        return set(map(int, users)) | set(ADMIN_IDS)
    except Exception as e:
        print(f"Error loading users: {e}")
        return set(ADMIN_IDS)

# Save authorized users to Google Sheets
def save_users():
    sheet.clear()
    for idx, user_id in enumerate(AUTHORIZED_USERS):
        sheet.update_cell(idx + 1, 1, user_id)

# Authorized users list
AUTHORIZED_USERS = load_users()

# List of OTC pairs
otc_pairs = [
    "🇦🇪/🇨🇳 AED/CNY OTC", 
    "🇦🇺/🇨🇭 AUD/CHF OTC", 
    "🇧🇭/🇨🇳 BHD/CNY OTC", 
    "🇪🇺/🇺🇸 EUR/USD OTC", 
    "🇨🇦/🇨🇭 CAD/CHF OTC", 
    "🇳🇿/🇯🇵 NZD/JPY OTC", 
    "🇪🇺/🇨🇭 EUR/CHF OTC", 
    "🇬🇧/🇯🇵 GBP/JPY OTC"
]

# AI-like responses
responses = [
        "🟢 **BUY Signal for {pair}** \n\n"
        "📡 **AI Analysis:** Market momentum detected 📈\n\n"
        "🧠 **Trend Prediction:** Upward breakout potential ✅\n\n"
        "⚙️ **Algorithm Confidence:** {confidence}%\n\n"
        "🔍 **Data Sources:** Multi-indicator convergence 📊",

        "🔴 **SELL Signal for {pair}** \n\n"
        "📡 **AI Analysis:** Bearish pressure increasing 📉\n\n"
        "🧠 **Trend Prediction:** Price drop likely 🔻\n\n"
        "⚙️ **Algorithm Confidence:** {confidence}%\n\n"
        "🔍 **Data Sources:** Volatility spike detected 📊",
        
        "🟢 **BUY Opportunity for {pair}** \n\n"
        "⚡ **AI-Driven Forecast:** Entry zone detected 🔥\n\n"
        "🔍 **Technical Metrics:** RSI, MACD, Bollinger Bands aligned 📊\n\n"
        "⚙️ **Confidence Score:** {confidence}%\n\n"
        "🛠️ **Risk-to-Reward Ratio:** Favorable entry 📈",
        
        "🔴 **SELL Alert for {pair}** \n\n"
        "📡 **AI Computation:** Market downturn projected 📉\n\n"
        "🧠 **Trend Confidence:** {confidence}%\n\n"
        "🔍 **Indicators Triggered:** RSI divergence, Moving Averages cross 🔴\n\n"
        "⏳ **Projected Price Action:** Decline expected soon ⚠️",
        
        "🟢 **Potential BUY for {pair}** \n\n"
        "🧠 **Deep Learning Model:** Bullish breakout anticipated 📈\n\n"
        "📡 **Multi-Source Data:** Liquidity surge detected 🔎\n\n"
        "⚙️ **Trade Probability:** {confidence}%\n\n"
        "🛠️ **Automated Analysis:** Strong market positioning 💰",
        
        "🔴 **Strong SELL Signal for {pair}** \n\n"
        "📊 **AI Risk Assessment:** Bearish divergence confirmed 📉\n\n"
        "📡 **Market Structure Shift:** Resistance level hit 🔻\n\n"
        "⚙️ **Confidence Score:** {confidence}%\n\n"
        "🛠️ **Machine Learning Model:** Trend reversal detected ⚠️",
        
        "🟢 **BUY Setup for {pair}** \n\n"
        "📡 **AI Projection:** Long position favored 🏆\n\n"
        "🔍 **Key Technicals:** Support retest, bullish candlestick pattern 📊\n\n"
        "⚙️ **Market Sentiment:** Positive trend confirmation ✅\n\n"
        "📌 **Trade Execution Level:** Optimized for profit 🚀",
        
        "🔴 **SELL Opportunity for {pair}** \n\n"
        "🧠 **Neural Network Prediction:** Market rejection detected 🚨\n\n"
        "📡 **Volatility Spike:** Unstable conditions ahead 📊\n\n"
        "⚙️ **Sell Confirmation:** {confidence}%\n\n"
        "🔍 **Price Projection:** Lower lows incoming 📉",
        
        "🟢 **Bullish BUY Signal for {pair}** \n\n"
        "📡 **Market Sentiment:** Positive trend reinforcement 📈\n\n"
        "🧠 **Neural Analysis:** Strengthened support detected ✅\n\n"
        "⚙️ **Prediction Accuracy:** {confidence}%\n\n"
        "🔍 **AI Confirmation:** Strong entry potential 📊",
        
        "🔴 **Confirmed SELL for {pair}** \n\n"
        "📊 **AI Trend Projection:** Downtrend continuation ⚠️\n\n"
        "📡 **Liquidity Analysis:** Weak buyer momentum detected 🔻\n\n"
        "⚙️ **Market Reversal Probability:** {confidence}%\n\n"
        "🛠️ **Trade Strategy:** Risk-managed exit suggested 💡"
    ]
# Image file IDs (replace with actual Telegram file IDs)
buy_image_id = "AgACAgUAAxkBAAKoeGfXFrnEQl8MM1xgIsN2tPB9e6q5AAJTwTEbswi5VgbbUQFoQg5PAQADAgADcwADNgQ"
sell_image_id = "AgACAgUAAxkBAAKodmfXFrYnjhxh-wsJcDm1pcjGjC8UAAJSwTEbswi5VtcdWgjFsLqrAQADAgADeAADNgQ"

# Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def keep_alive():
    render_url = "https://jamespocket2.onrender.com"
    while True:
        try:
            requests.get(render_url)
            print("✅ Self-ping successful!")
        except Exception as e:
            print(f"❌ Ping failed: {e}")
        time.sleep(300)

async def log_activity(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send logs to the log channel."""
    asyncio.create_task(context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=message))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    print(f"User {user.id} ({user.username}) started the bot.")

    asyncio.create_task(log_activity(context, f"User Started: \n{user.id} \n@{user.username}"))
    
    log_message = (
        f"🔔 User Started the Bot\n"
        f"👤 User ID: {user.id}\n"
        f"📛 Username: {user.username}"
    )
    
    log_message = escape_markdown_v2(log_message)
    
    if user.id not in AUTHORIZED_USERS:
        await update.message.reply_text(
    "❌ Access Denied. You are not authorized to use this bot.\n\n"
    "To get access, kindly join the channel: https://t.me/+zPRC_d9dHMM0NDBl "
    "or message @JoinLunaX."
)
        return

    await context.bot.send_message(chat_id=USER_STARTED_LOG_ID, text=log_message, parse_mode="MarkdownV2")

    
    welcome_message = """
📊 *Welcome to the Binary Trading Assistant!*

Our bot provides real-time trading signals for OTC Forex pairs.

🔹 *How It Works:*
✔️ Select an OTC Forex pair from the options below.
✔️ Receive a trading signal with market analysis.
✔️ Execute the trade quickly for optimal results.

⚠️ *Disclaimer:* Trading involves risk. Always trade responsibly.
    """
    keyboard = [otc_pairs[i:i + 2] for i in range(0, len(otc_pairs), 2)]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="Markdown")

async def simulate_analysis(update: Update, pair: str) -> None:
    analyzing_messages = [
        "⚡ Scanning {pair}...",
        "🤖 AI analyzing {pair}...",
        "📡 Data crunching {pair}...",
        "🔍 Processing {pair}...",
        "📊 Evaluating {pair}..."
    ]

    analyzing_message = await update.message.reply_text(random.choice(analyzing_messages).format(pair=pair), parse_mode="Markdown")

    step_variations = [
        ["🛰️ Processing data for {pair}...", "📡 Gathering insights for {pair}...", "🔍 Extracting indicators for {pair}..."],
        ["🤖 Running AI model for {pair}...", "🧠 Predicting trends for {pair}...", "🔬 Simulating movement for {pair}..."],
        ["✅ Generating signal for {pair}...", "📊 Finalizing analysis for {pair}...", "📌 Confirming trade for {pair}..."]
    ]

    # steps = [random.choice(variation) for variation in step_variations]
    steps = [random.choice(variation).format(pair=pair) for variation in step_variations]

    for step in steps:
        await asyncio.sleep(random.uniform(1.5, 2.0)) 
        await analyzing_message.edit_text(step, parse_mode="Markdown")

    BUY_IMAGES = [
        "AgACAgUAAxkBAAIC3Wfa0e3y-ouFKa6JOE5TrjMyVpYQAAI0xjEbJdXZVlAqAqzY7xPZAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIC32fa0fFFdgk8AAHApNIrPmAFUHhGBwACNcYxGyXV2VYAAfujv7riO-IBAAMCAAN5AAM2BA",
        "AgACAgUAAxkBAAIC4Wfa0fUMZIXOcxda79GylW6-y54UAAI2xjEbJdXZVmuEQW-_v5l5AQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIC42fa0fpL2URh_isSZJOXNrxOpzIlAAI3xjEbJdXZVsHl6tcbg9SRAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIDImfa1Mf68oZHY2FkYPokoinkYOlvAAJCxjEbJdXZVi8iv4nmyXOYAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIDJGfa1M0rxAfqK0_W8v6C0_M_8eRjAAJDxjEbJdXZVjRnqLuYoipWAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIDJmfa1M_y6xW2vZeMihGtRTs5Wm6SAAJExjEbJdXZVunXgA9Y_hjwAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIDKGfa1NJpYUQkFhngymP8-gioQ9HCAAJGxjEbJdXZVlEarAO3d22MAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIDKmfa1NWuyzq8Y5vfW1Zkpzqdf_wgAAJIxjEbJdXZVnPqB5rjVa8LAQADAgADeQADNgQ"
    ]
    SELL_IMAGES = [
        "AgACAgUAAxkBAAIEU2fa57niAxLnKpMeaKE5s57MDEJDAAJ5xjEbJdXZVp-owMy8c7xrAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIEVWfa579UPg_FN0cklGntfYzF2wyBAAJ6xjEbJdXZVvlKWKPY6im2AQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIEV2fa58Jd1oXJgR0LNuvRmAYP4UilAAJ7xjEbJdXZVr-3Zfgi5IpDAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIEWWfa58a5_-Fd9U42iFPefMN19NmEAAJ8xjEbJdXZVrBV8Mn5BbpiAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIEW2fa58j02bHojLQVXQWSb5dAlZ6dAAJ9xjEbJdXZVi06ljg6lLNwAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIEXWfa58tBU--AK00Jk3hq2xlljS3EAAJ-xjEbJdXZVhkFOsaPRky6AQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIEX2fa582HGTvYtsES2jzVG2zCX7aCAAJ_xjEbJdXZVp1E2cU6r-ZkAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIEYWfa59A02wmUPzJeFbw1-j4je4YjAAKAxjEbJdXZVoSm5PZcGWVJAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIEY2fa59TzGzQ2W18wNWIb3yWCtiywAAKBxjEbJdXZVu_xYOcUbp-bAQADAgADeQADNgQ",
        "AgACAgUAAxkBAAIEZWfa59iDaH-55zwTJiuYK0ePMU3bAAKCxjEbJdXZVm3aJGmv8Bh0AQADAgADeQADNgQ"
    ]
    buy_image_id = random.choice(BUY_IMAGES)
    sell_image_id = random.choice(SELL_IMAGES)
    
    confidence = random.randint(75, 80)
    signal_type = "BUY" if random.random() > 0.5 else "SELL"
    image_id = buy_image_id if signal_type == "BUY" else sell_image_id
    response_template = random.choice([r for r in responses if signal_type in r])
    caption = response_template.format(pair=pair, confidence=confidence)

    # Delete the last message before sending final response with image
    await analyzing_message.delete()
    await update.message.reply_photo(photo=image_id, caption=caption, parse_mode="Markdown")

    follow_up_messages = [
        "🔄 Ready for the next trade? Choose another OTC pair.",
        "📈 Let's keep it going! Select another pair.",
        "🧐 What's next? Drop another OTC pair below.",
        "⚡ Keep the momentum! Enter another OTC pair.",
        "🚀 Ready for more signals? Send your next OTC pair."
    ]
    await asyncio.sleep(random.uniform(0.5, 1.0))    # Small delay before follow-up
    await update.message.reply_text(random.choice(follow_up_messages))

async def add_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    try:
        new_user_id = int(context.args[0])
        AUTHORIZED_USERS.add(new_user_id)
        save_users()
        await update.message.reply_text(f"✅ User {new_user_id} has been added successfully.")

        # Log new user addition
        await log_activity(context, f"✅ **User Added:** {new_user_id} by @{user.username}")

    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: /addmember <user_id>")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_message = update.message.text
    
    if user.id not in AUTHORIZED_USERS:
        await update.message.reply_text("❌ Access Denied. You are not authorized to use this bot.")
        return
    
    if user_message in otc_pairs:
        print(f"User {user.id} ({user.username}) selected: {user_message}")
        await log_activity(context, f"Trade Selection: {user.id} @{user.username} \nSelected: {user_message}")
        await simulate_analysis(update, user_message)
    elif not user_message.startswith("/"):
        await log_activity(context, f"Message Received: {user.id} @{user.username} \nMessage: {user_message}")
        await update.message.reply_text("Please select a valid OTC pair from the keyboard.")

def escape_markdown_v2(text):
    """Escape special characters for MarkdownV2"""
    return re.sub(r"([_*[\]()~`>#+\-=|{}.!])", r"\\\1", text)

def run_flask():
    app.run(host="0.0.0.0", port=8080)

def main() -> None:
    application = Application.builder().token(TOKEN).concurrent_updates(True).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addmember", add_member))  
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    threading.Thread(target=keep_alive).start()
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
