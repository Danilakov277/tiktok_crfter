import time
import json
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def load_cookies(driver, path):
    if not os.path.exists(path): return False
    with open(path, "r") as f:
        cookies = json.load(f)
    for cookie in cookies:
        cookie.pop("sameSite", None)
        try: driver.add_cookie(cookie)
        except: pass
    return True

def instagram_upload(video_path_relative, caption):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    absolute_video_path = os.path.normpath(os.path.join(project_root, video_path_relative))

    options = uc.ChromeOptions()
    # options.add_argument("--headless") # Раскомментируйте после отладки
    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        driver.get("https://www.instagram.com/")
        time.sleep(4)
        if not load_cookies(driver, os.path.join(script_dir, "cookies", "instagram.json")):
            print("[ERROR] Cookies not found")
            return
        driver.refresh()
        time.sleep(5)

        # 1. Поиск кнопки "Создать" (Create) - пробуем разные варианты
        print("[INFO] Clicking Create...")
        create_selectors = [
            "//*[contains(@aria-label, 'New post')]",
            "//*[contains(@aria-label, 'Новая публикация')]",
            "//svg[@aria-label='New post']/ancestor::div[@role='button']",
            "//span[text()='Create']/ancestor::div[@role='link']"
        ]
        
        create_btn = None
        for selector in create_selectors:
            try:
                create_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                break
            except: continue
        
        if not create_btn:
            raise Exception("Create button not found")
        create_btn.click()
        time.sleep(2)

        # 2. Загрузка файла
        file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        file_input.send_keys(absolute_video_path)
        time.sleep(4)

        # 3. Кнопки "Далее" (их нужно нажать дважды)
        for _ in range(2):
            next_btn = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//div[@role='button'][text()='Next' or text()='Далее']"
            )))
            next_btn.click()
            time.sleep(2)

        # 4. Ввод описания
        caption_box = wait.until(EC.presence_of_element_located((
            By.XPATH, "//div[@aria-label='Write a caption...' or @aria-label='Введите подпись...']"
        )))
        driver.execute_script("arguments[0].focus();", caption_box)
        driver.execute_script("document.execCommand('insertText', false, arguments[0]);", caption)
        time.sleep(2)

        # 5. Кнопка "Поделиться"
        share_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH, "//div[@role='button'][text()='Share' or text()='Поделиться']"
        )))
        share_btn.click()
        
        # Ждем успеха
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'shared')]")))
        print("[SUCCESS] Published to Instagram!")

    except Exception as e:
        print(f"[ERROR] Instagram failed: {e}")
    finally:
        driver.quit()