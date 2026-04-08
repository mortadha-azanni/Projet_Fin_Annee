from .base import Base
from .category import Category
from .category_mapping import CategoryMapping, enrichProductsWithCategoryIds, getCategoryIdByUrl, normalizeCategoryUrl
from .product import Product


def saveProductsToDB(*args, **kwargs):
	from .database import saveProductsToDB as _saveProductsToDB

	return _saveProductsToDB(*args, **kwargs)


__all__ = [
	"Base",
	"Category",
	"CategoryMapping",
	"Product",
	"enrichProductsWithCategoryIds",
	"getCategoryIdByUrl",
	"normalizeCategoryUrl",
	"saveProductsToDB",
]
