from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from .models import Ad

BASE_URL = "https://www.olx.ua"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "uk-UA,uk;q=0.9",
}


async def fetch_ads(search_url: str, timeout: float = 15.0) -> list[Ad]:
    """Завантажує сторінку пошуку OLX і повертає список знайдених оголошень."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=timeout, follow_redirects=True) as client:
        response = await client.get(search_url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    cards = soup.select('div[data-testid="l-card"]')

    ads: list[Ad] = []
    for card in cards:
        ad_id = card.get("id")
        link_tag = card.select_one('a[data-testid="card-title-link"]')
        if not ad_id or not link_tag:
            continue

        href = link_tag.get("href", "")
        url = href if href.startswith("http") else f"{BASE_URL}{href}"

        title = link_tag.get("aria-label") or link_tag.get_text(strip=True)
        price_tag = card.select_one('p[data-testid="ad-price"]')
        location_tag = card.select_one('p[data-testid="location-date"]')
        image_tag = card.select_one("img")

        ads.append(
            Ad(
                ad_id=str(ad_id),
                title=title.strip(),
                price=price_tag.get_text(" ", strip=True) if price_tag else "Ціна не вказана",
                location_date=location_tag.get_text(" ", strip=True) if location_tag else "",
                url=url,
                image_url=image_tag.get("src") if image_tag else None,
            )
        )

    return ads
