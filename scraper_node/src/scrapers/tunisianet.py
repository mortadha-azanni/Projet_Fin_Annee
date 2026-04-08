"""Tunisianet scraper implementation."""

from __future__ import annotations

import logging

from src import config
from src.core.http import getSoup
from src.core.price import parsePrice
from src.io import loadLinesFromFile, saveLinesToFile
from src.models import buildProductRecord
from src.core.control import check_scraper_state


logger = logging.getLogger(__name__)


class TunisianetScraper:
    def __init__(self):
        self.updateBrand()

    def updateBrand(self):
        self.brands = []
        soup = getSoup(config.TUNISIANET_BRANDS_URL)
        if not soup:
            logger.warning("Soup object is None. Skipping Tunisianet brand scraping.")
            return
        try:
            brand_elements = soup.select("li.brand")
            for brand in brand_elements:
                img_element = brand.find("img")
                img_link = img_element["src"] if img_element else None
                name_div = brand.find("div", class_="brand-infos")
                name = name_div.find("p").text.strip() if name_div else None
                if name:
                    self.brands.append(
                        {
                            "name": name,
                            "imgLink": img_link,
                        }
                    )
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            logger.error("Error scraping Tunisianet brands: %s", error)
        except Exception:
            logger.exception("Unexpected error scraping Tunisianet brands")

    def associateBrand(self, imgLink):
        for brand in self.brands:
            if brand["imgLink"] == imgLink:
                return brand["name"]
        return None

    def updateCategory(self):
        soup = getSoup(config.TUNISIANET_BASE_URL)
        if not soup:
            logger.warning("Soup object is None. Skipping Tunisianet scraping.")
            return

        try:
            category_divs = soup.select("div.wb-sub-menu.menu-dropdown")
            unique_urls = []
            seen_urls = set()
            for category_div in category_divs:
                category_list = category_div.select("li.menu-item.item-line ")
                for category in category_list:
                    link_tag = category.find("a")
                    href = link_tag.get("href") if link_tag else None
                    if href and href not in seen_urls:
                        seen_urls.add(href)
                        unique_urls.append(href)

            saved = saveLinesToFile(unique_urls, config.TUNISIANET_CATEGORIES_FILE, label="Tunisianet categories")
            if not saved:
                logger.error("Failed to persist Tunisianet categories file.")
                return

            logger.info("Categories updated successfully (%s unique URLs).", len(unique_urls))

        except (AttributeError, KeyError, TypeError, ValueError) as error:
            logger.error("Failed to scrape category: %s", error)
        except Exception:
            logger.exception("Unexpected error scraping Tunisianet categories")

    def scrapeCategory(self, categoryUrl, productData):
        logger.info("Scraping category: %s", categoryUrl)
        soup = getSoup(categoryUrl)
        if not soup:
            logger.warning("Failed to load category URL: %s", categoryUrl)
            return
        page_index_list = soup.select("a.js-search-link")
        last_page_index = int(page_index_list[-2].text.strip()) if page_index_list and (page_index_list[-2].text.strip().isnumeric()) else 1
        logger.info("Total pages in category: %s", last_page_index)
        for page in range(1, last_page_index+1):
            check_scraper_state()
            page_url = f"{categoryUrl}?page={page}&order=product.position.asc"
            page_soup = getSoup(page_url)
            self.scrapePage(page_soup, productData, categoryUrl)

    def updateProducts(self, productData):
        try:
            category_urls = loadLinesFromFile(config.TUNISIANET_CATEGORIES_FILE, label="Tunisianet categories")
            logger.info("Loaded %s category URLs.", len(category_urls))
            for category_url in category_urls:
                check_scraper_state()
                self.scrapeCategory(category_url, productData)
        except (AttributeError, TypeError, ValueError, OSError) as error:
            logger.error("Failed to update products from category file: %s", error)
        except Exception:
            logger.exception("Unexpected error updating Tunisianet products")

    def scrapePage(self, soup, productData, sourceCategoryUrl=None):
        if not soup:
            logger.warning("Soup object is None. Skipping Tunisianet scraping.")
            return

        try:
            products_div = soup.select_one("div.products.product-thumbs")
            if not products_div:
                logger.warning("No products found on Tunisianet page.")
                return

            items = products_div.find_all("div", class_="item-product col-xs-12")
            for item in items:
                try:
                    name = item.find("h2").text.strip()
                    url_link = item.find("h2").find("a")["href"]
                    price = parsePrice(item.find("span", class_="price").text)
                    product_img = item.find("img", class_="center-block img-responsive")["src"]
                    brand_image = item.find("div", class_="product-manufacturer").find("img")["src"]
                    productData.append(
                        buildProductRecord(
                            source="tunisianet",
                            name=name,
                            price=price,
                            url=url_link,
                            image=product_img,
                            brand=self.associateBrand(brand_image),
                            sourceCategoryUrl=sourceCategoryUrl,
                        )
                    )
                except AttributeError as error:
                    logger.warning("Error parsing Tunisianet product item: %s", error)
                except (KeyError, TypeError, ValueError) as error:
                    logger.error("Unexpected data error parsing Tunisianet product item: %s", error)
                except Exception:
                    logger.exception("Unexpected runtime error parsing Tunisianet product item")
        except (AttributeError, TypeError, ValueError) as error:
            logger.error("Error scraping Tunisianet page: %s", error)
        except Exception:
            logger.exception("Unexpected error scraping Tunisianet page")
