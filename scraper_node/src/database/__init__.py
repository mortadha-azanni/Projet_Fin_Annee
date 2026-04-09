from .base import Base
from .category import Category
from .category_mapping import CategoryMapping, enrichProductsWithCategoryIds, getCategoryIdByUrl, normalizeCategoryUrl
from .product import Product


def saveProductsToDB(*args, **kwargs):
	from .database import saveProductsToDB as _saveProductsToDB

	return _saveProductsToDB(*args, **kwargs)


def clearProductsTable(*args, **kwargs):
	from .database import clearProductsTable as _clearProductsTable

	return _clearProductsTable(*args, **kwargs)


__all__ = [
	"Base",
	"Category",
	"CategoryMapping",
	"Product",
	"enrichProductsWithCategoryIds",
	"getCategoryIdByUrl",
	"normalizeCategoryUrl",
	"clearProductsTable",
	"saveProductsToDB",
]
