from __future__ import annotations

import asyncio
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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


def _with_page(url: str, page: int) -> str:
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "page"]
    query.append(("page", str(page)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _parse_card(card) -> Optional[Ad]:
    ad_id = card.get("id")
    link_tag = card.select_one('a[data-testid="card-title-link"]')
    if not ad_id or not link_tag:
        return None

    href = link_tag.get("href", "")
    url = href if href.startswith("http") else f"{BASE_URL}{href}"

    title = link_tag.get("aria-label") or link_tag.get_text(strip=True)
    price_tag = card.select_one('p[data-testid="ad-price"]')
    location_tag = card.select_one('p[data-testid="location-date"]')
    image_tag = card.select_one("img")

    return Ad(
        ad_id=str(ad_id),
        title=title.strip(),
        price=price_tag.get_text(" ", strip=True) if price_tag else "Ціна не вказана",
        location_date=location_tag.get_text(" ", strip=True) if location_tag else "",
        url=url,
        image_url=image_tag.get("src") if image_tag else None,
    )


async def fetch_ads(search_url: str, timeout: float = 15.0, max_pages: int = 5) -> list[Ad]:
    """Завантажує сторінки пошуку OLX (з пагінацією) і повертає список оголошень."""
    ads: list[Ad] = []
    seen_ids: set[str] = set()

    async with httpx.AsyncClient(headers=HEADERS, timeout=timeout, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            response = await client.get(_with_page(search_url, page))
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            cards = soup.select('div[data-testid="l-card"]')
            if not cards:
                break

            page_ads: list[Ad] = []
            for card in cards:
                ad = _parse_card(card)
                if ad and ad.ad_id not in seen_ids:
                    seen_ids.add(ad.ad_id)
                    page_ads.append(ad)

            if not page_ads:
                break

            ads.extend(page_ads)

            has_next_page = soup.select_one(f'div[data-testid="pagination-wrapper"] a[href*="page={page + 1}"]')
            if not has_next_page:
                break

            await asyncio.sleep(0.3)

    return ads


async def fetch_ad_description(ad_url: str, timeout: float = 15.0) -> Optional[str]:
    """Завантажує сторінку самого оголошення і повертає текст опису."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=timeout, follow_redirects=True) as client:
        response = await client.get(ad_url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    description_tag = soup.select_one('div[data-testid="ad_description"] > div')
    if not description_tag:
        return None

    text = description_tag.get_text("\n", strip=True)
    return text or None
