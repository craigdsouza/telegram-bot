# Bot Development Learnings

## Problem 1: Reminder System Not Working on Railway

### Problem Statement
The reminder system was not working on Railway despite the reminder handler successfully setting reminder times. Users could set reminders and see "Reminder set for 21:00 daily for user {telegram_user_id}" in logs, but no actual reminder messages were being sent. Railway logs showed no mention of "Starting reminder scheduler", "Scheduling all reminders", or "Fetched X reminders for users", indicating the reminder scheduler process was not running at all.

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
1. **Changed Process Management**:
   - Replaced subprocess with threading approach
   - Modified scheduler to use `threading.Thread(target=start_reminder_scheduler, daemon=True)`
   - Exposed `start_reminder_scheduler()` function from reminder_scheduler.py

2. **Enhanced Logging**:
   - Added more detailed logging to track scheduler startup and user discovery
   - Added logging for number of users found with reminders

### Learning
**Hypothesis Confirmed**: The threading approach successfully resolved the reminder scheduler issue on Railway. The scheduler is now running and sending reminders as expected.

**Key Insight**: Threading is indeed more reliable for Railway deployments than subprocess approaches.

**Note**: The exact root cause of why the subprocess approach failed remains unclear. While threading solved the issue, it's possible there were other factors involved that weren't captured in the logs.

---

## Problem 2: Database Schema Mismatch for Reminders

### Problem Statement
The reminder scheduler query required BOTH `reminder_time` AND `reminder_timezone` to be set:
```sql
WHERE reminder_time IS NOT NULL AND reminder_timezone IS NOT NULL
```
However, the reminder handler was only setting `reminder_time`, leaving `reminder_timezone` as NULL. This meant no users were ever found by the scheduler, even though reminders were being set.

### Hypothesis
The scheduler was not finding any users because the database schema requirements were not met. Adding the missing `reminder_timezone` column and updating the handler to set both fields should resolve this issue.

### Solution Implemented
1. **Fixed Database Schema**: 
   - Created migration to add `reminder_timezone` column
   - Updated reminder handler to set both `reminder_time` and `reminder_timezone`
   - Created script to fix existing reminders by setting timezone to '+05:30'

### Learning
**Hypothesis Confirmed**: Adding the missing `reminder_timezone` column and updating the handler resolved the issue. The scheduler now finds users with reminders set.

**Key Insight**: Always check database schema requirements - the scheduler query revealed a missing column requirement.

---

## Problem 3: AsyncLock Compatibility Issues

### Problem Statement
After fixing the reminder system, new errors emerged: `AttributeError("'AsyncLock' object has no attribute '_anyio_lock'")` when sending reminders. This indicated compatibility issues between python-telegram-bot and anyio libraries.

### Hypothesis
The AsyncLock compatibility issue occurs because of version conflicts between python-telegram-bot 20.4 and certain anyio versions. Creating a new event loop for each reminder instead of using `asyncio.run()` should resolve this.

### Solution Implemented
- Modified reminder scheduler to create a new event loop for each reminder
- Replaced `asyncio.run(send())` with explicit event loop management
- Added proper error handling and cleanup for event loops

### Learning
**Hypothesis Yet to be Confirmed**: 

**Key Insight**: 

---

## Problem 4: Railway Deployment Conflicts During Updates

### Problem Statement
After fixing the reminder system, new errors emerged: "Conflict: terminated by other getUpdates request; make sure that only one bot instance is running". This indicated multiple bot instances were running simultaneously, causing conflicts in Telegram's update polling mechanism. These conflicts only occurred during deployment updates, not during normal operation.

### Hypothesis
The conflict errors occur during Railway deployment updates when:
- A new deployment starts while the old deployment is still running
- Both bot instances poll Telegram simultaneously for a brief period
- Railway's deployment process allows overlap between old and new instances
- The UUID logging shows different instance IDs during these conflict periods

### Solution Implemented
1. **Enhanced Error Handler**: 
   - Added specific error handler for conflict errors
   - Changed conflict errors from ERROR to WARNING level
   - Prevented conflicts from causing bot crashes
   - Added instance ID logging to track which instance is running

2. **Better Polling Settings**:
   - Added timeouts to make polling more stable
   - Used more resilient polling configuration

### Learning
**Hypothesis Confirmed**: The "Conflict: terminated by other getUpdates request" error occurs during Railway deployment updates when old and new bot instances overlap briefly. This is a normal part of Railway's deployment process, not a code issue.

**Key Insights**:
1. **Deployment Overlap**: Railway allows brief overlap between old and new deployments during updates
2. **Error Resilience**: Bots should handle conflicts gracefully during deployment transitions
3. **Instance Tracking**: UUID logging helps identify when multiple instances are running during deployments

---

## Technical Details: Threads vs Subprocesses

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

#### Hybrid Approach (Current Implementation)
```python
# Reminder Scheduler: Pure Threading
reminder_thread = threading.Thread(target=start_reminder_scheduler, daemon=True)

# Google Sheets Sync: Thread + Subprocess
def run_google_sheets_sync():
    while True:
        subprocess.run(["python", "-m", "integrations.sync_google_sheet"], check=True)
        time.sleep(300)
sync_thread = threading.Thread(target=run_google_sheets_sync, daemon=True)
```

**Reminder Scheduler (Pure Threading):**
- **Why**: Needs shared bot instance, frequent operations (hourly), simple logic
- **Benefits**: Low overhead, shared state, Railway-friendly

**Google Sheets Sync (Thread + Subprocess):**
- **Why**: External dependencies, infrequent operations (5 min), isolation needs
- **Benefits**: Thread manages loop, subprocess provides isolation, automatic restart capability

---

## Key Takeaways
1. **Always check database schema requirements** - The scheduler query revealed a missing column requirement
2. **Platform-specific considerations** - What works locally may not work in containerized environments
3. **Process vs Thread choice** - For Railway/deployment environments, threading is often more reliable than subprocess
4. **Comprehensive logging** - Detailed logs are crucial for debugging deployment issues
5. **Database migrations** - Always create proper migrations for schema changes
6. **Single process deployment** - Avoid multiple bot instances by consolidating all functionality into one process
7. **Procfile configuration** - Ensure only one entry point is specified to prevent duplicate bot instances
8. **Error resilience** - Handle infrastructure conflicts gracefully rather than trying to prevent them

---

## Testing Checklist
- [x] Deploy changes to Railway
- [x] Check Railway logs for "Starting reminder scheduler"
- [x] Check Railway logs for "Found X users with reminders set"
- [x] Set a test reminder for near future
- [x] Verify reminder message is sent
- [x] Monitor logs for any errors or issues
- [x] Fix AsyncLock compatibility issue with new event loops
- [x] Handle Railway infrastructure conflicts gracefully
