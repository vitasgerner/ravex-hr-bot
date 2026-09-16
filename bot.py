import os
import json
import base64
import logging
from datetime import datetime
import anthropic
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Состояния диалога
TD_NUMBER, PHOTO, FULL_NAME, POSITION, SALARY, SCHEDULE, DATE, CONFIRM = range(8)

# Данные компании
COMPANY = {
    "name": "RAVEX FOOD GROUP",
    "bin": "260440030820",
    "address": "Республика Казахстан, Атырауская область, город Атырау, Микрорайон Жерұйық, улица Кенжебай Маденов, дом 1В, н.п. 1",
    "director": "Гернер Виталий Иванович",
    "director_iin": "830615550577",
    "director_id": "056009662",
}

POSITIONS = [
    ["Сушист", "Кассир"],
    ["Оператор-кассир", "Шеф-повар"],
    ["Управляющий", "Кухонный рабочий"],
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я HR-бот RAVEX FOOD GROUP.\n\n"
        "Оформляю нового сотрудника.\n\n"
        "📋 Сначала открой Реестр ТД и посмотри следующий свободный номер.\n\n"
        "Введи номер трудового договора (например: 09/26):",
        reply_markup=ReplyKeyboardRemove()
    )
    return TD_NUMBER

async def get_td_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    td = update.message.text.strip()
    context.user_data["td_number"] = td
    await update.message.reply_text(
        f"✅ Номер ТД: {td}\n\n"
        f"Теперь скинь фото удостоверения личности сотрудника 📸"
    )
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Пожалуйста, отправь именно фото 📸")
        return PHOTO

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(file.file_path) as resp:
            photo_bytes = await resp.read()

    photo_base64 = base64.standard_b64encode(photo_bytes).decode("utf-8")
    await update.message.reply_text("⏳ Читаю данные удостоверения...")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": photo_base64}
                },
                {
                    "type": "text",
                    "text": 'Прочитай данные с удостоверения личности РК и верни ТОЛЬКО JSON: {"full_name": "ФИО полностью", "iin": "ИИН 12 цифр", "id_number": "номер удостоверения", "id_date": "дата выдачи ДД.ММ.ГГГГ"}. Только JSON, без пояснений.'
                }
            ]
        }]
    )

    try:
        text = response.content[0].text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        context.user_data["employee"] = data

        await update.message.reply_text(
            f"✅ Данные прочитаны:\n\n"
            f"👤 ФИО: {data.get('full_name', '—')}\n"
            f"🔢 ИИН: {data.get('iin', '—')}\n"
            f"📄 Уд. №{data.get('id_number', '—')} от {data.get('id_date', '—')}\n\n"
            f"Всё верно? Выбери должность:",
            reply_markup=ReplyKeyboardMarkup(POSITIONS, one_time_keyboard=True)
        )
        return POSITION
    except:
        context.user_data["employee"] = {}
        await update.message.reply_text(
            "Не смог прочитать фото. Введи данные вручную:\n"
            "ФИО: ...\nИИН: ...\nУд. №: ...\nДата выдачи: ДД.ММ.ГГГГ"
        )
        return FULL_NAME

async def get_name_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    data = {}
    for line in text.strip().split("\n"):
        if "ФИО:" in line:
            data["full_name"] = line.replace("ФИО:", "").strip()
        elif "ИИН:" in line:
            data["iin"] = line.replace("ИИН:", "").strip()
        elif "Уд. №:" in line:
            data["id_number"] = line.replace("Уд. №:", "").strip()
        elif "Дата выдачи:" in line:
            data["id_date"] = line.replace("Дата выдачи:", "").strip()
    context.user_data["employee"] = data
    await update.message.reply_text(
        "Выбери должность:",
        reply_markup=ReplyKeyboardMarkup(POSITIONS, one_time_keyboard=True)
    )
    return POSITION

async def get_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["position"] = update.message.text.strip()
    keyboard = [["90 000", "120 000"], ["150 000", "Другой"]]
    await update.message.reply_text(
        "💰 Оклад (тенге в месяц):",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return SALARY

async def get_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    salary = update.message.text.strip().replace(" ", "")
    context.user_data["salary"] = salary
    keyboard = [["2/2", "5/2"]]
    await update.message.reply_text(
        "📅 График работы:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return SCHEDULE

async def get_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["schedule"] = update.message.text.strip()
    today = datetime.now().strftime("%d.%m.%Y")
    keyboard = [[today, "Другая дата"]]
    await update.message.reply_text(
        f"📆 Дата приёма на работу:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return DATE

async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = update.message.text.strip()
    if date == "Другая дата":
        await update.message.reply_text(
            "Введи дату в формате ДД.ММ.ГГГГ (например: 14.09.2026):",
            reply_markup=ReplyKeyboardRemove()
        )
        return DATE
    context.user_data["start_date"] = date

    emp = context.user_data.get("employee", {})
    td = context.user_data.get("td_number", "—")
    pos = context.user_data.get("position", "—")
    salary = context.user_data.get("salary", "—")
    schedule = context.user_data.get("schedule", "—")

    keyboard = [["✅ Верно, сохранить", "❌ Начать заново"]]
    await update.message.reply_text(
        f"📋 Проверь данные:\n\n"
        f"📄 № ТД: {td}\n"
        f"👤 {emp.get('full_name', '—')}\n"
        f"🔢 ИИН: {emp.get('iin', '—')}\n"
        f"📄 Уд. №{emp.get('id_number', '—')} от {emp.get('id_date', '—')}\n"
        f"💼 Должность: {pos}\n"
        f"💰 Оклад: {salary} тенге\n"
        f"📅 График: {schedule}\n"
        f"📆 Дата приёма: {date}\n\n"
        f"Всё верно?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return CONFIRM

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "Начать заново" in update.message.text:
        await update.message.reply_text("Начинаем заново. Введи номер ТД:", reply_markup=ReplyKeyboardRemove())
        return TD_NUMBER

    emp = context.user_data.get("employee", {})
    td = context.user_data.get("td_number", "—")
    pos = context.user_data.get("position", "—")
    salary = context.user_data.get("salary", "—")
    schedule = context.user_data.get("schedule", "—")
    date = context.user_data.get("start_date", "—")

    summary = (
        f"✅ *Данные сохранены!*\n\n"
        f"📄 № ТД: *{td}*\n"
        f"👤 *{emp.get('full_name', '—')}*\n"
        f"🔢 ИИН: `{emp.get('iin', '—')}`\n"
        f"📄 Уд. №{emp.get('id_number', '—')} от {emp.get('id_date', '—')} МВД РК\n"
        f"💼 Должность: {pos}\n"
        f"💰 Оклад: {salary} тенге\n"
        f"📅 График: {schedule}\n"
        f"📆 Дата приёма: {date}\n\n"
        f"📋 *Следующие шаги:*\n"
        f"1️⃣ Внеси № ТД в Реестр\n"
        f"2️⃣ Создай 4 документа\n"
        f"3️⃣ Распечатай и подпиши\n"
        f"4️⃣ Загрузи в Google Drive\n"
        f"5️⃣ Передай бухгалтеру → Енбек (5 рабочих дней!)"
    )

    await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено. Напиши /start чтобы начать заново.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            TD_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_td_number)],
            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name_manual)],
            POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_position)],
            SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_salary)],
            SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_schedule)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
