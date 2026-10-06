import os
import json
import urllib.parse
import urllib.request

from flask import Flask, request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = 952300757
MANAGER_USERNAME = "Packand_Chill"

TIKTOK_URL = "https://www.tiktok.com/@ehali.logistic?_r=1&_t=ZN-9AKrRs5w5ze"
TG_URL = "https://t.me/ehali_logistik"
MANAGER_URL = "https://t.me/Packand_Chill"

app = Flask(__name__)
telegram_app = Application.builder().token(BOT_TOKEN).build()

# Temporary state for users while they are filling out a request.
user_states = {}


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚚 Заказать машину", callback_data="order")],
        [InlineKeyboardButton("📞 Связаться с менеджером", callback_data="manager")],
        [InlineKeyboardButton("📱 Наши соцсети", callback_data="socials")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states.pop(update.effective_user.id, None)

    await update.message.reply_text(
        "🚚 ЕХАЛИ — грузоперевозки\n\n"
        "Грузоперевозки по Москве и области.\n"
        "Работаем с крупными компаниями, малым бизнесом и физическими лицами.\n\n"
        "Что вас интересует?",
        reply_markup=main_menu(),
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "order":
        user_states[uid] = {"step": "details"}

        await query.message.reply_text(
            "🚚 Отлично! Чтобы оформить заявку, отправьте одним сообщением:\n\n"
            "📍 Откуда → куда\n"
            "📦 Что перевозим\n"
            "📅 Когда нужна машина\n\n"
            "Например:\n"
            "Москва, ул. Ленина → Москва, ул. Пушкина\n"
            "Мебель, около 500 кг\n"
            "10 октября, после 15:00"
        )

    elif query.data == "manager":
        await query.message.reply_text(
            "📞 Связаться с менеджером:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "💬 Написать менеджеру",
                    url=MANAGER_URL
                )],
                [InlineKeyboardButton("⬅️ В меню", callback_data="menu")],
            ]),
        )

    elif query.data == "socials":
        await query.message.reply_text(
            "📱 Мы в соцсетях:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("TikTok", url=TIKTOK_URL)],
                [InlineKeyboardButton("Telegram", url=TG_URL)],
                [InlineKeyboardButton("⬅️ В меню", callback_data="menu")],
            ]),
        )

    elif query.data == "menu":
        await query.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu(),
        )


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = user_states.get(uid)

    if not state or state.get("step") != "phone":
        await update.message.reply_text(
            "Выберите действие в меню:",
            reply_markup=main_menu(),
        )
        return

    phone = update.message.contact.phone_number
    await finish_order(update, context, uid, phone)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = user_states.get(uid)

    if not state:
        await update.message.reply_text(
            "Выберите действие в меню:",
            reply_markup=main_menu(),
        )
        return

    if state.get("step") == "details":
        state["details"] = update.message.text.strip()
        state["step"] = "phone"

        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Отправить номер телефона", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

        await update.message.reply_text(
            "Спасибо! Теперь оставьте номер телефона — Telegram подставит его автоматически.",
            reply_markup=keyboard,
        )
        return

    if state.get("step") == "phone":
        # Allow manual phone entry as a fallback.
        await finish_order(update, context, uid, update.message.text.strip())


async def finish_order(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int, phone: str):
    state = user_states.get(uid, {})
    details = state.get("details", "Не указаны")

    user = update.effective_user
    username = f"@{user.username}" if user.username else "не указан"

    admin_message = (
        "🆕 НОВАЯ ЗАЯВКА «ЕХАЛИ»\n\n"
        f"📋 Заявка клиента:\n{details}\n\n"
        f"📞 Телефон: {phone}\n"
        f"👤 Telegram: {username}\n"
        f"🆔 Telegram ID: {uid}"
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_message,
    )

    user_states.pop(uid, None)

    await update.message.reply_text(
        "✅ Заявка отправлена!\n\n"
        "Менеджер свяжется с вами для уточнения деталей.",
        reply_markup=ReplyKeyboardRemove(),
    )

    await update.message.reply_text(
        "Что хотите сделать дальше?",
        reply_markup=main_menu(),
    )


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(buttons))
telegram_app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))


@app.get("/")
def health():
    return "ЕХАЛИ bot is running"


@app.route("/set-webhook", methods=["GET", "POST"])
def set_webhook():
    url = request.args.get("url")
    if not url:
        return "Pass ?url=https://YOUR-SERVICE.onrender.com/telegram", 400

    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    payload = urllib.parse.urlencode({"url": url}).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))

        if result.get("ok"):
            return f"Webhook set to {url}"

        return f"Telegram API error: {result}", 502
    except Exception as exc:
        return f"Webhook setup error: {exc}", 502


@app.post("/telegram")
def telegram_webhook():
    import asyncio

    update_data = request.get_json(force=True)
    update = Update.de_json(update_data, telegram_app.bot)

    async def process():
        await telegram_app.initialize()
        try:
            await telegram_app.process_update(update)
        finally:
            await telegram_app.shutdown()

    asyncio.run(process())
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
