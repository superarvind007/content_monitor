#!/usr/bin/env python3
"""
ClassForKids Monitor — Broomfield Primary School
Checks if "Join Waiting List" has changed to "Info & Booking"
and sends an email notification via Gmail.

Credentials are read from environment variables (GitHub Secrets).
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import os
import json
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

URL = "https://sportscoachingspecialists.classforkids.io/?venueName=Broomfield%20Primary%20School"

# Read from environment variables (set via GitHub Secrets)
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SENDER_APP_PASSWORD = os.environ.get("SENDER_APP_PASSWORD", "")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "")

STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".classforkids_state.json"
)


# ============================================================
# CORE LOGIC
# ============================================================

def load_state():
    """Load state to track if notification was already sent."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"notification_sent": False, "last_check": None, "last_status": None}


def save_state(state):
    """Persist state to file (cached between GitHub Actions runs)."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def create_driver():
    """Create a headless Chrome WebDriver."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def check_page():
    """
    Load the page with Selenium and detect button state.

    The page uses JavaScript to render class listings, so we need
    a real browser. When booking opens, the button changes:
      - CSS class: c4k-class-waiting-list-button → c4k-class-info-button
      - Text: "Join Waiting List" → "Info & Booking"
    """
    driver = None
    try:
        driver = create_driver()
        driver.get(URL)

        # Wait up to 20s for dynamic content to appear
        try:
            WebDriverWait(driver, 20).until(
                lambda d: (
                    d.find_elements(By.CSS_SELECTOR, ".c4k-class-waiting-list-button")
                    or d.find_elements(By.CSS_SELECTOR, ".c4k-class-info-button")
                    or d.find_elements(By.XPATH, "//*[contains(text(), 'Waiting List')]")
                    or d.find_elements(By.XPATH, "//*[contains(text(), 'Info & Booking')]")
                )
            )
        except Exception:
            pass

        # Extra time for any late-loading elements
        time.sleep(3)

        # 1) Check for "Info & Booking" (booking available!)
        booking_buttons = driver.find_elements(By.CSS_SELECTOR, ".c4k-class-info-button")
        booking_by_text = driver.find_elements(
            By.XPATH,
            "//*[contains(text(), 'Info & Booking') or contains(text(), 'Info & Book')]",
        )

        if booking_buttons or booking_by_text:
            btn = booking_buttons[0] if booking_buttons else booking_by_text[0]
            href = btn.get_attribute("href") or URL
            return {
                "status": "booking_available",
                "details": f"Booking is now available! Button: '{btn.text.strip()}'",
                "booking_url": href,
            }

        # 2) Check for "Join Waiting List" (no change yet)
        waiting_buttons = driver.find_elements(By.CSS_SELECTOR, ".c4k-class-waiting-list-button")
        waiting_by_text = driver.find_elements(By.XPATH, "//*[contains(text(), 'Waiting List')]")

        if waiting_buttons or waiting_by_text:
            return {
                "status": "waiting_list",
                "details": "Still showing 'Join Waiting List'. No booking yet.",
                "booking_url": None,
            }

        # 3) Neither found — page may have changed
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "Broomfield" in page_text:
            return {
                "status": "changed",
                "details": "Page changed! 'Join Waiting List' is gone but no booking button found. Check manually!",
                "booking_url": URL,
            }

        return {
            "status": "error",
            "details": "Could not find expected content. Page may have restructured.",
            "booking_url": None,
        }

    except Exception as e:
        return {"status": "error", "details": f"Error: {str(e)}", "booking_url": None}
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def send_email(result):
    """Send a notification email via Gmail SMTP."""
    if not all([SENDER_EMAIL, SENDER_APP_PASSWORD, RECIPIENT_EMAIL]):
        print("⚠️  Email not configured — set GitHub Secrets: SENDER_EMAIL, SENDER_APP_PASSWORD, RECIPIENT_EMAIL")
        return False

    booking_url = result.get("booking_url") or URL
    now = datetime.utcnow().strftime("%A %d %B %Y at %H:%M:%S UTC")

    subject = "🎉 ClassForKids Booking Available — Broomfield Primary School!"

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 24px; border-radius: 12px 12px 0 0; color: white; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">🎉 Booking Now Available!</h1>
            <p style="margin: 8px 0 0; opacity: 0.9;">Broomfield Primary School — Sports Coaching Specialists</p>
        </div>
        <div style="padding: 24px; background: #fff; border: 1px solid #e0e0e0; border-top: none;">
            <p style="color: #333; font-size: 16px;">{result['details']}</p>
            <div style="text-align: center; margin: 24px 0;">
                <a href="{booking_url}"
                   style="background: #4CAF50; color: white; padding: 14px 32px;
                          text-decoration: none; border-radius: 8px; font-size: 18px;
                          display: inline-block; font-weight: bold;">
                    📅 Book Now
                </a>
            </div>
        </div>
        <div style="padding: 16px; background: #f5f5f5; border-radius: 0 0 12px 12px;
                    border: 1px solid #e0e0e0; border-top: none;">
            <p style="color: #888; font-size: 12px; margin: 0;">
                Page: <a href="{URL}">{URL}</a><br>Detected: {now}
            </p>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg.attach(MIMEText(result["details"], "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print(f"✅ Email sent to {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False


def main():
    state = load_state()
    now = datetime.utcnow().isoformat() + "Z"

    print(f"\n{'='*60}")
    print(f"🔍 Checking ClassForKids at {now}")
    print(f"{'='*60}")

    result = check_page()
    state["last_check"] = now
    state["last_status"] = result["status"]

    if result["status"] in ("booking_available", "changed"):
        print(f"🎉 {result['details']}")
        if not state.get("notification_sent"):
            if send_email(result):
                state["notification_sent"] = True
        else:
            print("ℹ️  Notification already sent previously.")
    elif result["status"] == "waiting_list":
        print(f"⏳ {result['details']}")
    else:
        print(f"⚠️  {result['details']}")

    save_state(state)


if __name__ == "__main__":
    main()
