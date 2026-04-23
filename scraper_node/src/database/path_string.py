from sqlalchemy import Column, ForeignKey, Integer, Text

try:
    from pgvector.sqlalchemy import Vector
except ModuleNotFoundError:
    Vector = Text

from .base import Base


class PathString(Base):
    __tablename__ = "path_strings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    path = Column(Text, nullable=False)  # PostgreSQL ltree type (stored as text)
    embedding = Column(Vector(384))