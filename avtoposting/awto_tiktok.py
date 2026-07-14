import json
import time
import os
import platform
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

# Условный импорт для Linux (виртуальный дисплей)
if platform.system() == "Linux":
    from xvfbwrapper import Xvfb
else:
    Xvfb = None

def load_cookies(driver, path):
    if not os.path.exists(path):
        print(f"[ERROR] Файл с куки не найден: {path}")
        return False
    with open(path, "r", encoding="utf-8") as file:
        cookies = json.load(file)
        for cookie in cookies:
            if 'sameSite' in cookie and cookie['sameSite'] not in ["Strict", "Lax", "None"]:
                del cookie['sameSite']
            try:
                driver.add_cookie(cookie)
            except:
                pass
    return True

def tiktok_upload(video_path_relative, caption):
    # 1. Пути и настройки
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    absolute_video_path = os.path.normpath(os.path.join(project_root, video_path_relative))
    cookies_path = os.path.join(script_dir, "cookies", "tiktok.json")

    # 2. Инициализация дисплея (только для Linux)
    vdisplay = None
    if Xvfb:
        vdisplay = Xvfb(width=1280, height=720)
        vdisplay.start()

    # 3. Настройка стандартного Chrome Options
    options = webdriver.ChromeOptions()
    
    # Отключаем флаги автоматизации для обхода детектов TikTok
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    if platform.system() == "Linux":
        options.add_argument("--headless=new") 

    print("[INFO] Проверка и автозагрузка подходящего Chrome-драйвера...")
    service = Service(ChromeDriverManager().install())

    print("[INFO] Запуск браузера...")
    try:
        driver = webdriver.Chrome(service=service, options=options)
        
        # Применяем stealth-маскировку
        stealth(driver,
                languages=["ru-RU", "ru", "en-US", "en"],
                vendor="Google Inc.",
                platform="Win32" if platform.system() == "Windows" else "Linux x86_64",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
        )
    except Exception as e:
        print(f"[FATAL ERROR] Не удалось запустить браузер: {e}")
        if vdisplay: vdisplay.stop()
        return

    wait = WebDriverWait(driver, 40)

    try:
        print("[INFO] Переход на TikTok...")
        driver.get("https://www.tiktok.com/upload")
        load_cookies(driver, cookies_path)
        driver.refresh()
        time.sleep(5)

        print("[INFO] Загрузка файла...")
        file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        file_input.send_keys(absolute_video_path)
        
        # Небольшая пауза, чтобы файл подцепился формой
        time.sleep(3)

        print("[INFO] Ввод описания...")
        # Ищем по data-e2e или по contenteditable для надежности
        caption_box = wait.until(EC.presence_of_element_located((
            By.XPATH, "//div[@data-e2e='editor-caption-input'] | //div[@contenteditable='true']"
        )))
        
        # Фокусируем поле через JS
        driver.execute_script("arguments[0].focus();", caption_box)
        time.sleep(1)
        
        # Очищаем содержимое
        driver.execute_script("arguments[0].innerHTML = '';", caption_box)
        time.sleep(1)

        # Безопасный ввод текста с эмодзи через execCommand (в обход ограничений ChromeDriver)
        driver.execute_script("document.execCommand('insertText', false, arguments[0]);", caption)
        print("[INFO] Описание успешно введено.")
        
        # Даем видео время полностью загрузиться на сервер перед публикацией
        print("[INFO] Ожидание завершения загрузки видео...")
        time.sleep(12) 

        print("[INFO] Нажатие первой кнопки публикации...")
        post_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@data-e2e='post_video_button']")))
        driver.execute_script("arguments[0].click();", post_button)

        # --- ОБРАБОТКА ОКНА ПОДТВЕРЖДЕНИЯ (НОВОЕ) ---
        print("[INFO] Ожидание возможного окна подтверждения от TikTok...")
        time.sleep(4) # Даем всплывающему окну время появиться

        # Массив возможных путей до кнопки согласия на разных языках и кейсах
        confirm_xpaths = [
            "//button[contains(text(), 'Post anyway')]",
            "//button[contains(text(), 'Все равно опубликовать')]",
            "//button[contains(text(), 'Confirm')]",
            "//button[contains(text(), 'Подтвердить')]",
            "//button[contains(text(), 'Post')]",
            "//button[contains(text(), 'Опубликовать')]",
            "//div[contains(@class, 'modal')]//button[contains(@class, 'primary')]", # Основная кнопка в модалке
            "//div[contains(@class, 'modal')]//button[2]" # Обычно "Отмена" слева (1), а "Опубликовать" справа (2)
        ]

        modal_clicked = False
        for xpath in confirm_xpaths:
            try:
                # Пытаемся быстро найти кнопку подтверждения на экране
                confirm_button = driver.find_element(By.XPATH, xpath)
                if confirm_button.is_displayed() and confirm_button.is_enabled():
                    print(f"[INFO] Найдено окно подтверждения! Кликаем по кнопке: {xpath}")
                    driver.execute_script("arguments[0].click();", confirm_button)
                    modal_clicked = True
                    break
            except Exception:
                continue

        if not modal_clicked:
            print("[INFO] Окно дополнительного подтверждения не появилось. Видео ушло на публикацию напрямую.")

        print("[SUCCESS] Видео отправлено!")
        # Даем 15 секунд, чтобы TikTok успел обработать запрос на сервере до закрытия браузера
        time.sleep(15)

    except Exception as e:
        print(f"[ERROR] Ошибка при работе с сайтом: {e}")
    finally:
        print("[INFO] Закрытие браузера...")
        driver.quit()
        if vdisplay:
            vdisplay.stop()