"""
HH.ru Вакансии Монитор — для Railway
Алексей Кулик | @aleksey93_hh_bot
Версия 5.0 — OpenAI + детальный профиль + постоянная память
"""

import requests
import json
import time
import os
from datetime import datetime, timezone, timedelta

# ══════════════════════════════════════════════
TOKEN            = os.environ.get("BOT_TOKEN", "")
CHAT_ID          = os.environ.get("CHAT_ID", "")
OPENAI_API_KEY   = os.environ.get("OPENAI_API_KEY", "")
INTERVAL_MINUTES = int(os.environ.get("INTERVAL", "30"))
MEMORY_MSG_ID    = os.environ.get("MEMORY_MSG_ID", "")

KEYWORDS = [
    "операционный директор",
    "исполнительный директор",
    "COO",
    "директор по операциям",
    "директор розничной сети",
    "управляющий директор",
]

AREA         = 2
HOURS_FILTER = 48
SEEN_FILE    = "seen_vacancies.json"

# ══════════════════════════════════════════════
#  ДЕТАЛЬНЫЙ ПРОФИЛЬ КАНДИДАТА
# ══════════════════════════════════════════════
CANDIDATE_PROFILE = """
ФИО: Кулик Алексей Дмитриевич
Возраст: 32 года
Город: Санкт-Петербург
Телефон: +7 (911) 835-25-77
Email: kulik-alexey@mail.ru

ОПЫТ РАБОТЫ — 13 лет 10 месяцев

1. Silentium Company — Исполнительный директор (февраль 2022 — настоящее время, 4 года)
Группа компаний: розничная сеть ювелирных изделий, сеть ломбардов, производство.
Прямое подчинение: 45 человек (снабжение, бухгалтерия, IT, техотдел, склады).
Выручка группы: более 1 млрд руб./год. Полная ответственность за P&L и операционный бюджет.

Ключевые достижения:
— Разработал 3-летнюю стратегию развития сети — выручка группы выросла на 55% за 2 года
— Запустил флагманский объект площадью 2700 м² с международным туристическим трафиком — рост продаж на точке в 4 раза
— Оптимизировал логистику и складской учёт — снижение операционных издержек на 26% без потери качества
— Внедрил CRM-систему и обновил IT-инфраструктуру — время обработки заказов сократилось на 20%
— Выстроил систему KPI для всех подразделений — рост исполнительской дисциплины
— Провёл переговоры с арендодателями: дисконты, расторжение убыточных договоров, экономия 3+ млн руб./год
— Выстроил управленческую отчётность по 21 юрлицу в 7 налоговых режимах
— Закрыл 100% страховых случаев с полным получением выплат
— Успешно провёл переговоры с ключевыми поставщиками: отсрочки платежей, улучшение оборотного капитала

2. Silentium Company — Руководитель сети ломбардов (январь 2019 — настоящее время, 7 лет)
Управление сетью из 6 ломбардов и 4 скупок. Подчинение — 17 сотрудников.
Лицензируемый вид деятельности (ЦБ РФ).

Ключевые достижения:
— Открыл 3 новых ломбарда с нуля — полный цикл: помещение, регистрация, лицензирование, найм
— Внедрил систему мотивации оценщиков — объём выданных займов вырос на 75%
— Обеспечил полное соответствие ЦБ РФ, ГИИС ДМДК, РФМ — все проверки без штрафов
— Организовал реализацию невостребованного имущества через Avito и агрегаторы — оборот +45%
— Разработал регламенты оценки, хранения и страхования залогов

3. Silentium Company — Заместитель руководителя отдела безопасности (апрель 2016 — январь 2019)
Комплексная безопасность розничной сети: 30+ объектов.

Достижения:
— Внедрил единую систему видеонаблюдения и контроля доступа — потери от хищений снизились на 80%
— Провёл 20 служебных расследований; возбуждено 4 уголовных дела, возвращено имущества на 3+ млн руб.
— Обучил персонал противодействию мошенничеству — число инцидентов сократилось вдвое

4. ЗАО НПФ ТИРС — Инженер радиоэлектроники (июнь 2012 — апрель 2016)

ОБРАЗОВАНИЕ:
— СПбГПУ, 2015, Факультет экономики и менеджмента, Информационные системы в экономике и менеджменте
— Политехнический колледж, 2012, Программное обеспечение ВТ

КОМПЕТЕНЦИИ:
Управление: операционное управление холдингом, P&L, бюджетирование, стратегическое планирование,
антикризисное управление, масштабирование бизнеса, KPI-системы, управление персоналом 45+ чел.

Финансы и право: ЦБ РФ, ГИИС ДМДК, РФМ, 115-ФЗ, 7 налоговых режимов, комплаенс,
переговоры с ФНС и Росреестром, страхование объектов, коммерческая недвижимость.

Технологии: 1С:Предприятие, 1С Ломбард, CRM-системы, Avito, маркетплейсы, SEO,
видеонаблюдение, СКУД, IT-инфраструктура.

ЛИЧНЫЕ КАЧЕСТВА:
Системное мышление, умение выстраивать процессы с нуля, жёсткий контроль операционных показателей,
умение работать в режиме многозадачности, опыт взаимодействия с собственником бизнеса напрямую,
самостоятельность в принятии решений, лидерство.

Права: категории B, C. Личный автомобиль. Готов к редким командировкам.
"""

SYSTEM_PROMPT = """Ты помогаешь Алексею Кулику писать сопроводительные письма для откликов на вакансии.

Твоя задача — написать короткое, живое, деловое письмо от первого лица.

Правила:
1. Максимум 5-7 предложений — не больше
2. Начинай сразу с сути — без "Добрый день", без вступлений
3. Упомяни 2-3 конкретных достижения с цифрами которые релевантны именно этой вакансии
4. Пиши как живой человек — без канцелярита, без шаблонных фраз типа "рад предложить свою кандидатуру"
5. Не используй слова: "резюме прилагаю", "с уважением", "буду рад", "хотел бы"
6. Заканчивай конкретным предложением о встрече или звонке
7. Письмо должно звучать как написанное опытным руководителем — уверенно и по делу
8. Не упоминай что это написано ИИ
9. Адаптируй под специфику конкретной вакансии — если ломбарды, акцент на ломбарды; если ритейл — на ритейл
"""


# ══════════════════════════════════════════════
#  TELEGRAM HELPERS
# ══════════════════════════════════════════════
def tg(method, **kwargs):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    try:
        r = requests.post(url, json=kwargs, timeout=10)
        return r.json()
    except Exception as e:
        print(f"TG {method} error: {e}")
        return {}


# ══════════════════════════════════════════════
#  ПАМЯТЬ
# ══════════════════════════════════════════════
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))

    if MEMORY_MSG_ID:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getChat",
                params={"chat_id": CHAT_ID}, timeout=10
            )
            pinned = r.json().get("result", {}).get("pinned_message", {})
            if pinned and str(pinned.get("message_id")) == MEMORY_MSG_ID:
                text = pinned.get("text", "")
                if "MEMORY" in text:
                    ids = json.loads(text.replace("🗄 MEMORY\n", ""))
                    seen = set(ids)
                    with open(SEEN_FILE, "w") as f:
                        json.dump(list(seen), f)
                    print(f"Память восстановлена: {len(seen)} вакансий")
                    return seen
        except Exception as e:
            print(f"Ошибка восстановления памяти: {e}")
    return set()


def save_seen(seen):
    global MEMORY_MSG_ID
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

    seen_text = f"🗄 MEMORY\n{json.dumps(list(seen)[-1000:])}"
    if MEMORY_MSG_ID:
        tg("editMessageText",
           chat_id=CHAT_ID,
           message_id=int(MEMORY_MSG_ID),
           text=seen_text)
    else:
        r = tg("sendMessage",
               chat_id=CHAT_ID,
               text=seen_text,
               disable_notification=True)
        if r.get("ok"):
            mid = str(r["result"]["message_id"])
            MEMORY_MSG_ID = mid
            print(f"Создано хранилище памяти, ID сообщения: {mid}")
            print(f"Добавьте в Railway переменную MEMORY_MSG_ID = {mid}")
            tg("pinChatMessage",
               chat_id=CHAT_ID,
               message_id=int(mid),
               disable_notification=True)


# ══════════════════════════════════════════════
#  HH.RU
# ══════════════════════════════════════════════
def is_fresh(v):
    pub = v.get("published_at")
    if not pub:
        return True
    try:
        pt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - pt) <= timedelta(hours=HOURS_FILTER)
    except Exception:
        return True


def search_vacancies(keyword):
    try:
        r = requests.get(
            "https://api.hh.ru/vacancies",
            params={"text": keyword, "area": AREA, "per_page": 20,
                    "order_by": "publication_time", "search_field": "name"},
            headers={"User-Agent": "hh-monitor/5.0"},
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("items", [])
    except Exception as e:
        print(f"HH error: {e}")
    return []


def get_vacancy_details(vid):
    try:
        r = requests.get(
            f"https://api.hh.ru/vacancies/{vid}",
            headers={"User-Agent": "hh-monitor/5.0"},
            timeout=10
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"Vacancy detail error: {e}")
    return None


def clean_html(text):
    import re
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:3000]


# ══════════════════════════════════════════════
#  OPENAI — ГЕНЕРАЦИЯ ПИСЬМА
# ══════════════════════════════════════════════
def generate_cover_letter(title, company, description):
    if not OPENAI_API_KEY:
        return None

    user_prompt = f"""Напиши сопроводительное письмо для отклика на эту вакансию.

Вакансия: {title}
Компания: {company}
Описание вакансии:
{description}

Профиль кандидата:
{CANDIDATE_PROFILE}

Выбери 2-3 достижения которые максимально релевантны именно этой вакансии.
Письмо должно быть живым, деловым, уверенным — не шаблонным."""

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "max_tokens": 600,
                "temperature": 0.7,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
            },
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            print(f"OpenAI error: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"OpenAI exception: {e}")
    return None


# ══════════════════════════════════════════════
#  ОТПРАВКА ВАКАНСИИ
# ══════════════════════════════════════════════
def send_vacancy(v, keyword):
    title   = v.get("name", "—")
    company = v.get("employer", {}).get("name", "—")
    salary  = v.get("salary")
    url     = v.get("alternate_url", "")
    pub     = v.get("published_at", "")
    vid     = v.get("id")

    pub_str = ""
    if pub:
        try:
            t = datetime.fromisoformat(pub.replace("Z", "+00:00")) + timedelta(hours=3)
            pub_str = f"\n🕐 {t.strftime('%d.%m %H:%M')} МСК"
        except Exception:
            pass

    if salary:
        sf = salary.get("from")
        st = salary.get("to")
        cur = salary.get("currency", "RUB")
        if sf and st:
            sal = f"{sf:,}–{st:,} {cur}".replace(",", " ")
        elif sf:
            sal = f"от {sf:,} {cur}".replace(",", " ")
        elif st:
            sal = f"до {st:,} {cur}".replace(",", " ")
        else:
            sal = "не указана"
    else:
        sal = "не указана"

    # Карточка вакансии
    tg("sendMessage",
       chat_id=CHAT_ID,
       text=(f"🔔 <b>{title}</b>\n"
             f"🏢 {company}\n"
             f"💰 {sal}{pub_str}\n"
             f"🔍 <i>{keyword}</i>\n"
             f"🔗 <a href='{url}'>Открыть на hh.ru</a>"),
       parse_mode="HTML",
       disable_web_page_preview=False)

    # Сопроводительное письмо
    if OPENAI_API_KEY:
        details = get_vacancy_details(vid)
        if details:
            desc = clean_html(details.get("description", ""))
            letter = generate_cover_letter(title, company, desc)
            if letter:
                tg("sendMessage",
                   chat_id=CHAT_ID,
                   text=f"📝 <b>Сопроводительное письмо:</b>\n\n{letter}",
                   parse_mode="HTML")
                time.sleep(1)


# ══════════════════════════════════════════════
#  ОСНОВНОЙ ЦИКЛ
# ══════════════════════════════════════════════
def check_and_notify():
    seen = load_seen()
    new_count = old_count = 0

    for keyword in KEYWORDS:
        for v in search_vacancies(keyword):
            vid = str(v.get("id"))
            if vid in seen:
                continue
            if not is_fresh(v):
                seen.add(vid)
                old_count += 1
                continue
            seen.add(vid)
            send_vacancy(v, keyword)
            new_count += 1
            time.sleep(2)

    save_seen(seen)
    print(f"[{datetime.now().strftime('%H:%M %d.%m')}] "
          f"Новых: {new_count} | Отфильтровано: {old_count}")


def main():
    global CHAT_ID
    print("HH.ru Монитор v5.0 — OpenAI + постоянная память")

    if not CHAT_ID:
        r = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates", timeout=10)
        for upd in r.json().get("result", []):
            cid = upd.get("message", {}).get("chat", {}).get("id")
            if cid:
                CHAT_ID = str(cid)
                break
        if not CHAT_ID:
            print("Напишите /start боту и перезапустите")
            return

    letter_status = "✅ С письмами (OpenAI)" if OPENAI_API_KEY else "⚠️ Без писем — добавьте OPENAI_API_KEY"

    tg("sendMessage",
       chat_id=CHAT_ID,
       text=(f"✅ <b>Монитор v5.0 запущен!</b>\n\n"
             f"Запросы: {len(KEYWORDS)} шт.\n"
             f"📍 Санкт-Петербург\n"
             f"⏱ Каждые {INTERVAL_MINUTES} минут\n"
             f"📅 За последние {HOURS_FILTER} часов\n"
             f"🧠 Постоянная память\n"
             f"📝 {letter_status}"),
       parse_mode="HTML")

    check_and_notify()

    while True:
        time.sleep(INTERVAL_MINUTES * 60)
        check_and_notify()


if __name__ == "__main__":
    main()
