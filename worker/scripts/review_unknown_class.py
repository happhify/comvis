"""
scripts/review_unknown_class.py

Kebalikan dari review_hadi_class: memeriksa kelas UNKNOWN untuk mencari
foto Hadi yang salah tempat (mengurangi recall).

Karena kelas unknown besar, secara default hanya menampilkan foto yang
MODEL-nya sendiri sempat mengira Hadi -- yaitu foto unknown yang isinya
cocok dengan crop '*_hadi_*' di outputs/crops. Di situlah Hadi paling
mungkin salah tempat. Pakai --all untuk memeriksa SEMUA foto unknown.

Untuk tiap foto:
    h                 -> ini Hadi, pindahkan ke kelas hadi
    tombol lain       -> biarkan (memang unknown)   <- default aman
    z                 -> undo
    q                 -> berhenti

Foto tidak dihapus, hanya pindah kelas.
"""

import argparse
import hashlib
import os
import shutil

try:
    import cv2
except ImportError:
    cv2 = None

VALID_EXT = (".jpg", ".jpeg", ".png", ".bmp")
HADI_DIR = "datasets/known/hadi"
UNKNOWN_DIR = "datasets/unknown"
CROPS_DIR = "outputs/crops"


def list_images(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder)
                  if os.path.splitext(f)[1].lower() in VALID_EXT)


def file_hash(path):
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except Exception:
        return None
    return h.hexdigest()


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


def suspected_hadi_hashes():
    """Hash semua crop yang model beri label '*_hadi_*' (verified/unverified hadi)."""
    hashes = set()
    for f in list_images(CROPS_DIR):
        if "_hadi_" in f:  # cocok verified_hadi & unverified_hadi
            h = file_hash(os.path.join(CROPS_DIR, f))
            if h:
                hashes.add(h)
    return hashes


class Review:
    """Inti operasi file (dipisah dari cv2 supaya bisa diuji)."""

    def __init__(self, hadi_dir=HADI_DIR, unknown_dir=UNKNOWN_DIR):
        self.hadi_dir = hadi_dir
        self.unknown_dir = unknown_dir
        os.makedirs(hadi_dir, exist_ok=True)
        self.hadi_counter = highest_index(hadi_dir, "hadi")
        self.kept = 0
        self.rescued = 0
        self.history = []  # ("keep", name) | ("move", src_path, dst_path)

    def keep(self, name):
        self.kept += 1
        self.history.append(("keep", name))

    def rescue(self, name):
        """Pindahkan foto dari unknown ke hadi."""
        src = os.path.join(self.unknown_dir, name)
        self.hadi_counter += 1
        dst = os.path.join(self.hadi_dir, f"hadi_{self.hadi_counter:04d}.jpg")
        while os.path.exists(dst):
            self.hadi_counter += 1
            dst = os.path.join(self.hadi_dir, f"hadi_{self.hadi_counter:04d}.jpg")
        shutil.move(src, dst)
        self.rescued += 1
        self.history.append(("move", src, dst))

    def undo(self):
        if not self.history:
            return None
        action = self.history.pop()
        if action[0] == "keep":
            self.kept -= 1
            return action[1]
        _, src, dst = action
        if os.path.exists(dst):
            shutil.move(dst, src)
        self.rescued -= 1
        return os.path.basename(src)


def main():
    parser = argparse.ArgumentParser(description="Cari Hadi yang salah tempat di unknown.")
    parser.add_argument("--all", action="store_true",
                        help="Periksa SEMUA foto unknown, bukan cuma yang dicurigai model.")
    args = parser.parse_args()

    if cv2 is None:
        print("[ERROR] cv2 tidak tersedia.")
        return

    unknown_files = list_images(UNKNOWN_DIR)
    if not unknown_files:
        print(f"[ERROR] Tidak ada foto di {UNKNOWN_DIR}")
        return

    if args.all:
        files = unknown_files
        print(f"[INFO] Memeriksa SEMUA {len(files)} foto unknown.")
    else:
        print("[INFO] Memindai crop yang pernah dicurigai Hadi...")
        suspect = suspected_hadi_hashes()
        files = [f for f in unknown_files
                 if file_hash(os.path.join(UNKNOWN_DIR, f)) in suspect]
        print(f"[INFO] {len(files)} dari {len(unknown_files)} foto unknown pernah "
              f"dicurigai model sebagai Hadi -> itu yang diperiksa.")
        if not files:
            print("[INFO] Tidak ada. Kelas unknown kemungkinan sudah bersih dari Hadi.")
            print("       (pakai --all kalau mau memeriksa semuanya)")
            return

    rv = Review()
    print("[INFO] h = ini Hadi (pindah ke hadi) | tombol lain = biarkan | z = undo | q = quit")

    i = 0
    while i < len(files):
        name = files[i]
        path = os.path.join(UNKNOWN_DIR, name)
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

        top = f"{i + 1}/{len(files)}   h=ini HADI   lain=biarkan   z=undo   q=quit"
        bot = f"Diselamatkan ke hadi: {rv.rescued}"
        for text, y, col in ((top, 22, (0, 255, 0)),
                             (bot, preview.shape[0] - 12, (0, 200, 255))):
            cv2.putText(preview, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(preview, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        col, 1, cv2.LINE_AA)

        cv2.imshow("Periksa kelas UNKNOWN", preview)
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
        if key == ord("h"):
            rv.rescue(name)
            print(f"[HADI] {name} -> dipindah ke kelas hadi")
        else:
            rv.keep(name)
        i += 1

    cv2.destroyAllWindows()
    print("=" * 60)
    print(f"[DONE] Diselamatkan ke hadi: {rv.rescued}, dibiarkan unknown: {rv.kept}")
    print(f"       Kelas hadi sekarang: {len(list_images(HADI_DIR))} foto")
    print("[NEXT] clean_dataset.py --apply -> balance -> split -> audit -> train")


if __name__ == "__main__":
    main()