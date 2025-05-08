from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, Updater
import stripe
import threading

# --- CONFIG ---
TELEGRAM_TOKEN = "7860792872:AAHWlHGQRJFehrjRnRf6PmJ2SDMscb2gdN4"
GROUP_ID = -1002546521987
STRIPE_SECRET = "your_stripe_secret_key"

stripe.api_key = STRIPE_SECRET

# Stripe links
LINK_MENSAL = "https://buy.stripe.com/4gw29d1Pe6AP6nm6oo"
LINK_TRIMESTRAL = "https://buy.stripe.com/14kbJN65u2kz1325kl"
LINK_VITALICIO = "https://buy.stripe.com/bIYdRV3Xmf7lbHG6oq"

# --- TELEGRAM BOT ---
app = Flask(__name__)
bot = Bot(token=TELEGRAM_TOKEN)
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dispatcher = updater.dispatcher


def start(update: Update, context: CallbackContext):
    buttons = [
        [InlineKeyboardButton("📆 Assinar Mensal (€9.90)", url=LINK_MENSAL)],
        [InlineKeyboardButton("📅 Trimestral (€19.90)", url=LINK_TRIMESTRAL)],
        [InlineKeyboardButton("💎 Vitalício (€25.90)", url=LINK_VITALICIO)]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="\u2728 Bem-vindo ao nosso VIP!\n\nEscolha um plano abaixo para liberar seu acesso ao grupo privado:",
        reply_markup=reply_markup
    )


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


# --- STRIPE WEBHOOK ---
@app.route('/stripe_webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = 'your_stripe_webhook_secret'

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception as e:
        return f"Webhook Error: {str(e)}", 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})
        telegram_id = metadata.get('telegram_id')

        if telegram_id:
            try:
                bot.send_message(chat_id=telegram_id, text="✅ Pagamento confirmado! Bem-vindo ao grupo VIP!")
                bot.invite_chat_member(chat_id=GROUP_ID, user_id=int(telegram_id))
            except Exception as e:
                print("Erro ao adicionar ao grupo:", e)

    return '', 200


def run_flask():
    app.run(host='0.0.0.0', port=5000)

# Iniciar bot e servidor Flask simultaneamente
threading.Thread(target=run_flask).start()
updater.start_polling()
updater.idle()
