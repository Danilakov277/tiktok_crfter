import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

def ensure_directories():
    """Создает необходимые папки, если их нет"""
    dirs = ['downloads', 'database']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)

def load_downloaded_videos():
    """Загружает историю скачанных видео из JSON файла"""
    db_path = Path('database/downloaded_videos.json')
    if db_path.exists():
        with open(db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_downloaded_videos(videos_db):
    """Сохраняет историю скачанных видео"""
    db_path = Path('database/downloaded_videos.json')
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(videos_db, f, ensure_ascii=False, indent=2)

def generate_video_id(channel_name, video_title, video_url):
    """Генерирует уникальный ID для видео"""
    unique_string = f"{channel_name}_{video_title}_{video_url}"
    return hashlib.md5(unique_string.encode()).hexdigest()

def clean_filename(filename):
    """Очищает имя файла от недопустимых символов"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename[:200]  # ограничиваем длину

def extract_description(info_json_path):
    """Извлекает описание из JSON файла с метаданными"""
    try:
        with open(info_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            description = data.get('description', '')
            # Обрабатываем специальные символы и ссылки
            return description.strip()
    except Exception as e:
        print(f"Ошибка при чтении описания: {e}")
        return ""