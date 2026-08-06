"""
scripts/review_hadi_class.py

Memeriksa SEMUA foto yang saat ini ada di kelas hadi (datasets/known/hadi),
untuk memastikan tidak ada orang lain yang nyelip (penyebab false positive).

Untuk tiap foto:
    k / spasi / enter / tombol lain -> SIMPAN (memang Hadi)  <- default aman
    x                               -> BUKAN Hadi, pindahkan ke unknown
    z                               -> undo keputusan terakhir
    q                               -> berhenti

Default = SIMPAN, jadi salah pencet tidak akan membuang foto Hadi.
Hanya 'x' yang memindahkan. Foto yang dipindah TIDAK dihapus, hanya pindah
kelas ke unknown (jadi tetap berguna sebagai contoh negatif).

Tujuan: menangkap kesalahan sortir sebelumnya tanpa membongkar semuanya.
"""

import os
import shutil

try:
    import cv2
except ImportError:
    cv2 = None

VALID_EXT = (".jpg", ".jpeg", ".png", ".bmp")
HADI_DIR = "datasets/known/hadi"
UNKNOWN_DIR = "datasets/unknown"


def list_images(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder)
                  if os.path.splitext(f)[1].lower() in VALID_EXT)


def highest_index(folder, prefix):
    hi = 0
    for f in list_images(folder):
        stem = os.path.splitext(f)[0]
        if stem.startswith(prefix + "_"):
            try:
                hi = max(hi, int(stem[len(prefix) + 1:]))
            except ValueError:
                pass
    return hi


class Review:
    """Inti operasi file, dipisah dari cv2 supaya bisa diuji."""

    def __init__(self, hadi_dir=HADI_DIR, unknown_dir=UNKNOWN_DIR):
        self.hadi_dir = hadi_dir
        self.unknown_dir = unknown_dir
        os.makedirs(unknown_dir, exist_ok=True)
        self.unk_counter = highest_index(unknown_dir, "unknown")
        self.kept = 0
        self.moved = 0
        self.history = []  # ("keep", name) | ("move", src_path, dst_path)

    def keep(self, name):
        self.kept += 1
        self.history.append(("keep", name))

    def reject(self, name):
        """Pindahkan foto dari hadi ke unknown."""
        src = os.path.join(self.hadi_dir, name)
        self.unk_counter += 1
        dst = os.path.join(self.unknown_dir, f"unknown_{self.unk_counter:04d}.jpg")
        while os.path.exists(dst):
            self.unk_counter += 1
            dst = os.path.join(self.unknown_dir, f"unknown_{self.unk_counter:04d}.jpg")
        shutil.move(src, dst)
        self.moved += 1
        self.history.append(("move", src, dst))

    def undo(self):
        """Batalkan aksi terakhir. Return nama foto yang perlu ditampilkan ulang."""
        if not self.history:
            return None
        action = self.history.pop()
        if action[0] == "keep":
            self.kept -= 1
            return action[1]
        _, src, dst = action
        if os.path.exists(dst):
            shutil.move(dst, src)      # kembalikan ke hadi
        self.moved -= 1
        return os.path.basename(src)


def main():
    if cv2 is None:
        print("[ERROR] cv2 tidak tersedia.")
        return

    files = list_images(HADI_DIR)
    if not files:
        print(f"[ERROR] Tidak ada foto di {HADI_DIR}")
        return

    rv = Review()
    print(f"[INFO] Memeriksa {len(files)} foto di kelas hadi.")
    print("[INFO] x = BUKAN Hadi (pindah ke unknown) | tombol lain = simpan | z = undo | q = quit")

    i = 0
    while i < len(files):
        name = files[i]
        path = os.path.join(HADI_DIR, name)
        if not os.path.exists(path):
            i += 1
            continue

        img = cv2.imread(path)
        if img is None:
            print(f"[WARN] gagal baca {name}")
            i += 1
            continue

        preview = img.copy()
        if preview.shape[1] < 320:
            scale = 320 / preview.shape[1]
            preview = cv2.resize(preview, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_NEAREST)

        top = f"{i + 1}/{len(files)}   x=BUKAN Hadi   lain=simpan   z=undo   q=quit"
        bot = f"Disimpan {rv.kept}   Dibuang {rv.moved}"
        for text, y, col in ((top, 22, (0, 255, 0)),
                             (bot, preview.shape[0] - 12, (0, 200, 255))):
            cv2.putText(preview, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(preview, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        col, 1, cv2.LINE_AA)

        cv2.imshow("Periksa kelas HADI", preview)
        key = cv2.waitKey(0) & 0xFF

        if key == ord("q"):
            break
        if key == ord("z"):
            back = rv.undo()
            if back is not None:
                i = max(0, i - 1)
                print(f"[UNDO] {back}")
            else:
                print("[UNDO] tidak ada yang bisa dibatalkan")
            continue
        if key == ord("x"):
            rv.reject(name)
            print(f"[BUKAN HADI] {name} -> unknown")
        else:
            rv.keep(name)
        i += 1

    cv2.destroyAllWindows()
    print("=" * 60)
    print(f"[DONE] Disimpan {rv.kept}, dipindah ke unknown {rv.moved}")
    print(f"       Kelas hadi sekarang: {len(list_images(HADI_DIR))} foto")
    print("[NEXT] clean_dataset.py --apply -> balance -> split -> audit -> train")


if __name__ == "__main__":
    main()