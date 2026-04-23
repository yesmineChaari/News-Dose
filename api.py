import httpx
import psycopg2
import pandas as pd
import chromadb
import json
import google.generativeai as genai

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from typing import Optional

from config import (
    DB_CONFIG, CHROMA_PATH, CHROMA_COLLECTION,
    CLUSTERS_PATH, SEMANTIC_SIMILARITY_THRESHOLD,
    GENAI_API_KEY, GEMINI_MODEL_ID,
)

app = FastAPI(title="News Aggregator API")

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
chroma_collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)

if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)
    gemini_model = genai.GenerativeModel(GEMINI_MODEL_ID)
else:
    gemini_model = None


def query_db(sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = psycopg2.connect(**DB_CONFIG)
    df = pd.read_sql(sql, conn, params=params)
    conn.close()
    return df


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/latest")
def latest_articles(limit: int = 10):
    df = query_db("SELECT * FROM headlines ORDER BY scraped_at DESC LIMIT %s", (limit,))
    return df.to_dict(orient="records")


@app.get("/category/{category_name}")
def articles_by_category(category_name: str, limit: int = 10):
    df = query_db(
        "SELECT * FROM headlines WHERE LOWER(category) = LOWER(%s) ORDER BY scraped_at DESC LIMIT %s",
        (category_name, limit),
    )
    if df.empty:
        raise HTTPException(status_code=404, detail="Category not found")
    return df.to_dict(orient="records")


@app.get("/source/{source_name}")
def articles_by_source(source_name: str, limit: int = 10):
    df = query_db(
        "SELECT * FROM headlines WHERE LOWER(source) = LOWER(%s) ORDER BY scraped_at DESC LIMIT %s",
        (source_name, limit),
    )
    if df.empty:
        raise HTTPException(status_code=404, detail="Source not found")
    return df.to_dict(orient="records")


@app.get("/filter")
def articles_by_filter(
    category: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 50,
):
    sql = "SELECT * FROM headlines"
    conditions = []
    params = []

    if category:
        conditions.append("LOWER(category) = LOWER(%s)")
        params.append(category)
    if source:
        conditions.append("LOWER(source) = LOWER(%s)")
        params.append(source)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY scraped_at DESC LIMIT %s"
    params.append(limit)

    df = query_db(sql, tuple(params))
    if df.empty:
        raise HTTPException(status_code=404, detail="No articles found for this filter")
    return df.to_dict(orient="records")


@app.get("/clustered")
def clustered_stories(
    limit: int = 50,
    category: Optional[str] = None,
    source: Optional[str] = None,
):
    if not CLUSTERS_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Cluster cache not found. Run the scrapers pipeline to build it.",
        )

    try:
        with CLUSTERS_PATH.open("r", encoding="utf-8") as f:
            clusters = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load clusters cache: {e}")

    if not isinstance(clusters, list):
        return []

    def article_matches(a: dict) -> bool:
        if category and str(a.get("category", "")).lower() != category.lower():
            return False
        if source and str(a.get("source", "")).lower() != source.lower():
            return False
        return True

    filtered_clusters = []
    for cluster in clusters:
        if not isinstance(cluster, list):
            continue

        if not category and not source:
            if len(cluster) > 1:
                filtered_clusters.append(cluster)
            continue

        sub = [a for a in cluster if isinstance(a, dict) and article_matches(a)]
        if len(sub) > 1:
            filtered_clusters.append(sub)

    return filtered_clusters[:limit]


@app.get("/semantic_search")
def semantic_search(
    query: str,
    category: Optional[str] = None,
    source: Optional[str] = None,
):
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty")

    try:
        results = chroma_collection.query(query_texts=[query], n_results=10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {e}")

    metadatas_list = results.get("metadatas") or []
    distances_list = results.get("distances") or []

    if not metadatas_list:
        return []

    metadatas = metadatas_list[0]
    distances = distances_list[0] if distances_list else [None] * len(metadatas)

    def metadata_matches(meta: dict | None) -> bool:
        if not isinstance(meta, dict):
            return False
        if category and str(meta.get("category", "")).lower() != category.lower():
            return False
        if source and str(meta.get("source", "")).lower() != source.lower():
            return False
        return True

    filtered = []
    for meta, dist in zip(metadatas, distances):
        if dist is None:
            if metadata_matches(meta):
                filtered.append(meta)
            continue
        similarity = 1 - dist
        if similarity >= SEMANTIC_SIMILARITY_THRESHOLD and metadata_matches(meta):
            meta = dict(meta) if meta else {}
            meta["similarity"] = float(similarity)
            filtered.append(meta)

    if not filtered:
        fallback = []
        for meta, dist in zip(metadatas, distances):
            if not metadata_matches(meta):
                continue
            item = dict(meta)
            item["similarity"] = float(1 - dist) if dist is not None else None
            fallback.append(item)
        filtered = fallback

    return filtered


@app.get("/summarize")
async def summarize(url: str):
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL must not be empty")

    if gemini_model is None:
        raise HTTPException(
            status_code=500,
            detail="Gemini model not configured. Set API_KEY in your .env file.",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Article returned HTTP {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch article: {e}")

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        article_text = " ".join(p for p in paragraphs if p)[:5000]

        if not article_text:
            return {"summary": "Could not extract text from this article."}

        prompt = (
            "Provide a brief, 3-bullet-point summary of the following news article:\n\n"
            f"{article_text}"
        )

        ai_response = await run_in_threadpool(gemini_model.generate_content, prompt)
        summary_text = getattr(ai_response, "text", None) or "No summary could be generated."

        return {"summary": summary_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {e}")
