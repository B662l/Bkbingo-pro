import os
import time
import random
from threading import Thread, Lock
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import telebot

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
SUPPORT_BOT_TOKEN = "YOUR_SUPPORT_BOT_TOKEN"

bot = telebot.TeleBot(BOT_TOKEN)
support_bot = telebot.TeleBot(SUPPORT_BOT_TOKEN)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bkbingo_secret_key_2026'
socketio = SocketIO(app, cors_allowed_origins="*")

db_lock = Lock()
users_db = {}
cards_database = {}

def generate_sample_cards():
    global cards_database
    for card_id in range(1, 51):
        matrix = []
        nums = list(range(1, 76))
        random.shuffle(nums)
        for r in range(5):
            row = nums[r*5:(r+1)*5]
            if r == 2:
                row[2] = 0
            matrix.append(row)
        cards_database[card_id] = matrix

generate_sample_cards()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('get_user_balance')
def handle_get_balance(data):
    uid = data.get('user_id', 12345)
    balance = 100.0
    if uid in users_db:
        balance = users_db[uid]["balance"]
    emit('balance_update', {'balance': balance})

WEBAPP_URL = "https://bkbingo-pro.onrender.com"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    name = message.from_user.first_name
    
    with db_lock:
        if uid not in users_db:
            users_db[uid] = {"id": uid, "name": name, "balance": 100.0, "history": []}

    markup = telebot.types.InlineKeyboardMarkup()
    web_app = telebot.types.WebAppInfo(url=WEBAPP_URL)
    markup.add(telebot.types.InlineKeyboardButton("🎮 BKBINGO PRO ጀምር", web_app=web_app))
    markup.add(telebot.types.InlineKeyboardButton("💰 አካውንት መሙላት (Deposit)", callback_data="deposit_info"))
    markup.add(telebot.types.InlineKeyboardButton("🎧 የደንበኛ አገልግሎት (Support)", url="https://t.me/BkbingosupportBot"))

    bot.send_message(message.chat.id, f"ሰላም <b>{name}</b>! ወደ <b>BKBINGO PRO</b> በደህና መጡ።", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "deposit_info")
def callback_deposit(call):
    deposit_text = (
        "💳 <b>አካውንት ለመሙላት (Deposit)፦</b>\n\n"
        "🔹 <b>ቴሌብር:</b> 09xxxxxxxx (ብርቱኩን አበበ)\n"
        "🔹 <b>ንግድ ባንክ:</b> 1000xxxxxxxxxx\n\n"
        "ክፍያው ሲረጋገጥ ለድጋፍ ቦታችን ይላኩ!"
    )
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, deposit_text, parse_mode="HTML")

if __name__ == '__main__':
    bot_thread = Thread(target=lambda: bot.infinity_polling(none_stop=True))
    bot_thread.daemon = True
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
