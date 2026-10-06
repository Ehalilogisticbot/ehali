import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = 952300757

app = Flask(__name__)
telegram_app = Application.builder().token(BOT_TOKEN).build()

# Temporary storage for the current application step.
user_states = {}

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚚 Заказать машину", callback_data="order")],
        [InlineKeyboardButton("💰 Рассчитать стоимость", callback_data="price")],
        [InlineKeyboardButton("📋 Наши услуги", callback_data="services")],
        [InlineKeyboardButton("🏢 Для бизнеса", callback_data="business")],
        [InlineKeyboardButton("📞 Связаться с нами", callback_data="contact")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states.pop(update.effective_user.id, None)
    await update.message.reply_text(
        "🚚 ЕХАЛИ — грузоперевозки\n\n"
        "Перевозим грузы по Москве и области.\n"
        "Работаем с крупными компаниями, малым бизнесом и физическими лицами.\n\n"
        "Что вас интересует?",
        reply_markup=main_menu()
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data in ("order", "price"):
        user_states[uid] = {"step": 1, "type": "Заказ машины" if query.data == "order" else "Расчёт стоимости"}
        await query.message.reply_text("1/7 📍 Напишите адрес, откуда нужно забрать груз:")
    elif query.data == "services":
        await query.message.reply_text(
            "📋 Наши услуги:\n\n"
            "• Грузоперевозки по Москве и области\n"
            "• Подача машины к адресу\n"
            "• Перевозка мебели, техники, товаров и других грузов\n"
            "• Работа с физическими лицами и бизнесом\n\n"
            "Для оформления заявки нажмите «Заказать машину».",
            reply_markup=main_menu()
        )
    elif query.data == "business":
        await query.message.reply_text(
            "🏢 Работаем с крупными компаниями, малым бизнесом и физическими лицами.\n\n"
            "Если вам нужны регулярные перевозки или машина под задачи компании — оставьте заявку, и менеджер свяжется с вами.",
            reply_markup=main_menu()
        )
    elif query.data == "contact":
        await query.message.reply_text(
            "📞 Оставьте заявку через кнопку «Заказать машину» — менеджер свяжется с вами.\n\n"
            "Если хотите, позже сюда можно добавить телефон, сайт и соцсети.",
            reply_markup=main_menu()
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    state = user_states.get(uid)

    if not state:
        await update.message.reply_text("Выберите действие в меню:", reply_markup=main_menu())
        return

    text = update.message.text.strip()
    step = state["step"]

    fields = {
        1: ("from", "2/7 📍 Теперь напишите адрес доставки:"),
        2: ("to", "3/7 📦 Что перевозим?"),
        3: ("cargo", "4/7 ⚖️ Укажите примерный вес или объём:"),
        4: ("weight", "5/7 📅 Когда нужна машина?"),
        5: ("date", "6/7 👤 Как вас зовут?"),
        6: ("name", "7/7 📞 Напишите номер телефона:"),
    }

    if step in fields:
        key, next_text = fields[step]
        state[key] = text
        state["step"] += 1
        await update.message.reply_text(next_text)
        return

    if step == 7:
        state["phone"] = text

        order_type = state["type"]
        message = (
            "🆕 НОВАЯ ЗАЯВКА «ЕХАЛИ»\n\n"
            f"📌 Тип: {order_type}\n"
            f"📍 Откуда: {state['from']}\n"
            f"📍 Куда: {state['to']}\n"
            f"📦 Груз: {state['cargo']}\n"
            f"⚖️ Вес/объём: {state['weight']}\n"
            f"📅 Дата: {state['date']}\n"
            f"👤 Имя: {state['name']}\n"
            f"📞 Телефон: {state['phone']}\n\n"
            f"🆔 Telegram ID клиента: {uid}"
        )

        await context.bot.send_message(chat_id=ADMIN_ID, text=message)
        user_states.pop(uid, None)

        await update.message.reply_text(
            "✅ Заявка принята!\n\n"
            "Менеджер свяжется с вами для уточнения деталей и стоимости.",
            reply_markup=main_menu()
        )

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(buttons))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

@app.get("/")
def health():
    return "ЕХАЛИ bot is running"

@app.post("/telegram")
async def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    await telegram_app.process_update(update)
    return "ok"

@app.post("/set-webhook")
def set_webhook():
    # Use this endpoint once after deployment:
    # /set-webhook?url=https://YOUR-SERVICE.onrender.com/telegram
    url = request.args.get("url")
    if not url:
        return "Pass ?url=https://YOUR-SERVICE.onrender.com/telegram", 400
    import asyncio
    asyncio.run(telegram_app.bot.set_webhook(url=url))
    return f"Webhook set to {url}"

if __name__ == "__main__":
    import asyncio
    asyncio.run(telegram_app.initialize())
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
