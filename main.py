"""
HH.ru Вакансии Монитор — для Railway
Алексей Кулик | @aleksey93_hh_bot
"""

import requests
import json
import time
import os
from datetime import datetime

# Настройки — берутся из переменных окружения Railway
TOKEN   = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
INTERVAL_MINUTES = int(os.environ.get("INTERVAL", "30"))

KEYWORDS = [
    "операционный директор",
    "исполнительный директор",
    "COO",
    "директор по операциям",
    "директор розничной сети",
    "управляющий директор",
]

AREA = 2  # Санкт-Петербург
SEEN_FILE = "seen_vacancies.json"


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def search_vacancies(keyword):
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": keyword,
        "area": AREA,
        "per_page": 20,
        "order_by": "publication_time",
        "search_field": "name",
    }
    headers = {"User-Agent": "hh-monitor-bot/1.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get("items", [])
    except Exception as e:
        print(f"Ошибка запроса: {e}")
    return []


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"Telegram: {r.status_code}")
    except Exception as e:
        print(f"Ошибка Telegram: {e}")


def get_chat_id():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    r = requests.get(url, timeout=10)
    data = r.json()
    if data.get("result"):
        for update in data["result"]:
            msg = update.get("message", {})
            chat = msg.get("chat", {})
            cid = chat.get("id")
            if cid:
                print(f"Chat ID найден: {cid}")
                return str(cid)
    return None


def format_vacancy(v, keyword):
    title   = v.get("name", "—")
    company = v.get("employer", {}).get("name", "—")
    salary  = v.get("salary")
    url     = v.get("alternate_url", "")

    if salary:
        s_from = salary.get("from")
        s_to   = salary.get("to")
        cur    = salary.get("currency", "RUB")
        if s_from and s_to:
            sal_str = f"{s_from:,}–{s_to:,} {cur}"
        elif s_from:
            sal_str = f"от {s_from:,} {cur}"
        elif s_to:
            sal_str = f"до {s_to:,} {cur}"
        else:
            sal_str = "не указана"
    else:
        sal_str = "не указана"

    return (
        f"🔔 <b>{title}</b>\n"
        f"🏢 {company}\n"
        f"💰 {sal_str}\n"
        f"🔍 <i>{keyword}</i>\n"
        f"🔗 <a href='{url}'>Открыть на hh.ru</a>"
    )


def check_and_notify():
    seen = load_seen()
    new_count = 0

    for keyword in KEYWORDS:
        vacancies = search_vacancies(keyword)
        for v in vacancies:
            vid = str(v.get("id"))
            if vid not in seen:
                seen.add(vid)
                text = format_vacancy(v, keyword)
                send_telegram(text)
                new_count += 1
                time.sleep(1)

    save_seen(seen)
    now = datetime.now().strftime("%H:%M %d.%m")
    print(f"[{now}] Новых вакансий: {new_count}")


def main():
    global CHAT_ID

    print("HH.ru Монитор запускается...")

    # Получить chat_id автоматически если не задан
    if not CHAT_ID:
        print("CHAT_ID не задан, ищем автоматически...")
        CHAT_ID = get_chat_id()
        if not CHAT_ID:
            print("Напишите /start боту @aleksey93_hh_bot и перезапустите")
            return

    # Стартовое сообщение
    send_telegram(
        "✅ <b>Монитор вакансий запущен!</b>\n\n"
        "Ищу по запросам:\n" +
        "\n".join([f"• {k}" for k in KEYWORDS]) +
        f"\n\n📍 Санкт-Петербург\n"
        f"⏱ Каждые {INTERVAL_MINUTES} минут"
    )

    # Первая проверка сразу
    check_and_notify()

    # Цикл
    while True:
        time.sleep(INTERVAL_MINUTES * 60)
        check_and_notify()


if __name__ == "__main__":
    main()
