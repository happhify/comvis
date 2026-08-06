import os
from datetime import datetime


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_timestamp_string():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def crop_bbox(frame, bbox):
    x1, y1, x2, y2 = bbox

    height, width = frame.shape[:2]

    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(width, x2)
    y2 = min(height, y2)

    crop = frame[y1:y2, x1:x2]

    return crop

def resize_frame_by_width(frame, target_width):
    """
    Resize frame berdasarkan lebar target.
    Aspect ratio tetap dijaga.
    """
    if frame is None:
        return None

    if target_width is None or target_width <= 0:
        return frame

    height, width = frame.shape[:2]

    if width <= target_width:
        return frame

    scale = target_width / width
    new_height = int(height * scale)

    import cv2
    resized = cv2.resize(frame, (target_width, new_height))

    return resized