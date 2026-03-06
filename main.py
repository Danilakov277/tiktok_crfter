#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Instagram & TikTok Downloader
Скачивает Reels и TikTok видео
"""

import sys
from pathlib import Path
import time

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent))

from config import Config
from image_to_en_text import StaticBlockRemover






def print_header():
    """Красивый заголовок"""
    print("""
    ╔══════════════════════════════════════╗
    ║     Instagram & TikTok Downloader    ║
    ║         Версия 1.0                    ║
    ╚══════════════════════════════════════╝
    """)


def tiktok_menu(config):
 
        # Автоматический режим
        from tiktok_downloader import TikTokDownloader
        downloader = TikTokDownloader(config)
        
        profile = "arawaza_intl"
        
        if profile:
            downloaded = downloader.download_from_profile(profile)
            
            if downloaded:
                print(f"\n✅ Готово! Всего видео в папке: {downloaded}")
            else:
                print("\n❌ Новых видео не найдено")

    


def main():
    print_header()
    
    # Загружаем конфиг
    config = Config()
    
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
            tiktok_menu(config)
        elif choice == "3":
            print("\n👋 До свидания!")
            break
        elif choice =="4":
            # Передаем ключ из конфига
            remover = StaticBlockRemover(gemini_api_key=config.GEMINI_API_KEY)

            remover.process_video(
                "downloads/tiktok/arawaza_intl/20260225_7610852964332342535_karate_arawaza_teamarawaza_kumite_fyp.mp4",
                "refacture/tiktok/cleaned.mp4"
            )
            
            image_path = "refacture/tiktok/cleaned_cropped.jpg"
            text = remover.extract_text_from_image(image_path)

            print("\n✅ Итоговый текст в переменной:")
            print(text)

        else:
            print("❌ Неверный выбор. Попробуй снова.")
        
        
        print("\n" + "="*50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Программа остановлена пользователем")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
    

