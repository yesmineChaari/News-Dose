from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "news"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "port": int(os.getenv("DB_PORT", 5434)),
}

CHROMA_PATH = "./chroma_db"
CHROMA_COLLECTION = "news_articles"

RAW_DIR = Path("data/raw")
CLEAN_DIR = Path("data/cleaned")
CLUSTERS_PATH = Path("data/clustered_cache.json")

CLUSTER_DISTANCE_THRESHOLD = 0.4
SEMANTIC_SIMILARITY_THRESHOLD = 0.4

GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-1.5-flash")
GENAI_API_KEY = os.getenv("API_KEY")

CANONICAL_CATEGORIES = {
    "world": "World",
    "business": "Business",
    "markets": "Business",
    "tech": "Technology",
    "technology": "Technology",
    "science": "Science",
    "health": "Health",
    "sport": "Sports",
    "sports": "Sports",
    "culture": "Culture",
    "entertainment": "Entertainment",
    "travel": "Travel",
    "climate": "Climate",
    "lifestyle": "Lifestyle",
    "innovation": "Technology",
    "arts": "Culture",
    "earth": "Climate",
}

JUNK_KEYWORDS = [
    "sudoku", "crossword", "killer sudoku", "prize crossword",
    "cryptic crossword", "quick crossword", "puzzle", "quiz",
    "wordle", "print version", "click here to access",
    "sign up", "subscribe here", "newsletter",
    "in pictures", "watch:", "video:",
]

JUNK_HEADLINE_PATTERNS = [
    r"^sign up",
    r"^subscribe",
    r"^watch\b",
    r"best of our",
    r"delivered to your inbox",
    r"^sign up to",
    r"^sign up for",
]
