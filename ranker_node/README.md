# Ranker Node

Ranking and scoring microservice for processing and ordering data.

## Features

- Rank items based on various criteria
- Sort and filter results
- Scoring algorithms
- Future: ML-based ranking, personalization

## Endpoints

### `GET /`
Service information

### `GET /health`
Health check endpoint

### `POST /rank`
Rank a list of items

**Request Body:**
```json
[
  {"title": "Item 1", "score": 10},
  {"title": "Item 2", "score": 5}
]
```

**Response:**
```json
{
  "message": "Ranking functionality to be implemented",
  "ranked_items": [
    {"title": "Item 1", "score": 10},
    {"title": "Item 2", "score": 5}
  ]
}
```

## TODO: Implement Ranking Logic

### Simple Ranking Strategies
- Sort by score/relevance
- Filter by threshold
- Boost recent items
- Keyword matching

### Advanced Strategies
- Machine learning models
- Collaborative filtering
- Content-based filtering
- Hybrid approaches

## Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- Future: `scikit-learn`, `pandas`, `numpy` for ML-based ranking

## Development

```bash
uv sync
uv run uvicorn main:app --reload --port 8000
```
