import asyncio
import os
from aiogram import Bot
from dotenv import load_dotenv

async def check_bot():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        return
    
    print(f"Checking bot with token (start): {token[:10]}...")
    bot = Bot(token=token)
    try:
        me = await bot.get_me()
        print(f"✅ Connection successful!")
        print(f"🤖 Bot Name: {me.first_name}")
        print(f"🤖 Bot Username: @{me.username}")
        print(f"🤖 Bot ID: {me.id}")
        
        # Check if another polling session is active
        webhook = await bot.get_webhook_info()
        if webhook.url:
            print(f"⚠️ Bot has a webhook set: {webhook.url}")
        else:
            print("✅ No active webhook (good for polling)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(check_bot())
