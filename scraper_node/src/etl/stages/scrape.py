"""Scrape stage implementation."""

from ..contracts import PipelineContext
from src.scrapers import MyTekScraper, TunisianetScraper
from src.core.control import check_scraper_state


def stage_scrape(context: PipelineContext) -> PipelineContext:
    """Populate context.data with raw scraped items."""
    product_data: list[dict] = []

    check_scraper_state()
    tunisianet_scraper = TunisianetScraper()
    tunisianet_scraper.updateProducts(product_data)
    context.progress(
        "running",
        f"Finished Tunisianet... Products found: {len(product_data)}",
        len(product_data),
        {"stage": "scrape", "source": "tunisianet"},
    )

    check_scraper_state()
    mytek_scraper = MyTekScraper()
    mytek_scraper.updateProducts(product_data)
    context.progress(
        "running",
        f"Finished MyTek... Total Products: {len(product_data)}",
        len(product_data),
        {"stage": "scrape", "source": "mytek"},
    )

    context.data = product_data
    return context
