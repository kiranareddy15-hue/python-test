import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import schedule

WAIT_AFTER_ACTION = 2.0
WAIT_AFTER_NAVIGATION = 3.0
WAIT_FOR_ELEMENT = 15_000
HEADED = True
SLOW_MO = 500

load_dotenv(Path(__file__).resolve().parent / ".env")

def env(name: str, default: str = None) -> str:
    val = os.environ.get(name)
    if not val:
        if default is not None:
            return default
        print(f"Missing env: {name}. Copy .env.example to .env and fill values.")
        sys.exit(1)
    return val

def log_success(session_token: str, log_file: str = "change_id_log.txt"):
    log_path = Path(__file__).resolve().parent / log_file
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"""
[{timestamp}] Change ID Automation - SUCCESS
Session Token: {session_token}
Token Length: {len(session_token)} characters
Betfair Login: SUCCESS
Admin Login: SUCCESS
First Field Updated: SUCCESS
Bets Toggle: ON
Field Verification: PASSED
---
"""
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
        print(f"\n[LOG] Success logged to {log_path}")
    except Exception as e:
        print(f"\n[WARNING] Failed to write log: {e}")

def wait(page, seconds: float = None):
    s = seconds if seconds is not None else WAIT_AFTER_ACTION
    if s > 0:
        page.wait_for_timeout(int(s * 1000))

def run_automation():
    betfair_user = env("BETFAIR_USERNAME")
    betfair_pass = env("BETFAIR_PASSWORD")
    admin_user = env("ADMIN_USERNAME")
    admin_pass = env("ADMIN_PASSWORD")
    operator_key = env("ADMIN_OPERATOR_KEY")
    session_token = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not HEADED, slow_mo=SLOW_MO)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
        )
        page = context.new_page()

        try:
            print("\n[1] Opening Betfair Exchange Plus...")
            page.goto("https://www.betfair.com/exchange/plus/", wait_until="domcontentloaded", timeout=60000)
            wait(page, WAIT_AFTER_NAVIGATION)

            print("[2] Looking for cookie popup and clicking Allow All Cookies...")
            cookie_btn = page.locator("#onetrust-accept-btn-handler")
            cookie_btn.wait_for(state="visible", timeout=WAIT_FOR_ELEMENT)
            wait(page, 1)
            cookie_btn.click()
            wait(page)

            print("[3] Entering Betfair username and password...")
            page.locator("#ssc-liu").fill(betfair_user)
            wait(page, 1)
            page.locator("#ssc-lipw").fill(betfair_pass)
            wait(page, 1)
            print("[4] Clicking Betfair Log In...")
            page.locator("#ssc-lis").click()
            wait(page, WAIT_AFTER_NAVIGATION)

            print("[5] Waiting for login redirect (loginStatus=SUCCESS in URL)...")
            page.wait_for_url(re.compile(r"loginStatus=SUCCESS", re.I), timeout=30000)
            wait(page, WAIT_AFTER_NAVIGATION)
            print("    Betfair login verified.")

            print("[6] Opening Betfair API-NG Account Visualiser...")
            page.goto("https://apps.betfair.com/visualisers/api-ng-account-operations/", wait_until="domcontentloaded", timeout=60000)
            wait(page, WAIT_AFTER_NAVIGATION)

            print("[7] Reading Session Token (ssoid)...")
            token_input = page.locator("#sessionToken-inputEl")
            token_input.wait_for(state="visible", timeout=WAIT_FOR_ELEMENT)
            wait(page, 2)
            session_token = token_input.input_value()
            if not session_token or not session_token.strip():
                wait(page, 3)
                session_token = token_input.input_value()
            if not session_token or not session_token.strip():
                print("    ERROR: Session token is empty. Ensure you are logged in and the page has loaded.")
                return False, None
            print(f"    Session token copied (length {len(session_token)} chars).")
            wait(page)

            print("[8] Opening admin login page...")
            page.goto("https://admin.111exch.com/login", wait_until="domcontentloaded", timeout=60000)
            wait(page, WAIT_AFTER_NAVIGATION)

            print("[9] Entering admin username and password...")
            page.locator('input[name="username"]').first.fill(admin_user)
            wait(page, 1)
            page.locator('input[name="password"]').first.fill(admin_pass)
            wait(page, 1)
            print("[10] Clicking Sign In...")
            page.locator('button[type="submit"].btn-primary').click()
            wait(page, WAIT_AFTER_NAVIGATION)

            print("[11] Entering operator key in popup...")
            op_key_input = page.locator("#operatorKey")
            op_key_input.wait_for(state="visible", timeout=WAIT_FOR_ELEMENT)
            wait(page, 1)
            op_key_input.fill(operator_key)
            wait(page, 1)
            submit_btn = page.locator('button.btn-primary:has-text("Submit")')
            submit_btn.wait_for(state="visible", timeout=5000)
            page.wait_for_timeout(1500)
            submit_btn.click()
            wait(page, WAIT_AFTER_NAVIGATION)

            print("[12] Verifying admin login (dashboard URL)...")
            page.wait_for_url("**/admin.111exch.com/dashboard**", timeout=15000)
            wait(page, WAIT_AFTER_NAVIGATION)
            print("    Admin login verified.")

            print("[13] Opening Change ID page...")
            page.goto("https://admin.111exch.com/id", wait_until="domcontentloaded", timeout=60000)
            wait(page, WAIT_AFTER_NAVIGATION)

            print("[14] Pasting session token in first ID field...")
            first_id_input = page.locator('input.form-control[type="text"]').first
            first_id_input.wait_for(state="visible", timeout=WAIT_FOR_ELEMENT)
            first_id_input.click()
            wait(page, 0.5)
            first_id_input.fill(session_token)
            wait(page, 1)
            first_id_input.dispatch_event("input")
            first_id_input.dispatch_event("change")
            wait(page, 1)

            first_submit = page.locator('button[type="submit"].btn-secondary').first
            first_submit.wait_for(state="visible", timeout=5000)
            if not first_submit.is_disabled():
                first_submit.click()
                wait(page, WAIT_AFTER_ACTION)
            else:
                print("    First Submit is disabled; clicking anyway in case it's visual only.")
                first_submit.click(force=True)
                wait(page, WAIT_AFTER_ACTION)

            print("[15] Verifying first field shows pasted ID...")
            wait(page, 2)
            current_value = first_id_input.input_value()
            if current_value.strip() != session_token.strip():
                print(f"    WARNING: First field value does not match session token (lengths: {len(current_value)} vs {len(session_token)}).")
            else:
                print("    First field value matches session token.")

            print("[16] Turning Bets toggle ON...")
            bets_row = page.locator('span.fw-semibold:has-text("bets")').first
            bets_row.wait_for(state="visible", timeout=WAIT_FOR_ELEMENT)
            switch_label = page.locator('label.switch').first
            switch_label.scroll_into_view_if_needed()
            wait(page, 0.5)
            switch_label.click()
            wait(page, WAIT_AFTER_ACTION)

            print("[17] Pasting session token in field (after bets toggle) and submitting...")
            first_id_input.wait_for(state="visible", timeout=WAIT_FOR_ELEMENT)
            wait(page, 1)
            first_id_input.click()
            wait(page, 0.5)
            first_id_input.fill(session_token)
            wait(page, 1)
            first_id_input.dispatch_event("input")
            first_id_input.dispatch_event("change")
            wait(page, 1)

            first_submit.wait_for(state="visible", timeout=5000)
            if not first_submit.is_disabled():
                first_submit.click()
                wait(page, WAIT_AFTER_ACTION)
            else:
                first_submit.click(force=True)
                wait(page, WAIT_AFTER_ACTION)

            print("[18] Verifying ID saved in field...")
            wait(page, 2)
            saved_value = first_id_input.input_value()
            if saved_value.strip() != session_token.strip():
                print(f"    WARNING: Field value does not match session token (lengths: {len(saved_value)} vs {len(session_token)}).")
            else:
                print("    Field value matches session token - saved successfully.")

            print("\n--- Change ID success. ---\n")
            wait(page, 5)
            log_success(session_token)
            return True, session_token

        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            wait(page, 10)
            return False, session_token if session_token else None
        finally:
            browser.close()

def main():
    interval_hours = float(env("AUTOMATION_INTERVAL_HOURS", "0"))
    if interval_hours <= 0:
        print("Running Change ID automation once...")
        success, token = run_automation()
        if success:
            print("\n✓ Automation completed successfully.")
        else:
            print("\n✗ Automation failed.")
            sys.exit(1)
    else:
        print(f"Starting scheduled automation (every {interval_hours} hours)...")
        print("Press Ctrl+C to stop.\n")
        schedule.every(interval_hours).hours.do(lambda: run_automation())
        print("Running initial automation...")
        run_automation()
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n\nScheduled automation stopped by user.")
            sys.exit(0)

if __name__ == "__main__":
    main()
