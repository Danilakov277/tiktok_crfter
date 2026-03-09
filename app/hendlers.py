from aiogram import Router,F
from aiogram.types import Message,CallbackQuery
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile

from processing.tiktok_downloader import TikTokDownloader
from processing.image_to_en_text import StaticBlockRemover
from config import Config
import app.keyboards as kb
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

router = Router()
config = Config()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("hello",reply_markup=kb.menu)

@router.callback_query(F.data == "next")
async def next(callback: CallbackQuery):
    downloader = TikTokDownloader(config)
    remover = StaticBlockRemover(gemini_api_key=config.GEMINI_API_KEY)
    profile = "arawaza_intl"
            
    downloaded = downloader.download_from_profile(profile)
    print("ok")
    if downloaded =="":
        return 0
            
    video_path = str(downloaded)
    remover.process_video(
        video_path,
        "refacture/tiktok/cleaned.mp4"
    )
    
            
    
    
    await callback.message.answer_video(FSInputFile("refacture/tiktok/cleaned.mp4"))
    await callback.message.answer("описание",reply_markup=kb.menu)
    

@router.callback_query(F.data == "upload")
async def next(callback: CallbackQuery):
    await callback.answer("upload")