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


def _extract_url_keywords(url: str) -> list[str]:
    """Extract searchable keywords from category URL."""
    if not url:
        return []
    
    parts = []
    
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path if parsed.path else url
    
    path = path.lower()
    path = path.replace(".html", "").replace(".tn", "").replace("-", " ").replace("/", " ")
    
    url_keyword_expansions = {
        "pc portable": "laptop ordinateur portable notebook ultrabook",
        "pc de bureau": "desktop ordinateur fixe tour",
        "pc tout en un": "all in one aio",
        "carte graphique": "gpu graphics",
        "carte mere": "motherboard主板",
        "processeur": "cpu processor",
        "barrette memoire": "ram memory",
        "disque dur": "hdd hard drive",
        "disque ssd": "ssd nvme",
        "televiseur": "tv television",
        "telephone": "smartphone mobile phone",
        "casque ecouteur": "headphone headset audio",
        "imprimante": "printer",
        "gamer gaming": "game player",
    }
    
    for key, expansion in url_keyword_expansions.items():
        if key in path:
            parts.extend(expansion.split())
    
    parts.extend(path.split())
    
    return [p for p in parts if len(p) > 1]


def build_bm25_dictionary(product: dict, category_path: str = "") -> str:
    """Build BM25-searchable text string from product fields + category context."""
    parts = []
    
    if product.get("brand"):
        parts.append(product["brand"].lower())
    
    if category_path:
        path_keywords = category_path.lower().replace(".", " ").replace("-", " ").replace("_", " ")
        parts.append(path_keywords)
        for level in category_path.split("."):
            parts.append(level.lower().replace("_", " ").strip())
    
    url_keywords = _extract_url_keywords(product.get("source_category_url", ""))
    parts.extend(url_keywords)
    
    if product.get("name"):
        name = product["name"].lower()
        parts.append(name)
        
        for ram in re.findall(r"(\d+)\s*Go", name, re.IGNORECASE):
            parts.append(f"{ram}go")
        
        for size, unit in re.findall(r"(\d+)\s*(Go|To)", name, re.IGNORECASE):
            parts.append(f"{size}{unit.lower()}")
        
        for screen in re.findall(r"(\d+\.?\d*)\s*pouces?", name, re.IGNORECASE):
            parts.append(f'{screen}"')
            parts.append(f"{screen}inch")
        
        keywords = ["ssd", "hdd", "nvme", "rgb", "wifi", "bluetooth", "hdmi", "usb",
                    "i3", "i5", "i7", "i9", "m1", "m2", "m3", "m4", "ryzen", "ryzen 5", "ryzen 7", "ryzen 9", "core",
                    "windows", "macos", "linux", "android", "ios", "chrome",
                    "gaming", "gamer", "pro", "ultra", "max",
                    "portable", "notebook", "ultrabook", "macbook", "thinkpad", "latitude", "elitebook",
                    "predator", "legion", "omen", "rog", "strix", "nitro", "tuf",
                    "air", "pro", "max", "mini", "plus", "plus pro",
                    "touch", "tactile", "finger", "stylet",
                    "bluetooth", "wireless", "cable",
                    "led", "rgb", "backlit",
                    "mechanical", "membrane",
                    "720p", "1080p", "1440p", "4k", "5k", "8k", "60hz", "144hz", "240hz",
                    "webcam", "camera", "mic", "microphone"]
        for kw in keywords:
            if kw in name:
                parts.append(kw)
    
    return " ".join(dict.fromkeys(parts))


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
