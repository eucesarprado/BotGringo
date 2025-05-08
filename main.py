from flask import Flask, request, jsonify
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, Updater
import stripe
import threading
import os

# --- CONFIG ---
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
GROUP_ID = int(os.environ['GROUP_ID'])
STRIPE_SECRET = os.environ['STRIPE_SECRET']
WEBHOOK_SECRET = os.environ['WEBHOOK_SECRET']

stripe.api_key = STRIPE_SECRET

# --- TELEGRAM BOT ---
app = Flask(__name__)
bot = Bot(token=TELEGRAM_TOKEN)
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dispatcher = updater.dispatcher


# Cria link dinâmico para assinatura
@app.route('/checkout')
def create_checkout():
    telegram_id = request.args.get('telegram_id')
    plan = request.args.get('plan', 'monthly')

    if not telegram_id:
        return jsonify({'error': 'telegram_id is required'}), 400

    price_lookup = {
        'monthly': 'price_xxx1',  # substitua pelos IDs reais dos preços
        'quarterly': 'price_xxx2',
        'lifetime': 'price_xxx3'
    }

    price_id = price_lookup.get(plan)
    if not price_id:
        return jsonify({'error': 'invalid plan'}), 400

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': price_id,
            'quantity': 1,
        }],
        mode='payment',
        success_url='https://t.me/seubot',
        cancel_url='https://t.me/seubot',
        metadata={
            'telegram_id': telegram_id
        }
    )
    return jsonify({'url': checkout_session.url})


def start(update: Update, context: CallbackContext):
    telegram_id = update.effective_user.id
    buttons = [
        [InlineKeyboardButton("📆 Assinar Mensal (€9.90)", url=f"https://seubot.up.railway.app/checkout?telegram_id={telegram_id}&plan=monthly")],
        [InlineKeyboardButton("📅 Trimestral (€19.90)", url=f"https://seubot.up.railway.app/checkout?telegram_id={telegram_id}&plan=quarterly")],
        [InlineKeyboardButton("💎 Vitalício (€25.90)", url=f"https://seubot.up.railway.app/checkout?telegram_id={telegram_id}&plan=lifetime")]
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

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
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
