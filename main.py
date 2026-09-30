"""
HH.ru Вакансии Монитор — для Railway
Алексей Кулик | @aleksey93_hh_bot
Версия 6.0 — браузерные заголовки для обхода блокировки hh.ru
"""

import requests
import json
import time
import os
from datetime import datetime, timezone, timedelta

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

# Заголовки имитирующие реальный браузер
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://hh.ru/",
    "Origin": "https://hh.ru",
    "HH-User-Agent": "api-test-agent",
}

CANDIDATE_PROFILE = """
ФИО: Кулик Алексей Дмитриевич
Возраст: 32 года, Санкт-Петербург
Телефон: +7 (911) 835-25-77 | Email: kulik-alexey@mail.ru

ОПЫТ — 13 лет 10 месяцев

Silentium Company — Исполнительный директор (фев.2022 — н.в.)
Холдинг: ювелирный ритейл, ломбарды, производство. Выручка 1+ млрд руб./год. 45 чел. в подчинении. Полный P&L.
• Стратегия развития сети → выручка +55% за 2 года
• Флагманский объект 2700 м² с турпотоком → продажи ×4
• Оптимизация логистики → издержки −26%
• CRM + IT-инфраструктура → обработка заказов +20%
• KPI для всех подразделений, отчётность по 21 юрлицу / 7 налоговых режимов
• Переговоры с арендодателями → экономия 3+ млн руб./год
• Переговоры с поставщиками → отсрочки платежей

Silentium Company — Руководитель сети ломбардов (янв.2019 — н.в.)
6 ломбардов, 4 скупки, 17 сотрудников. Лицензия ЦБ РФ.
• Открыл 3 ломбарда с нуля (помещение → лицензия → найм)
• Мотивация оценщиков → займы +75%
• ЦБ РФ, ГИИС ДМДК, РФМ — все проверки без штрафов
• Онлайн-реализация залогов (Avito) → оборот +45%

Silentium Company — Зам. руководителя отдела безопасности (апр.2016 — янв.2019)
30+ объектов (магазины, склады, производство)
• Видеонаблюдение + СКУД → хищения −80% за год
• 20 расследований, 4 уголовных дела, возврат 3+ млн руб.

КОМПЕТЕНЦИИ: операционное управление, P&L, бюджетирование, стратегия,
антикризис, KPI, управление персоналом, ЦБ РФ, 115-ФЗ, комплаенс,
1С, CRM, переговоры, коммерческая недвижимость, масштабирование сетей
"""

SYSTEM_PROMPT = """Ты помогаешь Алексею Кулику писать сопроводительные письма.
Правила:
- 5-6 предложений максимум
- Начинай сразу с сути, без "Добрый день"
- 2-3 конкретных достижения с цифрами релевантных вакансии
- Живой деловой язык, без канцелярита
- Без "рад предложить", "резюме прилагаю", "с уважением"
- Заканчивай предложением о встрече или звонке
- Уверенно, как пишет опытный руководитель
- Адаптируй под специфику вакансии"""


def tg(method, **kwargs):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/{method}",
            json=kwargs, timeout=10)
        return r.json()
    except Exception as e:
        print(f"TG {method} error: {e}")
        return {}


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    if MEMORY_MSG_ID:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getChat",
                params={"chat_id": CHAT_ID}, timeout=10)
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
            print(f"Ошибка памяти: {e}")
    return set()


def save_seen(seen):
    global MEMORY_MSG_ID
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)
    seen_text = f"🗄 MEMORY\n{json.dumps(list(seen)[-1000:])}"
    if MEMORY_MSG_ID:
        tg("editMessageText", chat_id=CHAT_ID,
           message_id=int(MEMORY_MSG_ID), text=seen_text)
    else:
        r = tg("sendMessage", chat_id=CHAT_ID,
                text=seen_text, disable_notification=True)
        if r.get("ok"):
            mid = str(r["result"]["message_id"])
            MEMORY_MSG_ID = mid
            print(f"Создано хранилище памяти, ID: {mid}")
            print(f"Добавьте в Railway: MEMORY_MSG_ID = {mid}")
            tg("pinChatMessage", chat_id=CHAT_ID,
               message_id=int(mid), disable_notification=True)


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
    """Поиск с браузерными заголовками"""
    try:
        session = requests.Session()
        session.headers.update(BROWSER_HEADERS)

        # Сначала заходим на главную чтобы получить куки
        session.get("https://hh.ru/", timeout=10)
        time.sleep(1)

        r = session.get(
            "https://api.hh.ru/vacancies",
            params={
                "text": keyword,
                "area": AREA,
                "per_page": 20,
                "order_by": "publication_time",
                "search_field": "name",
            },
            timeout=15
        )
        print(f"HH статус [{keyword}]: {r.status_code}")
        if r.status_code == 200:
            items = r.json().get("items", [])
            print(f"  Найдено: {len(items)}")
            return items
        else:
            print(f"  Ошибка: {r.text[:100]}")
    except Exception as e:
        print(f"HH error [{keyword}]: {e}")
    return []


def get_vacancy_details(vid):
    try:
        session = requests.Session()
        session.headers.update(BROWSER_HEADERS)
        r = session.get(f"https://api.hh.ru/vacancies/{vid}", timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"Detail error: {e}")
    return None


def clean_html(text):
    import re
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:3000]


def generate_cover_letter(title, company, description):
    if not OPENAI_API_KEY:
        return None
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
                    {"role": "user", "content":
                        f"Вакансия: {title}\nКомпания: {company}\n"
                        f"Описание: {description}\n\nПрофиль:\n{CANDIDATE_PROFILE}"},
                ],
            },
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        print(f"OpenAI error: {r.status_code}")
    except Exception as e:
        print(f"OpenAI exception: {e}")
    return None


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
        sf, st = salary.get("from"), salary.get("to")
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

    tg("sendMessage", chat_id=CHAT_ID,
       text=(f"🔔 <b>{title}</b>\n"
             f"🏢 {company}\n"
             f"💰 {sal}{pub_str}\n"
             f"🔍 <i>{keyword}</i>\n"
             f"🔗 <a href='{url}'>Открыть на hh.ru</a>"),
       parse_mode="HTML", disable_web_page_preview=False)

    if OPENAI_API_KEY:
        details = get_vacancy_details(vid)
        if details:
            desc = clean_html(details.get("description", ""))
            letter = generate_cover_letter(title, company, desc)
            if letter:
                tg("sendMessage", chat_id=CHAT_ID,
                   text=f"📝 <b>Сопроводительное письмо:</b>\n\n{letter}",
                   parse_mode="HTML")
                time.sleep(1)


def check_and_notify():
    seen = load_seen()
    new_count = old_count = blocked = 0

    for keyword in KEYWORDS:
        vacancies = search_vacancies(keyword)
        if not vacancies:
            blocked += 1
        for v in vacancies:
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
    now = datetime.now().strftime("%H:%M %d.%m")
    print(f"[{now}] Новых: {new_count} | Старых: {old_count} | Блок: {blocked}/{len(KEYWORDS)}")

    if blocked == len(KEYWORDS):
        tg("sendMessage", chat_id=CHAT_ID,
           text="⚠️ hh.ru блокирует запросы с этого сервера. Нужен российский хостинг.")


def main():
    global CHAT_ID
    print("HH.ru Монитор v6.0 — браузерные заголовки")

    if not CHAT_ID:
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", timeout=10)
        for upd in r.json().get("result", []):
            cid = upd.get("message", {}).get("chat", {}).get("id")
            if cid:
                CHAT_ID = str(cid)
                break

    tg("sendMessage", chat_id=CHAT_ID,
       text=(f"✅ <b>Монитор v6.0 запущен!</b>\n\n"
             f"📍 Санкт-Петербург · {len(KEYWORDS)} запросов\n"
             f"⏱ Каждые {INTERVAL_MINUTES} минут\n"
             f"📅 За последние {HOURS_FILTER} часов\n"
             f"🧠 Постоянная память\n"
             f"📝 {'✅ OpenAI' if OPENAI_API_KEY else '⚠️ Без писем'}\n"
             f"🌐 Браузерные заголовки v6"),
       parse_mode="HTML")

    check_and_notify()

    while True:
        time.sleep(INTERVAL_MINUTES * 60)
        check_and_notify()


if __name__ == "__main__":
    main()
