# Panduan Dataset — Tugas 2 (Data Product)

Folder ini digunakan untuk menempatkan dataset yang dipakai dalam dashboard analitik.

> **PENTING:** Jangan pernah melakukan `git commit` atau `git push` file dataset besar (>100MB) langsung ke repository GitHub! File data besar harus diabaikan melalui `.gitignore`.

---

## Informasi Dataset Kelompok

- **Nama Dataset:** [Sentiment140 (Go, Bhayani & Huang, Stanford, 2009)]
- **Sumber Data:** [https://cs.stanford.edu/people/alecmgo/trainingandtestdata.zip / https://huggingface.co/datasets/stanfordnlp/sentiment140]
- **Ukuran File Mentah:** [±226 MB]
- **Jumlah Baris:** [1.600.000 baris]
- **Format File:** [CSV]

---

## Instruksi Pengunduhan & Penyiapan Data

Tuliskan perintah atau script untuk mengunduh dataset secara otomatis:

```bash

python -m src.ingestion.download
python -m src.cleaning.clean        # -> data/interim/tweets_clean.parquet + reports/cleaning_report.json
python -m src.features.aggregate    # -> data/processed/agg_*.parquet

atau 

curl -L -o data/raw/trainingandtestdata.zip https://cs.stanford.edu/people/alecmgo/trainingandtestdata.zip
python -m zipfile -e data/raw/trainingandtestdata.zip data/raw/

```

---

## Skema Struktur Kolom Data

| Nama Kolom | Tipe Data | Deskripsi Makna Bisnis |
|------------|:---------:|------------------------|
| `polarity` | Int32 | Label sentimen: 0 = negatif, 2 = netral, 4 = positif |
| `id` | Int64 | ID unik tweet |
| `date` | Utf8 | Waktu tweet |
| `query` | Utf8 | Kata kunci pencarian saat pengumpulan data |
| `user` | Utf8 | 	Nama pengguna penulis tweet |
| `text` | Utf8 | isi tweet |

