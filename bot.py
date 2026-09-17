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
ALLOWED_USERS = [1357240248, 5877382242]  # Виталий, Управляющий
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

TD_NUMBER, PHOTO, FULL_NAME, POSITION, SALARY, SCHEDULE, DATE, CONFIRM = range(8)

COMPANY = {
    "name": "RAVEX FOOD GROUP",
    "bin": "260440030820",
    "address": "РК, Атырауская область, г. Атырау, мкр. Жерұйық, ул. Кенжебай Маденов, д. 1В, кв/офис 1",
    "address_full": "Республика Казахстан, Атырауская область, город Атырау, Микрорайон Жерұйық, улица Кенжебай Маденов, дом 1В, н.п. 1, почтовый индекс 060000",
    "director": "Гернер Виталий Иванович",
    "director_short": "Гернер В.И.",
}

POSITIONS = [
    ["Сушист", "Кассир"],
    ["Оператор-кассир", "Шеф-повар"],
    ["Управляющий", "Кухонный рабочий"],
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("⛔ Нет доступа.")
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Привет! Я HR-бот RAVEX FOOD GROUP.\n"
        "Оформляю нового сотрудника.",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "📋 Сначала открой Реестр ТД и посмотри следующий свободный номер.\n\n"
        "Введи номер трудового договора (например: 09/26):"
    )
    return TD_NUMBER

async def get_td_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    td = update.message.text.strip()
    if "Оформить нового" in td or "Проверить" in td:
        return await start(update, context)
    context.user_data["td_number"] = td
    await update.message.reply_text(f"✅ Номер ТД: {td}")
    await update.message.reply_text("Теперь скинь фото удостоверения личности сотрудника 📸")
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
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": photo_base64}},
                {"type": "text", "text": 'Прочитай данные с удостоверения личности РК и верни ТОЛЬКО JSON: {"full_name": "ФИО полностью", "iin": "ИИН 12 цифр", "id_number": "номер удостоверения", "id_date": "дата выдачи ДД.ММ.ГГГГ"}. Только JSON, без пояснений.'}
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
    if salary == "Другой":
        await update.message.reply_text(
            "Введи сумму оклада (только цифры, например: 95000):",
            reply_markup=ReplyKeyboardRemove()
        )
        return SALARY
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
        "📆 Дата приёма на работу:",
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

    keyboard = [["✅ Верно, создать документы", "❌ Начать заново"]]
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
        return await start(update, context)

    emp = context.user_data.get("employee", {})
    td = context.user_data.get("td_number", "—")
    pos = context.user_data.get("position", "—")
    salary = context.user_data.get("salary", "—")
    schedule = context.user_data.get("schedule", "—")
    date = context.user_data.get("start_date", "—")

    await update.message.reply_text("⏳ Генерирую документы, подожди...", reply_markup=ReplyKeyboardRemove())

    try:
        from generate_docs import generate_all_docs
        import tempfile

        data = {
            "td_number": td,
            "employee": emp,
            "position": pos,
            "salary": str(salary).replace(" ", ""),
            "schedule": schedule,
            "start_date": date,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = generate_all_docs(data, tmpdir)

            await update.message.reply_text(
                f"✅ *Документы готовы!*\n\n"
                f"📄 № ТД: *{td}*\n"
                f"👤 *{emp.get('full_name', '—')}*\n"
                f"🔢 ИИН: `{emp.get('iin', '—')}`\n"
                f"📄 Уд. №{emp.get('id_number', '—')} от {emp.get('id_date', '—')} МВД РК\n"
                f"💼 Должность: {pos}\n"
                f"💰 Оклад: {salary} тенге\n"
                f"📅 График: {schedule}\n"
                f"📆 Дата приёма: {date}",
                parse_mode="Markdown"
            )

            doc_names = {
                'td': '📋 Трудовой договор',
                'prikaz': '📝 Приказ о приёме',
                'zayavlenie': '✍️ Заявление на приём',
                'ipn': '💰 Заявление ИПН',
            }
            for key, name in doc_names.items():
                with open(paths[key], 'rb') as f:
                    await update.message.reply_document(
                        document=f,
                        filename=paths[key].split('/')[-1],
                        caption=name
                    )

            keyboard = [["🆕 Оформить нового сотрудника"]]
            await update.message.reply_text(
                "📋 *Следующие шаги:*\n"
                "1️⃣ Внеси № ТД в Реестр ТД\n"
                "2️⃣ Распечатай и подпиши все 4 документа\n"
                "3️⃣ Загрузи сканы в Google Drive\n"
                "4️⃣ Передай бухгалтеру → Енбек (5 рабочих дней!)",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}\n\nПопробуй снова /start")

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено. Напиши /start чтобы начать заново.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^🆕 Оформить нового сотрудника$"), start),
        ],
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
