import cv2


def get_color_by_status(status):
    if status == "verified":
        return (0, 255, 0)

    if status == "unknown":
        return (0, 0, 255)

    return (255, 255, 255)


def draw_person_boxes(frame, detections):
    for detection in detections:
        x1, y1, x2, y2 = detection["bbox"]

        status = detection.get("status", "person")
        display_label = detection.get("display_label", "person")

        color = get_color_by_status(status)

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            2,
        )

        cv2.putText(
            frame,
            display_label,
            (x1, max(y1 - 10, 30)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )

    return frame


def draw_hud(
    frame,
    lines,
    color=(0, 255, 0),
    margin=20,
    line_height=32,
    scale=0.75,
    thickness=2,
):
    """
    (BARU) Menulis info FPS/Persons/Camera di KIRI-BAWAH frame.

    Kenapa di bawah: kamera CCTV membakar timestamp-nya sendiri di
    kiri-ATAS, jadi teks kita dulu bertumpuk dan sulit dibaca.

    Tiap baris digambar dua kali: hitam tebal dulu sebagai garis tepi,
    lalu warna aslinya di atasnya. Ini membuat teks tetap terbaca
    walau latarnya terang (lantai/jendela).

    Isi 'lines' boleh:
      - string biasa              -> pakai warna default
      - tuple (teks, warna)       -> pakai warna sendiri
    """
    if not lines:
        return frame

    height = frame.shape[0]

    # Baris terakhir menempel margin bawah, baris sebelumnya naik ke atas
    start_y = height - margin - (len(lines) - 1) * line_height

    for index, item in enumerate(lines):
        if isinstance(item, (tuple, list)) and len(item) == 2:
            text, line_color = item[0], item[1]
        else:
            text, line_color = item, color

        y = start_y + index * line_height

        cv2.putText(frame, str(text), (margin, y), cv2.FONT_HERSHEY_SIMPLEX,
                    scale, (0, 0, 0), thickness + 3, cv2.LINE_AA)
        cv2.putText(frame, str(text), (margin, y), cv2.FONT_HERSHEY_SIMPLEX,
                    scale, line_color, thickness, cv2.LINE_AA)

    return frame