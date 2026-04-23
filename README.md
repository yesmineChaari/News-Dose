# News Dose

News Dose is a Python-based news aggregation project that scrapes headlines from multiple sources, stores structured data in PostgreSQL, indexes semantic vectors in ChromaDB, and serves results through a FastAPI backend with a Streamlit frontend.

## Features

- Multi-source scraping (BBC, CNN, The Guardian)
- Data cleaning and category normalization
- Structured article storage in PostgreSQL
- Semantic search powered by ChromaDB
- Clustered story view (related coverage across sources)
- Article summarization endpoint using Gemini
- Streamlit UI with filters, paging, clustered mode, and semantic search

## Tech Stack

- Python
- PostgreSQL
- ChromaDB
- FastAPI
- Streamlit
- BeautifulSoup
- Google Generative AI SDK

## Project Structure

├── run_scrapers.py        # Main pipeline runner
├── api.py                 # FastAPI application and endpoints
├── app.py                 # Streamlit frontend
├── config.py              # Central configuration and environment variables

├── scraper/               # Source-specific scrapers
│   ├── bbc.py
│   ├── cnn.py
│   └── guardian.py

├── data/
│   ├── clean_data.py      # Cleans raw CSV files
│   ├── insert_data.py     # Inserts into Postgres & Chroma, builds cluster cache
│   ├── db_setup.py        # Ensures database schema exists
│   │
│   ├── raw/               # Raw scraped output
│   ├── cleaned/           # Cleaned CSV output
│   └── clustered_cache.json  # Cached cluster groups used by API

├── chroma_db/             # Local Chroma persistence directory

## How It Works

### Ingestion Pipeline

Running `run_scrapers.py` performs this sequence:

1. Ensures DB schema exists (`data/db_setup.py`)
2. Clears `headlines` table in PostgreSQL
3. Clears and recreates Chroma collection (`news_articles`)
4. Clears `data/raw` and `data/cleaned`
5. Scrapes BBC/CNN/Guardian into raw CSV/JSON
6. Cleans raw CSV files (`data/clean_data.py`)
7. Inserts cleaned rows into PostgreSQL and Chroma (`data/insert_data.py`)
8. Builds clusters and writes `data/clustered_cache.json`

### Data Stores

- PostgreSQL is used for exact/filter queries and list views
- ChromaDB is used for semantic similarity search and clustering support

## Prerequisites

- Python 3.11+ (project currently runs in Python 3.14 venv)
- PostgreSQL running and reachable
- Optional: Gemini API key for summarization endpoint

## Environment Configuration

Create a `.env` file in the project root (if not already present):

```env
DB_HOST=localhost
DB_PORT=5434
DB_NAME=news
DB_USER=postgres
DB_PASSWORD=password

API_KEY=your_gemini_api_key_here
GEMINI_MODEL_ID=gemini-1.5-flash
```

Notes:

- `API_KEY` is required only for `/summarize`
- Default DB values are also defined in `config.py`


## Running the Project

### 1) Run the ingestion pipeline

```powershell
.\venv\Scripts\python.exe run_scrapers.py
```

### 2) Start the API (Terminal 1)

```powershell
.\venv\Scripts\python.exe -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### 3) Start Streamlit UI (Terminal 2)

```powershell
streamlit run app.py
```

Open:

- UI: http://localhost:8501
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## API Endpoints

- `GET /health`: API health check
- `GET /latest?limit=10`: latest articles
- `GET /category/{category_name}?limit=10`: articles by category
- `GET /source/{source_name}?limit=10`: articles by source
- `GET /filter?category=&source=&limit=50`: filtered list view
- `GET /clustered?category=&source=&limit=50`: clustered related stories (from cache)
- `GET /semantic_search?query=...`: semantic search via ChromaDB
- `GET /summarize?url=...`: AI summary of a full article page

## Similarity and Clustering Thresholds

Defined in `config.py`:

- `SEMANTIC_SIMILARITY_THRESHOLD = 0.4`
- `CLUSTER_DISTANCE_THRESHOLD = 0.4`

Interpretation:

- Semantic endpoint computes `similarity = 1 - distance` and filters by similarity threshold
- Clustering keeps candidates where distance is below cluster threshold

