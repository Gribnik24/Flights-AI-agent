from os import getenv
from dotenv import load_dotenv
import asyncio
from aiogram import Bot, Dispatcher

from handlers.routes import router

load_dotenv()

BOT_TOKEN = getenv('BOT_TOKEN')

dp = Dispatcher()
dp.include_router(router)

async def main():
    bot = Bot(token=BOT_TOKEN,)
    print("Бот запущен и ждет запросов...")
    await dp.start_polling(bot, timeout=30)

if __name__ == '__main__':
    asyncio.run(main())