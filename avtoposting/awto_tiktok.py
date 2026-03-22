import json
import time
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CAPTION = "Auto upload test 🚀"

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

def tiktok_upload(video_path_relative):
    # ПУТЬ 1: Папка, где лежит этот скрипт (D:\...\avtoposting)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # ПУТЬ 2: Корень проекта (D:\...\inst_tt_progect)
    project_root = os.path.dirname(script_dir)
    
    # Собираем абсолютные пути
    absolute_video_path = os.path.normpath(os.path.join(project_root, video_path_relative))
    # Куки лежат в папке cookies внутри avtoposting
    cookies_path = os.path.normpath(os.path.join(script_dir, "cookies", "tiktok.json"))

    if not os.path.exists(absolute_video_path):
        print(f"[ERROR] Видео не найдено: {absolute_video_path}")
        return

    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 30)

    try:
        print("[INFO] Открываем TikTok...")
        driver.get("https://www.tiktok.com")
        time.sleep(3)

        print(f"[INFO] Загружаем cookies из: {cookies_path}")
        if not load_cookies(driver, cookies_path):
            return
            
        driver.refresh()
        time.sleep(5)

        print("[INFO] Переходим на страницу загрузки...")
        driver.get("https://www.tiktok.com/creator-center/upload")

        print("[INFO] Загружаем файл...")
        upload_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file' or @accept='video/*']")))
        upload_input.send_keys(absolute_video_path)

        print("[INFO] Вводим описание (с поддержкой эмодзи)...")
        caption_box = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@contenteditable='true']")))
        
        # 1. Сначала кликаем и фокусируемся на поле
        driver.execute_script("arguments[0].focus();", caption_box)
        time.sleep(1)
        
        # 2. Очищаем поле (если там что-то было)
        caption_box.clear() 

        # 3. Вставляем текст через JavaScript execCommand
        # Это позволяет вставить эмодзи без ошибки ChromeDriver BMP
        js_script = "document.execCommand('insertText', false, arguments[0]);"
        driver.execute_script(js_script, CAPTION)
        
        print(f"[INFO] Текст '{CAPTION}' успешно вставлен.")

# 5. Ожидание кнопки публикации и нажатие
        print("[INFO] Ждем готовности кнопки публикации...")
        # Увеличим время, так как видео должно прогрузиться на 100%
        time.sleep(10) 
        
        # Ищем кнопку по data-e2e (это самый надежный способ в TikTok)
        post_button = wait.until(EC.presence_of_element_located((By.XPATH, "//button[@data-e2e='post_video_button']")))

        print("[INFO] Нажимаем кнопку 'Опубликовать' через JavaScript (обход обучающих окон)...")
        # Кликаем через JS, игнорируя react-joyride__overlay и любые другие всплывашки
        driver.execute_script("arguments[0].click();", post_button)
        
        print("[SUCCESS] Кнопка нажата! Видео отправляется на сервер...")
        # Даем время на завершение запроса перед закрытием браузера
        print("[INFO] Ждем готовности основной кнопки публикации...")
        time.sleep(10) 
        
        # Ищем основную кнопку
        post_button = wait.until(EC.presence_of_element_located((By.XPATH, "//button[@data-e2e='post_video_button']")))
        print("[INFO] Нажимаем основную кнопку через JS...")
        driver.execute_script("arguments[0].click();", post_button)
        
        # --- НОВЫЙ БЛОК: Финальное подтверждение ---
        print("[INFO] Проверяем наличие финального виджета подтверждения...")
        try:
            # Ждем появления финальной кнопки в модальном окне (обычно у нее data-e2e='post-button')
            # Если TikTok изменил атрибут, используем поиск по тексту "Post" или "Опубликовать"
            final_post_button = wait.until(EC.presence_of_element_located((
                By.XPATH, "//div[contains(@class, 'modal')]//button[contains(., 'Post') or contains(., 'Опубликовать')]"
            )))
            
            print("[INFO] Нажимаем финальную кнопку подтверждения...")
            driver.execute_script("arguments[0].click();", final_post_button)
            print("[SUCCESS] Видео окончательно опубликовано!")
        except Exception as e:
            print("[INFO] Финальный виджет не появился или кнопка не найдена (возможно, видео ушло сразу).")
        
        time.sleep(15) 

    except Exception as e:
        print(f"[ERROR] Ошибка в Selenium: {e}")
    finally:
        driver.quit()
