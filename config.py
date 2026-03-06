import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class Config:
    # Instagram данные из .env
    INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
    INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # Папки для сохранения
    DOWNLOAD_DIR = 'downloads'
    SESSIONS_DIR = 'sessions'
    DATABASE_DIR = 'database'
    
    # Максимальное количество видео для скачивания за один раз
    MAX_VIDEOS_PER_CHANNEL = 3
    
    # Список каналов
    CHANNELS = [
        {
            'name': 'arawaza_intl',
            'url': 'https://www.instagram.com/arawaza_intl/',
            'platform': 'instagram',
            'language': 'en',
        },
        {
            'name': 'arawaza_intl',
            'url': 'https://www.tiktok.com/@arawaza_intl',
            'platform': 'tiktok',
            'language': 'en',
        }
    ]