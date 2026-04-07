"""Fetch categories and products from PostgreSQL."""
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

USER = os.getenv("DB_USER") or os.getenv("user") or "postgres"
PASSWORD = os.getenv("DB_PASSWORD") or os.getenv("password") or ""
HOST = os.getenv("DB_HOST") or os.getenv("host") or "localhost"
PORT = os.getenv("DB_PORT") or os.getenv("port") or "5432"
DBNAME = os.getenv("DB_NAME") or os.getenv("dbname") or "postgres"
SSL_MODE = os.getenv("DB_SSLMODE") or os.getenv("sslmode")

DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}"
if SSL_MODE:
    DATABASE_URL = f"{DATABASE_URL}?sslmode={SSL_MODE}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 5})

def getCategories():
    """Fetch categories from PostgreSQL."""
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT id, name, slug, parent_id, dictionary, "
                "COALESCE(NULLIF(dictionary, ''), name) AS search_text "
                "FROM categories;"
            )
        )
        categories = [dict(row._mapping) for row in result.fetchall()]
    return categories

def getProductByCategory(category_id, price_min=None, price_max=None, query_embedding=None, limit=200):
    """
    Fetch products for a given category from PostgreSQL.
    
    Args:
        category_id: The category ID to filter by
        price_min: Minimum price filter (optional)
        price_max: Maximum price filter (optional)
        query_embedding: Numpy array or list representing the query embedding for pgvector cosine distance sorting
        limit: Max number of products to return
    """
    with engine.connect() as conn:
        query = (
            "SELECT id, description, price, category_id, urllink, urlimg, embedding, dictionary, "
            "COALESCE(NULLIF(dictionary, ''), description) AS search_text "
            "FROM products WHERE category_id = :category_id"
        )
        params = {"category_id": category_id, "limit": limit}
        
        # Add price range filters if provided
        if price_min is not None:
            query += " AND price >= :price_min"
            params["price_min"] = price_min
        if price_max is not None:
            query += " AND price <= :price_max"
            params["price_max"] = price_max
            
        if query_embedding is not None:
            # Cast python list to pgvector literal string representation e.g., '[0.1, 0.2, ...]'
            # For SQLAlchemy execute, passing it via JSON dump or direct string
            import json
            # Convert float32 numpy objects to native Python floats for JSON serialization
            params["query_embedding"] = json.dumps([float(x) for x in query_embedding])
            # Sort by cosine distance using the pgvector `<=>` operator against the casted parameter
            # Use CAST() instead of :: to avoid SQLAlchemy parameter binding conflicts
            query += " ORDER BY embedding <=> CAST(:query_embedding AS vector) LIMIT :limit"
        else:
            query += " LIMIT :limit"
        
        result = conn.execute(text(query), params)
        products = [dict(row._mapping) for row in result.fetchall()]
    return products

def getCategoriesPath():
    """Fetch all category paths from the path_strings table."""
    with engine.connect() as conn:
        query = "SELECT id, category_id, path, embedding FROM path_strings;"
        result = conn.execute(text(query))
        paths = [dict(row._mapping) for row in result.fetchall()]
    return paths