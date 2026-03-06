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

        # 2. Рисуем белую плашку
        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=25,
            fill=(255, 255, 255)
        )

        # 3. Загружаем шрифты
        try:
            # Arial для четкого русского текста
            font_text = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
            # Segoe UI Emoji для ЦВЕТНЫХ эмодзи
            font_emoji = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", font_size)
        except:
            font_text = ImageFont.load_default()
            font_emoji = font_text

        # 4. Сначала рассчитываем общую ширину (чтобы отцентрировать)
        items = []
        total_width = 0
        max_h = 0

        for char in text:
            is_emoji = char in emoji.EMOJI_DATA
            f = font_emoji if is_emoji else font_text
            
            # Замеряем каждый символ
            bbox = draw.textbbox((0, 0), char, font=f, embedded_color=is_emoji)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            
            items.append((char, f, w, is_emoji))
            total_width += w
            max_h = max(max_h, h)

        # Координаты для центрирования
        rect_w = x2 - x1
        rect_h = y2 - y1
        current_x = x1 + (rect_w - total_width) // 2
        text_y = y1 + (rect_h - max_h) // 2

        # 5. Рисуем посимвольно
        for char, f, w, is_emoji in items:
            draw.text(
                (current_x, text_y),
                char,
                font=f,
                fill=(0, 0, 0), # Черный для текста
                embedded_color=is_emoji # ВКЛЮЧАЕТ ЦВЕТ только для эмодзи
            )
            current_x += w

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

        roi_y_start = int(height * 0.6)

        roi = first_frame[roi_y_start:height, :]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        thresh = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )[1]

        data = pytesseract.image_to_data(
            thresh,
            output_type=pytesseract.Output.DICT
        )

        coords = []

        for i in range(len(data["text"])):

            if data["text"][i].strip():

                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]

                coords.append((x, y, w, h))

        if not coords:
            print("❌ Текст не найден")
            return

        padding = 25

        min_x = min(c[0] for c in coords)
        min_y = min(c[1] for c in coords)

        max_y = max(c[1] + c[3] for c in coords)

        rect_x1 = min_x - padding
        rect_x2 = width - min_x + padding

        rect_y1 = roi_y_start + min_y - padding
        rect_y2 = roi_y_start + max_y + padding

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
            os.remove(temp_img)

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
                    "Распознай текст, переведи на русский и сохрани emoji. Верни только текст.",
                    img
                ]
            )

            return response.text.strip()

        except Exception as e:

            print("Ошибка Gemini:", e)
            return ""