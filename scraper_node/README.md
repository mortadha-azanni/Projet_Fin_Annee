# Scraper Node

Web scraping microservice for extracting data from URLs.

## Features

- URL validation
- HTML content extraction
- Data parsing and structuring
- Future: JavaScript rendering, proxy support, rate limiting

## Endpoints

### `GET /`
Service information

### `GET /health`
Health check endpoint

### `GET /scrape`
Scrape data from a given URL

**Parameters:**
- `url` (query param): URL to scrape

**Response:**
```json
{
  "url": "https://example.com",
  "message": "Scraping functionality to be implemented",
  "data": []
}
```

## TODO: Implement Scraping Logic

### Option 1: BeautifulSoup (for static sites)
```python
import requests
from bs4 import BeautifulSoup
```

### Option 2: Playwright (for JavaScript-heavy sites)
```python
from playwright.async_api import async_playwright
```

## Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- Future: `beautifulsoup4`, `requests`, or `playwright`

## Development

```bash
uv sync
uv run uvicorn main:app --reload --port 8000
```
