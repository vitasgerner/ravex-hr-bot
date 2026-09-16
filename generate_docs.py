from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from datetime import datetime, timedelta
import os
import re

# Register fonts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
pdfmetrics.registerFont(TTFont('DejaVu', os.path.join(BASE_DIR, 'DejaVuSerif.ttf')))
pdfmetrics.registerFont(TTFont('DejaVuBold', os.path.join(BASE_DIR, 'DejaVuSerif-Bold.ttf')))

W, H = A4
MARGIN_LEFT = 3.0 * cm
MARGIN_RIGHT = 1.5 * cm
TEXT_WIDTH = W - MARGIN_LEFT - MARGIN_RIGHT
FONT = 'DejaVu'
FONT_BOLD = 'DejaVuBold'
FONT_SIZE = 10
LINE_HEIGHT = 14

COMPANY = {
    "name": "RAVEX FOOD GROUP",
    "bin": "260440030820",
    "address": "РК, Атырауская область, г. Атырау, мкр. Жерұйық, ул. Кенжебай Маденов, д. 1В, кв/офис 1",
    "address_full": "Республика Казахстан, Атырауская область, город Атырау, Микрорайон Жерұйық, улица Кенжебай Маденов, дом 1В, н.п. 1, почтовый индекс 060000",
    "director": "Гернер Виталий Иванович",
    "director_short": "Гернер В.И.",
}

def salary_to_words(amount):
    """Convert salary number to words in Russian"""
    words = {
        90000: "Девяносто тысяч",
        95000: "Девяносто пять тысяч",
        100000: "Сто тысяч",
        110000: "Сто десять тысяч",
        120000: "Сто двадцать тысяч",
        130000: "Сто тридцать тысяч",
        150000: "Сто пятьдесят тысяч",
    }
    try:
        n = int(str(amount).replace(" ", "").replace("000", "000"))
        return words.get(n, f"{amount}")
    except:
        return str(amount)

def get_schedule_details(position, schedule):
    """Get work schedule details based on position and schedule"""
    if schedule == "5/2" or position in ["Шеф-повар", "Управляющий", "Оператор-кассир"]:
        return {
            "type": "5/2",
            "time": "с 09:00 до 18:00",
            "breaks": "перерыв для отдыха и приёма пищи с 13:00 до 14:00",
            "breaks_note": "Перерыв не является рабочим временем."
        }
    else:
        return {
            "type": "2/2",
            "time": "с 11:00 до 00:00",
            "breaks": "два перерыва для отдыха и приёма пищи: с 15:00 до 16:00 и с 20:00 до 21:00",
            "breaks_note": "Перерывы не являются рабочим временем."
        }

def is_cashier(position):
    return position in ["Кассир", "Оператор-кассир"]

def parse_date(date_str):
    """Parse date string DD.MM.YYYY"""
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except:
        return datetime.now()

def add_year(date_str):
    """Add 1 year to date"""
    d = parse_date(date_str)
    try:
        return d.replace(year=d.year + 1).strftime("%d.%m.%Y")
    except:
        return (d + timedelta(days=365)).strftime("%d.%m.%Y")

def month_name(date_str):
    """Get date in format '14 сентября 2026 г.'"""
    months = {1:"января",2:"февраля",3:"марта",4:"апреля",5:"мая",6:"июня",
              7:"июля",8:"августа",9:"сентября",10:"октября",11:"ноября",12:"декабря"}
    d = parse_date(date_str)
    return f"{d.day} {months[d.month]} {d.year} г."

class PDFDoc:
    def __init__(self, filename):
        self.c = canvas.Canvas(filename, pagesize=A4)
        self.y = H - 2*cm
        self.c.setFont(FONT, FONT_SIZE)

    def save(self):
        self.c.save()

    def new_page(self):
        self.c.showPage()
        self.y = H - 2*cm
        self.c.setFont(FONT, FONT_SIZE)

    def check_page(self, lines=1):
        if self.y < 3*cm + lines * LINE_HEIGHT:
            self.new_page()

    def text(self, txt, bold=False, size=None, indent=0, align='left'):
        self.check_page()
        font = FONT_BOLD if bold else FONT
        sz = size or FONT_SIZE
        self.c.setFont(font, sz)
        x = MARGIN_LEFT + indent
        if align == 'center':
            self.c.drawCentredString(W/2, self.y, txt)
        elif align == 'right':
            self.c.drawRightString(W - MARGIN_RIGHT, self.y, txt)
        else:
            self.c.drawString(x, self.y, txt)
        self.y -= LINE_HEIGHT
        self.c.setFont(FONT, FONT_SIZE)

    def wrap_text(self, txt, bold=False, indent=0, size=None):
        """Draw wrapped text"""
        font = FONT_BOLD if bold else FONT
        sz = size or FONT_SIZE
        self.c.setFont(font, sz)
        max_width = TEXT_WIDTH - indent
        words = txt.split(' ')
        line = ''
        for word in words:
            test = line + ' ' + word if line else word
            if self.c.stringWidth(test, font, sz) <= max_width:
                line = test
            else:
                self.check_page()
                self.c.drawString(MARGIN_LEFT + indent, self.y, line)
                self.y -= LINE_HEIGHT
                line = word
        if line:
            self.check_page()
            self.c.drawString(MARGIN_LEFT + indent, self.y, line)
            self.y -= LINE_HEIGHT
        self.c.setFont(FONT, FONT_SIZE)

    def space(self, n=1):
        self.y -= LINE_HEIGHT * n

    def line(self):
        self.c.line(MARGIN_LEFT, self.y, W - MARGIN_RIGHT, self.y)
        self.y -= LINE_HEIGHT * 0.5

    def two_col(self, left, right, bold_left=False, bold_right=False):
        """Two column text"""
        self.check_page()
        mid = W / 2
        fl = FONT_BOLD if bold_left else FONT
        fr = FONT_BOLD if bold_right else FONT
        self.c.setFont(fl, FONT_SIZE)
        self.c.drawString(MARGIN_LEFT, self.y, left)
        self.c.setFont(fr, FONT_SIZE)
        self.c.drawString(mid, self.y, right)
        self.y -= LINE_HEIGHT
        self.c.setFont(FONT, FONT_SIZE)

def generate_td(data, output_path):
    """Generate Трудовой договор"""
    td_num = data['td_number']
    emp_name = data['employee']['full_name']
    emp_iin = data['employee']['iin']
    emp_id = data['employee']['id_number']
    emp_id_date = data['employee']['id_date']
    position = data['position']
    salary = str(data['salary']).replace(" ", "")
    salary_words = salary_to_words(int(salary))
    schedule = data['schedule']
    start_date = data['start_date']
    end_date = add_year(start_date)
    sched = get_schedule_details(position, schedule)
    cashier = is_cashier(position)

    doc = PDFDoc(output_path)

    # Header
    doc.text(f"Трудовой договор № {td_num}", bold=True, size=12, align='center')
    doc.space(0.3)
    doc.two_col(f"г. Атырау", f"{month_name(start_date)}")
    doc.space()

    # Intro
    intro = (f"Товарищество с ограниченной ответственностью «{COMPANY['name']}», "
             f"БИН {COMPANY['bin']}, в лице Директора {COMPANY['director']}, "
             f"действующего на основании Устава, именуемое в дальнейшем «Работодатель», "
             f"с одной стороны, и гражданин(ка) Республики Казахстан {emp_name}, "
             f"удостоверение личности № {emp_id}, выданное {emp_id_date} г. МВД РК, "
             f"ИИН {emp_iin}, именуемый(ая) в дальнейшем «Работник», с другой стороны, "
             f"заключили настоящий Трудовой Договор (далее — Договор) о нижеследующем:")
    doc.wrap_text(intro)
    doc.space()

    # Section 1
    doc.text("1. ПРЕДМЕТ ДОГОВОРА", bold=True, align='center')
    doc.wrap_text("1.1 Предметом Договора являются трудовые отношения между Работником и Работодателем.", indent=1*cm)
    doc.wrap_text("1.2 Работодатель обязуется предоставить Работнику работу, обеспечить условия труда, своевременно и в полном объёме выплачивать заработную плату, а Работник обязуется лично выполнять работу за вознаграждение и соблюдать трудовой распорядок.", indent=1*cm)
    doc.wrap_text("1.3 При осуществлении своих прав и исполнении обязанностей Работник должен действовать в интересах Работодателя добросовестно.", indent=1*cm)
    doc.wrap_text(f"1.4 Должность, на которую принимается Работник: {position}.", indent=1*cm)
    doc.wrap_text(f"1.5 Место выполнения работы: {COMPANY['address_full']}.", indent=1*cm)
    doc.space()

    # Section 2
    doc.text("2. СРОК ДЕЙСТВИЯ ДОГОВОРА", bold=True, align='center')
    doc.wrap_text(f"2.1 Настоящий договор заключён сроком на один год:", indent=1*cm)
    doc.wrap_text(f"- дата начала работы — {start_date} г.;", indent=1.5*cm)
    doc.wrap_text(f"- дата окончания работы — {end_date} г.", indent=1.5*cm)
    doc.wrap_text("2.2 Если срок договора истёк и ни одна из Сторон не потребовала его расторжения, Договор продлевается на неопределённый срок.", indent=1*cm)
    doc.wrap_text("2.3 В целях проверки соответствия квалификации Работника поручаемой ему работе устанавливается испытательный срок продолжительностью 2 (два) месяца. Испытательный срок начинается с начала действия Договора.", indent=1*cm)
    doc.space()

    # Section 3
    doc.text("3. ПРАВА И ОБЯЗАННОСТИ РАБОТНИКА", bold=True, align='center')
    doc.text("3.1 Работник имеет право на:", bold=True)
    rights = [
        "3.1.1 заключение, изменение, дополнение трудового договора;",
        "3.1.2 требование от Работодателя выполнения условий Договора;",
        "3.1.3 безопасность и охрану труда;",
        "3.1.4 своевременную и в полном объёме выплату заработной платы;",
        "3.1.5 отдых, в том числе оплачиваемый ежегодный трудовой отпуск;",
        "3.1.6 безвозмездный доступ к своим персональным данным;",
        "3.1.7 исключение и исправление неверных персональных данных;",
        "3.1.8 досрочное расторжение настоящего Договора согласно законодательству РК.",
    ]
    for r in rights:
        doc.wrap_text(r, indent=1*cm)

    doc.space(0.5)
    doc.text("3.2 Работник обязан:", bold=True)
    duties = [
        "3.2.1 добросовестно выполнять трудовые обязанности, обусловленные настоящим Договором;",
        "3.2.2 соблюдать трудовую дисциплину, установленные Работодателем правила внутреннего трудового распорядка;",
        "3.2.3 соблюдать требования по безопасности и охране труда, пожарной безопасности;",
        "3.2.4 бережно относиться к имуществу Работодателя;",
        "3.2.5 не распивать спиртные напитки в помещениях Работодателя;",
        "3.2.6 незамедлительно сообщать Работодателю о возникшей ситуации, представляющей угрозу жизни и здоровью людей;",
        "3.2.7 не допускать действий, способных причинить вред Работодателю;",
        "3.2.8 повышать профессиональный уровень, знать и выполнять требования внутренних актов Работодателя;",
        "3.2.9 не разглашать сведений, составляющих служебную, коммерческую и иную охраняемую законом тайну;",
        "3.2.10 письменно предупреждать Работодателя о досрочном расторжении Договора не менее чем за один месяц;",
        "3.2.11 возместить сумму аванса в случае, если аванс не отработан;",
        "3.2.12 сообщать Работодателю о возникшей ситуации, представляющей угрозу сохранности имущества;",
        "3.2.13 предоставлять Работодателю достоверные сведения о своих персональных данных;",
        "3.2.14 в случае изменения персональных данных в течение 10 календарных дней сообщить об этом Работодателю;",
        "3.2.15 возместить сумму аванса в случае досрочного расторжения Договора по инициативе Работника.",
    ]

    if cashier:
        cashier_duties = [
            "3.2.16 нести персональную материальную ответственность за сохранность денежных средств в кассе;",
            "3.2.17 вести кассовые операции строго в соответствии с установленными правилами, фиксировать все операции в системе учёта;",
            "3.2.18 производить выдачу денежных средств на основании устного или письменного распоряжения Директора или уполномоченного лица, с обязательной фиксацией каждой операции;",
            "3.2.19 при обнаружении недостачи или излишка денежных средств немедленно сообщить Работодателю и составить акт;",
            "3.2.20 нести полную материальную ответственность за недостачу денежных средств, выявленную по результатам инвентаризации кассы.",
        ]
        duties.extend(cashier_duties)

    for d in duties:
        doc.wrap_text(d, indent=1*cm)
    doc.space()

    # Section 4
    doc.text("4. ПРАВА И ОБЯЗАННОСТИ РАБОТОДАТЕЛЯ", bold=True, align='center')
    doc.text("4.1 Работодатель имеет право:", bold=True)
    employer_rights = [
        "4.1.1 на свободу выбора при приёме на работу;",
        "4.1.2 изменять, дополнять, расторгать Договор в установленном порядке;",
        "4.1.3 издавать в пределах своих полномочий акты Работодателя;",
        "4.1.4 требовать от Работника выполнения условий Договора;",
        "4.1.5 поощрять Работника, налагать дисциплинарные взыскания;",
        "4.1.6 требовать возврата аванса за неотработанное время;",
        "4.1.7 оплачивать профессиональное обучение Работника;",
        "4.1.8 пересматривать должностные обязанности Работника;",
        "4.1.9 отстранить Работника от выполнения должностных обязанностей;",
        "4.1.10 с письменного согласия Работника привлекать его к работе в выходные дни;",
        "4.1.11 на досрочное расторжение Договора и увольнение Работника;",
        "4.1.12 на возмещение вреда, нанесённого Работником;",
        "4.1.13 обращаться в суд в целях защиты своих прав;",
        "4.1.14 на отказ от продления Договора по истечении срока;",
        "4.1.15 осуществлять сбор и обработку персональных данных;",
        "4.1.16 извещать Работника посредством мессенджеров согласно ТК РК.",
    ]
    for r in employer_rights:
        doc.wrap_text(r, indent=1*cm)

    doc.space(0.5)
    doc.text("4.2 Работодатель обязан:", bold=True)
    employer_duties = [
        "4.2.1 предоставлять Работнику обусловленную Договором работу;",
        "4.2.2 создать Работнику условия, необходимые для нормальной работы;",
        "4.2.3 осуществлять внутренний контроль по безопасности и охране труда;",
        "4.2.4 соблюдать требования по защите персональных данных Работника;",
        "4.2.5 своевременно и в полном размере выплачивать Работнику заработную плату;",
        "4.2.6 знакомить Работника с актами Работодателя;",
        "4.2.7 обеспечить Работника необходимыми инструментами;",
        "4.2.8 предоставлять Работнику ежегодный оплачиваемый трудовой отпуск;",
        "4.2.9 удерживать выданную сумму аванса при досрочном расторжении;",
        "4.2.10 обеспечивать защиту персональных данных Работника.",
    ]
    for d in employer_duties:
        doc.wrap_text(d, indent=1*cm)
    doc.space()

    # Section 5
    doc.text("5. ОПЛАТА ТРУДА", bold=True, align='center')
    doc.wrap_text("5.1 Размер заработной платы устанавливается Работодателем в соответствии со штатным расписанием.", indent=1*cm)
    doc.wrap_text(f"5.2 Заработная плата выплачивается не реже одного раза в месяц, не позднее десятого числа следующего месяца в размере {int(salary):,} ({salary_words}) тенге.".replace(',', ' '), indent=1*cm)
    doc.wrap_text("5.3 По желанию Работника 20 числа каждого месяца может выплачиваться аванс в размере до 50% от базовой заработной платы.", indent=1*cm)
    doc.wrap_text("5.4 По результатам работы Работнику может быть выплачено вознаграждение в соответствии с решением Работодателя. Выплата премии является правом, а не обязанностью Работодателя.", indent=1*cm)
    doc.wrap_text("5.5 Удержания из заработной платы могут производиться на основании акта Работодателя при наличии письменного согласия Работника.", indent=1*cm)
    doc.space()

    # Section 6
    doc.text("6. РЕЖИМ РАБОЧЕГО ВРЕМЕНИ", bold=True, align='center')
    doc.text("6.1 Работодатель устанавливает:", bold=True)
    doc.wrap_text(f"- сменный график работы {sched['type']};", indent=1.5*cm)
    doc.wrap_text(f"- продолжительность рабочей смены: {sched['time']};", indent=1.5*cm)
    doc.wrap_text(f"- {sched['breaks']}.", indent=1.5*cm)
    doc.wrap_text(sched['breaks_note'], indent=1*cm)
    doc.space()

    # Section 7
    doc.text("7. ЕЖЕГОДНЫЙ ТРУДОВОЙ ОТПУСК", bold=True, align='center')
    doc.wrap_text("7.1 Работодатель ежегодно предоставляет Работнику оплачиваемый трудовой отпуск продолжительностью 24 (двадцать четыре) календарных дня.", indent=1*cm)
    doc.wrap_text("7.2 Ежегодный трудовой отпуск может быть перенесён или продлён при временной нетрудоспособности Работника.", indent=1*cm)
    doc.wrap_text("7.3 При прекращении Договора Работнику производится компенсационная выплата за неиспользованные дни отпуска.", indent=1*cm)
    doc.wrap_text("7.4 По желанию Работника с согласия Работодателя может быть предоставлен отпуск без сохранения заработной платы.", indent=1*cm)
    doc.space()

    # Section 8
    doc.text("8. ПООЩРЕНИЕ И ДИСЦИПЛИНАРНЫЕ ВЗЫСКАНИЯ", bold=True, align='center')
    doc.wrap_text("8.1 Работодатель вправе применять различные виды поощрений Работника за успехи в труде.", indent=1*cm)
    doc.wrap_text("8.2 За совершение дисциплинарного проступка Работодатель вправе применять дисциплинарные взыскания, установленные ТК РК.", indent=1*cm)
    doc.space()

    # Section 9
    doc.text("9. ОТВЕТСТВЕННОСТЬ СТОРОН", bold=True, align='center')
    doc.wrap_text("9.1 Работник несёт материальную ответственность перед Работодателем за ущерб, причинённый утратой или повреждением имущества.", indent=1*cm)

    liability_items = "1) необеспечения сохранности имущества; 2) получения имущества под отчёт; 3) причинения ущерба в состоянии опьянения; 4) недостачи или умышленного уничтожения имущества; 5) причинения ущерба незаконными действиями; 6) за неотработанный аванс; 7) за ненадлежащее исполнение должностных обязанностей"

    if cashier:
        liability_items += "; 8) за недостачу денежных средств в кассе, выявленную при инвентаризации; 9) за выдачу денежных средств без распоряжения Директора или уполномоченного лица; 10) за неправильный расчёт заработной платы сотрудников и выплат курьерам, повлёкший финансовый ущерб Работодателю"

    doc.wrap_text(f"9.2 Материальная ответственность в полном объёме возлагается на Работника в случаях: {liability_items}.", indent=1*cm)
    doc.wrap_text("9.3 За нарушение условий настоящего Договора Стороны несут ответственность, предусмотренную трудовым законодательством РК.", indent=1*cm)
    doc.space()

    # Section 10
    doc.text("10. ИЗМЕНЕНИЕ И РАСТОРЖЕНИЕ ДОГОВОРА", bold=True, align='center')
    doc.wrap_text("10.1 В период действия настоящего Договора Стороны вправе вносить изменения и дополнения в письменной форме.", indent=1*cm)
    doc.wrap_text("10.2 Внесение изменений осуществляется в течение пяти рабочих дней со дня подачи предложения.", indent=1*cm)
    doc.wrap_text("10.3 Договор может быть расторгнут по соглашению Сторон или инициативе одной из Сторон.", indent=1*cm)
    doc.wrap_text("10.4 Действие Договора может быть прекращено в соответствии с Трудовым кодексом РК.", indent=1*cm)
    doc.wrap_text("10.5 При расторжении Договора выплата причитающихся сумм производится не позднее трёх рабочих дней после его расторжения в кассе предприятия без дополнительного уведомления.", indent=1*cm)
    doc.space()

    # Section 11
    doc.text("11. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ", bold=True, align='center')
    doc.wrap_text("11.1 Все отношения, не урегулированные Договором, регулируются законодательством Республики Казахстан.", indent=1*cm)
    doc.wrap_text("11.2 Договор составлен в двух экземплярах на русском языке, имеющих одинаковую юридическую силу.", indent=1*cm)
    doc.wrap_text("11.3 Договор о полной индивидуальной материальной ответственности является неотъемлемой частью настоящего Договора.", indent=1*cm)
    doc.space()

    # Section 12 - new page
    doc.new_page()
    doc.text("12. АДРЕСА, РЕКВИЗИТЫ И ПОДПИСИ СТОРОН", bold=True, align='center')
    doc.space()

    # Two columns - fixed layout
    mid = W / 2
    
    # Работодатель / Работник headers
    doc.check_page()
    doc.c.setFont(FONT_BOLD, FONT_SIZE)
    doc.c.drawString(MARGIN_LEFT, doc.y, "Работодатель:")
    doc.c.drawString(mid, doc.y, "Работник:")
    doc.y -= LINE_HEIGHT
    
    # Company name / Employee name
    doc.c.setFont(FONT, FONT_SIZE)
    doc.c.drawString(MARGIN_LEFT, doc.y, f"ТОО «{COMPANY['name']}»")
    doc.c.drawString(mid, doc.y, emp_name)
    doc.y -= LINE_HEIGHT
    
    # Address left, address right
    doc.c.drawString(MARGIN_LEFT, doc.y, "Юр. адрес: РК, г. Атырау,")
    doc.c.drawString(mid, doc.y, "Адрес проживания: ____________________")
    doc.y -= LINE_HEIGHT
    doc.c.drawString(MARGIN_LEFT, doc.y, "Жерұйық, д.1В, кв/офис 1")
    doc.c.drawString(mid, doc.y, "Адрес прописки: ______________________")
    doc.y -= LINE_HEIGHT
    doc.c.drawString(MARGIN_LEFT, doc.y, f"БИН {COMPANY['bin']}")
    doc.y -= LINE_HEIGHT
    doc.space()
    
    # Director / ID
    doc.c.setFont(FONT_BOLD, FONT_SIZE)
    doc.c.drawString(MARGIN_LEFT, doc.y, "Директор")
    doc.c.setFont(FONT, FONT_SIZE)
    doc.c.drawString(mid, doc.y, f"Уд. личности № {emp_id}, выд. {emp_id_date} г. МВД РК")
    doc.y -= LINE_HEIGHT
    doc.c.drawString(mid, doc.y, f"ИИН {emp_iin}")
    doc.y -= LINE_HEIGHT
    doc.space()
    doc.c.drawString(MARGIN_LEFT, doc.y, f"_____________ / {COMPANY['director_short']}/")
    doc.c.drawString(mid, doc.y, emp_name)
    doc.y -= LINE_HEIGHT
    doc.c.drawString(MARGIN_LEFT, doc.y, "МП")
    doc.c.drawString(mid, doc.y, "_____________________________")
    doc.y -= LINE_HEIGHT
    doc.c.setFont(FONT, FONT_SIZE)
    doc.space(2)

    # Personal data consent
    doc.text("С Положением «О персональных данных и их защите» ознакомлен:", bold=True, align='center')
    doc.wrap_text("Даю Работодателю согласие на получение, обработку, защиту, накопление, хранение, уточнение, использование, распространение, обезличивание, блокирование, уничтожение персональных данных, определённых Законом «О персональных данных и их защите» от 21 мая 2013 г. № 94-V Закона РК. Даю своё согласие на фото/видео регистрацию на территории предприятия.")
    doc.space()
    doc.text("_____________ / _______________________________")
    doc.text("   подпись              Ф.И.О.")
    doc.space()
    doc.wrap_text(f"Трудовой договор мною прочитан, экземпляр трудового договора получил(-а) ________ / ___________________")
    doc.two_col("   подпись              ФИО", "дата ___________________")
    doc.space(0.5)
    doc.text("Изданы приказы Работодателя:", bold=True)
    doc.text("— о приёме работника на работу № ____________ от _______________________________________")
    doc.space(0.5)
    doc.text("— о расторжении или прекращении Договора № ____________ от ___________________________.")
    doc.space(0.5)
    doc.text("Основание расторжения Договора: _________________________ Трудового Кодекса РК")

    # Appendix - new page
    doc.new_page()
    doc.text(f"Приложение № 1", bold=True, align='right')
    doc.text(f"к Трудовому договору № {td_num}", align='right')
    doc.text(f"{month_name(start_date)}", align='right')
    doc.space()
    doc.text("ДОГОВОР", bold=True, size=12, align='center')
    doc.text("О ПОЛНОЙ ИНДИВИДУАЛЬНОЙ МАТЕРИАЛЬНОЙ ОТВЕТСТВЕННОСТИ", bold=True, align='center')
    doc.space()
    doc.two_col("г. Атырау", month_name(start_date))
    doc.space()

    mat_intro = (f"Товарищество с ограниченной ответственностью «{COMPANY['name']}», "
                f"БИН {COMPANY['bin']}, в лице Директора {COMPANY['director']}, "
                f"действующего на основании Устава, именуемое в дальнейшем «Работодатель», "
                f"с одной стороны, и гражданин(ка) Республики Казахстан {emp_name}, "
                f"именуемый(ая) в дальнейшем «Работник», с другой стороны, "
                f"в целях обеспечения сохранности материальных ценностей, заключили настоящий Договор о нижеследующем.")
    doc.wrap_text(mat_intro)
    doc.space()

    doc.wrap_text(f"1. Работник, занимающий должность {position} на основании Трудового договора № {td_num} от {month_name(start_date)}, принимает на себя полную материальную ответственность за: недостачу ценностей, подтверждённую инвентаризацией; утрату ценностей вследствие халатности; ущерб, причинённый умышленно или в результате неаккуратного отношения к обязанностям.", indent=1*cm)
    doc.wrap_text("2. Работник обязуется: бережно относиться к ценностям; своевременно сообщать о всех обстоятельствах, угрожающих сохранности ценностей; участвовать в проведении инвентаризации.", indent=1*cm)
    doc.wrap_text("3. Работодатель обязуется: создавать условия, необходимые для обеспечения сохранности ценностей; ознакомить Работника с действующими правилами работы.", indent=1*cm)
    doc.wrap_text("4. В случае необеспечения по вине Работника сохранности ценностей Работник обязан выплатить Работодателю размер причинённого ущерба.", indent=1*cm)
    doc.wrap_text("5. Настоящий Договор составлен в двух экземплярах, имеющих одинаковую юридическую силу.", indent=1*cm)
    doc.space(2)

    doc.two_col("Работодатель:", "Работник:", bold_left=True, bold_right=True)
    doc.two_col(f"ТОО «{COMPANY['name']}»", emp_name)
    doc.two_col(f"БИН {COMPANY['bin']}", f"ИИН {emp_iin}")
    doc.space()
    doc.two_col(f"_____________ / {COMPANY['director_short']}/", "_____________________________")
    doc.two_col("МП", f"{emp_name}")

    doc.save()

def generate_prikaz(data, output_path):
    """Generate Приказ о приёме"""
    td_num = data['td_number']
    emp_name = data['employee']['full_name']
    position = data['position']
    start_date = data['start_date']

    # Order number
    order_num = td_num.replace("/26", "/26-Л/С") if "/26" in td_num else f"{td_num}-Л/С"

    # Employee initials: Акимова Сабрина Константиновна -> Акимова С.К.
    parts = emp_name.split()
    if len(parts) >= 3:
        emp_initials = f"{parts[0]} {parts[1][0]}.{parts[2][0]}."
    elif len(parts) == 2:
        emp_initials = f"{parts[0]} {parts[1][0]}."
    else:
        emp_initials = emp_name

    doc = PDFDoc(output_path)

    doc.text(f"Товарищество с ограниченной ответственностью «{COMPANY['name']}»", bold=True, align='center')
    doc.text(f"БИН {COMPANY['bin']}", align='center')
    doc.space()
    doc.text(f"ПРИКАЗ № {order_num}", bold=True, size=13, align='center')
    doc.text(f"от {month_name(start_date)}", align='center')
    doc.text("«О приёме на работу»", bold=True, align='center')
    doc.space(2)

    # Table with two columns: 35% / 65%
    col1 = TEXT_WIDTH * 0.35
    col2 = TEXT_WIDTH * 0.65
    x1 = MARGIN_LEFT
    x2 = MARGIN_LEFT + col1

    def prikaz_row(label, value, gap=LINE_HEIGHT + 2):
        doc.check_page()
        doc.c.setFont(FONT, FONT_SIZE)
        doc.c.drawString(x1, doc.y, label)
        # Wrap value in right column
        words = value.split()
        line = ''
        first = True
        y_tmp = doc.y
        for word in words:
            test = line + ' ' + word if line else word
            if doc.c.stringWidth(test, FONT, FONT_SIZE) <= col2 - 5:
                line = test
            else:
                doc.c.drawString(x2, y_tmp, line)
                y_tmp -= LINE_HEIGHT
                line = word
        if line:
            doc.c.drawString(x2, y_tmp, line)
            y_tmp -= LINE_HEIGHT
        doc.y = min(doc.y - gap, y_tmp)

    prikaz_row("Принять на работу с:", month_name(start_date))
    prikaz_row("Ф.И.О:", emp_name)
    prikaz_row("Должность (профессия):", position)
    prikaz_row("Испытательный срок:", "2 (два) месяца")
    prikaz_row("Основание:", f"Заявление работника, Трудовой договор № {td_num} от {start_date} г.")
    doc.space(3)

    doc.text("Директор", bold=True)
    doc.space()
    doc.text(f"_________________ / {COMPANY['director_short']}/")
    doc.space(2)

    doc.text("С Приказом ознакомлен:", bold=True)
    doc.space()
    doc.two_col(f"_________________ / {emp_initials}/", f"«____» ______________ {start_date.split('.')[-1]} г.")

    doc.save()

def generate_zayavlenie(data, output_path):
    """Generate Заявление о приёме"""
    emp_name = data['employee']['full_name']
    emp_iin = data['employee']['iin']
    emp_id = data['employee']['id_number']
    position = data['position']
    start_date = data['start_date']

    doc = PDFDoc(output_path)
    doc.y = H - 3*cm

    # Right side header
    for line in [
        f"Директору ТОО «{COMPANY['name']}»",
        f"{COMPANY['director_short']}",
        f"от {emp_name}",
        f"ИИН: {emp_iin}",
        f"Уд. личности № {emp_id}",
        "Место проживания: _______________________",
        "Место прописки: _________________________",
        "Тел.: ___________________________________",
    ]:
        doc.text(line, align='right')

    doc.space(2)
    doc.text("ЗАЯВЛЕНИЕ", bold=True, size=13, align='center')
    doc.space(2)

    doc.wrap_text(f"Прошу принять меня на работу по трудовому договору в качестве {position} с {month_name(start_date)}.", indent=1*cm)
    doc.space(3)

    doc.text(f"_________________ /                           /          «____» ______________ {start_date.split('.')[-1]} г.")

    doc.save()

def generate_ipn(data, output_path):
    """Generate Заявление ИПН"""
    emp_name = data['employee']['full_name']
    emp_iin = data['employee']['iin']
    start_date = data['start_date']
    date_text = month_name(start_date)

    doc = PDFDoc(output_path)
    doc.y = H - 3*cm

    for line in [
        f"ТОО «{COMPANY['name']}»,",
        f"Директору {COMPANY['director_short']}",
        f"от {emp_name}",
        f"ИИН: {emp_iin}",
    ]:
        doc.text(line, align='right')

    doc.space(2)
    doc.text("З А Я В Л Е Н И Е", bold=True, size=12, align='center')
    doc.space(2)

    doc.wrap_text(
        f"В соответствии со статьёй 403 Налогового кодекса Республики Казахстан от 18 июля 2025 года № 214-VIII "
        f"в целях уменьшения налогооблагаемого дохода при исчислении индивидуального подоходного налога прошу "
        f"производить расчёт с применением базового налогового вычета в размере 30-кратного месячного расчётного "
        f"показателя к моему доходу за каждый календарный месяц с «{start_date.split('.')[0]}» "
        f"{date_text.split()[1]} {start_date.split('.')[-1]} года.",
        indent=1*cm
    )
    doc.space()
    doc.wrap_text(f"Указанный налоговый вычет по моим доходам применяется только в ТОО «{COMPANY['name']}».", indent=1*cm)
    doc.space()
    doc.wrap_text("В случае изменения обстоятельств, дающих право на использование данного налогового вычета, обязуюсь немедленно сообщить об этом. Я несу полную ответственность за предоставленную информацию.", indent=1*cm)
    doc.space(3)

    doc.two_col(f"«{start_date.split('.')[0]}» {date_text.split()[1]} {start_date.split('.')[-1]} г.",
                f"_________________ /                           /")

    doc.save()

def generate_all_docs(data, output_dir="/tmp"):
    """Generate all 4 documents and return file paths"""
    td_num_clean = data['td_number'].replace("/", "-")
    emp_last = data['employee']['full_name'].split()[0]

    paths = {
        'td': f"{output_dir}/ТД_{td_num_clean}_{emp_last}.pdf",
        'prikaz': f"{output_dir}/Приказ_{td_num_clean}_{emp_last}.pdf",
        'zayavlenie': f"{output_dir}/Заявление_{td_num_clean}_{emp_last}.pdf",
        'ipn': f"{output_dir}/ИПН_{td_num_clean}_{emp_last}.pdf",
    }

    generate_td(data, paths['td'])
    generate_prikaz(data, paths['prikaz'])
    generate_zayavlenie(data, paths['zayavlenie'])
    generate_ipn(data, paths['ipn'])

    return paths

if __name__ == "__main__":
    # Test
    test_data = {
        "td_number": "09/26",
        "employee": {
            "full_name": "Акимова Сабрина Константиновна",
            "iin": "060416650533",
            "id_number": "052655972",
            "id_date": "27.04.2022",
        },
        "position": "Сушист",
        "salary": "90000",
        "schedule": "2/2",
        "start_date": "14.09.2026",
    }
    paths = generate_all_docs(test_data, "/home/claude")
    print("Generated:", paths)
