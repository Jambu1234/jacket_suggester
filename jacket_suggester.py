#!/usr/bin/env python3
"""
Jacket Suggester - Daily SMS recommender
Fetches London weather and sends jacket recommendation via Twilio SMS
"""
from dotenv import load_dotenv
load_dotenv()
import os
import json
import urllib.request
from datetime import datetime, date


# ── Configuration ────────────────────────────────────────────────────────────
LATITUDE = 52.5736
LONGITUDE = -0.2477
TIMEZONE = "Europe/London"

GMAIL_ADDRESS    = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TO_EMAIL         = os.environ["TO_EMAIL"]     # your verified number


# ── Jacket definitions ────────────────────────────────────────────────────────
JACKETS = {
    1: {
        "name": "Big Jacket (Jacket 1)",
        "emoji": "🧥",
        "desc": "Your heavy-duty coat — built for storms, heavy rain, and freezing temps.",
    },
    2: {
        "name": "H&M Jacket (Jacket 2)",
        "emoji": "🧥",  # placeholder — update to your jacket emoji
        "desc": "Your moderate jacket — good protection, not too heavy.",
    },
    3: {
        "name": "Fleece (Jacket 3)",
        "emoji": "🧶",
        "desc": "Your fleece — light, cosy, great for mild dry mornings.",
    },
    4: {
        "name": "Formal / Full-sleeve top (No jacket)",
        "emoji": "👔",
        "desc": "No jacket needed — a smart long-sleeve will do fine.",
    },
    5: {
        "name": "Light / Relaxed wear (No jacket)",
        "emoji": "👕",
        "desc": "No jacket needed — keep it light and breathable today.",
    },
}


# ── Weather fetch ─────────────────────────────────────────────────────────────
def fetch_weather():
    """Fetch hourly forecast from Open-Meteo (free, no API key)."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LATITUDE}&longitude={LONGITUDE}"
        f"&hourly=temperature_2m,precipitation_probability,precipitation"
        f"&daily=temperature_2m_max,temperature_2m_min"
        f"&timezone={TIMEZONE}"
        f"&forecast_days=1"
    )
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())


def parse_weather(data):
    """Extract the values we care about from the API response."""
    hourly_times = data["hourly"]["time"]
    hourly_temp  = data["hourly"]["temperature_2m"]
    hourly_rain  = data["hourly"]["precipitation_probability"]

    today = date.today().isoformat()

    def avg_for_hours(hour_start, hour_end):
        temps, rains = [], []
        for i, t in enumerate(hourly_times):
            if not t.startswith(today):
                continue
            h = int(t[11:13])
            if hour_start <= h <= hour_end:
                temps.append(hourly_temp[i])
                rains.append(hourly_rain[i])
        avg_t = sum(temps) / len(temps) if temps else 0
        max_r = max(rains) if rains else 0
        return round(avg_t, 1), max_r

    morning_temp, morning_rain = avg_for_hours(8, 8)    # 08:00
    evening_temp, evening_rain = avg_for_hours(17, 17)  # 17:00

    day_max = data["daily"]["temperature_2m_max"][0]
    day_min = data["daily"]["temperature_2m_min"][0]

    return {
        "morning_temp": morning_temp,
        "morning_rain": morning_rain,
        "evening_temp": evening_temp,
        "evening_rain": evening_rain,
        "day_max": day_max,
        "day_min": day_min,
        "temp_rise": day_max - day_min,   # how much the day warms up
    }


# ── Jacket decision logic ─────────────────────────────────────────────────────
def pick_jacket(w):
    """
    Decision priority:
    1. Storm / heavy rain / very cold  → Jacket 1
    2. Moderate conditions (rain <20%, 6–17°C) → Jacket 2
    3. Mild & dry (8–20°C, no rain)   → Jacket 3  (if day starts cold)
    4. Warm day (12–25°C)             → Jacket 4  (if day starts warm)
    5. Hot/humid (25°C+)              → Jacket 5
    Overlap zone (12–20°C, dry): if morning temp <12°C → Jacket 3 (fleece)
                                  if morning temp ≥12°C → Jacket 4 (formal top)
    Evening safety: if evening rain or cold, bump up jacket level.
    """
    mt = w["morning_temp"]
    mr = w["morning_rain"]
    et = w["evening_temp"]
    er = w["evening_rain"]
    day_max = w["day_max"]

    # ── Rule 1: extreme / stormy ──────────────────────────────────────────────
    if mr >= 60 or er >= 60 or mt < 5 or et < 5:
        return 1, "storm or extreme cold forecast for your walks"

    # ── Rule 2: moderate jacket ───────────────────────────────────────────────
    if (mr < 20 and er < 20) and (6 <= mt <= 17 or 6 <= et <= 17):
        # only recommend jacket 2 if some rain risk (20–59%) or cold (6–11°C)
        if mr >= 20 or er >= 20 or mt < 10 or et < 10:
            return 2, "light rain risk or cool temperatures around your walk times"

    # ── Rule 3 vs 4 overlap: mild dry 8–20°C ─────────────────────────────────
    both_dry   = mr < 20 and er < 20
    mild_range = (8 <= mt <= 20) and (8 <= et <= 20)

    if both_dry and mild_range:
        day_starts_cold = mt < 12
        if day_starts_cold:
            return 3, f"mild morning ({mt}°C) warming to {day_max}°C — fleece for the cool start"
        else:
            return 4, f"warm morning ({mt}°C) with a {day_max}°C high — no jacket needed"

    # ── Rule 5: hot / humid ───────────────────────────────────────────────────
    if mt >= 25 or day_max >= 28:
        return 5, f"it's going to be hot (up to {day_max}°C) — keep it light"

    # ── Rule 4: warm day ─────────────────────────────────────────────────────
    if 12 <= mt <= 25 and both_dry:
        return 4, f"warm and dry ({mt}°C morning, {day_max}°C high)"

    # ── Safe default ──────────────────────────────────────────────────────────
    return 1, "mixed forecast — better safe than sorry"


# ── Evening warning ───────────────────────────────────────────────────────────
def evening_note(w, jacket_id):
    """Add an evening heads-up if conditions worsen after office hours."""
    notes = []
    if w["evening_rain"] >= 40 and jacket_id >= 3:
        notes.append(f"⚠️ Evening rain chance: {w['evening_rain']}% — consider carrying something waterproof for the 5pm walk home.")
    if w["evening_temp"] < w["morning_temp"] - 5:
        notes.append(f"🌡️ Temperature drops to {w['evening_temp']}°C by 5pm — it'll feel colder on the way home.")
    return " ".join(notes)


# ── SMS builder ───────────────────────────────────────────────────────────────
def build_message(w, jacket_id, reason):
    j = JACKETS[jacket_id]
    today_str = datetime.now().strftime("%A %#d %b")

    msg = (
        f"Good morning! 🌤️ Jacket Suggester — {today_str}\n\n"
        f"{j['emoji']} {j['name']}\n"
        f"{j['desc']}\n\n"
        f"Why: {reason}\n\n"
        f"🚶 8am walk: {w['morning_temp']}°C, rain {w['morning_rain']}%\n"
        f"🚶 5pm walk: {w['evening_temp']}°C, rain {w['evening_rain']}%\n"
        f"📊 Day range: {w['day_min']}°C – {w['day_max']}°C"
    )

    note = evening_note(w, jacket_id)
    if note:
        msg += f"\n\n{note}"

    return msg


def send_email(body):
    import smtplib
    from email.mime.text import MIMEText

    gmail_address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    to_email = os.environ["TO_EMAIL"]

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "🧥 Jacket Suggester"
    msg["From"] = gmail_address
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_address, app_password)
        smtp.sendmail(gmail_address, to_email, msg.as_string())
        print("Email sent! ✅")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    import urllib.parse

    print("Fetching London weather forecast...")
    raw = fetch_weather()
    w   = parse_weather(raw)

    print(f"Morning: {w['morning_temp']}°C, rain {w['morning_rain']}%")
    print(f"Evening: {w['evening_temp']}°C, rain {w['evening_rain']}%")
    print(f"Day range: {w['day_min']}–{w['day_max']}°C")

    jacket_id, reason = pick_jacket(w)
    print(f"Jacket pick: {jacket_id} — {reason}")

    message = build_message(w, jacket_id, reason)
    print("\n── Message preview ──────────────────────────────")
    print(message)
    print("─────────────────────────────────────────────────\n")

    send_email(message)
    print("Done! ✅")


if __name__ == "__main__":
    main()
