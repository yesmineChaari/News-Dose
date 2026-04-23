import psycopg2
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DB_CONFIG


def setup_database() -> None:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    print("Connected to database")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS headlines (
            id SERIAL PRIMARY KEY,
            headline TEXT NOT NULL,
            description TEXT,
            source TEXT NOT NULL,
            category TEXT,
            scraped_at TIMESTAMP,
            url TEXT
        );
    """)

    try:
        cur.execute("ALTER TABLE headlines ADD COLUMN IF NOT EXISTS url TEXT;")
    except Exception:
        pass

    try:
        cur.execute("""
            ALTER TABLE headlines
            ADD CONSTRAINT unique_headline_source
            UNIQUE (headline, source);
        """)
        conn.commit()
        print("Unique constraint added")
    except Exception:
        conn.rollback()
        print("Unique constraint already exists — continuing.")

    cur = conn.cursor()

    indexes = [
        ("idx_news_source", "source"),
        ("idx_news_category", "category"),
        ("idx_news_scraped_at", "scraped_at"),
    ]

    for index_name, column in indexes:
        try:
            cur.execute(f"CREATE INDEX {index_name} ON headlines ({column});")
            print(f"Index {index_name} created")
        except Exception:
            conn.rollback()
            cur = conn.cursor()
            print(f"Index {index_name} already exists — skipping.")

    conn.commit()
    cur.close()
    conn.close()
    print("Database setup complete")


if __name__ == "__main__":
    setup_database()
