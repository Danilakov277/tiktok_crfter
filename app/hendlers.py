from aiogram import Router,F
from aiogram.types import Message,CallbackQuery
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile

from processing.tiktok_downloader import TikTokDownloader
from processing.image_to_en_text import StaticBlockRemover
from config import Config
import app.keyboards as kb
from avtoposting.awto_tiktok import tiktok_upload


router = Router()
config = Config()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("hello",reply_markup=kb.menu)

@router.callback_query(F.data == "next")
async def next_handler(callback: CallbackQuery):
    # 1. ОТВЕЧАЕМ СРАЗУ, чтобы убрать "часики" и избежать тайм-аута
    await callback.answer("Начинаю обработку видео...")
    
    # 2. Отправляем сообщение-статус, чтобы юзер не скучал
    status_msg = await callback.message.answer("⏳ Скачиваю и обрабатываю видео, подождите...")

    try:
        downloader = TikTokDownloader(config)
        remover = StaticBlockRemover(gemini_api_key=config.GEMINI_API_KEY)
        profile = "arawaza_intl"
                
        downloaded = downloader.download_from_profile(profile)
        
        if not downloaded:
            await status_msg.edit_text("❌ Новых видео не найдено.")
            return 
                
        video_path = str(downloaded)
        description_path = video_path.replace(".mp4", ".description")
        
        # 3. Обработка (может занять время)
        output_video = "refacture/tiktok/cleaned.mp4"
        remover.process_video(video_path, output_video)
        
        description_text = remover.translate_description_from_file(description_path)
        
        # 4. Отправляем результат
        await callback.message.answer_video(
            FSInputFile(output_video),
            caption=description_text or "Готово!",
            reply_markup=kb.menu
        )
        
        # Удаляем временное сообщение о загрузке
        await status_msg.delete()

    except Exception as e:
        print(f"Ошибка в процессе: {e}")
        await status_msg.edit_text("⚠️ Произошла ошибка при обработке видео.",reply_markup=kb.menu)
    

@router.callback_query(F.data == "upload")
async def next(callback: CallbackQuery):
# 1. ОТВЕЧАЕМ СРАЗУ, чтобы убрать "часики" и избежать тайм-аута
    await callback.answer("Начинаю выкладывать видео...")
            
    # 2. Отправляем сообщение-статус, чтобы юзер не скучал
    status_msg = await callback.message.answer("⏳ выкладываю видео, подождите...")

    try:
        output_video = "refacture/tiktok/cleaned.mp4"
        tiktok_upload(output_video)

        # 4. Отправляем результат
        await callback.message.answer(  
            text="✅ Видео успешно опубликовано в TikTok!",
            reply_markup=kb.menu
        )
                
                # Удаляем временное сообщение о загрузке
        await status_msg.delete()

    except Exception as e:
        print(f"Ошибка в процессе: {e}")
        await status_msg.edit_text("⚠️ Произошла ошибка.",reply_markup=kb.menu)