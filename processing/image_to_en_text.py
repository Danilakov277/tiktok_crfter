import cv2
import os
import pytesseract
import numpy as np
import subprocess
from pilmoji import Pilmoji
from google import genai
from PIL import Image, ImageDraw, ImageFont
import emoji
import shutil


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

    def _draw_styled_block(self, frame, text, rect_coords, initial_font_size):
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        x1, y1, x2, y2 = rect_coords
        rect_w = x2 - x1
        rect_h = y2 - y1
        
        padding = 20
        max_target_w = rect_w - (padding * 2)
        max_target_h = rect_h - (padding * 2)

        font_size = initial_font_size
        line_spacing = 15
        
        final_line_data = []
        total_h = 0
        
        # Цикл подбора размера шрифта
        while font_size > 10:
            try:
                font_text = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
                font_emoji = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", font_size)
            except:
                font_text = ImageFont.load_default()
                font_emoji = font_text

            lines = text.split('\n')
            total_h = 0
            max_line_w = 0
            temp_line_data = []

            for line in lines:
                line_w = 0
                line_max_h = 0
                for char in line:
                    is_emoji = char in emoji.EMOJI_DATA
                    f = font_emoji if is_emoji else font_text
                    bbox = draw.textbbox((0, 0), char, font=f, embedded_color=is_emoji)
                    line_w += (bbox[2] - bbox[0])
                    line_max_h = max(line_max_h, bbox[3] - bbox[1])
                
                if not line: line_max_h = font_size
                max_line_w = max(max_line_w, line_w)
                total_h += line_max_h + line_spacing
                temp_line_data.append({'width': line_w, 'height': line_max_h})

            total_h -= line_spacing
            if max_line_w <= max_target_w and total_h <= max_target_h:
                final_line_data = temp_line_data
                break
            font_size -= 2
        
        draw.rounded_rectangle([x1, y1, x2, y2], radius=25, fill=(255, 255, 255))

        lines = text.split('\n')
        current_y = y1 + (rect_h - total_h) // 2
        for i, line in enumerate(lines):
            line_w = final_line_data[i]['width']
            current_x = x1 + (rect_w - line_w) // 2
            for char in line:
                is_emoji = char in emoji.EMOJI_DATA
                f = font_emoji if is_emoji else font_text
                bbox = draw.textbbox((0, 0), char, font=f, embedded_color=is_emoji)
                draw.text((current_x, current_y), char, font=f, fill=(0, 0, 0), embedded_color=is_emoji)
                current_x += (bbox[2] - bbox[0])
            current_y += final_line_data[i]['height'] + line_spacing

        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    # -------------------------------------------------
    # Основная обработка
    # -------------------------------------------------

    def process_video(self, input_path, output_path):
        cap = cv2.VideoCapture(input_path)
        temp_video = "temp_render.mp4"
        temp_img = "temp_roi.jpg"

        try:
            if not cap.isOpened(): return

            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            ret, first_frame = cap.read()
            if not ret: raise Exception("Кадр не захвачен")

            # Фокусируемся на нижней части (TikTok текст обычно там)
            roi_y_start = int(height * 0.6)
            roi = first_frame[roi_y_start:height, :]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Улучшенная бинаризация для белого текста
            _, thresh = cv2.threshold(gray, 210, 255, cv2.THRESH_BINARY_INV)
            data = pytesseract.image_to_data(thresh, output_type=pytesseract.Output.DICT, config="--psm 11")
            
            coords = []
            for i in range(len(data["text"])):
                text_str = data["text"][i].strip()
                conf = int(data["conf"][i])
                # ИСПРАВЛЕНИЕ: Порог уверенности 70% + проверка на буквы/цифры
                if conf > 70 and any(c.isalnum() for c in text_str):
                    coords.append({
                        'x': data["left"][i], 
                        'y': data["top"][i], 
                        'w': data["width"][i], 
                        'h': data["height"][i]
                    })

            if not coords:
                print("⚠️ Текст не найден")
                cap.release()
                shutil.copy(input_path, output_path)
                return

            # ИСПРАВЛЕНИЕ: Фильтрация выбросов (убираем одиночные блоки далеко от центра масс)
            center_x = np.median([c['x'] + c['w']/2 for c in coords])
            center_y = np.median([c['y'] + c['h']/2 for c in coords])
            
            # Оставляем только те блоки, которые не слишком далеко от «центра» текста
            filtered_coords = [
                c for c in coords 
                if abs((c['x'] + c['w']/2) - center_x) < width * 0.4
                and abs((c['y'] + c['h']/2) - center_y) < height * 0.2
            ]

            if not filtered_coords: filtered_coords = coords # на всякий случай

            padding = 25
            min_x = min(c['x'] for c in filtered_coords)
            max_x = max(c['x'] + c['w'] for c in filtered_coords)
            min_y = min(c['y'] for c in filtered_coords)
            max_y = max(c['y'] + c['h'] for c in filtered_coords)

            rect_x1 = max(0, min_x - padding)
            rect_x2 = width - rect_x1
            rect_y1 = max(0, roi_y_start + min_y - padding)
            rect_y2 = min(height, roi_y_start + max_y + padding)

            crop = first_frame[rect_y1:rect_y2, rect_x1:rect_x2]
            cv2.imwrite(temp_img, crop)

            final_text = self.extract_text_from_image(temp_img)
            if not final_text or len(final_text.strip()) < 2: 
                raise Exception("Gemini не нашел осмысленного текста")

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            while True:
                ret, frame = cap.read()
                if not ret: break
                frame = self._draw_styled_block(frame, final_text, (rect_x1, rect_y1, rect_x2, rect_y2), 34)
                out.write(frame)

            cap.release()
            out.release()

            subprocess.run(["ffmpeg", "-y", "-i", temp_video, "-i", input_path, "-c:v", "libx264", "-crf", "22", "-c:a", "copy", "-map", "0:v:0", "-map", "1:a:0", output_path], check=True)

        except Exception as e:
            print(f"❌ Пропуск: {e}")
            if cap.isOpened(): cap.release()
            shutil.copy(input_path, output_path)
        finally:
            for f in [temp_video, temp_img, input_path]:
                if os.path.exists(f): 
                    try: os.remove(f)
                    except: pass
        

        # --------------------------------------
        # временное видео без звука
        # --------------------------------------


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

    def translate_description_from_file(self, file_path):
            """
            Читает текстовый файл описания, отправляет в Gemini 
            и возвращает переведенную строку.
            """
            if not os.path.exists(file_path):
                print("⚠️ Файл описания не найден.")
                return ""

            if not self.client:
                print("❌ Клиент Gemini не инициализирован.")
                return ""

            try:
                # Читаем оригинальный текст из файла
                with open(file_path, "r", encoding="utf-8") as f:
                    original_text = f.read()

                if not original_text.strip():
                    return ""

                # Отправляем в нейросеть
                print("📝 Перевожу описание видео...")
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        "Переведи это описание видео из TikTok на русский язык. "
                        "ВАЖНО: Сохрани все оригинальные хештеги (не переводи их, оставь как есть) "
                        "Если на картинке нет осмысленного текста, верни пустую строку" 
                        "и сохрани все эмодзи. Выдай только готовый переведенный текст без лишних комментариев:\n\n"
                        + original_text
                    ]
                )
                os.remove(file_path)
                return response.text.strip()

            except Exception as e:
                print(f"❌ Ошибка при чтении или переводе описания: {e}")
                os.remove(file_path)
                return ""