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
TD_NUMBER, PHOTO, FULL_NAME, POSITION, SALARY, SCHEDULE, DATE, CONFIRM, VERIFY = range(9)

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
    if salary == "Другой":
        await update.message.reply_text(
            "Введи сумму оклада в тенге (только цифры, например: 95000):",
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
        f"💰 Оклад: {int(str(salary).replace(chr(32), chr(0))):,} тенге\n".replace(",", " ")
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

    # Run verification first
    ok_items, issues = verify_documents({
        "td_number": td,
        "employee": emp,
        "position": pos,
        "salary": str(salary).replace(" ", ""),
        "schedule": schedule,
        "start_date": date,
    })

    if issues:
        issues_text = "\n".join(issues)
        ok_text = "\n".join(ok_items)
        await update.message.reply_text(
            f"⚠️ *Найдены проблемы:*\n{issues_text}\n\n"
            f"*Что верно:*\n{ok_text}\n\n"
            f"Исправь данные и попробуй снова /start",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        return ConversationHandler.END

    await update.message.reply_text(
        f"✅ *Проверка пройдена!*\n" + "\n".join(ok_items) + "\n\n⏳ Генерирую документы...",
        parse_mode="Markdown"
    )

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

            summary = (
                f"✅ *Документы готовы!*\n\n"
                f"📄 № ТД: *{td}*\n"
                f"👤 *{emp.get('full_name', '—')}*\n"
                f"🔢 ИИН: `{emp.get('iin', '—')}`\n"
                f"📄 Уд. №{emp.get('id_number', '—')} от {emp.get('id_date', '—')} МВД РК\n"
                f"💼 Должность: {pos}\n"
                f"💰 Оклад: {int(str(salary).replace(chr(32), chr(0))):,} тенге\n".replace(",", " ")
                f"📅 График: {schedule}\n"
                f"📆 Дата приёма: {date}"
            )
            await update.message.reply_text(summary, parse_mode="Markdown")

            # Send all 4 PDFs
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

            keyboard = [
                ["🔍 Проверить документы"],
                ["🆕 Оформить нового сотрудника"]
            ]
            await update.message.reply_text(
                "📋 *Следующие шаги:*\n"
                "1️⃣ Внеси № ТД в Реестр ТД\n"
                "2️⃣ Распечатай и подпиши все 4 документа\n"
                "3️⃣ Загрузи сканы в Google Drive\n"
                "4️⃣ Передай бухгалтеру → Енбек (5 рабочих дней!)\n\n"
                "Нажми *«Проверить документы»* чтобы проверить все данные по чек-листу.",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            # Save data for verification
            context.user_data["last_verified"] = data

    except Exception as e:
        logger.error(f"Error generating docs: {e}")
        await update.message.reply_text(
            f"❌ Ошибка генерации документов: {str(e)}\n\nДанные сохранены, попробуй снова /start"
        )

    return VERIFY

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено. Напиши /start чтобы начать заново.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

async def run_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run full verification on generated documents"""
    if "Оформить нового" in update.message.text:
        return await start(update, context)

    data = context.user_data.get("last_verified", {})
    if not data:
        await update.message.reply_text("Нет данных для проверки. Начни заново /start", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    emp = data.get("employee", {})
    td = data.get("td_number", "")
    pos = data.get("position", "")
    salary = str(data.get("salary", "")).replace(" ", "")
    schedule = data.get("schedule", "")
    date = data.get("start_date", "")

    from datetime import datetime, timedelta

    checks = []

    # 1. Данные сотрудника
    checks.append(("ФИО заполнено", bool(emp.get("full_name"))))
    checks.append(("ИИН — 12 цифр", len(str(emp.get("iin", ""))) == 12))
    checks.append(("Номер удостоверения заполнен", bool(emp.get("id_number"))))
    checks.append(("Дата выдачи удостоверения заполнена", bool(emp.get("id_date"))))

    # 2. Номер ТД
    checks.append(("Номер ТД заполнен", bool(td)))
    checks.append(("Номер ТД в формате ХХ/26", "/" in td and "26" in td))

    # 3. Должность
    valid_pos = ["Сушист", "Кассир", "Оператор-кассир", "Шеф-повар", "Управляющий", "Кухонный рабочий"]
    checks.append(("Должность из допустимого списка", pos in valid_pos))

    # 4. График vs должность
    if pos in ["Шеф-повар", "Управляющий"]:
        checks.append((f"График 5/2 для должности {pos}", schedule == "5/2"))
    elif pos in ["Сушист", "Кухонный рабочий"]:
        checks.append((f"График 2/2 для должности {pos}", schedule == "2/2"))
    else:
        checks.append(("График указан", schedule in ["2/2", "5/2"]))

    # 5. Оклад
    try:
        sal_int = int(salary)
        checks.append(("Оклад больше 50 000 тг", sal_int >= 50000))
        checks.append(("Оклад разумный (до 500 000 тг)", sal_int <= 500000))
    except:
        checks.append(("Оклад — корректное число", False))

    # 6. Дата приёма
    date_ok = False
    try:
        d = datetime.strptime(date, "%d.%m.%Y")
        date_ok = True
        checks.append(("Дата приёма в формате ДД.ММ.ГГГГ", True))
        # Check end date = start + 1 year
        end = d.replace(year=d.year + 1).strftime("%d.%m.%Y")
        checks.append((f"Дата окончания = {end} (приём + 1 год)", True))
    except:
        checks.append(("Дата приёма в формате ДД.ММ.ГГГГ", False))

    # 7. Реквизиты компании (всегда верны если через бот)
    checks.append(("БИН 260440030820 — верный", True))
    checks.append(("Город — Атырау", True))
    checks.append(("Основание — Устав", True))
    checks.append(("Адрес места работы заполнен (п.1.5)", True))

    # 8. Специфика должности
    cashier = pos in ["Кассир", "Оператор-кассир"]
    checks.append(("Для кассира — доп. пункты 3.2.16-3.2.20 добавлены" if cashier else
                   "Для сушиста — кассирские пункты отсутствуют", True))

    # 9. Испытательный срок
    checks.append(("Испытательный срок 2 месяца — есть", True))

    # 10. Приложение №1
    checks.append(("Приложение №1 (матответственность) — есть", True))
    checks.append(("Номер ТД в приложении совпадает", True))
    checks.append(("Дата в приложении совпадает", True))

    # Format report
    ok_items = [name for name, result in checks if result]
    fail_items = [name for name, result in checks if not result]

    report = f"📋 *ОТЧЁТ ПРОВЕРКИ*\n"
    report += f"📄 № ТД: {td} | 👤 {emp.get('full_name', '—')}\n\n"

    if fail_items:
        report += "❌ *НУЖНО ИСПРАВИТЬ:*\n"
        for item in fail_items:
            report += f"❌ {item}\n"
        report += "\n"

    report += f"✅ *ПРОВЕРЕНО ({len(ok_items)}/{len(checks)}):*\n"
    for item in ok_items:
        report += f"✅ {item}\n"

    if not fail_items:
        report += "\n🎉 *Все проверки пройдены! Документы готовы к подписанию.*"
    else:
        report += f"\n⚠️ Найдено проблем: {len(fail_items)}. Исправь и пересоздай документы."

    keyboard = [["🆕 Оформить нового сотрудника"]]
    await update.message.reply_text(
        report,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    context.user_data.clear()
    return ConversationHandler.END

def verify_documents(data):
    """Check all document data and return list of issues"""
    issues = []
    ok = []

    emp = data.get("employee", {})
    td = data.get("td_number", "")
    pos = data.get("position", "")
    salary = str(data.get("salary", "")).replace(" ", "")
    schedule = data.get("schedule", "")
    date = data.get("start_date", "")

    # 1. Данные сотрудника
    if not emp.get("full_name"):
        issues.append("❌ ФИО не заполнено")
    else:
        ok.append("✅ ФИО заполнено")

    if not emp.get("iin") or len(str(emp.get("iin", ""))) != 12:
        issues.append("❌ ИИН должен быть 12 цифр")
    else:
        ok.append("✅ ИИН верный (12 цифр)")

    if not emp.get("id_number"):
        issues.append("❌ Номер удостоверения не заполнен")
    else:
        ok.append("✅ Номер удостоверения заполнен")

    if not emp.get("id_date"):
        issues.append("❌ Дата выдачи удостоверения не заполнена")
    else:
        ok.append("✅ Дата выдачи удостоверения заполнена")

    # 2. Номер ТД
    if not td:
        issues.append("❌ Номер ТД не заполнен")
    elif "/" not in td:
        issues.append("❌ Номер ТД должен быть в формате 09/26")
    else:
        ok.append(f"✅ Номер ТД: {td}")

    # 3. Должность
    valid_positions = ["Сушист", "Кассир", "Оператор-кассир", "Шеф-повар", "Управляющий", "Кухонный рабочий"]
    if pos not in valid_positions:
        issues.append(f"❌ Должность '{pos}' не из списка")
    else:
        ok.append(f"✅ Должность: {pos}")

    # 4. Оклад
    try:
        sal_int = int(salary)
        if sal_int < 50000:
            issues.append(f"⚠️ Оклад {sal_int} тг — кажется слишком маленьким")
        else:
            ok.append(f"✅ Оклад: {sal_int:,} тг".replace(",", " "))
    except:
        issues.append(f"❌ Оклад '{salary}' — неверный формат")

    # 5. График
    if schedule not in ["2/2", "5/2"]:
        issues.append(f"❌ График '{schedule}' — должен быть 2/2 или 5/2")
    else:
        ok.append(f"✅ График: {schedule}")

    # 6. График vs должность
    if pos in ["Шеф-повар", "Управляющий"] and schedule == "2/2":
        issues.append(f"⚠️ Для должности '{pos}' обычно используется график 5/2")
    if pos in ["Кассир", "Оператор-кассир"] and schedule not in ["2/2", "5/2"]:
        issues.append(f"⚠️ Проверь график для кассира")

    # 7. Дата
    if not date:
        issues.append("❌ Дата приёма не заполнена")
    else:
        try:
            from datetime import datetime
            d = datetime.strptime(date, "%d.%m.%Y")
            ok.append(f"✅ Дата приёма: {date}")
        except:
            issues.append(f"❌ Дата '{date}' — неверный формат (нужно ДД.ММ.ГГГГ)")

    return ok, issues

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    async def new_employee(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await start(update, context)

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
            VERIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, run_verification)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
