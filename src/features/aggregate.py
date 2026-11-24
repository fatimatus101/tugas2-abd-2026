"""Tahap 3a - agregasi ringan untuk dashboard (Streamlit TIDAK boleh membaca 1,6 juta baris)."""
import duckdb

from src.common import load_config, abs_path

STOP = [
    "that", "this", "with", "have", "just", "your", "what", "when", "will", "from", "they", "been", "were",
    "there", "their", "about", "would", "could", "should", "than", "then", "them", "these", "those", "into",
    "over", "also", "more", "some", "very", "much", "here", "only", "http", "https", "www", "quot", "amp",
    "does", "dont", "didnt", "cant", "doesnt", "which", "while", "being", "because", "going", "still",
]


def run() -> None:
    cfg = load_config()
    src = abs_path(cfg["paths"]["interim_parquet"]).as_posix()
    out = abs_path(f"{cfg['paths']['processed_dir']}/_").parent
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{cfg['duckdb']['memory_limit']}'")
    con.execute(f"SET threads={cfg['duckdb']['threads']}")

    def save(sql: str, name: str) -> None:
        con.execute(f"COPY ({sql}) TO '{(out / name).as_posix()}' (FORMAT PARQUET)")

    save(f"""SELECT date_trunc('day', posted_at) AS day, label, count(*) AS n
             FROM read_parquet('{src}') WHERE posted_at IS NOT NULL GROUP BY 1, 2 ORDER BY 1, 2""", "agg_daily.parquet")
    save(f"""SELECT CAST(extract('hour' FROM posted_at) AS INTEGER) AS hour_of_day, label, count(*) AS n
             FROM read_parquet('{src}') WHERE posted_at IS NOT NULL GROUP BY 1, 2 ORDER BY 1, 2""", "agg_hourly.parquet")
    save(f"""SELECT CAST(floor(length(text) / 10) * 10 AS INTEGER) AS len_bucket, label, count(*) AS n
             FROM read_parquet('{src}') GROUP BY 1, 2 ORDER BY 1, 2""", "agg_length.parquet")

    stop = ", ".join(f"'{w}'" for w in STOP)
    save(f"""
        WITH tok AS (
            SELECT label,
                   unnest(regexp_extract_all(
                       regexp_replace(lower(text), 'https?://\\S+|@\\w+', ' ', 'g'), '[a-z]{{4,}}')) AS word
            FROM read_parquet('{src}')
        )
        SELECT label, word, count(*) AS n FROM tok WHERE word NOT IN ({stop})
        GROUP BY label, word
        QUALIFY row_number() OVER (PARTITION BY label ORDER BY count(*) DESC) <= 50
        ORDER BY label, n DESC""", "agg_top_words.parquet")
    print("Agregat tersimpan di", out)


if __name__ == "__main__":
    run()
