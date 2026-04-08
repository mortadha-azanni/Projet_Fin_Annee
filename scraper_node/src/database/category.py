from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import backref, relationship

from .base import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    slug = Column(Text, unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"))

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
