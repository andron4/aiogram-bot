from os import getenv
import asyncio
from aiogram import Dispatcher, Bot
from dotenv import load_dotenv
from handlers.routes import router

load_dotenv()
TOKEN = getenv("BOT_TOKEN")

print("BOT_TOKEN exists:", TOKEN is not None)

dp = Dispatcher()
dp.include_router(router)


async def main():
    bot = Bot(token=TOKEN)

    #asyncio.create_task(notifier(bot))

    print('Start...')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
