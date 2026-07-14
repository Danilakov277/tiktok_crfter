import cv2
import os
import json
import numpy as np
import subprocess
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
    # Основная обработка через Gemini
    # -------------------------------------------------
    def process_video(self, input_path, output_path):
        cap = cv2.VideoCapture(input_path)
        temp_video = "temp_render.mp4"
        temp_img = "temp_frame.jpg"

        try:
            if not cap.isOpened(): return

            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            ret, first_frame = cap.read()
            if not ret: raise Exception("Кадр не захвачен")

            cv2.imwrite(temp_img, first_frame)

            gemini_data = self.analyze_frame_with_gemini(temp_img)
            
            if not gemini_data or not gemini_data.get("translation"): 
                raise Exception("Gemini не нашел текст или не вернул перевод")

            final_text = gemini_data["translation"]
            box = gemini_data.get("box", [0, 0, 1000, 1000])

            ymin_norm, xmin_norm, ymax_norm, xmax_norm = box

            rect_y1 = int(ymin_norm * height / 1000)
            rect_x1 = int(xmin_norm * width / 1000)
            rect_y2 = int(ymax_norm * height / 1000)
            rect_x2 = int(xmax_norm * width / 1000)

            padding = 30
            rect_x1 = max(0, rect_x1 - padding)
            rect_x2 = min(width, rect_x2 + padding)
            rect_y1 = max(0, rect_y1 - padding)
            rect_y2 = min(height, rect_y2 + padding)

            if (rect_x2 - rect_x1) < 50 or (rect_y2 - rect_y1) < 30:
                raise Exception("Gemini вернул слишком маленькие координаты для плашки")

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

    # -------------------------------------------------
    # Комплексный анализ кадра
    # -------------------------------------------------
    def analyze_frame_with_gemini(self, image_path):
        if not self.client:
            return None

        try:
            img = Image.open(image_path)
            
            prompt = """
            Find the main text (like TikTok captions or subtitles) on this image.
            Perform two tasks:
            1. Translate the text into Russian. Preserve emojis. Keep the same number of lines if possible.
            2. Determine the bounding box coordinates of this text.
            
            Return ONLY a valid JSON object. Do not include Markdown blocks like ```json. 
            Format:
            {
              "translation": "Твой перевод здесь",
              "box": [ymin, xmin, ymax, xmax]
            }
            
            The 'box' coordinates MUST be integers from 0 to 1000, representing normalized relative positions on the image (where 0 is top/left edge and 1000 is bottom/right edge).
            """

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, img]
            )
            
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3].strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:-3].strip()

            return json.loads(raw_text)

        except Exception as e:
            print("Ошибка Gemini:", e)
            return None

    # -------------------------------------------------
    # Перевод описания
    # -------------------------------------------------
    def translate_description_from_file(self, file_path):
        if not os.path.exists(file_path):
            print("⚠️ Файл описания не найден.")
            return ""

        if not self.client:
            print("❌ Клиент Gemini не инициализирован.")
            return ""

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_text = f.read()

            if not original_text.strip():
                return ""

            print("📝 Перевожу описание видео...")
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    "Переведи это описание видео из TikTok на русский язык. "
                    "ВАЖНО: Сохрани все оригинальные хештеги (не переводи их, оставь как есть) "
                    "Если на картинке нет осмысленного текста, верни пустую строку "
                    "и сохрани все эмодзи. Выдай только готовый переведенный текст без лишних комментариев:\n\n"
                    + original_text
                ]
            )
            os.remove(file_path)
            return response.text.strip()

        except Exception as e:
            print(f"❌ Ошибка при чтении или переводе описания: {e}")
            try:
                os.remove(file_path)
            except:
                pass
            return ""