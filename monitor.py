# -*- coding: utf-8 -*-
"""
Biletinial - PROFESYONEL (İstanbul Avrupa) tarih izleyici.
14 Kasım 2025 ve SONRASI bir tarih görünürse e-posta gönderir.
Windows Görev Zamanlayıcı ile günde 2 kez koşturulabilir.
"""

import os, re, json, smtplib
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.utils import formataddr
from dotenv import load_dotenv

# ------------------------- Ayarlar -------------------------
load_dotenv()  # .env dosyasını okur (NOT: .env.example okunmaz)

TARGET_URL = os.getenv("TARGET_URL", "https://biletinial.com/tr-tr/tiyatro/profesyonel-dt")
VENUE_URL  = os.getenv("VENUE_URL",  "https://biletinial.com/tr-tr/mekan/istanbul-devlet-tiyatrosu")

# 14 Kasım 2025 ve sonrası (>= 2025-11-14)
CUTOFF_DATE_STR = os.getenv("CUTOFF_DATE", "2025-11-14")
CUTOFF_DATE = datetime.strptime(CUTOFF_DATE_STR, "%Y-%m-%d").date()

# Ay beyaz listesi: sadece bu ayları dikkate al (gürültüyü azaltır)
# Varsayılan: Kasım, Aralık
ALLOWED_MONTHS = os.getenv("ALLOWED_MONTHS", "Kasım,Aralık")
ALLOWED_SET = {m.strip() for m in ALLOWED_MONTHS.split(",") if m.strip()}

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL") or SMTP_USER
TO_EMAIL   = os.getenv("TO_EMAIL") or SMTP_USER

STATE_PATH = Path("state.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}

MONTHS_TR = {
    "Ocak": 1, "Şubat": 2, "Subat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5, "Mayis": 5,
    "Haziran": 6, "Temmuz": 7, "Ağustos": 8, "Agustos": 8, "Eylül": 9, "Eylul": 9,
    "Ekim": 10, "Kasım": 11, "Kasim": 11, "Aralık": 12, "Aralik": 12,
    "Oca": 1, "Şub": 2, "Sub": 2, "Mar": 3, "Nis": 4, "May": 5, "Haz": 6,
    "Tem": 7, "Ağu": 8, "Agu": 8, "Eyl": 9, "Eki": 10, "Kas": 11, "Ara": 12
}

DEBUG = os.getenv("DEBUG", "0") == "1"

# ------------------------- Yardımcılar -------------------------
def _normalize_month(mon_key: str) -> Optional[int]:
    k = (mon_key
         .replace("ğ","g").replace("Ğ","G")
         .replace("ı","i").replace("İ","I")
         .replace("â","a").replace("Â","A"))
    # Ay beyaz listesi kontrolü (adıyla)
    if ALLOWED_SET and not any(x in mon_key or x in k for x in ALLOWED_SET):
        return None
    return MONTHS_TR.get(mon_key) or MONTHS_TR.get(k) or MONTHS_TR.get(mon_key[:3])

def fetch_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def scan_text_for_dates(text_blob: str) -> List[date]:
    """
    Serbest metinde tarih tara:
      - '15 Kasım', '16 Kas', 'Kas 16' gibi.
    Sadece ALLOWED_MONTHS'teki aylara izin verilir (varsayılan: Kasım, Aralık).
    """
    pats = [
        r"(\b\d{1,2})\s+(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|Haziran|Temmuz|Ağustos|Agustos|Eylül|Eylul|Ekim|Kasım|Kasim|Aralık|Aralik)\b",
        r"\b(Oca|Şub|Sub|Mar|Nis|May|Haz|Tem|Ağu|Agu|Eyl|Eki|Kas|Ara)\s*(\d{1,2})\b",
        r"\b(\d{1,2})\s*(Oca|Şub|Sub|Mar|Nis|May|Haz|Tem|Ağu|Agu|Eyl|Eki|Kas|Ara)\b",
    ]
    found = []
    for pat in pats:
        for m in re.finditer(pat, text_blob, flags=re.IGNORECASE):
            if len(m.groups()) == 2:
                g1, g2 = m.groups()
                if g1.isdigit():
                    day = int(g1); mon_key = g2
                else:
                    mon_key = g1; day = int(g2)
            else:
                day = int(m.group(1)); mon_key = m.group(2)

            month = _normalize_month(mon_key)
            if not month:
                continue
            yr = date.today().year
            try:
                found.append(date(yr, month, day))
            except ValueError:
                pass
    return sorted(set(found))

def parse_show_page(html: str) -> List[date]:
    soup = BeautifulSoup(html, "html.parser")
    text = " ".join(s.strip() for s in soup.stripped_strings)
    dates = scan_text_for_dates(text)
    if DEBUG: print(f"[DEBUG] Gösteri sayfası: {len(dates)} aday -> {dates}")
    return dates

def parse_venue_page(html: str) -> List[date]:
    """
    Mekan sayfasında 'PROFESYONEL ... Kasım - 15 - 16' formatı varsa onu oku.
    Sadece bu bloğu kullan (genel tarama yapma ki gürültü gelmesin).
    """
    soup = BeautifulSoup(html, "html.parser")
    all_text = " ".join(s.strip() for s in soup.stripped_strings)

    block = re.search(
        r"PROFESYONEL\s+Kas[ıi]m\s*-\s*([0-9]{1,2}(?:\s*-\s*[0-9]{1,2})*)",
        all_text, flags=re.IGNORECASE
    )
    found = []
    if block:
        yr = date.today().year
        for d in re.findall(r"[0-9]{1,2}", block.group(1)):
            try:
                found.append(date(yr, 11, int(d)))  # Kasım=11
            except ValueError:
                pass
    if DEBUG: print(f"[DEBUG] Mekan sayfası: {len(found)} aday -> {found}")
    return sorted(set(found))

def load_state() -> Optional[str]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8")).get("last_notified_max_date")
        except Exception:
            return None
    return None

def save_state(d: date) -> None:
    STATE_PATH.write_text(json.dumps({"last_notified_max_date": d.isoformat()}, ensure_ascii=False, indent=2), encoding="utf-8")

def send_email(subject: str, body: str) -> None:
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS and FROM_EMAIL and TO_EMAIL):
        print("[WARN] SMTP bilgileri eksik; e-posta gönderilmeyecek.")
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("Bilet İzleyici", FROM_EMAIL))
    msg["To"] = TO_EMAIL
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    print("[INFO] E-posta gönderildi:", TO_EMAIL)

# ------------------------- Ana akış -------------------------
def main():
    print(CUTOFF_DATE)  # debug amaçlı, istersen kaldır

    # 1) Gösteri sayfasını tara
    show_html = fetch_html(TARGET_URL)
    dates_show = parse_show_page(show_html)

    # 2) Mekan sayfasını tara (yalnızca 'Kasım - 15 - 16' bloğu)
    venue_dates = []
    try:
        venue_html = fetch_html(VENUE_URL)
        venue_dates = parse_venue_page(venue_html)
    except Exception as e:
        print("[WARN] Mekan sayfası alınamadı:", e)

    # 3) Birleştir (tekrarı kaldır)
    dates = sorted(set(dates_show) | set(venue_dates))
    print("[INFO] Bulunan tarih(ler):", ", ".join(d.isoformat() for d in dates) if dates else "(yok)")

    # 4) Eşik sonrası olanları filtrele
    newer = [d for d in dates if d >= CUTOFF_DATE]  # "14 ve sonrası" istenirse >= kullan
    if not newer:
        print(f"[INFO] {CUTOFF_DATE} ve sonrasında tarih yok.")
        return

    max_new = max(newer)
    last = load_state()
    if last == max_new.isoformat():
        print("[INFO] En büyük tarih değişmedi; e-posta gönderilmeyecek.")
        return

    subject = f"Profesyonel Bilet Alert Yeni tarih: {max_new.strftime('%d.%m.%Y')})"
    list_lines = "\n".join(f"- {d.strftime('%d %B %Y')}" for d in newer)
    body = f"""Merhaba,

"PROFESYONEL" oyunu için yeni tarih(ler) tespit edildi.

Bulunanlar:
{list_lines}

Sayfa: {TARGET_URL}

Sevgiler,
Selçuk
"""
    send_email(subject, body)
    save_state(max_new)

if __name__ == "__main__":
    main()
