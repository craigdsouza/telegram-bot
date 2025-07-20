import subprocess
import time
import threading
from scripts.reminder_scheduler import start_reminder_scheduler

def run_bot():
    subprocess.Popen(["python", "bot.py"])

def run_export():
    subprocess.run(["python","-m","integrations.sync_google_sheet"])

def run_reminder_scheduler():
    # Start reminder scheduler in a separate thread instead of subprocess, what does this mean?
    reminder_thread = threading.Thread(target=start_reminder_scheduler, daemon=True)
    reminder_thread.start()
    print("Reminder scheduler started in thread")

if __name__ == "__main__":
    run_bot()  # Start the bot
    run_reminder_scheduler()

    while True:
        run_export()  # Run the export script
        time.sleep(300)  # Wait 5 minutes (300 seconds)