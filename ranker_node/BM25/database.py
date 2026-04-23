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


def getCategoryPath(category_id: int) -> str:
    """Get ltree path for a category by ID.
    
    Returns: 'informatique.ordinateurs.pc-portable'
    """
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT path FROM categories WHERE id = :id"),
            {"id": category_id}
        )
        row = result.fetchone()
        return row[0] if row else ""


def getSubcategoryIds(category_id: int) -> list[int]:
    """Get all descendant category IDs using ltree.
    
    Uses ltree <@ operator to find all descendants of a category.
    Returns: [111, 112, 113, ...] (includes the category itself)
    """
    category_path = getCategoryPath(category_id)
    if not category_path:
        return [category_id]
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id FROM categories 
                WHERE path::ltree <@ :path::ltree
            """),
            {"path": category_path}
        )
        return [row[0] for row in result]


def getAncestorIds(category_id: int) -> list[int]:
    """Get all ancestor category IDs using ltree.
    
    Returns: [1, 11, 111] (root to immediate parent)
    """
    category_path = getCategoryPath(category_id)
    if not category_path:
        return []
    
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id FROM categories 
                WHERE :path::ltree <@ path::ltree
                ORDER BY nlevel(path::ltree)
            """),
            {"path": category_path}
        )
        return [row[0] for row in result]


def getProductByCategoryTree(category_id: int, price_min=None, price_max=None, query_embedding=None, limit=200):
    """Fetch products from category AND all subcategories using ltree.

    Args:
        category_id: The root category ID
        price_min: Minimum price filter (optional)
        price_max: Maximum price filter (optional)
        query_embedding: Embedding for pgvector cosine distance sorting
        limit: Max number of products to return

    Returns products from all categories under the given category tree.
    """
    category_path = getCategoryPath(category_id)
    if not category_path:
        return []

    with engine.connect() as conn:
        query = (
            "SELECT p.id, p.description, p.price, p.category_id, p.urllink, p.urlimg, p.embedding, p.dictionary, "
            "COALESCE(NULLIF(p.dictionary, ''), p.description) AS search_text "
            "FROM products p "
            "JOIN categories c ON p.category_id = c.id "
            "WHERE c.path::ltree <@ :path::ltree"
        )
        params = {"path": category_path, "limit": limit}

        if price_min is not None:
            query += " AND p.price >= :price_min"
            params["price_min"] = price_min
        if price_max is not None:
            query += " AND p.price <= :price_max"
            params["price_max"] = price_max

        if query_embedding is not None:
            import json
            params["query_embedding"] = json.dumps([float(x) for x in query_embedding])
            query += " ORDER BY p.embedding <=> CAST(:query_embedding AS vector) LIMIT :limit"
        else:
            query += " ORDER BY p.price LIMIT :limit"

        result = conn.execute(text(query), params)
        products = [dict(row._mapping) for row in result.fetchall()]
    return products