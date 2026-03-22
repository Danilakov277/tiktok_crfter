
import sys
from pathlib import Path
import time
import asyncio

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent))

from config import Config







from aiogram import Bot, Dispatcher, types
import os
from app.hendlers import router



async def main():
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    dp =Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
        asyncio.run(main())

    

