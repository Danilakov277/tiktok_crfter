
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


"""
def main():
    config = Config()
    asyncio.run(telegram_bot())
    while True:
        print("\n" + "="*50)
        print("📋 Главное меню:")
        print("  1. 📸 Скачать из Instagram")
        print("  2. 🎵 Скачать из TikTok")
        print("  3. 🚪 Выйти")
        print("  4. 🚪 obrabotat")
        
        choice = input("\n👉 Выбери платформу (1-3): ").strip()
        
        if choice == "1":
            pass
        elif choice == "2":
            # скачать 
            # обработать 
            # удалить 
            
            downloader = TikTokDownloader(config)
            remover = StaticBlockRemover(gemini_api_key=config.GEMINI_API_KEY)
            profile = "arawaza_intl"
            
            if profile:
                downloaded = downloader.download_from_profile(profile)
                
                if downloaded =="":
                    return 0
            

            remover.process_video(
                downloaded,
                "refacture/tiktok/cleaned.mp4"
            )
            
            image_path = "refacture/tiktok/cleaned_cropped.jpg"
            text = remover.extract_text_from_image(image_path)

            print("\n✅ Итоговый текст в переменной:")
            print(text)


        elif choice == "3":
            print("\n👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор. Попробуй снова.")
        
        
        print("\n" + "="*50)
"""

async def main():
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    dp =Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
        asyncio.run(main())

    

