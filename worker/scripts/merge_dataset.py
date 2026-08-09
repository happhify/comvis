"""
scripts/merge_dataset.py

Gabungkan dataset hadi/unknown dari folder lain (mis. project lama yang
belum pakai Docker) ke dalam datasets/known/hadi dan datasets/unknown
di project ini.

Kenapa perlu script khusus (bukan copy-paste manual):
- Kedua project pakai penamaan file yang SAMA (hadi_0001.jpg, dst),
  jadi copy langsung akan SALING MENIMPA file yang kebetulan bernomor
  sama walau isinya beda.
- Kalau kebetulan ada gambar yang identik (dari crop yang sama), tidak
  perlu digandakan.
- Kalau ada isi gambar yang di project lama masuk kelas "hadi" tapi di
  project ini isi yang sama sudah ada di kelas "unknown" (atau
  sebaliknya), itu KONFLIK LABEL dan tidak boleh diputuskan otomatis
  -> hanya dilaporkan, tidak disalin.

File baru diberi nama lanjutan dari nomor tertinggi yang sudah ada
(hadi_XXXX.jpg / unknown_XXXX.jpg), jadi tidak ada nomor yang ketiban.

Contoh:
    python scripts/merge_dataset.py \\
        --hadi-src "D:/Projects/comvis/datasets/known/hadi" \\
        --unknown-src "D:/Projects/comvis/datasets/unknown" \\
        --dry-run

    python scripts/merge_dataset.py \\
        --hadi-src "D:/Projects/comvis/datasets/known/hadi" \\
        --unknown-src "D:/Projects/comvis/datasets/unknown"
"""

import argparse
import hashlib
import os
import shutil

VALID_EXT = (".jpg", ".jpeg", ".png", ".bmp")

TARGET_DIRS = {
    "hadi": "datasets/known/hadi",
    "unknown": "datasets/unknown",
}


def list_images(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in VALID_EXT
    )


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


def merge_class(label, src_dir, target_dir, other_idx, dry_run):
    print("=" * 60)
    print(f"[INFO] Kelas: {label}")
    print(f"[INFO] Sumber: {src_dir}")
    print(f"[INFO] Tujuan: {target_dir}")

    if not os.path.isdir(src_dir):
        print(f"[ERROR] Folder sumber tidak ditemukan: {src_dir}")
        return {"copied": 0, "dup": 0, "conflict": 0}

    os.makedirs(target_dir, exist_ok=True)
    target_idx = build_index(target_dir)
    counter = highest_index(target_dir, label)

    stats = {"copied": 0, "dup": 0, "conflict": 0}
    src_files = list_images(src_dir)
    print(f"[INFO] {len(src_files)} gambar di sumber")

    for name in src_files:
        src_path = os.path.join(src_dir, name)
        h = file_hash(src_path)

        if h in other_idx:
            stats["conflict"] += 1
            print(f"[CONFLICT] {name} isinya sama dengan gambar kelas lain "
                  f"({other_idx[h]}) -> DILEWATI, cek manual.")
            continue

        if h in target_idx:
            stats["dup"] += 1
            continue

        counter += 1
        dst_name = f"{label}_{counter:04d}.jpg"
        dst_path = os.path.join(target_dir, dst_name)
        while os.path.exists(dst_path):
            counter += 1
            dst_name = f"{label}_{counter:04d}.jpg"
            dst_path = os.path.join(target_dir, dst_name)

        if not dry_run:
            shutil.copy2(src_path, dst_path)
        target_idx[h] = dst_path
        stats["copied"] += 1

    print(f"[{'DRY-RUN' if dry_run else 'DONE'}] {label}: "
          f"{stats['copied']} baru, {stats['dup']} duplikat dilewati, "
          f"{stats['conflict']} konflik label dilewati")
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hadi-src", required=True, help="Folder hadi dari dataset lama")
    parser.add_argument("--unknown-src", required=True, help="Folder unknown dari dataset lama")
    parser.add_argument("--dry-run", action="store_true",
                         help="Cuma hitung, tidak menyalin apa pun")
    args = parser.parse_args()

    hadi_target = TARGET_DIRS["hadi"]
    unknown_target = TARGET_DIRS["unknown"]

    # index awal tiap kelas tujuan, dipakai buat deteksi konflik silang
    hadi_idx_for_conflict = build_index(hadi_target)
    unknown_idx_for_conflict = build_index(unknown_target)

    total = {"copied": 0, "dup": 0, "conflict": 0}

    r1 = merge_class("hadi", args.hadi_src, hadi_target,
                      unknown_idx_for_conflict, args.dry_run)
    r2 = merge_class("unknown", args.unknown_src, unknown_target,
                      hadi_idx_for_conflict, args.dry_run)

    for r in (r1, r2):
        for k in total:
            total[k] += r[k]

    print("=" * 60)
    print(f"[SUMMARY] Total baru: {total['copied']}, "
          f"duplikat: {total['dup']}, konflik: {total['conflict']}")
    print(f"[INFO] Total sekarang -> hadi {len(list_images(hadi_target))}, "
          f"unknown {len(list_images(unknown_target))}"
          + (" (dry-run, belum berubah)" if args.dry_run else ""))

    if args.dry_run:
        print("[NEXT] Kalau hasil di atas sudah sesuai, jalankan lagi tanpa --dry-run")
    else:
        print("[NEXT] python scripts/audit_dataset.py -> split_dataset.py -> train_classifier.py")


if __name__ == "__main__":
    main()
