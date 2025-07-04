import subprocess
import time

def run_bot():
    subprocess.Popen(["python", "bot.py"])

def run_export():
    subprocess.run(["python","-m","integrations.sync_google_sheet"])

def run_reminder_scheduler():
    subprocess.run(["python", "-m", "scripts.reminder_scheduler"])

if __name__ == "__main__":
    run_bot()  # Start the bot

    while True:
        run_export()  # Run the export script
        run_reminder_scheduler()
        time.sleep(300)  # Wait 5 minutes (300 seconds)