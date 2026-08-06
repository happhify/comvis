"""
scripts/label_hadi.py

Sortir BINER: Hadi vs Unknown. Untuk tiap crop:
    h            -> masuk kelas hadi
    tombol lain  -> masuk kelas unknown
    z            -> undo (batalkan keputusan terakhir)
    q            -> berhenti

Gambar buram TIDAK perlu di-skip: sortir saja, lalu hapus manual dari
folder nanti (sesuai caramu).

Dua pengaman:
1. KEPUTUSAN BARU MENANG. Kalau crop yang sama sudah pernah masuk kelas
   lain (dari sortir lama yang salah), file lama itu DIPINDAH keluar dulu,
   jadi tidak ada satu gambar berada di dua kelas sekaligus (yang bikin
   training kacau). Ini yang membuat "sortir ulang" aman.
2. Anti-duplikat: kalau isi crop sudah ada di kelas tujuan, tidak disalin dua kali.

File yang di-override DIPINDAH ke datasets/_sort_trash (bukan dihapus).

Contoh:
    python scripts/label_hadi.py --filter "*20260727*"
    python scripts/label_hadi.py --filter "*20260727*hadi*" --every 2
"""

import argparse
import fnmatch
import hashlib
import os
import shutil

try:
    import cv2
except ImportError:
    cv2 = None

VALID_EXT = (".jpg", ".jpeg", ".png", ".bmp")
SOURCE_DIR = "outputs/crops"
HADI_DIR = "datasets/known/hadi"
UNKNOWN_DIR = "datasets/unknown"
TRASH_DIR = "datasets/_sort_trash"


def list_images(folder, pattern=None, every=1):
    if not os.path.isdir(folder):
        return []
    files = [f for f in os.listdir(folder)
             if os.path.splitext(f)[1].lower() in VALID_EXT]
    if pattern:
        files = [f for f in files if fnmatch.fnmatch(f, pattern)]
    files.sort()
    if every and every > 1:
        files = files[::every]
    return files


def file_hash(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_index(folder):
    idx = {}
    for f in list_images(folder):
        idx[file_hash(os.path.join(folder, f))] = os.path.join(folder, f)
    return idx


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


class Sorter:
    def __init__(self, hadi_dir=HADI_DIR, unknown_dir=UNKNOWN_DIR, trash_dir=TRASH_DIR):
        self.dirs = {"hadi": hadi_dir, "unknown": unknown_dir}
        self.trash_dir = trash_dir
        for d in self.dirs.values():
            os.makedirs(d, exist_ok=True)
        self.idx = {c: build_index(d) for c, d in self.dirs.items()}
        self.counter = {c: highest_index(d, c) for c, d in self.dirs.items()}
        self.last_action = None
        self.stats = {"hadi": 0, "unknown": 0, "override": 0, "dup": 0}

    def place(self, src_path, target):
        other = "unknown" if target == "hadi" else "hadi"
        h = file_hash(src_path)
        action = {"target": target, "copied": None, "restored": []}

        # (1) keputusan baru menang: buang isi yang sama dari kelas lain
        if h in self.idx[other]:
            old = self.idx[other].pop(h)
            os.makedirs(self.trash_dir, exist_ok=True)
            base = os.path.basename(old)
            trash = os.path.join(self.trash_dir, f"{other}__{base}")
            n = 1
            while os.path.exists(trash):
                trash = os.path.join(self.trash_dir, f"{other}__{n}__{base}")
                n += 1
            shutil.move(old, trash)
            action["restored"].append((trash, old, other, h))
            self.stats["override"] += 1

        # (2) anti-duplikat di kelas tujuan
        if h in self.idx[target]:
            self.stats["dup"] += 1
        else:
            self.counter[target] += 1
            dst = os.path.join(self.dirs[target], f"{target}_{self.counter[target]:04d}.jpg")
            while os.path.exists(dst):
                self.counter[target] += 1
                dst = os.path.join(self.dirs[target], f"{target}_{self.counter[target]:04d}.jpg")
            shutil.copy2(src_path, dst)
            self.idx[target][h] = dst
            action["copied"] = dst
            self.stats[target] += 1

        self.last_action = action
        return action

    def undo(self):
        if not self.last_action:
            return False
        a = self.last_action
        if a["copied"] and os.path.exists(a["copied"]):
            self.idx[a["target"]].pop(file_hash(a["copied"]), None)
            os.remove(a["copied"])
            self.stats[a["target"]] -= 1
        for trash, orig, cls, h in a["restored"]:
            if os.path.exists(trash):
                shutil.move(trash, orig)
                self.idx[cls][h] = orig
                self.stats["override"] -= 1
        self.last_action = None
        return True


def main():
    parser = argparse.ArgumentParser(description="Sortir biner Hadi vs Unknown.")
    parser.add_argument("--source", default=SOURCE_DIR)
    parser.add_argument("--filter", default=None, help='mis. "*20260727*hadi*"')
    parser.add_argument("--every", type=int, default=1)
    args = parser.parse_args()

    if cv2 is None:
        print("[ERROR] cv2 tidak tersedia di environment ini.")
        return

    files = list_images(args.source, args.filter, args.every)
    if not files:
        print(f"[ERROR] Tidak ada gambar cocok di {args.source}")
        if args.filter:
            print(f"        filter: {args.filter}")
        return

    s = Sorter()
    print(f"[INFO] {len(files)} gambar dari {args.source}"
          + (f" (filter {args.filter})" if args.filter else ""))
    print("[INFO] h = Hadi | tombol lain = Unknown | z = Undo | q = Quit")
    print("[INFO] Buram tidak perlu di-skip; hapus manual dari folder nanti.")

    i = 0
    while i < len(files):
        name = files[i]
        src = os.path.join(args.source, name)
        img = cv2.imread(src)
        if img is None:
            print(f"[WARN] gagal baca {name}")
            i += 1
            continue

        preview = img.copy()
        if preview.shape[1] < 320:
            scale = 320 / preview.shape[1]
            preview = cv2.resize(preview, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_NEAREST)

        top = f"{i + 1}/{len(files)}   h=Hadi  lain=Unknown  z=Undo  q=Quit"
        bot = f"Hadi +{s.stats['hadi']}   Unknown +{s.stats['unknown']}"
        for text, y, col in ((top, 22, (0, 255, 0)),
                             (bot, preview.shape[0] - 12, (0, 255, 255))):
            cv2.putText(preview, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(preview, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        col, 1, cv2.LINE_AA)

        cv2.imshow("Sortir: Hadi vs Unknown", preview)
        key = cv2.waitKey(0) & 0xFF

        if key == ord("q"):
            print("[INFO] Berhenti.")
            break
        if key == ord("z"):
            if s.undo():
                i = max(0, i - 1)
                print(f"[UNDO] kembali ke {files[i]}")
            else:
                print("[UNDO] tidak ada yang bisa dibatalkan")
            continue

        target = "hadi" if key == ord("h") else "unknown"
        s.place(src, target)
        print(f"[{target.upper()}] {name}")
        i += 1

    cv2.destroyAllWindows()
    print("=" * 60)
    print(f"[DONE] Hadi +{s.stats['hadi']}, Unknown +{s.stats['unknown']}, "
          f"override {s.stats['override']}, duplikat dilewati {s.stats['dup']}")
    print(f"       Total sekarang -> hadi {len(list_images(HADI_DIR))}, "
          f"unknown {len(list_images(UNKNOWN_DIR))}")
    print(f"[INFO] File yang di-override dipindah ke {TRASH_DIR} (bukan dihapus).")
    print("[NEXT] clean_dataset.py --apply -> split_dataset -> audit_dataset -> train")


if __name__ == "__main__":
    main()