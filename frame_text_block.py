import cv2
import os
import pytesseract
import numpy as np


class StaticBlockRemover:

    def __init__(self):
        # если нужно указать путь к tesseract:
        # pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        pass

    def process_video(self, input_path, output_path):

        cap = cv2.VideoCapture(input_path)

        if not cap.isOpened():
            print("❌ Не удалось открыть видео")
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # ---------- ШАГ 1: читаем первый кадр ----------
        ret, first_frame = cap.read()
        if not ret:
            print("❌ Не удалось считать первый кадр")
            return

        # ---------- ШАГ 2: ищем текст ----------
        roi = first_frame[int(height * 0.6):height, :]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        data = pytesseract.image_to_data(
            thresh,
            output_type=pytesseract.Output.DICT,
            config="--psm 6"
        )

        boxes = []

        for i, text in enumerate(data["text"]):
            text = text.strip()
            if len(text) > 2:
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]

                y_global = int(height * 0.6) + y
                boxes.append((x, y_global, w, h))

        if not boxes:
            print("❌ Текст не найден")
            return

        # ---------- ШАГ 3: строим общий блок ----------
# ---------- ШАГ 3: строим общий блок ----------

        min_x = min([b[0] for b in boxes])
        min_y = min([b[1] for b in boxes])
        max_x = max([b[0] + b[2] for b in boxes])
        max_y = max([b[1] + b[3] for b in boxes])

        padding = 5

        min_y = max(0, min_y - padding)
        max_y = min(height, max_y + padding)

        # ширина блока
        block_width = (width - (min_x*2)) + (padding*2)

        # центр кадра
        center_x = width // 2

        # центрируем по X
        min_x = center_x - block_width // 2
        max_x = center_x + block_width // 2

        # защита от выхода за границы
        min_x = max(0, min_x)
        max_x = min(width, max_x)

        # сохраняем вырезанную область как фото
        cropped = first_frame[min_y:max_y, min_x:max_x]
        

        # перематываем видео в начало
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        # ---------- формируем пути корректно ----------

# папка, куда сохраняется видео
        output_folder = os.path.dirname(output_path)

        # если путь передан без папки — создаём "processed"
        if output_folder == "":
            output_folder = "processed"
            os.makedirs(output_folder, exist_ok=True)
            output_path = os.path.join(output_folder, output_path)
        else:
            os.makedirs(output_folder, exist_ok=True)

        # имя файла без расширения
        base_name = os.path.splitext(os.path.basename(output_path))[0]

        # путь для фото
        image_path = os.path.join(output_folder, f"{base_name}_cropped.jpg")

        # сохраняем фото
        cropped = first_frame[min_y:max_y, min_x:max_x]
        cv2.imwrite(image_path, cropped)

        print(f"📸 Фото сохранено: {image_path}")

        # ---------- создаём видео writer ----------
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        # ---------- ШАГ 4: закрашиваем эту область на всём видео ----------
        while True:

            ret, frame = cap.read()
            if not ret:
                break

            roi_block = frame[min_y:max_y, min_x:max_x]
            avg_color = cv2.mean(roi_block)[:3]

            cv2.rectangle(
                frame,
                (min_x, min_y),
                (max_x, max_y),
                avg_color,
                -1
            )

            out.write(frame)

        cap.release()
        out.release()

        print("✅ Область закрашена на всём видео")
        print("📸 cropped_area.jpg сохранён")