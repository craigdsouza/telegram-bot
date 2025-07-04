import subprocess
import time

def run_bot():
    subprocess.Popen(["python", "bot.py"])

def run_export():
    subprocess.run(["python","-m","integrations.sync_google_sheet"])

def run_reminder_scheduler():
    subprocess.Popen(["python", "-m", "scripts.reminder_scheduler"])

if __name__ == "__main__":
    run_bot()  # Start the bot
    run_reminder_scheduler()

    while True:
        run_export()  # Run the export script
        time.sleep(300)  # Wait 5 minutes (300 seconds)