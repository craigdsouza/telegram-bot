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

# Try different import paths for Request class based on python-telegram-bot version
try:
    from telegram.request import Request
except ImportError:
    try:
        from telegram.request._httpxrequest import HTTPXRequest as Request
    except ImportError:
        # Fallback to basic bot initialization without custom request settings
        Request = None

# Get logger - don't set up logging here since we're running as a thread
# The main bot process already configures logging
logger = logging.getLogger(__name__)

# Cache to track last scheduled reminder times for each user
# Format: {telegram_user_id: (reminder_time, reminder_timezone, next_scheduled_time)}
reminder_cache = {}

load_dotenv()
try:
    if Request is not None:
        # Configure bot with larger connection pool and timeouts
        bot = Bot(
            token=os.getenv("TELEGRAM_BOT_TOKEN"),
            request=Request(
                connection_pool_size=20,  # Increase pool size
                connect_timeout=30.0,
                read_timeout=30.0,
                write_timeout=30.0,
                pool_timeout=60.0  # Increase pool timeout
            )
        )
        logger.info("Bot initialized with enhanced connection pool settings")
    else:
        # Fallback to basic bot initialization
        bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
        logger.info("Bot initialized with default settings (Request import not available)")
except Exception as e:
    logger.error(f"Failed to initialize bot: {e}")
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
        logger.debug(f"[DB_FETCH] Retrieved {cur.rowcount} users with reminders")
        return cur.fetchall()

def send_reminder(telegram_user_id):
    async def send():
        try:
            await bot.send_message(chat_id=telegram_user_id, text="⏰ Don't forget to enter your expenses for today!")
            logger.info(f"[REMINDER_SENT] User {telegram_user_id}")
        except Exception as e:
            logger.error(f"[REMINDER_FAILED] User {telegram_user_id} - Error: {e}")
            # Don't re-raise to avoid crashing the scheduler
    
    # Create a new event loop for each reminder to avoid AsyncLock issues
    loop = None
    try:
        # Check if there's already an event loop running
        try:
            loop = asyncio.get_running_loop()
            # If we get here, there's already a loop running
            logger.warning(f"[REMINDER_WARNING] User {telegram_user_id} - Event loop already running, using existing loop")
            asyncio.create_task(send())
        except RuntimeError:
            # No event loop running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send())
    except Exception as e:
        logger.error(f"[REMINDER_FAILED] User {telegram_user_id} - Event loop error: {e}")
    finally:
        # Only close the loop if we created it
        if loop and not loop.is_running():
            try:
                loop.close()
            except Exception as e:
                logger.warning(f"[REMINDER_WARNING] User {telegram_user_id} - Failed to close event loop: {e}")

def cleanup_cache_for_user(telegram_user_id):
    """Remove a user from the cache when their reminder is disabled or user is deleted."""
    if telegram_user_id in reminder_cache:
        del reminder_cache[telegram_user_id]
        logger.info(f"[CACHE_CLEARED] User {telegram_user_id}")

def schedule_all_reminders(scheduler):
    logger.info("[SCHEDULER_START] Processing reminders")
    users = fetch_reminder_users()
    logger.info(f"[SCHEDULER_INFO] Found {len(users)} users with reminders set")
    
    # Get current user IDs to clean up cache
    current_user_ids = {user[0] for user in users}
    
    # Clean up cache for users who no longer have reminders
    for cached_user_id in list(reminder_cache.keys()):
        if cached_user_id not in current_user_ids:
            cleanup_cache_for_user(cached_user_id)
    
    scheduled_count = 0
    skipped_count = 0
    scheduled_users = []
    skipped_users = []
    
    for telegram_user_id, reminder_time, reminder_timezone in users:
        # Parse time and timezone
        if isinstance(reminder_time, str):
            reminder_time = dt_time.fromisoformat(reminder_time)
        try:
            tz = pytz.timezone(reminder_timezone)
        except Exception:
            # fallback to UTC offset if tz name fails
            if reminder_timezone.startswith(('+', '-')):
                offset_minutes = parse_utc_offset(reminder_timezone)
                tz = pytz.FixedOffset(offset_minutes)
            else:
                raise
        
        # Calculate next reminder datetime in user's local time
        now_local = datetime.now(tz)
        next_reminder_local = now_local.replace(hour=reminder_time.hour, minute=reminder_time.minute, second=0, microsecond=0)
        if next_reminder_local < now_local:
            next_reminder_local += timedelta(days=1)
        
        # Convert to UTC for scheduling
        next_reminder_utc = next_reminder_local.astimezone(pytz.utc)
        
        # Check if we need to re-schedule this reminder
        cache_key = telegram_user_id
        cached_data = reminder_cache.get(cache_key)
        
        should_schedule = False
        reason = ""
        
        if cached_data is None:
            # First time scheduling for this user
            should_schedule = True
            reason = "new user"
        else:
            cached_time, cached_timezone, cached_next_scheduled = cached_data
            
            # Check if reminder time or timezone changed
            if (reminder_time != cached_time or reminder_timezone != cached_timezone):
                should_schedule = True
                reason = "settings changed"
            # Check if the scheduled time has passed (within 5 minutes tolerance)
            elif abs((next_reminder_utc - cached_next_scheduled).total_seconds()) > 300:  # 5 minutes
                should_schedule = True
                reason = "time advanced"
        
        if should_schedule:
            # Schedule the job
            scheduler.add_job(
                send_reminder,
                'date',
                run_date=next_reminder_utc,
                args=[telegram_user_id],
                id=f"reminder_{telegram_user_id}",
                replace_existing=True
            )
            
            # Update cache
            reminder_cache[cache_key] = (reminder_time, reminder_timezone, next_reminder_utc)
            
            logger.info(f"[REMINDER_SCHEDULED] User {telegram_user_id} at {next_reminder_local.strftime('%Y-%m-%d %H:%M:%S')} ({reason})")
            scheduled_count += 1
            scheduled_users.append(telegram_user_id)
        else:
            skipped_count += 1
            skipped_users.append(telegram_user_id)
    
    # Log summary with details only if there are scheduled reminders
    if scheduled_count > 0:
        logger.info(f"[SCHEDULER_COMPLETE] {scheduled_count} scheduled, {skipped_count} skipped")
        if skipped_count > 0:
            logger.debug(f"[SCHEDULER_DETAILS] Skipped users: {', '.join(map(str, skipped_users))}")
    else:
        # Only log if no reminders were scheduled (quieter)
        logger.debug(f"[SCHEDULER_COMPLETE] {scheduled_count} scheduled, {skipped_count} skipped (no changes)")

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

def start_reminder_scheduler():
    """Start the reminder scheduler in a separate thread."""
    logger.info("[SCHEDULER_INIT] Starting reminder scheduler")
    try:
        scheduler = BackgroundScheduler()
        scheduler.start()
        logger.info("[SCHEDULER_INIT] Background scheduler started successfully")
        
        # Schedule all reminders now, and then every hour to catch updates
        schedule_all_reminders(scheduler)
        logger.info("[SCHEDULER_INIT] Initial reminder scheduling completed")
        
        from time import sleep
        while True:
            try:
                sleep(3600)  # Sleep for 1 hour
                logger.info("[SCHEDULER_HOURLY] Running hourly reminder check")
                schedule_all_reminders(scheduler)  # Re-schedule to catch new/changed reminders
            except Exception as e:
                logger.error(f"[SCHEDULER_ERROR] Error in hourly reminder check: {e}")
                # Continue running despite errors
                sleep(60)  # Wait 1 minute before continuing
    except Exception as e:
        logger.error(f"[SCHEDULER_CRITICAL] Critical error in reminder scheduler: {e}")
        raise

if __name__ == "__main__":
    start_reminder_scheduler()
