import time
import csv
import os
import subprocess
from datetime import datetime

# --- CONFIG ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_FILE = os.path.join(DATA_DIR, "mac_activity_log.csv")
POLL_INTERVAL = 5

# Set your session limit here
SESSION_DURATION_HOURS = 3
SESSION_LIMIT_SECONDS = SESSION_DURATION_HOURS * 3600

def get_active_window_applescript():
    """
    Uses AppleScript to ask macOS strictly who is in front.
    This is slower but more reliable on M3 Macs.
    """
    script = '''
    global frontApp, frontAppName, windowTitle
    
    tell application "System Events"
        set frontApp to first application process whose frontmost is true
        set frontAppName to name of frontApp
        
        try
            tell process frontAppName
                set windowTitle to name of front window
            end tell
        on error
            set windowTitle to ""
        end try
    end tell
    
    return frontAppName & "|||" & windowTitle
    '''

    try:
        result = subprocess.check_output(['osascript', '-e', script], stderr=subprocess.STDOUT)
        result = result.decode('utf-8').strip()
        
        if "|||" in result:
            app_name, window_title = result.split("|||", 1)
            return app_name, window_title
        else:
            return result, "Unknown"
            
    except Exception as e:
        return "VS Code", "Active (Script Error)"

def send_notification(message, title="Data Science Project"):
    """Sends a native macOS notification"""
    try:
        # Plays the 'Glass' sound and shows a banner
        cmd = f'display notification "{message}" with title "{title}" sound name "Glass"'
        subprocess.call(["osascript", "-e", cmd])
    except Exception as e:
        print(f"⚠️ Notification failed: {e}")

def log_activity():
    # Initialize CSV with header if missing
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "app_name", "window_title"])

    print(f"⚡ AppleScript Tracker running for {SESSION_DURATION_HOURS} hours...")
    print(f"   Saving to: {LOG_FILE}")
    print("   (Minimize this window. I will notify you when time is up.)")
    
    start_time = time.time()
    
    try:
        while True:
            # 1. CHECK TIMER
            elapsed_seconds = time.time() - start_time
            if elapsed_seconds > SESSION_LIMIT_SECONDS:
                print("\n⏰ 3 HOURS REACHED! Session Complete.")
                send_notification("3 Hours Complete! Observation finished.", "Tracker Finished")
                break

            # 2. LOG ACTIVITY
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            app, title = get_active_window_applescript()
            
            if app:
                with open(LOG_FILE, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, app, title])
                # print(f"[{timestamp}] {app} - {title}") # Commented out to keep terminal clean
            
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopped manually.")

if __name__ == "__main__":
    log_activity()