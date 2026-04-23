from sqlalchemy import Column, Float, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import relationship

try:
    from pgvector.sqlalchemy import Vector
except ModuleNotFoundError:
    Vector = Text

from .base import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    urllink = Column(Text, nullable=False)
    urlimg = Column(Text, nullable=False)
    dictionary = Column(Text, nullable=True)

    embedding = Column(Vector(384))

    category = relationship("Category", back_populates="products")

    __table_args__ = (
        Index(
            "products_embedding_idx",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, price={self.price}, category_id={self.category_id})>"
