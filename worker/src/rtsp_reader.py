import time
import cv2


class RTSPReader:
    def __init__(
        self,
        source,
        source_name="camera",
        reconnect=True,
        reconnect_delay_seconds=3,
        max_failed_reads=30,
    ):
        self.source = source
        self.source_name = source_name
        self.reconnect = reconnect
        self.reconnect_delay_seconds = reconnect_delay_seconds
        self.max_failed_reads = max_failed_reads

        self.cap = None
        self.failed_reads = 0

    def connect(self):
        print(f"[INFO] Mencoba membuka source: {self.source_name}")
        print(f"[INFO] Source: {self.source}")

        self.cap = cv2.VideoCapture(self.source)

        if not self.cap.isOpened():
            print(f"[ERROR] Gagal membuka source: {self.source_name}")
            return False

        print(f"[INFO] Berhasil membuka source: {self.source_name}")
        return True

    def read(self):
        if self.cap is None:
            print("[WARNING] Kamera belum terkoneksi.")
            return False, None

        ret, frame = self.cap.read()

        if not ret or frame is None:
            self.failed_reads += 1
            print(f"[WARNING] Gagal membaca frame. Percobaan gagal: {self.failed_reads}")

            if self.reconnect and self.failed_reads >= self.max_failed_reads:
                print("[WARNING] Terlalu banyak gagal baca frame. Mencoba reconnect...")
                self.reconnect_camera()

            return False, None

        self.failed_reads = 0
        return True, frame

    def reconnect_camera(self):
        self.release()

        print(f"[INFO] Menunggu {self.reconnect_delay_seconds} detik sebelum reconnect...")
        time.sleep(self.reconnect_delay_seconds)

        self.failed_reads = 0
        self.connect()

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            print(f"[INFO] Source {self.source_name} ditutup.")