"""Tahap 2 - CLEANING: Sentiment140 mentah -> Parquet bersih (out-of-core via DuckDB).

Menulis reports/cleaning_report.json sebagai BUKTI syarat >1 juta baris ATAU >500 MB.
Mendukung dua sumber: CSV asli Stanford (latin-1, tanpa header) atau Parquet mirror HF.
"""
import json

import duckdb

from src.common import load_config, abs_path

CSV_COLS = "{'polarity':'INTEGER','id':'BIGINT','date':'VARCHAR','query_string':'VARCHAR','user':'VARCHAR','text':'VARCHAR'}"


def _create_raw_view(con, raw_dir, cfg) -> tuple[str, float, bool]:
    csv = raw_dir / cfg["dataset"]["members"]["train"]
    pq = raw_dir / cfg["dataset"]["fallback_name"]
    used_ignore = False
    if csv.exists():
        base = f"read_csv('{csv.as_posix()}', header=false, columns={CSV_COLS}, encoding='latin-1'"
        try:
            con.execute(f"CREATE VIEW raw AS SELECT polarity, id AS tweet_id, date AS date_str, \"user\" AS username, text FROM {base})")
            con.execute("SELECT count(*) FROM raw").fetchone()
        except duckdb.Error:
            con.execute("DROP VIEW IF EXISTS raw")
            used_ignore = True
            con.execute(f"CREATE VIEW raw AS SELECT polarity, id AS tweet_id, date AS date_str, \"user\" AS username, text FROM {base}, ignore_errors=true)")
        return csv.name, csv.stat().st_size / 1e6, used_ignore
    if pq.exists():
        con.execute(
            f"CREATE VIEW raw AS SELECT CAST(sentiment AS INTEGER) AS polarity, CAST(NULL AS BIGINT) AS tweet_id, "
            f"date AS date_str, \"user\" AS username, text FROM read_parquet('{pq.as_posix()}')"
        )
        return pq.name, pq.stat().st_size / 1e6, False
    raise SystemExit("Belum ada file mentah. Jalankan: python -m src.ingestion.download")


def run(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    raw_dir = abs_path(f"{cfg['dataset']['raw_dir']}/_").parent
    out = abs_path(cfg["paths"]["interim_parquet"])
    report_path = abs_path(f"{cfg['paths']['reports_dir']}/cleaning_report.json")

    con = duckdb.connect()
    con.execute(f"SET memory_limit='{cfg['duckdb']['memory_limit']}'")
    con.execute(f"SET threads={cfg['duckdb']['threads']}")
    source_name, source_mb, used_ignore = _create_raw_view(con, raw_dir, cfg)

    n_raw = con.execute("SELECT count(*) FROM raw").fetchone()[0]
    n_valid = con.execute(
        "SELECT count(*) FROM raw WHERE polarity IN (0, 4) AND text IS NOT NULL AND length(trim(text)) > 0"
    ).fetchone()[0]

    con.execute(f"""
        COPY (
            SELECT DISTINCT
                tweet_id,
                try_strptime(replace(date_str, ' PDT', ''), '%a %b %d %H:%M:%S %Y') AS posted_at,
                username,
                trim(text)                                   AS text,
                CASE polarity WHEN 4 THEN 1 ELSE 0 END       AS label
            FROM raw
            WHERE polarity IN (0, 4)
              AND text IS NOT NULL AND length(trim(text)) > 0
        ) TO '{out.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    p = out.as_posix()
    n_clean = con.execute(f"SELECT count(*) FROM read_parquet('{p}')").fetchone()[0]
    null_dt = con.execute(f"SELECT count(*) FROM read_parquet('{p}') WHERE posted_at IS NULL").fetchone()[0]
    dist = dict(con.execute(f"SELECT label, count(*) FROM read_parquet('{p}') GROUP BY 1 ORDER BY 1").fetchall())

    report = {
        "dataset": cfg["dataset"]["name"],
        "source_file": source_name,
        "csv_ignore_errors_used": used_ignore,
        "rows_raw": n_raw,
        "rows_valid_label_and_text": n_valid,
        "rows_clean": n_clean,
        "rows_dropped": n_raw - n_clean,
        "duplicates_removed": n_valid - n_clean,
        "null_posted_at": null_dt,
        "label_counts": {str(k): v for k, v in dist.items()},
        "raw_file_mb": round(source_mb, 1),
        "meets_min_rows": n_raw > cfg["requirements"]["min_rows"],
        "meets_min_size": source_mb > cfg["requirements"]["min_size_mb"],
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    run()
