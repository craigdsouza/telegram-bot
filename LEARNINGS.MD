# Bot Development Learnings

## Reminder System Debugging: Threads vs Subprocesses and Multiple Bot Instances

### Problem Statement
The reminder system was not working on Railway despite the reminder handler successfully setting reminder times. Users could set reminders and see "Reminder set for 21:00 daily for user {telegram_user_id}" in logs, but no actual reminder messages were being sent. Railway logs showed no mention of "Starting reminder scheduler", "Scheduling all reminders", or "Fetched X reminders for users", indicating the reminder scheduler process was not running at all.

Additionally, after fixing the reminder system, new errors emerged: "Conflict: terminated by other getUpdates request; make sure that only one bot instance is running". This indicated multiple bot instances were running simultaneously, causing conflicts in Telegram's update polling mechanism.

### Root Cause Analysis
1. **Database Schema Issue**: The reminder scheduler query required BOTH `reminder_time` AND `reminder_timezone` to be set:
   ```sql
   WHERE reminder_time IS NOT NULL AND reminder_timezone IS NOT NULL
   ```
   However, the reminder handler was only setting `reminder_time`, leaving `reminder_timezone` as NULL.

2. **Process Management Issue**: The original scheduler used subprocess to start the reminder scheduler:
   ```python
   def run_reminder_scheduler():
       subprocess.Popen(["python", "-m", "scripts.reminder_scheduler"])
   ```
   This subprocess approach was not working properly on Railway's containerized environment.

3. **Multiple Bot Instances Issue**: The deployment setup was causing multiple bot instances to run:
   - **Procfile** specified `worker: python scheduler.py`
   - **scheduler.py** started the bot with `subprocess.Popen(["python", "bot.py"])`
   - This created a subprocess bot instance within the main scheduler process
   - Railway might also be running `bot.py` directly in some cases
   - Result: Multiple bot instances polling Telegram simultaneously

### Hypothesis
The subprocess approach fails on Railway because:
- Railway's container environment may not properly handle subprocess spawning
- Subprocesses may not have access to the same environment variables or file system
- The main process may not be monitoring subprocess health
- Railway's process management may kill subprocesses that appear orphaned

Using threading instead of subprocess should work better because:
- Threads run within the same process and share the same environment
- Railway can monitor the main process and all its threads
- No inter-process communication issues
- Better integration with Railway's container lifecycle

### Solution Implemented
1. **Fixed Database Schema**: 
   - Created migration to add `reminder_timezone` column
   - Updated reminder handler to set both `reminder_time` and `reminder_timezone`
   - Created script to fix existing reminders by setting timezone to '+05:30'

2. **Changed Process Management**:
   - Replaced subprocess with threading approach
   - Modified scheduler to use `threading.Thread(target=start_reminder_scheduler, daemon=True)`
   - Exposed `start_reminder_scheduler()` function from reminder_scheduler.py

3. **Consolidated to Single Process**:
   - Moved reminder scheduler into main bot process using threading
   - Moved Google Sheets sync into main bot process using threading
   - Updated Procfile to run `bot.py` directly instead of `scheduler.py`
   - Eliminated subprocess approach entirely

4. **Enhanced Logging**:
   - Added more detailed logging to track scheduler startup and user discovery
   - Added logging for number of users found with reminders

### Technical Details: Threads vs Subprocesses

#### Subprocess Approach (Original)
```python
subprocess.Popen(["python", "-m", "scripts.reminder_scheduler"])
```
- **Pros**: Complete process isolation, can restart independently
- **Cons**: 
  - Separate process with its own memory space
  - Environment variables may not be inherited
  - Inter-process communication complexity
  - Platform-specific process management issues
  - Railway may not properly monitor subprocesses

#### Threading Approach (New)
```python
reminder_thread = threading.Thread(target=start_reminder_scheduler, daemon=True)
reminder_thread.start()
```
- **Pros**: 
  - Same process, shared memory and environment
  - Railway monitors the main process
  - No inter-process communication overhead
  - Better integration with containerized environments
- **Cons**: 
  - Single point of failure (if main process crashes, all threads stop)
  - Shared memory can lead to race conditions (mitigated by using daemon threads)

### Learning
**Hypothesis Confirmed**: The threading approach successfully resolved the reminder scheduler issue on Railway. The scheduler is now running and sending reminders as expected.

**Additional Finding**: A new issue emerged with AsyncLock compatibility between python-telegram-bot and anyio libraries. This was resolved by creating a new event loop for each reminder instead of using `asyncio.run()`.

**Key Insights**:
1. **Threading vs Subprocess**: Threading is indeed more reliable for Railway deployments
2. **Async Event Loops**: When using async operations in threaded environments, create new event loops to avoid conflicts
3. **Library Version Conflicts**: python-telegram-bot 20.4 can have compatibility issues with certain anyio versions

### Key Takeaways
1. **Always check database schema requirements** - The scheduler query revealed a missing column requirement
2. **Platform-specific considerations** - What works locally may not work in containerized environments
3. **Process vs Thread choice** - For Railway/deployment environments, threading is often more reliable than subprocess
4. **Comprehensive logging** - Detailed logs are crucial for debugging deployment issues
5. **Database migrations** - Always create proper migrations for schema changes
6. **Single process deployment** - Avoid multiple bot instances by consolidating all functionality into one process
7. **Procfile configuration** - Ensure only one entry point is specified to prevent duplicate bot instances

### Testing Checklist
- [x] Deploy changes to Railway
- [x] Check Railway logs for "Starting reminder scheduler"
- [x] Check Railway logs for "Found X users with reminders set"
- [x] Set a test reminder for near future
- [x] Verify reminder message is sent
- [x] Monitor logs for any errors or issues
- [x] Fix AsyncLock compatibility issue with new event loops
