import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin, urlparse

CNN_CATEGORIES = {
    "World": "https://edition.cnn.com/world",
    "Business": "https://edition.cnn.com/business",
    "Technology": "https://edition.cnn.com/business/tech",
    "Health": "https://edition.cnn.com/health",
    "Entertainment": "https://edition.cnn.com/entertainment",
    "Sports": "https://edition.cnn.com/sport",
    "Travel": "https://edition.cnn.com/travel",
    "Style": "https://edition.cnn.com/style",
    "Markets": "https://edition.cnn.com/markets",
    "Science": "https://edition.cnn.com/science",
    "Climate": "https://edition.cnn.com/climate",
    "Weather": "https://edition.cnn.com/weather",
}

HEADLINE_SELECTOR = ".container__headline-text"


def _is_video_url(url: str) -> bool:
    if not url:
        return False
    path = urlparse(url).path.lower()
    return "/video/" in path or "/videos/" in path or path.endswith("-vrtc-digvid")


def _scrape_category(category: str, url: str, headers: dict) -> list[dict]:
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"  [CNN] Failed to fetch {category}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    headline_elements = soup.select(HEADLINE_SELECTOR)
    results = []

    for h in headline_elements:
        text = h.get_text(strip=True)
        if not text:
            continue

        article_url = ""
        link_tag = h.find_parent("a")
        if link_tag and link_tag.get("href"):
            article_url = urljoin("https://edition.cnn.com", link_tag["href"])

        if _is_video_url(article_url):
            continue

        results.append({
            "headline": text,
            "description": "",
            "source": "CNN",
            "category": category,
            "scraped_at": datetime.now(),
            "url": article_url,
        })

    print(f"  [CNN] {category}: {len(results)} articles")
    return results


def get_cnn_headlines_by_category() -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0"}
    results = []

    for category, url in CNN_CATEGORIES.items():
        articles = _scrape_category(category, url, headers)
        results.extend(articles)

    print(f"[CNN] Total: {len(results)} articles")
    return results


if __name__ == "__main__":
    data = get_cnn_headlines_by_category()
    print(f"\nTotal headlines collected: {len(data)}")
