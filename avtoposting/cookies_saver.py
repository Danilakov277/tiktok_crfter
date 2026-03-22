import json
import os
import time
import undetected_chromedriver as uc # Используем обход блокировок

def save_cookies(site_name, url):
    # Настраиваем опции
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")

    # undetected_chromedriver сам скачает нужный драйвер
    print(f"[INFO] Запускаем браузер для {site_name}...")
    driver = uc.Chrome(options=options)

    try:
        print(f"[INFO] Открываем {url}")
        driver.get(url)

        print("[ACTION REQUIRED] Авторизуйся вручную, затем нажми ENTER в этой консоли...")
        input()

        # Создаём папку cookies рядом со скриптом
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_dir = os.path.join(base_dir, "cookies")
        os.makedirs(cookies_dir, exist_ok=True)

        # Получаем и сохраняем куки
        cookies = driver.get_cookies()
        file_path = os.path.join(cookies_dir, f"{site_name}.json")

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(cookies, file, indent=4)

        print(f"[SUCCESS] Куки успешно сохранены в {file_path}")

    except Exception as e:
        print(f"[ERROR] Произошла ошибка: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    save_cookies("tiktok", "https://www.tiktok.com/login")
    save_cookies("instagram", "https://www.instagram.com/accounts/login/")