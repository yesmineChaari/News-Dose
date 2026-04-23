import pandas as pd
import psycopg2
import chromadb
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import (
    DB_CONFIG, CHROMA_PATH, CHROMA_COLLECTION,
    CLEAN_DIR, CLUSTERS_PATH, CANONICAL_CATEGORIES,
    CLUSTER_DISTANCE_THRESHOLD,
)

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
chroma_collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)


def safe_str(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def normalize_category(cat: str) -> str | None:
    if not cat:
        return None
    return CANONICAL_CATEGORIES.get(cat.strip().lower(), cat.strip()) or None


def clean_description(desc) -> str:
    text = safe_str(desc)
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def insert_csv_to_db(csv_file: Path, conn) -> None:
    df = pd.read_csv(csv_file)
    df["description"] = df["description"].apply(clean_description)
    df["category"] = df["category"].apply(lambda c: normalize_category(safe_str(c)))

    if df["scraped_at"].dtype == object:
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce")

    inserted = 0

    with conn.cursor() as cur:
        for _, row in df.iterrows():
            headline = safe_str(row.get("headline"))
            description = safe_str(row.get("description"))
            source = safe_str(row.get("source"))
            category = normalize_category(safe_str(row.get("category")))
            url = safe_str(row.get("url"))
            scraped_at = row.get("scraped_at")

            if not headline or not source:
                continue

            try:
                cur.execute("""
                    INSERT INTO headlines (headline, description, source, category, scraped_at, url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (headline, source) DO NOTHING
                """, (headline, description, source, category, scraped_at, url))
            except Exception as e:
                print(f"  DB insert error for '{headline}': {e}")
                continue

            document_text = f"{headline}. {description}".strip()
            chroma_id = f"{source}::{url}" if url else f"{source}::{headline}"

            if document_text and chroma_id:
                try:
                    chroma_collection.add(
                        documents=[document_text],
                        metadatas=[{
                            "headline": headline,
                            "description": description,
                            "link": url,
                            "source": source,
                            "category": category or "",
                        }],
                        ids=[chroma_id],
                    )
                except Exception as e:
                    print(f"  ChromaDB insert error for '{headline}': {e}")

            inserted += 1

    conn.commit()
    print(f"  {csv_file.name}: {inserted} rows processed")


def build_and_store_clusters(limit: int | None = None) -> None:
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Could not connect to DB for clustering: {e}")
        return

    sql = "SELECT * FROM headlines ORDER BY scraped_at DESC"
    params = ()
    if limit is not None:
        sql += " LIMIT %s"
        params = (limit,)

    try:
        df = pd.read_sql(sql, conn, params=params)
    except Exception as e:
        print(f"Error reading articles for clustering: {e}")
        conn.close()
        return

    conn.close()

    if df.empty:
        print("No articles found to cluster.")
        CLUSTERS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CLUSTERS_PATH.write_text("[]", encoding="utf-8")
        return

    articles = df.to_dict(orient="records")

    for article in articles:
        url = article.get("url") or ""
        source = article.get("source") or ""
        article["link"] = f"{source}::{url}" if url else f"{source}::{article.get('headline', '')}"

    articles_by_link = {a["link"]: a for a in articles if a.get("link")}
    visited_links: set[str] = set()
    clusters: list[list[dict]] = []

    for article in articles:
        link = article.get("link")
        if not link or link in visited_links:
            continue

        visited_links.add(link)
        current_cluster = [article]
        query_text = f"{article.get('headline', '')} {article.get('description', '')}"

        try:
            results = chroma_collection.query(query_texts=[query_text], n_results=10)
        except Exception as e:
            print(f"ChromaDB query error: {e}")
            clusters.append(current_cluster)
            continue

        metadatas_list = results.get("metadatas") or []
        distances_list = results.get("distances") or []

        if metadatas_list and distances_list:
            for meta, dist in zip(metadatas_list[0], distances_list[0]):
                if meta is None or dist is None or dist >= CLUSTER_DISTANCE_THRESHOLD:
                    continue

                candidate_link = None
                if isinstance(meta, dict):
                    candidate_meta_url = meta.get("link") or ""
                    candidate_source = meta.get("source") or ""
                    candidate_link = f"{candidate_source}::{candidate_meta_url}" if candidate_meta_url else None

                if not candidate_link or candidate_link not in articles_by_link:
                    continue

                if candidate_link in visited_links:
                    continue

                current_cluster.append(articles_by_link[candidate_link])
                visited_links.add(candidate_link)

        clusters.append(current_cluster)

    try:
        CLUSTERS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CLUSTERS_PATH.open("w", encoding="utf-8") as f:
            json.dump(clusters, f, default=str, ensure_ascii=False)
        print(f"Stored {len(clusters)} clusters to {CLUSTERS_PATH}")
    except Exception as e:
        print(f"Failed to write clusters cache: {e}")


def main() -> None:
    csv_files = list(CLEAN_DIR.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {CLEAN_DIR}")
        return

    conn = psycopg2.connect(**DB_CONFIG)

    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS headlines (
                id SERIAL PRIMARY KEY,
                headline TEXT,
                description TEXT,
                source TEXT,
                category TEXT,
                scraped_at TIMESTAMP,
                url TEXT,
                UNIQUE(headline, source)
            )
        """)
        try:
            cur.execute("ALTER TABLE headlines ADD COLUMN IF NOT EXISTS url TEXT;")
        except Exception:
            pass
        conn.commit()

    for csv_file in csv_files:
        insert_csv_to_db(csv_file, conn)

    conn.close()
    print("All cleaned CSVs inserted into database.")

    build_and_store_clusters()


if __name__ == "__main__":
    main()
