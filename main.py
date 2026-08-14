import os
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

WEBAPP_URL = "https://bkbingo-pro.onrender.com"

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

@socketio.on('register_user')
def handle_register(data):
    uid = data.get('user_id', 12345)
    name = data.get('name', 'Player')
    phone = data.get('phone', '')
    
    with db_lock:
        if uid not in users_db:
            users_db[uid] = {"id": uid, "name": name, "phone": phone, "balance": 0.0, "history": []}
            emit('auth_response', {'status': 'success', 'message': 'በተሳካ ሁኔታ ተመዝግበዋል!', 'balance': 0.0}, room=request.sid)
        else:
            emit('auth_response', {'status': 'success', 'message': 'እንኳን ደህና መጡ!', 'balance': users_db[uid]["balance"]}, room=request.sid)

@socketio.on('login_user')
def handle_login(data):
    phone = data.get('phone')
    with db_lock:
        for uid, user in users_db.items():
            if user["phone"] == phone:
                emit('auth_response', {'status': 'success', 'user_id': uid, 'balance': user["balance"]}, room=request.sid)
                return
        # ለሙከራ እንዲመች ከሌለ በራስ ሰር ይፈጥራል
        new_uid = random.randint(10000, 99999)
        users_db[new_uid] = {"id": new_uid, "name": "User", "phone": phone, "balance": 0.0, "history": []}
        emit('auth_response', {'status': 'success', 'user_id': new_uid, 'balance': 0.0}, room=request.sid)

@socketio.on('get_user_balance')
def handle_get_balance(data):
    uid = data.get('user_id', 12345)
    balance = 0.0
    with db_lock:
        if uid in users_db:
            balance = users_db[uid]["balance"]
    emit('balance_update', {'balance': balance})

@socketio.on('submit_deposit')
def handle_submit_deposit(data):
    uid = data.get('user_id', 12345)
    amount = float(data.get('amount', 0))
    tx_id = data.get('tx_id', '')
    method = data.get('method', 'Telebirr')
    
    with db_lock:
        if uid in users_db:
            users_db[uid]["balance"] += amount
            users_db[uid]["history"].append(f"Deposit: +{amount} ETB via {method} (Tx: {tx_id})")
            new_balance = users_db[uid]["balance"]
            emit('balance_update', {'balance': new_balance}, room=request.sid)
            emit('deposit_response', {'status': 'success', 'message': 'ክፍያዎ ተረጋገጠ! አሁን መጫወት ይችላሉ።', 'balance': new_balance})
        else:
            emit('deposit_response', {'status': 'error', 'message': 'እባክዎ መጀመሪያ ይግቡ!'})

@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = message.from_user.id
    name = message.from_user.first_name
    
    with db_lock:
        if uid not in users_db:
            users_db[uid] = {"id": uid, "name": name, "phone": "", "balance": 0.0, "history": []}

    markup = telebot.types.InlineKeyboardMarkup()
    web_app = telebot.types.WebAppInfo(url=WEBAPP_URL)
    markup.add(telebot.types.InlineKeyboardButton("🎲 ጨዋታ ጀምር (Open App)", web_app=web_app))
    markup.add(telebot.types.InlineKeyboardButton("👤 ፕሮፋይል / ባለንብረት", callback_data="profile_info"))
    markup.add(telebot.types.InlineKeyboardButton("💰 ዲፖዚት (Deposit)", callback_data="deposit_info"))
    markup.add(telebot.types.InlineKeyboardButton("🎧 የደንበኛ አገልግሎት (Support)", url="https://t.me/BkbingosupportBot"))

    bot.send_message(message.chat.id, f"👋 ሰላም <b>{name}</b>!\n\nወደ <b>BKBIngo House</b> ድንቅ የቢንጎ መድረክ በደህና መጡ 🎲\n💰 ባለንብረት:- {users_db[uid]['balance']} ETB\n\nለመጫወት ከታች ያለውን '🎲 ጨዋታ ጀምር' የሚለውን ይጫኑ።", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "deposit_info")
def callback_deposit(call):
    deposit_text = (
        "💳 <b>አካውንት ለመሙላት (Deposit)፦</b>\n\n"
        "🔹 <b>ቴሌብር (Telebirr):</b> 09xxxxxxxx (Biruk Reta)\n"
        "🔹 <b>ንግድ ባንክ (CBE):</b> 1000xxxxxxxxxx (Biruk Reta)\n\n"
        "ብር ከላኩ በኋላ በመተግበሪያው ውስጥ በዲፖዚት ፎርም በማስገባት አካውንትዎን ማفረስት ይችላሉ!"
    )
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, deposit_text, parse_mode="HTML")

@support_bot.message_handler(commands=['start'])
def support_welcome(message):
    support_bot.send_message(message.chat.id, "ሰላም! የ BKBINGO PRO የደንበኛ እርዳታ ማዕከል ነን። እንዴት ልንረዳዎ እንችላለን?", parse_mode="HTML")

if __name__ == '__main__':
    bot_thread = Thread(target=lambda: bot.infinity_polling(none_stop=True))
    bot_thread.daemon = True
    bot_thread.start()
    
    support_thread = Thread(target=lambda: support_bot.infinity_polling(none_stop=True))
    support_thread.daemon = True
    support_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
