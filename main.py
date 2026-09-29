"""
HH.ru Вакансии Монитор — для Railway
Алексей Кулик | @aleksey93_hh_bot
Версия 4.0 — постоянная память через Telegram (не слетает при перезапуске)
"""

import requests
import json
import time
import os
from datetime import datetime, timezone, timedelta

# ══════════════════════════════════════════════
TOKEN            = os.environ.get("BOT_TOKEN", "")
CHAT_ID          = os.environ.get("CHAT_ID", "")
CLAUDE_API_KEY   = os.environ.get("CLAUDE_API_KEY", "")
INTERVAL_MINUTES = int(os.environ.get("INTERVAL", "30"))
# ID сообщения где хранится список виденных вакансий
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
HOURS_FILTER = 48  # увеличили до 48 часов для надёжности
SEEN_FILE    = "seen_vacancies.json"

CANDIDATE_PROFILE = """
Имя: Алексей Кулик
Роль: Исполнительный директор / COO, Санкт-Петербург
Опыт: 13 лет операционного управления
Выручка: более 1 млрд руб./год
Команда: 45 человек в прямом подчинении
Достижения:
- Рост выручки группы +55% за 2 года
- Снижение операционных издержек −26%
- Рост займов ломбардной сети +75%
- Открыл 10+ объектов с нуля
- Снижение потерь от хищений −80%
- Внедрил CRM, KPI-системы, отчётность по 21 юрлицу
- Опыт: ЦБ РФ, ГИИС ДМДК, РФМ, 7 налоговых режимов
Контакт: +7 (911) 835-25-77 | kulik-alexey@mail.ru
"""


# ══════════════════════════════════════════════
#  ПАМЯТЬ — хранится в Telegram сообщении
# ══════════════════════════════════════════════

def tg_request(method, **kwargs):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    try:
        r = requests.post(url, json=kwargs, timeout=10)
        return r.json()
    except Exception as e:
        print(f"TG error {method}: {e}")
        return {}


def load_seen_from_telegram():
    """Читает список виденных вакансий из закреплённого сообщения"""
    global MEMORY_MSG_ID
    if not MEMORY_MSG_ID:
        return set()
    try:
        # Получаем сообщение по ID
        r = tg_request("forwardMessage",
            chat_id=CHAT_ID,
            from_chat_id=CHAT_ID,
            message_id=int(MEMORY_MSG_ID)
        )
        # Проще — просто читаем из локального файла как резерв
    except Exception:
        pass
    return load_seen_local()


def load_seen_local():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    """Сохраняет локально + отправляет резервную копию в Telegram"""
    global MEMORY_MSG_ID

    # Локальное сохранение
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

    # Резервная копия в Telegram — обновляем или создаём сообщение
    seen_text = f"🗄 MEMORY\n{json.dumps(list(seen)[-500:])}"  # последние 500 ID

    if MEMORY_MSG_ID:
        # Обновляем существующее сообщение
        tg_request("editMessageText",
            chat_id=CHAT_ID,
            message_id=int(MEMORY_MSG_ID),
            text=seen_text
        )
    else:
        # Создаём новое сообщение-хранилище
        r = tg_request("sendMessage",
            chat_id=CHAT_ID,
            text=seen_text,
            disable_notification=True
        )
        if r.get("ok"):
            msg_id = str(r["result"]["message_id"])
            MEMORY_MSG_ID = msg_id
            print(f"Создано хранилище памяти, ID сообщения: {msg_id}")
            print(f"Добавьте в Railway переменную MEMORY_MSG_ID = {msg_id}")
            # Закрепляем сообщение
            tg_request("pinChatMessage",
                chat_id=CHAT_ID,
                message_id=int(msg_id),
                disable_notification=True
            )


def load_seen():
    """Загружает память — сначала локально, при перезапуске восстанавливает из Telegram"""
    local = load_seen_local()
    if local:
        return local

    # Если локальный файл пуст (перезапуск) — читаем из Telegram
    if MEMORY_MSG_ID:
        try:
            # Получаем обновления чтобы найти сообщение с памятью
            r = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getChat",
                params={"chat_id": CHAT_ID},
                timeout=10
            )
            # Пробуем прочитать закреплённое сообщение
            chat_data = r.json().get("result", {})
            pinned = chat_data.get("pinned_message", {})
            if pinned and str(pinned.get("message_id")) == MEMORY_MSG_ID:
                text = pinned.get("text", "")
                if "MEMORY" in text:
                    ids_json = text.replace("🗄 MEMORY\n", "")
                    ids = json.loads(ids_json)
                    seen = set(ids)
                    # Восстанавливаем локально
                    with open(SEEN_FILE, "w") as f:
                        json.dump(list(seen), f)
                    print(f"Память восстановлена из Telegram: {len(seen)} вакансий")
                    return seen
        except Exception as e:
            print(f"Ошибка восстановления памяти: {e}")

    return set()


# ══════════════════════════════════════════════
#  ОСНОВНАЯ ЛОГИКА
# ══════════════════════════════════════════════

def is_fresh(vacancy):
    published = vacancy.get("published_at")
    if not published:
        return True
    try:
        pub_time = datetime.fromisoformat(published.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - pub_time) <= timedelta(hours=HOURS_FILTER)
    except Exception:
        return True


def get_vacancy_details(vacancy_id):
    url = f"https://api.hh.ru/vacancies/{vacancy_id}"
    headers = {"User-Agent": "hh-monitor-bot/4.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"Ошибка вакансии: {e}")
    return None


def clean_html(text):
    import re
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:2000]


def generate_cover_letter(vacancy_title, company, description):
    if not CLAUDE_API_KEY:
        return None
    prompt = f"""Напиши короткое сопроводительное письмо (5-6 предложений) для отклика.

Вакансия: {vacancy_title}
Компания: {company}
Описание: {description}

Кандидат:
{CANDIDATE_PROFILE}

Требования: коротко, с цифрами, живой язык, без "Добрый день" и подписи."""

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()["content"][0]["text"]
    except Exception as e:
        print(f"Claude error: {e}")
    return None


def search_vacancies(keyword):
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": keyword, "area": AREA,
        "per_page": 20, "order_by": "publication_time",
        "search_field": "name",
    }
    try:
        r = requests.get(url, params=params,
                         headers={"User-Agent": "hh-monitor/4.0"}, timeout=10)
        if r.status_code == 200:
            return r.json().get("items", [])
    except Exception as e:
        print(f"HH error: {e}")
    return []


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
        sf, st, cur = salary.get("from"), salary.get("to"), salary.get("currency","RUB")
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

    tg_request("sendMessage",
        chat_id=CHAT_ID,
        text=(f"🔔 <b>{title}</b>\n"
              f"🏢 {company}\n"
              f"💰 {sal}{pub_str}\n"
              f"🔍 <i>{keyword}</i>\n"
              f"🔗 <a href='{url}'>Открыть на hh.ru</a>"),
        parse_mode="HTML",
        disable_web_page_preview=False,
    )

    if CLAUDE_API_KEY:
        details = get_vacancy_details(vid)
        if details:
            desc = clean_html(details.get("description", ""))
            letter = generate_cover_letter(title, company, desc)
            if letter:
                tg_request("sendMessage",
                    chat_id=CHAT_ID,
                    text=f"📝 <b>Сопроводительное письмо:</b>\n\n{letter}",
                    parse_mode="HTML",
                )
                time.sleep(0.5)


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
    print("HH.ru Монитор v4.0 — с постоянной памятью")

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

    letter_status = "✅ С письмами" if CLAUDE_API_KEY else "⏳ Без писем (ждём баланс)"

    tg_request("sendMessage",
        chat_id=CHAT_ID,
        text=(f"✅ <b>Монитор v4.0 запущен!</b>\n\n"
              f"Запросы: {len(KEYWORDS)} шт.\n"
              f"📍 Санкт-Петербург\n"
              f"⏱ Каждые {INTERVAL_MINUTES} минут\n"
              f"📅 За последние {HOURS_FILTER} часов\n"
              f"🧠 Постоянная память (не слетает)\n"
              f"📝 {letter_status}"),
        parse_mode="HTML",
    )

    check_and_notify()

    while True:
        time.sleep(INTERVAL_MINUTES * 60)
        check_and_notify()


if __name__ == "__main__":
    main()
