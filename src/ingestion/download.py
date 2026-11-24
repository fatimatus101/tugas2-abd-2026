"""Tahap 1 - INGESTION: unduh Sentiment140 (zip Stanford; fallback Parquet HF), resumable + batas ukuran."""
import sys
import zipfile

import requests
from tqdm import tqdm

from src.common import load_config, abs_path


def remote_size(url: str) -> int | None:
    r = requests.head(url, allow_redirects=True, timeout=60)
    r.raise_for_status()
    n = r.headers.get("content-length")
    return int(n) if n else None


def guarded_download(url: str, dest, max_mb: float) -> None:
    size = remote_size(url)
    if size is None:
        print("Ukuran file tidak diketahui; dibatalkan demi keamanan.")
        sys.exit(1)
    print(f"{dest.name}: {size / 1e6:.1f} MB (batas {max_mb} MB)")
    if size / 1e6 > max_mb:
        print("DIBATALKAN: melebihi batas ukuran.")
        sys.exit(1)

    done = dest.stat().st_size if dest.exists() else 0
    if done >= size:
        print("Sudah lengkap:", dest.name)
        return
    headers = {"Range": f"bytes={done}-"} if done else {}
    with requests.get(url, stream=True, headers=headers, timeout=60) as r:
        r.raise_for_status()
        resumed = r.status_code == 206
        with open(dest, "ab" if resumed else "wb") as f, tqdm(
            total=size, initial=done if resumed else 0, unit="B", unit_scale=True, desc=dest.name
        ) as bar:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                bar.update(len(chunk))


def extract_members(zip_path, members: dict, out_dir) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        names = {n.split("/")[-1]: n for n in zf.namelist()}
        for key, fname in members.items():
            if fname not in names:
                print(f"PERINGATAN: {fname} tidak ada di zip (isi: {sorted(names)})")
                continue
            with zf.open(names[fname]) as src, open(out_dir / fname, "wb") as dst:
                while chunk := src.read(1 << 20):
                    dst.write(chunk)
            print("Diekstrak:", fname)


def main() -> None:
    cfg = load_config()["dataset"]
    raw_dir = abs_path(f"{cfg['raw_dir']}/_").parent
    zip_path = raw_dir / cfg["zip_name"]
    try:
        guarded_download(cfg["url"], zip_path, cfg["max_download_mb"])
        extract_members(zip_path, cfg["members"], raw_dir)
    except (requests.RequestException, zipfile.BadZipFile) as e:
        print(f"Sumber utama gagal ({e!r}). Mencoba fallback Parquet Hugging Face...")
        guarded_download(cfg["fallback_url"], raw_dir / cfg["fallback_name"], cfg["max_download_mb"])
    print("Selesai.")


if __name__ == "__main__":
    main()
