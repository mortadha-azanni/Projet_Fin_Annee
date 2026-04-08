"""Runtime configuration for scraping pipeline."""

from __future__ import annotations

from pathlib import Path
import os
from urllib.parse import quote, quote_plus, urlparse

from dotenv import dotenv_values


# Load environment variables from web-scraping/.env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOTENV_VALUES = dotenv_values(PROJECT_ROOT / ".env")


def _getEnv(*keys: str, default=None):
	"""Return first non-empty value from .env, then process environment."""

	for key in keys:
		value = DOTENV_VALUES.get(key)
		if value:
			return value

		value = os.getenv(key)
		if value:
			return value

	return default

REQUEST_TIMEOUT_SECONDS = 10
API_REQUEST_TIMEOUT_SECONDS = 20
CATEGORY_SLEEP_SECONDS = 1

DB_USER = _getEnv("DB_USER", "USER")
DB_PASSWORD = _getEnv("DB_PASSWORD", "PASSWORD")
DB_HOST = _getEnv("DB_HOST", "HOST")
DB_PORT = _getEnv("DB_PORT", "PORT", default="5432")
DB_NAME = _getEnv("DB_NAME", "DBNAME")
DATABASE_URL = _getEnv("DATABASE_URL")


def _parseDbPort(port_value) -> int:
	"""Parse and validate database port."""

	try:
		port = int(port_value)
	except (TypeError, ValueError) as error:
		raise ValueError("DB_PORT/PORT must be a valid integer") from error

	if not 1 <= port <= 65535:
		raise ValueError("DB_PORT/PORT must be between 1 and 65535")

	return port


def getDatabaseUrl() -> str:
	"""Return a Postgres connection URL built from environment variables."""

	if DATABASE_URL:
		parsed_url = urlparse(DATABASE_URL)
		if parsed_url.scheme not in {"postgresql", "postgresql+psycopg2", "postgresql+psycopg"}:
			raise ValueError("DATABASE_URL must use a PostgreSQL scheme")
		return DATABASE_URL

	missing_vars = []
	if not DB_USER:
		missing_vars.append("DB_USER/USER")
	if not DB_PASSWORD:
		missing_vars.append("DB_PASSWORD/PASSWORD")
	if not DB_HOST:
		missing_vars.append("DB_HOST/HOST")
	if not DB_NAME:
		missing_vars.append("DB_NAME/DBNAME")

	if missing_vars:
		missing_values = ", ".join(missing_vars)
		raise ValueError(f"Missing database configuration: {missing_values}")

	port = _parseDbPort(DB_PORT)
	encoded_db_name = quote(DB_NAME, safe="")

	return f"postgresql+psycopg2://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{port}/{encoded_db_name}?sslmode=require"

TUNISIANET_BRANDS_URL = "https://www.tunisianet.com.tn/marques"
TUNISIANET_BASE_URL = "https://www.tunisianet.com.tn"
MYTEK_BASE_URL = "https://www.mytek.tn"
MYTEK_PRODUCT_API_URL = "https://www.mytek.tn/opensearch_api/api/productData"

TUNISIANET_CATEGORIES_FILE = "tunisianet_categories.txt"
MYTEK_CATEGORIES_FILE = "mytek_categories.txt"

DEFAULT_OUTPUT_FILE = "json/products.json"
DEFAULT_ENRICHED_OUTPUT_FILE = "json/products_with_specs.json"
DEFAULT_CATEGORY_OUTPUT_FILE = "json/classification_table.json"
DEFAULT_CLASSIFICATION_OUTPUT_FILE = DEFAULT_CATEGORY_OUTPUT_FILE
DEFAULT_VECTOR_INDEX_FILE = "json/vector_index.faiss"
DEFAULT_VECTOR_METADATA_FILE = "json/vector_metadata.json"
