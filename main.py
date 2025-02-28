import os
import random
import asyncio
import threading 
import requests
import time
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Replace 'YOUR_TOKEN' with the token you got from BotFather
TOKEN = os.getenv("TELEGRAM_TOKEN") or "7731418334:AAHtY9KU6RnQ0dVwLSXzqlocJZo3olK3vzM"

# List of OTC pairs
otc_pairs = [
    "AED/CNY OTC", "AUD/CHF OTC", "BHD/CNY OTC", "EUR/USD OTC", 
    "CAD/CHF OTC", "NZD/JPY OTC", "EUR/CHF OTC", "GBP/JPY OTC"
]

# List of randomized responses
responses = [
    "📊 **{pair}:** ⬆️⬆️⬆️ 🟢",
    "📊 **{pair}:** ⬇️⬇️⬇️ 🔴"
]

# Create a Flask app
app = Flask(__name__)

# Simple route to respond to UptimeRobot pings
@app.route('/')
def home():
    return "Bot is running!"

# Keep-alive function to prevent service from sleeping
def keep_alive():
    render_url = "https://jsmblckpocket.onrender.com"
    while True:
        try:
            requests.get(render_url)
            print("✅ Self-ping successful!")
        except Exception as e:
            print(f"❌ Ping failed: {e}")
        time.sleep(300)  # Ping every 5 minutes

# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    # Log the user's username
    print(f"User {user.id} ({user.username}) started the bot.")

    # Custom welcome message with Markdown formatting
    welcome_message = """
📊 *Welcome to the Binary Trading Bot!*

✅ Select an OTC Forex pair below to receive trading signals.

⏳ *All trades are based on a 5-second expiry time.* Ensure you follow this timing for better accuracy.

🚀 *After receiving a signal, open Pocket Option and execute the trade as fast as possible for optimal results.*

⚠️ *Disclaimer:* This bot provides trading signals based on market analysis. However, OTC (Over-The-Counter) pairs operate in a *simulated market* environment, which means price movements may not reflect real-world conditions. Due to this, signals may not always be accurate. Use the information at your own discretion and always practice responsible trading.

🎯 *Trading x Flow x Bot*
    """
    # Create a reply keyboard with the OTC pairs
    keyboard = [otc_pairs[i:i + 2] for i in range(0, len(otc_pairs), 2)]  # Arrange buttons in 2 columns
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)  # Keep keyboard visible
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"  # Enable Markdown formatting
    )

# Function to simulate analysis and send the final signal
async def simulate_analysis(update: Update, pair: str) -> None:
    # Send an "Analyzing..." message
    analyzing_message = await update.message.reply_text(
        f"🔍 Analyzing {pair}...",
        parse_mode="Markdown"
    )
    # Simulate analysis delay (3 seconds)
    await asyncio.sleep(3)
    # Randomly select a response template
    response_template = random.choice(responses)
    # Replace {pair} with the selected pair
    response = response_template.format(pair=pair)
    # Edit the "Analyzing..." message to show the final signal
    await analyzing_message.edit_text(
        response,
        parse_mode="Markdown"  # Enable Markdown formatting
    )

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    user = update.message.from_user

    if user_message in otc_pairs:
        # Log the user and their selected pair
        print(f"User {user.id} ({user.username}) selected: {user_message}")
        # Run the analysis simulation in the background
        asyncio.create_task(simulate_analysis(update, user_message))
    else:
        await update.message.reply_text("Please select a valid OTC pair from the keyboard.")

# Function to run the Flask app
# Run Flask app in a separate thread for UptimeRobot
def run_flask():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_flask).start()


def main() -> None:
    # Create an Application object with your bot's token
    application = Application.builder().token(TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))

    # Register a message handler to process messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Flask server in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    # Start the keep-alive function in a separate thread
    keep_alive_thread = threading.Thread(target=keep_alive)
    keep_alive_thread.start()

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
