import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

CATEGORIES = {
    "News": "https://www.bbc.com/news",
    "Sport": "https://www.bbc.com/sport",
    "Business": "https://www.bbc.com/business",
    "Innovation": "https://www.bbc.com/innovation",
    "Culture": "https://www.bbc.com/culture",
    "Arts": "https://www.bbc.com/arts",
    "Earth": "https://www.bbc.com/future-planet",
    "Travel": "https://www.bbc.com/travel",
}

HEADLINE_SELECTOR = '[data-testid="card-headline"]'
SPORT_HEADLINE_SELECTOR = "h3.gs-c-promo-heading__title"
DESCRIPTION_SELECTOR = '[data-testid="card-description"]'
SPORT_DESCRIPTION_SELECTOR = "p.gs-c-promo-summary"
CARD_SELECTOR = '[data-testid="card-text-wrapper"]'
SPORT_CARD_SELECTOR = "li.gs-c-promo"


def _scrape_category(category: str, url: str, headers: dict) -> list[dict]:
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"  [BBC] Failed to fetch {category}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    is_sport = category == "Sport"
    card_sel = SPORT_CARD_SELECTOR if is_sport else CARD_SELECTOR
    h_sel = SPORT_HEADLINE_SELECTOR if is_sport else HEADLINE_SELECTOR
    d_sel = SPORT_DESCRIPTION_SELECTOR if is_sport else DESCRIPTION_SELECTOR

    cards = soup.select(card_sel)

    if cards:
        for card in cards:
            headline_el = card.select_one(h_sel)
            description_el = card.select_one(d_sel)

            if not headline_el:
                continue

            text = headline_el.get_text(strip=True)
            description = description_el.get_text(strip=True) if description_el else ""

            link_tag = headline_el.find_parent("a") or card.find("a")
            article_url = ""
            if link_tag and link_tag.get("href"):
                article_url = urljoin("https://www.bbc.com", link_tag["href"])

            if text:
                results.append({
                    "headline": text,
                    "description": description,
                    "source": "BBC",
                    "category": category,
                    "scraped_at": datetime.now(),
                    "url": article_url,
                })
    else:
        headline_elements = soup.select(h_sel)
        description_elements = soup.select(d_sel)

        for idx, h in enumerate(headline_elements):
            text = h.get_text(strip=True)
            description = description_elements[idx].get_text(strip=True) if idx < len(description_elements) else ""

            link_tag = h.find_parent("a")
            article_url = ""
            if link_tag and link_tag.get("href"):
                article_url = urljoin("https://www.bbc.com", link_tag["href"])

            if text:
                results.append({
                    "headline": text,
                    "description": description,
                    "source": "BBC",
                    "category": category,
                    "scraped_at": datetime.now(),
                    "url": article_url,
                })

    print(f"  [BBC] {category}: {len(results)} articles")
    return results


def get_bbc_headlines_by_category() -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0"}
    results = []

    for category, url in CATEGORIES.items():
        articles = _scrape_category(category, url, headers)
        results.extend(articles)

    print(f"[BBC] Total: {len(results)} articles")
    return results


if __name__ == "__main__":
    data = get_bbc_headlines_by_category()
    print(f"\nTotal headlines found: {len(data)}")
