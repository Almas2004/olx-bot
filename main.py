import requests
import time
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import html

# Загружаем токен и chat_id из .env
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Константы
SEARCH_URL = "https://www.olx.kz/elektronika/telefony-i-aksesuary/mobilnye-telefony-smartfony/atyrau/?search%5Bdist%5D=100&search%5Bfilter_float_price:to%5D=55000&search%5Bfilter_enum_mobile_phone_manufacturer%5D%5B0%5D=2065&search%5Bfilter_enum_operating_system%5D%5B0%5D=2"
CHECK_INTERVAL = 30  # в секундах (5 минут)
SEEN_FILE = "seen.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def load_seen():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        for link in seen:
            f.write(link + "\n")


def get_latest_ads():
    response = requests.get(SEARCH_URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    ads = soup.select('div[data-testid="listing-grid"] div[data-cy="l-card"]')[:50]  # проверяем 50

    results = []
    for ad in ads:
        title_tag = ad.select_one('a.css-1tqlkj0')
        price_tag = ad.select_one('p[data-testid="ad-price"]')
        link_tag = ad.select_one('a')

        if not link_tag or "href" not in link_tag.attrs:
            continue

        title = title_tag.get_text(strip=True) if title_tag else "Без заголовка"
        price = price_tag.get_text(strip=True) if price_tag else "Цена не указана"
        link = "https://www.olx.kz" + link_tag["href"]

        results.append((title, price, link))

    return results


def send_telegram_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ BOT_TOKEN или CHAT_ID не заданы!")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ Ошибка Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")


def main():
    seen_links = load_seen()
    print("🔁 Запущен мониторинг новых объявлений...\n")

    while True:
        ads = get_latest_ads()
        new_ads = [ad for ad in ads if ad[2] not in seen_links]

        if new_ads:
            print(f"🆕 Найдено новых объявлений: {len(new_ads)}\n")
            
            for i, (title, price, link) in enumerate(new_ads, 1):
                print(f"{i}. {title}")
                print(f"   💰 {price}")
                print(f"   🔗 {link}\n")

                # Экранируем HTML-символы
                safe_price = html.escape(price)
                safe_link = html.escape(link)

                message = f"📢 Появилось новое объявление\n💰 {safe_price}\n🔗 <a href='{safe_link}'>Смотреть на OLX</a>"
                send_telegram_message(message)
                seen_links.add(link)

            save_seen(seen_links)
        else:
            print("⏳ Новых объявлений пока нет...\n")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")