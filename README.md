# 🧥 Jacket Suggester

Sends you a daily SMS every morning with the perfect jacket recommendation
based on London's weather — specifically tuned for your **8am and 5pm walks**.

---

## How it works

1. Fetches London's hourly forecast from [Open-Meteo](https://open-meteo.com) (free, no key needed)
2. Checks temperature and rain probability at **8:00 AM** and **5:00 PM**
3. Applies your jacket logic (see below)
4. Sends you an SMS via Twilio at **~7:30 AM** every morning

### Jacket logic

| Jacket | When |
|--------|------|
| 🧥 Jacket 1 — Big coat | Storm, rain ≥60%, or temp below 5°C |
| Jacket 2 — Moderate | Rain <20% but cool (6–17°C) |
| 🧶 Jacket 3 — Fleece | Mild & dry (8–20°C), morning starts cold (<12°C) |
| 👔 Jacket 4 — Formal top | Warm & dry (12–25°C), morning already warm (≥12°C) |
| 👕 Jacket 5 — Light wear | Hot or humid (25°C+) |

Evening warnings are added automatically if conditions worsen by 5pm.

---

## Setup (one-time, ~10 minutes)

### 1. Twilio account
1. Sign up free at [twilio.com](https://www.twilio.com/try-twilio) — no credit card needed
2. From the Console, grab your:
   - **Account SID**
   - **Auth Token**
   - **Twilio phone number** (click "Get phone number")
3. Verify your personal mobile number in the Console

### 2. GitHub repo
1. Create a **private** GitHub repository
2. Add these files to the root:
   - `jacket_suggester.py`
   - `.github/workflows/daily.yml`
3. Go to **Settings → Secrets and variables → Actions** and add:

| Secret name | Value |
|-------------|-------|
| `TWILIO_ACCOUNT_SID` | Your Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token |
| `TWILIO_FROM_NUMBER` | Your Twilio number e.g. `+441234567890` |
| `YOUR_PHONE_NUMBER` | Your mobile e.g. `+447700900000` |

### 3. Test it
- Go to **Actions → Daily Jacket Suggester → Run workflow**
- You should receive an SMS within ~30 seconds!

### 4. Done!
GitHub Actions will now run it automatically every morning at ~7:30 AM London time.
It's free for public repos and free within the generous GitHub Actions free tier for private repos
(2,000 minutes/month — this job uses ~10 seconds per run).

---

## Security notes
- Your phone number is stored only in GitHub Secrets (encrypted, never visible in logs)
- Keep your repo **private**
- Never commit your Twilio credentials directly into the code

---

## Customising
Edit `jacket_suggester.py` to update jacket names, descriptions, or tweak temperature thresholds.
All jacket logic is in the `pick_jacket()` function — easy to adjust.
