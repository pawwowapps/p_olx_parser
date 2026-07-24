from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Ad:
    ad_id: str
    title: str
    price: str
    location_date: str
    url: str
    image_url: Optional[str]
