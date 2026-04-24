"""Persistence stage implementation."""

from ..contracts import PipelineContext
from src import config
from src.database import clearProductsTable, enrichProductsWithCategoryIds, saveProductsToDB
from src.database.category_mapping import loadCategoryMappings
from src.database.session import getSession, initDb
from src.io import saveProductsToJson


def stage_persist(context: PipelineContext) -> PipelineContext:
    """Persist processed items to storage."""
    if not context.data:
        context.progress(
            "running",
            "No products to persist",
            0,
            {"stage": "persist"},
        )
        return context

    saveProductsToJson(context.data, config.DEFAULT_OUTPUT_FILE)
    context.progress(
        "running",
        "Saving products to database...",
        len(context.data),
        {"stage": "persist"},
    )

    initDb()
    with getSession() as session:
        category_mappings = loadCategoryMappings(session)
        context.data = enrichProductsWithCategoryIds(context.data, session, category_mappings)

    clearProductsTable(logger=context.meta.get("logger"))
    saveProductsToDB(context.data, logger=context.meta.get("logger"))
    context.meta["persisted"] = True
    return context
