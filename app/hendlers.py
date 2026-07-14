from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from processing.tiktok_downloader import TikTokDownloader
from processing.image_to_en_text import StaticBlockRemover
from config import Config
import app.keyboards as kb
import os
import asyncio
from avtoposting.awto_tiktok import tiktok_upload
from avtoposting.awto_instagram import instagram_upload
import functools

router = Router()
config = Config()

# Пути к файлам (вынесем в константы для удобства)
VIDEO_PATH = "refacture/tiktok/cleaned.mp4"
CAPTION_PATH = "refacture/tiktok/cleaned.txt"

@router.callback_query(F.data == "next")
async def next_handler(callback: CallbackQuery):
    await callback.answer("Начинаю обработку видео...")
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
        
        # Очистка видео
        remover.process_video(video_path, VIDEO_PATH)
        
        # --- ШАГ 1: Получаем текст и СОХРАНЯЕМ его ---
        description_text = remover.translate_description_from_file(description_path)
        final_caption = description_text or "Check this out! 🚀"
        
        with open(CAPTION_PATH, "w", encoding="utf-8") as f:
            f.write(final_caption)
        
        print(f"[DEBUG] Описание сохранено в файл: {final_caption}")

        # Отправляем видео пользователю для проверки
        await callback.message.answer_video(
            FSInputFile(VIDEO_PATH),
            caption=f"Текст для публикации:\n\n{final_caption}",
            reply_markup=kb.menu
        )
        await status_msg.delete()

    except Exception as e:
        print(f"Ошибка в обработке: {e}")
        await status_msg.edit_text(f"⚠️ Ошибка при обработке: {e}", reply_markup=kb.menu)


@router.callback_query(F.data == "upload")
async def upload_callback_handler(callback: CallbackQuery):
    await callback.answer("Запускаю Selenium...")
    status_msg = await callback.message.answer("⏳ Публикация в процессе, это займет около 1-2 минут...")

    # --- ШАГ 2: ЧИТАЕМ сохраненный текст ---
    caption_text = "New video! 🚀" # Запасной вариант
    
    if os.path.exists(CAPTION_PATH):
        with open(CAPTION_PATH, "r", encoding="utf-8") as f:
            caption_text = f.read()
        print(f"[DEBUG] Текст прочитан из файла: {caption_text}")
    else:
        print("[DEBUG] Файл с описанием не найден, использую стандартный текст")

    try:
        # Запуск функций загрузки
        # ВАЖНО: убедись, что в самих скриптах (awto_tiktok.py и т.д.) 
        # функции принимают аргумент caption
        #await asyncio.to_thread(instagram_upload, VIDEO_PATH, caption_text)
        loop = asyncio.get_running_loop()
        # Запускаем тяжелый браузер в фоне, чтобы бот не завис!
        await loop.run_in_executor(
            None, 
            functools.partial(tiktok_upload, VIDEO_PATH, caption_text)
        )

        await callback.message.answer(  
            text="✅ Видео и текст успешно опубликованы!",
            reply_markup=kb.menu
        )
        await status_msg.delete()

    except Exception as e:
        print(f"Ошибка при выкладывании: {e}")
        await status_msg.edit_text(text=f"⚠️ Ошибка Selenium: {e}", reply_markup=kb.menu)