from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import backref, relationship
from sqlalchemy import text

from .base import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"))
    path = Column(Text, nullable=True)  # PostgreSQL ltree format: "informatique.ordinateurs.pc_portable"
    dictionary = Column(Text, nullable=True)

    # Self-referential relationship for parent/child categories.
    subcategories = relationship(
        "Category",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete",
    )

    mappings = relationship("CategoryMapping", back_populates="category", cascade="all, delete")
    products = relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', slug='{self.slug}')>"


from .category_mapping import CategoryMapping
from .product import Product


def build_category_path(category: "Category", session) -> str:
    """Build full ltree path from root to this category.
    
    Returns dot-separated path: 'informatique.ordinateurs.pc_portable'
    """
    path_parts = []
    current = category
    
    while current:
        path_parts.insert(0, current.slug)
        if current.parent_id:
            current = session.get(Category, current.parent_id)
        else:
            current = None
    
    return ".".join(path_parts)


def get_category_path(category_id: int, session) -> str:
    """Get ltree path for a category by ID."""
    category = session.get(Category, category_id)
    if not category:
        return ""
    return build_category_path(category, session)


def get_subcategories(category_id: int, session) -> list[int]:
    """Get all descendant category IDs using ltree.
    
    Uses ltree <@ operator to find all descendants of a category.
    Returns: [111, 112, 113, ...] (includes the category itself)
    """
    category = session.get(Category, category_id)
    if not category or not category.path:
        return [category_id]
    
    result = session.execute(
        text("""
            SELECT id FROM categories 
            WHERE path <@ :path::ltree
        """),
        {"path": category.path}
    )
    return [row[0] for row in result]


def get_ancestor_ids(category_id: int, session) -> list[int]:
    """Get all ancestor category IDs using ltree.
    
    Returns: [1, 11, 111] (root to parent of given category)
    """
    category = session.get(Category, category_id)
    if not category or not category.path:
        return []
    
    result = session.execute(
        text("""
            SELECT id FROM categories 
            WHERE :path::ltree <@ path
        """),
        {"path": category.path}
    )
    return [row[0] for row in result]


def get_category_level(category_id: int, session) -> int:
    """Get depth level of category (0 = root).
    
    For ltree path 'informatique.ordinateurs.pc_portable', returns 2.
    """
    category = session.get(Category, category_id)
    if not category or not category.path:
        return 0
    return category.path.count(".")


def path_to_display_format(path: str) -> str:
    """Convert ltree path to human-readable format.
    
    'informatique.ordinateurs.pc_portable' -> 'Informatique > Ordinateurs > Pc Portable'
    """
    if not path:
        return ""
    parts = path.split(".")
    return " > ".join(p.replace("-", " ").title() for p in parts)
