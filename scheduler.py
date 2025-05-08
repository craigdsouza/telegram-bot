import subprocess
import time

def run_bot():
    subprocess.Popen(["python", "bot.py"])

def run_export():
    subprocess.run(["python", "export_to_sheets.py"])

if __name__ == "__main__":
    run_bot()  # Start the bot

    while True:
        run_export()  # Run the export script
        time.sleep(300)  # Wait 5 minutes (300 seconds)