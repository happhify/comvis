import time

from app.shared_state import shared_state


def mjpeg_generator():
    """
    Generator untuk endpoint MJPEG stream.

    Browser akan menerima frame berulang seperti video.
    React cukup menampilkan:
    <img src="/api/stream" />
    """

    while True:
        frame = shared_state.get_latest_frame()

        if frame is None:
            time.sleep(0.1)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            frame +
            b"\r\n"
        )

        # Delay kecil agar endpoint tidak terlalu membebani CPU
        time.sleep(0.03)