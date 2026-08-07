FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

WORKDIR /app

# opencv butuh libGL/libglib walau pakai paket headless.
# tzdata dibutuhkan supaya env var TZ (di docker-compose.yml) benar-benar
# diikuti - tanpa ini datetime.now() Python selalu UTC walau TZ di-set,
# karena base image ini tidak menyertakan /usr/share/zoneinfo.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY worker/requirements.txt .
# ultralytics menarik "opencv-python" (varian GUI) sebagai dependency-nya
# sendiri, bentrok dengan "opencv-python-headless" di requirements.txt ini
# (keduanya menulis ke folder cv2/ yang sama). force-reinstall headless
# paling akhir supaya filenya yang menang, bukan campuran dari keduanya.
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --force-reinstall opencv-python-headless

COPY worker/ .

# main.py membaca config/camera.yaml, models/*.pt dan menulis outputs/*
# secara relatif terhadap cwd -> semuanya di-bind-mount ke /app/* lewat
# docker-compose.
ENV HEADLESS=true
# Tanpa ini, print() di Python di-buffer penuh (bukan per-baris) karena
# stdout container bukan TTY -> "docker compose logs" jadi telat/kosong
# padahal proses sebenarnya jalan normal.
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
