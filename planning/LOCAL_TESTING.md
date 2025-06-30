# Local Testing Guide

This guide explains how to test changes to the Telegram bot locally without affecting production.

## Setup

1. **Create a test bot**
   - Message `@BotFather` on Telegram
   - Use `/newbot` to create a test bot
   - Save the API token

2. **Configure environment**
   ```bash
   cp .env .env.test
   # Edit .env.test with test bot token and test database
   ```

## Testing Methods

### Option 1: Polling (Simpler)
1. In `bot.py`, change to:
   ```python
   if __name__ == '__main__':
       application.run_polling()
   ```
2. Run:
   ```bash
   source venv/bin/activate
   env $(cat .env.test | xargs) python bot.py
   ```

### Option 2: Webhooks (Production-like)
1. Start ngrok:
   ```bash
   ngrok http 8000
   ```
2. Set webhook:
   ```bash
   curl -F "url=https://YOUR_NGROK_URL/webhook" \
        https://api.telegram.org/botYOUR_TEST_BOT_TOKEN/setWebhook
   ```
3. Run the bot normally

## Testing Workflow

1. Make changes locally
2. Test with your test bot
3. Verify functionality
4. Push to production when ready

## Notes
- Use a separate test database
- Your test bot will have a different username
- Webhooks provide more realistic testing
