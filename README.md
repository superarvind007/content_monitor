# ClassForKids Monitor 🏫

Monitors [Broomfield Primary School on ClassForKids](https://sportscoachingspecialists.classforkids.io/?venueName=Broomfield%20Primary%20School) and sends an email when **"Join Waiting List"** changes to **"Info & Booking"**.

Runs for **free** on GitHub Actions every 15 minutes using headless Chrome.

## Setup (5 minutes)

### 1. Create a Gmail App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** if not already on
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Generate a new app password for **"Mail"**
5. Copy the 16-character password (e.g. `abcd efgh ijkl mnop`)

### 2. Add GitHub Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 3 secrets:

| Secret Name | Value |
|---|---|
| `SENDER_EMAIL` | Your Gmail address (e.g. `you@gmail.com`) |
| `SENDER_APP_PASSWORD` | The 16-char app password from step 1 |
| `RECIPIENT_EMAIL` | Where to receive notifications (can be same as sender) |

### 3. Push and Go

```bash
git add -A
git commit -m "Add ClassForKids monitor"
git push
```

The workflow starts automatically — checks every 15 minutes, 24/7.

## Manual Test

Go to your repo → **Actions** → **Monitor ClassForKids** → **Run workflow** to trigger a check immediately.

## How It Works

- Uses **Selenium + headless Chrome** (pre-installed on GitHub runners)
- Detects button CSS class change: `c4k-class-waiting-list-button` → `c4k-class-info-button`
- Sends a styled HTML email via Gmail SMTP
- Caches state between runs to avoid duplicate notifications

## Free Tier Usage

GitHub Actions free tier gives **2,000 minutes/month** for private repos (unlimited for public). This workflow uses ~1 min per run × 96 runs/day = **~96 min/day ≈ 2,880 min/month**. To stay within limits on a **private repo**, increase the cron interval to `*/30` (every 30 min) in `.github/workflows/monitor.yml`.

For a **public repo**, there are no limits.
