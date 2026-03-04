import subprocess
from pathlib import Path


class TikTokDownloader:
    """
    Production-загрузчик TikTok:
    - скачивает видео
    - сохраняет описание
    - не скачивает повторно уже загруженные видео
    """

    def __init__(self, config):
        self.config = config
        self.download_dir = Path(config.DOWNLOAD_DIR) / "tiktok"
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download_from_profile(self, username):

        print(f"\n🎯 Автоматическое скачивание из TikTok: @{username}")
        print("=" * 50)

        username = username.replace("@", "")
        profile_url = f"https://www.tiktok.com/@{username}"

        user_dir = self.download_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)

        archive_file = user_dir / "archive.txt"

        # считаем сколько видео было ДО
        before_count = len(list(user_dir.glob("*.mp4")))

        command = [
            "yt-dlp",

            # не скачивать уже скачанные
            "--download-archive", str(archive_file),

            # скачать N НОВЫХ видео
            "--max-downloads", str(self.config.MAX_VIDEOS_PER_CHANNEL),

            "--write-description",
            "--restrict-filenames",
            "--ignore-errors",

            "-o", str(user_dir / "%(upload_date)s_%(id)s_%(title)s.%(ext)s"),

            profile_url
        ]

        try:
            result = subprocess.run(command)

            if result.returncode == 0:
                print("hohohoho")
                return 0

            # считаем после
            after_count = len(list(user_dir.glob("*.mp4")))

            new_videos = after_count - before_count

            return new_videos

        except Exception as e:
            print(f"\n❌ Ошибка yt-dlp: {e}")
            return 0