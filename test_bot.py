from telethon import TelegramClient, events
import asyncio

API_ID = 21124241
API_HASH = "b7ddce3d3683f54be788fddae73fa468"
BOT_TOKEN = "8457573508:AAHTXv1eMFpZhK7cYj54CGBIeBCZTS-K1og"

client = TelegramClient('test_bot', API_ID, API_HASH)

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply("✅ Bot is working! Token is valid!")
    print(f"Received /start from user {event.sender_id}")

async def main():
    print("Starting bot...")
    await client.start(bot_token=BOT_TOKEN)
    print("Bot started successfully!")
    print(f"Bot username: {(await client.get_me()).username}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
