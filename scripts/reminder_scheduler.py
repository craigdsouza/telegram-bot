import os
import psycopg2
import pytz
from datetime import datetime, timedelta, time as dt_time
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot
from dotenv import load_dotenv
import logging
import re
import asyncio

# Enable logging
logging.basicConfig(
    filename='bot.log',
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Send logs to console as well
def _enable_console_logging():
    console_handler = logging.StreamHandler() # send logs to console
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

_enable_console_logging()

load_dotenv()
try:
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    # print("Bot initialized")
except Exception as e:
    logger.error(f"Failed to initialize bot: {e}")
    # print(f"Failed to initialize bot: {e}")
    raise e


def get_db_connection():
    url = os.getenv("DATABASE_PUBLIC_URL")
    return psycopg2.connect(url)

def fetch_reminder_users():
    conn = get_db_connection()
    with conn, conn.cursor() as cur:
        cur.execute("""
            SELECT telegram_user_id, reminder_time, reminder_timezone
            FROM users
            WHERE reminder_time IS NOT NULL AND reminder_timezone IS NOT NULL
        """)
        logger.info(f"Fetched {cur.rowcount} reminders for users")
        # print(f"Fetched {cur.rowcount} reminders for users")
        return cur.fetchall()

def send_reminder(telegram_user_id):
    async def send():
        try:
            await bot.send_message(chat_id=telegram_user_id, text="⏰ Don't forget to enter your expenses for today!")
            logger.info(f"Sent reminder to {telegram_user_id}")
            # print(f"Sent reminder to {telegram_user_id}")
        except Exception as e:
            logger.error(f"Failed to send reminder to {telegram_user_id}: {e}")
            # print(f"Failed to send reminder to {telegram_user_id}: {e}")
    asyncio.run(send())

def schedule_all_reminders(scheduler):
    logger.info("Scheduling all reminders")
    # print("Scheduling all reminders")
    users = fetch_reminder_users()
    now_utc = datetime.now(pytz.utc).replace(second=0, microsecond=0)
    # print(f"Now UTC: {now_utc}")
    for telegram_user_id, reminder_time, reminder_timezone in users:
        # Parse time and timezone
        if isinstance(reminder_time, str):
            reminder_time = dt_time.fromisoformat(reminder_time)
        try:
            tz = pytz.timezone(reminder_timezone)
            # print(f"Timezone: {tz}")
        except Exception:
            # fallback to UTC offset if tz name fails
            if reminder_timezone.startswith(('+', '-')):
                offset_minutes = parse_utc_offset(reminder_timezone)
                tz = pytz.FixedOffset(offset_minutes)
                # print(f"Fallback timezone: {tz}")
            else:
                raise
        # Next reminder datetime in user's local time
        now_local = datetime.now(tz)
        # print(f"Now local: {now_local}")
        next_reminder_local = now_local.replace(hour=reminder_time.hour, minute=reminder_time.minute, second=0, microsecond=0)
        # print(f"Next reminder local: {next_reminder_local}")
        if next_reminder_local < now_local:
            next_reminder_local += timedelta(days=1)
        # print(f"Next reminder local: {next_reminder_local}")
        # Convert to UTC
        next_reminder_utc = next_reminder_local.astimezone(pytz.utc)
        # print(f"Next reminder UTC: {next_reminder_utc}")
        # Schedule the job
        scheduler.add_job(
            send_reminder,
            'date',
            run_date=next_reminder_utc,
            args=[telegram_user_id],
            id=f"reminder_{telegram_user_id}",
            replace_existing=True
        )
        logger.info(f"Scheduled reminder for {telegram_user_id} at {next_reminder_utc} UTC")
        # print(f"Scheduled reminder for {telegram_user_id} at {next_reminder_utc} UTC")

def parse_utc_offset(offset_str):
    # offset_str: "+05:30" or "-04:00"
    match = re.match(r'^([+-])(\d{2}):(\d{2})$', offset_str)
    if not match:
        raise ValueError("Invalid UTC offset format")
    sign, hours, minutes = match.groups()
    total_minutes = int(hours) * 60 + int(minutes)
    if sign == '-':
        total_minutes = -total_minutes
    return total_minutes

if __name__ == "__main__":
    logger.info("Starting reminder scheduler")
    # print("Starting reminder scheduler")
    scheduler = BackgroundScheduler()
    scheduler.start()
    # Schedule all reminders now, and then every hour to catch updates
    schedule_all_reminders(scheduler)
    from time import sleep
    while True:
        sleep(3600)
