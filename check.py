"""Watch the IRCTC HeliYatra homepage and ping Telegram when the
Kedarnath booking banner changes (e.g. bookings open for 16 Oct onwards)."""
import os
import re
import sys
import pathlib
import requests
from bs4 import BeautifulSoup

URL = "https://www.heliyatra.irctc.co.in/"
STATE = pathlib.Path("last_seen.txt")
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
MANUAL = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"


def telegram(msg: str) -> None:
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg, "disable_web_page_preview": True},
        timeout=30,
    )
    r.raise_for_status()


def kedarnath_banner() -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
        "Accept-Language": "en-IN,en;q=0.9",
    }
    html = requests.get(URL, headers=headers, timeout=45).text
    soup = BeautifulSoup(html, "html.parser")
    h3 = soup.find(lambda t: t.name == "h3" and "Kedarnath" in t.get_text())
    if h3 is None or h3.find_next_sibling("div") is None:
        raise RuntimeError("Kedarnath card not found on page")
    text = " ".join(h3.find_next_sibling("div").get_text(" ").split())
    text = re.sub(r"\s+([.,])", r"\1", text)  # "2026 ." -> "2026."
    if len(text) < 10:
        raise RuntimeError("Kedarnath card is empty")
    return text


def main() -> None:
    last = STATE.read_text().strip() if STATE.exists() else ""
    try:
        banner = kedarnath_banner()
    except Exception as e:  # site down, blocked, or layout changed
        if last != "ERROR" or MANUAL:
            telegram(f"⚠️ Kedarnath heli monitor couldn't read the site: {e}\n{URL}")
            STATE.write_text("ERROR")
        print("error:", e)
        sys.exit(0)

    print("banner:", banner)
    if MANUAL:
        telegram(f"✅ Monitor is working. Current Kedarnath banner:\n{banner}")
    if last and last not in (banner, "ERROR"):
        telegram(f"🚁 KEDARNATH HELI BANNER CHANGED!\n\nNow: {banner}\n\nWas: {last}\n\n{URL}")
    elif last == "ERROR" and not MANUAL:
        telegram(f"✅ Monitor can read the site again. Banner:\n{banner}")
    STATE.write_text(banner)


if __name__ == "__main__":
    main()
