import cv2
import pytesseract
import numpy as np


class TextDetector:

    def __init__(self):
        # если нужно явно указать путь к tesseract:
        # pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        pass

    def detect_text(self, input_path, output_path):

        cap = cv2.VideoCapture(input_path)

        if not cap.isOpened():
            print("❌ Не удалось открыть видео")
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # анализируем каждый 5-й кадр
            if frame_count % 5 == 0:

                # берём нижнюю часть видео (где обычно субтитры)
                roi = frame[int(height * 0.6):height, :]

                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (5, 5), 0)
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

                data = pytesseract.image_to_data(
                    thresh,
                    output_type=pytesseract.Output.DICT,
                    config="--psm 6"
                )

                n_boxes = len(data["text"])

                for i in range(n_boxes):

                    text = data["text"][i].strip()

                    if len(text) > 2:

                        x = data["left"][i]
                        y = data["top"][i]
                        w = data["width"][i]
                        h = data["height"][i]

                        # перевод координат из ROI в глобальные
                        y_global = int(height * 0.6) + y

                        print(f"Найден текст: {text}")
                        print(f"Координаты: x={x}, y={y_global}, w={w}, h={h}")
                        print("-" * 40)

                        # рисуем рамку
                        cv2.rectangle(
                            frame,
                            (x, y_global),
                            (x + w, y_global + h),
                            (0, 255, 0),
                            2
                        )

            out.write(frame)

        cap.release()
        out.release()

        print("✅ Детекция завершена")



class BlockTextDetector:

    def __init__(self):
        # если нужно явно указать путь:
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

        print("FPS:", fps)
        print("Размер:", width, "x", height)

        # ---------- ШАГ 1: анализ первых 5 кадров ----------
        boxes = []

        for i in range(5):

            ret, frame = cap.read()
            if not ret:
                break

            # берем нижнюю треть видео (обычно там текст)
            roi = frame[int(height * 0.6):height, :]

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

            data = pytesseract.image_to_data(
                thresh,
                output_type=pytesseract.Output.DICT,
                config="--psm 6"
            )

            for j, text in enumerate(data["text"]):

                text = text.strip()

                if len(text) > 2:

                    x = data["left"][j]
                    y = data["top"][j]
                    w = data["width"][j]
                    h = data["height"][j]

                    # переводим координаты ROI в глобальные
                    y_global = int(height * 0.6) + y

                    boxes.append((x, y_global, w, h))

                    print("Найден текст:", text)

        if not boxes:
            print("❌ Текст не найден в первых 5 кадрах")
            return

        # ---------- ШАГ 2: объединяем все найденные области ----------
        

        filtered_boxes = []

        for (x, y, w, h) in boxes:

            # игнорируем слишком маленькие области
            if w < 30 or h < 20:
                continue

            filtered_boxes.append((x, y, w, h))

        if not filtered_boxes:
            print("❌ После фильтрации текст не найден")
            return

        # вычисляем медианное значение Y, чтобы убрать выбросы вниз
        ys = [b[1] for b in filtered_boxes]
        median_y = np.median(ys)

        # оставляем только боксы близкие к основной строке
        aligned_boxes = []

        for (x, y, w, h) in filtered_boxes:
            if abs(y - median_y) < 50:
                aligned_boxes.append((x, y, w, h))

        if not aligned_boxes:
            aligned_boxes = filtered_boxes

        # вычисляем общий блок
        # ---------- ШАГ 2: вычисляем базовые границы ----------

        min_x = min([b[0] for b in aligned_boxes])
        max_x = max([b[0] + b[2] for b in aligned_boxes])
        min_y = min([b[1] for b in aligned_boxes])
        max_y = max([b[1] + b[3] for b in aligned_boxes])

        text_width = max_x - min_x
        text_height = max_y - min_y

        # ---------- ЦЕНТРИРОВАНИЕ ПО X ----------

        video_center_x = width // 2

        half_width = text_width // 2

        # делаем ширину чуть больше (запас)
        half_width += 70

        min_x = video_center_x - half_width
        max_x = video_center_x + half_width

        # защита от выхода за границы
        min_x = max(0, min_x)
        max_x = min(width, max_x)

        # ---------- Добавляем вертикальный padding ----------

        padding_y = 25
        min_y = max(0, min_y - padding_y)
        max_y = min(height, max_y + padding_y)

        print("Центрированный блок:")
        print("x:", min_x)
        print("y:", min_y)
        print("w:", max_x - min_x)
        print("h:", max_y - min_y)

        # перематываем видео в начало
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # ---------- ШАГ 3: закрашиваем найденную область на всём видео ----------

        while True:

            ret, frame = cap.read()
            if not ret:
                break

            roi = frame[min_y:max_y, min_x:max_x]
            avg_color = cv2.mean(roi)[:3]

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

        print("✅ Блок закрашен на всём видео")