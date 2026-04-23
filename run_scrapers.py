import sys
import subprocess
import psycopg2
import pandas as pd
import chromadb

from pathlib import Path
from config import DB_CONFIG, RAW_DIR, CLEAN_DIR, CHROMA_PATH, CHROMA_COLLECTION

from scraper.bbc import get_bbc_headlines_by_category
from scraper.cnn import get_cnn_headlines_by_category
from scraper.guardian import get_guardian_headlines_by_category

RAW_DIR.mkdir(parents=True, exist_ok=True)
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

SCRAPERS = {
    "bbc": get_bbc_headlines_by_category,
    "cnn": get_cnn_headlines_by_category,
    "guardian": get_guardian_headlines_by_category,
}


def run_step(cmd: list, description: str) -> None:
    print(f"\n[STEP] {description}...")
    result = subprocess.run(cmd, check=True)
    print(f"[OK] {description} done (exit {result.returncode})")


def clear_database() -> None:
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        try:
            cur.execute("TRUNCATE TABLE headlines RESTART IDENTITY;")
        except Exception:
            cur.execute("DELETE FROM headlines;")
        conn.commit()
        cur.close()
        conn.close()
        print("[CLEAN] Cleared existing headlines from database.")
    except Exception as e:
        print(f"[WARN] Could not clear database: {e}")


def clear_chroma_collection() -> None:
    """Reset semantic index so it matches freshly loaded Postgres rows."""
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        try:
            client.delete_collection(CHROMA_COLLECTION)
            print("[CLEAN] Cleared existing Chroma collection.")
        except Exception:
            print("[INFO] Chroma collection did not exist yet; creating fresh one.")

        client.get_or_create_collection(CHROMA_COLLECTION)
    except Exception as e:
        print(f"[WARN] Could not reset Chroma collection: {e}")


def clear_data_folders() -> None:
    for folder in (RAW_DIR, CLEAN_DIR):
        if not folder.exists():
            continue
        removed = sum(1 for f in folder.glob("*") if f.is_file() and not f.unlink())
        print(f"[CLEAN] Cleared {removed} files from {folder}")


def run_scraper(name: str, scraper_func) -> None:
    print(f"\n[SCRAPER] Running scraper: {name.upper()}")

    data = scraper_func()

    if not data:
        print(f"[WARN] No data returned for {name}")
        return

    df = pd.DataFrame(data)
    csv_path = RAW_DIR / f"{name}.csv"
    json_path = RAW_DIR / f"{name}.json"

    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", lines=True, force_ascii=False)

    print(f"[OK] Saved {len(df)} articles -> {csv_path}")


def main() -> None:
    run_step([sys.executable, "data/db_setup.py"], "Setting up database schema")

    clear_database()
    clear_chroma_collection()
    clear_data_folders()

    for name, scraper_func in SCRAPERS.items():
        try:
            run_scraper(name, scraper_func)
        except Exception as e:
            print(f"[ERROR] Error running {name} scraper: {e}")

    run_step([sys.executable, "data/clean_data.py"], "Cleaning scraped CSV files")
    run_step([sys.executable, "data/insert_data.py"], "Inserting data into database")


if __name__ == "__main__":
    main()
