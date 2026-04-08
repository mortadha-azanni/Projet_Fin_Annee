"""Canonical data models for scraped products."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import re

def utcNowIso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalizeText(value: str | None) -> str | None:
    if not isinstance(value, str):
        return value
    return re.sub(r"\s+", " ", value).strip()


def normalizeBrand(value: str | None) -> str | None:
    normalized = normalizeText(value)
    if not normalized:
        return None
    return normalized.title()


@dataclass
class ProductRecord:
    name: str | None
    price: float | int | None
    url: str | None
    image: str | None
    brand: str | None
    source: str
    category_id: int | None = None
    source_category_url: str | None = None
    scraped_at: str = field(default_factory=utcNowIso)
    validation_issues: list[str] = field(default_factory=list)
    is_valid: bool = False

    def validate(self) -> None:
        issues: list[str] = []
        if not self.name:
            issues.append("missing_name")
        if not self.url:
            issues.append("missing_url")
        if not self.image:
            issues.append("missing_image")
        if not isinstance(self.price, (int, float)) or self.price <= 0:
            issues.append("invalid_price")
        self.validation_issues = issues
        self.is_valid = len(issues) == 0

    def toDict(self) -> dict:
        self.name = normalizeText(self.name)
        self.url = normalizeText(self.url)
        self.image = normalizeText(self.image)
        self.brand = normalizeBrand(self.brand)
        self.source_category_url = normalizeText(self.source_category_url)

        self.validate()
        return asdict(self)


def buildProductRecord(
    source: str,
    name: str | None,
    price: float | int | None,
    url: str | None,
    image: str | None,
    brand: str | None,
    sourceCategoryUrl: str | None = None,
    categoryId: int | None = None,
) -> dict:
    return ProductRecord(
        source=source,
        name=name,
        price=price,
        url=url,
        image=image,
        brand=brand,
        category_id=categoryId,
        source_category_url=sourceCategoryUrl,
    ).toDict()
