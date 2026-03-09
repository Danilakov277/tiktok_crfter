import cv2
import os
import pytesseract
import numpy as np
import subprocess
from pilmoji import Pilmoji
from google import genai
from PIL import Image, ImageDraw, ImageFont
import emoji


class StaticBlockRemover:

    def __init__(self, gemini_api_key=None):

        self.gemini_api_key = gemini_api_key

        if gemini_api_key:
            self.client = genai.Client(api_key=gemini_api_key)
        else:
            self.client = None

    # -------------------------------------------------
    # Рисование плашки + текста
    # -------------------------------------------------

    def _draw_styled_block(self, frame, text, rect_coords, font_size):
    # 1. Конвертация кадра
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        x1, y1, x2, y2 = rect_coords
        rect_w = x2 - x1
        rect_h = y2 - y1

        # 2. Рисуем белую плашку
        draw.rounded_rectangle([x1, y1, x2, y2], radius=25, fill=(255, 255, 255))

        # 3. Загружаем шрифты
        try:
            font_text = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
            font_emoji = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", font_size)
        except:
            font_text = ImageFont.load_default()
            font_emoji = font_text

        # 4. Разбиваем текст на строки и считаем размеры
        lines = text.split('\n')
        line_data = []
        total_block_h = 0
        line_spacing = 10 # Расстояние между строками

        for line in lines:
            items = []
            line_w = 0
            line_max_h = 0
            
            for char in line:
                is_emoji = char in emoji.EMOJI_DATA
                f = font_emoji if is_emoji else font_text
                bbox = draw.textbbox((0, 0), char, font=f, embedded_color=is_emoji)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                items.append((char, f, w, is_emoji))
                line_w += w
                line_max_h = max(line_max_h, h)
            
            if not line: # Если строка пустая (двойной \n)
                line_max_h = font_size
                
            line_data.append({
                'items': items,
                'width': line_w,
                'height': line_max_h
            })
            total_block_h += line_max_h + line_spacing

        # Убираем лишний отступ после последней строки
        total_block_h -= line_spacing

        # 5. Рисуем строки с центрированием
        # Начальная точка Y для всего блока текста (центрирование по вертикали)
        current_y = y1 + (rect_h - total_block_h) // 2

        for line in line_data:
            # Начальная точка X для конкретной строки (центрирование по горизонтали)
            current_x = x1 + (rect_w - line['width']) // 2
            
            for char, f, w, is_emoji in line['items']:
                draw.text(
                    (current_x, current_y),
                    char,
                    font=f,
                    fill=(0, 0, 0),
                    embedded_color=is_emoji
                )
                current_x += w
            
            # Переход на следующую строку
            current_y += line['height'] + line_spacing

        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    # -------------------------------------------------
    # Основная обработка
    # -------------------------------------------------

    def process_video(self, input_path, output_path):

        cap = cv2.VideoCapture(input_path)

        if not cap.isOpened():
            print("❌ Не удалось открыть видео")
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        ret, first_frame = cap.read()
        if not ret:
            print("❌ Не удалось считать кадр")
            return

# ---------- ШАГ 2: ищем текст ----------
        roi_y_start = int(height * 0.6)
        roi = first_frame[roi_y_start:height, :]

        # --- ИСПРАВЛЕНИЕ 1: Ищем только светлый/белый текст TikTok ---
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Отсекаем всё, что темнее 180 (оставляем только яркий белый текст)
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        # Инвертируем: Tesseract лучше всего читает черный текст на белом фоне
        thresh = cv2.bitwise_not(binary)

        # --- ИСПРАВЛЕНИЕ 2: Используем --psm 6 (Единый блок текста) ---
        # Этот режим идеально подходит для чтения абзацев в несколько строк
        data = pytesseract.image_to_data(
            thresh,
            output_type=pytesseract.Output.DICT,
            config="--psm 6"
        )

        coords = []

        for i in range(len(data["text"])):
            text_str = data["text"][i].strip()
            # Фильтруем мусор
            if len(text_str) >= 2 or (len(text_str) == 1 and text_str.isalnum()):
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                coords.append((x, y, w, h))

        if not coords:
            print("❌ Текст не найден")
            return

        padding = 25

        # --- ИСПРАВЛЕНИЕ 3: Вычисляем реальные границы текста ---
        min_x = min(c[0] for c in coords)
        max_x = max(c[0] + c[2] for c in coords) # Настоящий конец текста по ширине
        min_y = min(c[1] for c in coords)
        max_y = max(c[1] + c[3] for c in coords)

        # Формируем рамку, которая аккуратно облегает найденный текст
        rect_x1 = max(0, min_x - padding)
        rect_x2 = width - rect_x1
        
        rect_y1 = max(0, roi_y_start + min_y - padding)
        rect_y2 = min(height, roi_y_start + max_y + padding + 10) 

        temp_img = "temp_roi.jpg"

        cv2.imwrite(
            temp_img,
            first_frame[rect_y1:rect_y2, rect_x1:rect_x2]
        )

        final_text = self.extract_text_from_image(temp_img)

        # --------------------------------------
        # временное видео без звука
        # --------------------------------------

        temp_video = "temp_video.mp4"

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        out = cv2.VideoWriter(
            temp_video,
            fourcc,
            fps,
            (width, height)
        )

        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        while True:

            ret, frame = cap.read()

            if not ret:
                break

            if final_text:

                frame = self._draw_styled_block(
                    frame,
                    final_text,
                    (rect_x1, rect_y1, rect_x2, rect_y2),
                    font_size=36
                )

            out.write(frame)

        cap.release()
        out.release()

        # --------------------------------------
        # добавляем звук обратно
        # --------------------------------------

        command = [
            "ffmpeg",
            "-y",
            "-i", temp_video,
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "copy",
            "-map", "0:v:0",
            "-map", "1:a:0",
            output_path
        ]

        subprocess.run(command)

        os.remove(temp_video)

        if os.path.exists(temp_img):
            #os.remove(temp_img)
            pass

        print("✅ Видео обработано")
        print("🎵 Звук сохранён")
        print("📦 Размер видео оптимизирован")

    # -------------------------------------------------
    # Gemini OCR + перевод
    # -------------------------------------------------

    def extract_text_from_image(self, image_path):

        if not self.client:
            return ""

        try:

            img = Image.open(image_path)

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    "Распознай текст на картинке. Переведи его на русский. "
                    "ВАЖНО: Сохрани точно такое же количество строк, как на картинке. "
                    "Если на картинке текст в две строки — верни две строки. "
                    "Сохрани все эмодзи. Не пиши ничего, кроме перевода.", 
                    img
                ]
            )

            return response.text.strip()

        except Exception as e:

            print("Ошибка Gemini:", e)
            return ""