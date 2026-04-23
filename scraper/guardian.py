import feedparser
from datetime import datetime
from bs4 import BeautifulSoup

GUARDIAN_FEEDS = {
    "World": "https://www.theguardian.com/world/rss",
    "Business": "https://www.theguardian.com/uk/business/rss",
    "Technology": "https://www.theguardian.com/uk/technology/rss",
    "Culture": "https://www.theguardian.com/culture/rss",
    "Sport": "https://www.theguardian.com/uk/sport/rss",
    "Environment": "https://www.theguardian.com/environment/rss",
    "Lifestyle": "https://www.theguardian.com/lifeandstyle/rss",
}


def _clean_html(html_text: str) -> str:
    if not html_text:
        return ""
    return BeautifulSoup(html_text, "html.parser").get_text(separator=" ", strip=True)


def _scrape_feed(category: str, url: str) -> list[dict]:
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"  [Guardian] Failed to fetch {category}: {e}")
        return []

    if not feed.entries:
        print(f"  [Guardian] {category}: 0 articles (empty feed)")
        return []

    results = []
    for entry in feed.entries:
        try:
            results.append({
                "headline": entry.title,
                "description": _clean_html(entry.get("summary", "")),
                "source": "The Guardian",
                "category": category,
                "scraped_at": datetime.now(),
                "url": entry.get("link", ""),
            })
        except Exception as e:
            print(f"  [Guardian] Skipping entry in {category}: {e}")

    print(f"  [Guardian] {category}: {len(results)} articles")
    return results


def get_guardian_headlines_by_category() -> list[dict]:
    results = []

    for category, url in GUARDIAN_FEEDS.items():
        articles = _scrape_feed(category, url)
        results.extend(articles)

    print(f"[Guardian] Total: {len(results)} articles")
    return results


if __name__ == "__main__":
    data = get_guardian_headlines_by_category()
    print(f"\nTotal Guardian headlines collected: {len(data)}")
