"""JSON persistence helpers for product datasets."""

from __future__ import annotations

import json
import logging


logger = logging.getLogger(__name__)


def saveProductsToJson(product_data: list[dict], file_name: str) -> bool:
    return saveJsonToFile(product_data, file_name, "Products")


def loadJsonFromFile(file_name: str, label: str = "Data") -> list | dict | None:
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error("File not found: %s", file_name)
        return None
    except json.JSONDecodeError as error:
        logger.error("Invalid JSON in %s: %s", file_name, error)
        return None
    except OSError as error:
        logger.error("I/O error loading %s from %s: %s", label.lower(), file_name, error)
        return None


def loadProductsFromJson(file_name: str) -> list[dict]:
    data = loadJsonFromFile(file_name, label="Products")
    if data is None:
        return []

    if not isinstance(data, list):
        logger.error("Invalid products payload in %s: expected a JSON list.", file_name)
        return []

    return data

def loadLinesFromFile(file_name: str, label: str = "Lines") -> list[str]:
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        logger.error("File not found: %s", file_name)
        return []
    except OSError as error:
        logger.error("I/O error loading %s from %s: %s", label.lower(), file_name, error)
        return []


def saveLinesToFile(lines: list[str], file_name: str, label: str = "Lines") -> bool:
    try:
        with open(file_name, "w", encoding="utf-8") as file:
            for line in lines:
                file.write(f"{line}\n")
        logger.info("%s saved to %s", label, file_name)
        return True
    except OSError as error:
        logger.error("I/O error saving %s to %s: %s", label.lower(), file_name, error)
        return False


def saveJsonToFile(data: list | dict, file_name: str, label: str = "Data") -> bool:
    try:
        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        logger.info("%s saved to %s", label, file_name)
        return True
    except (OSError, TypeError, ValueError) as error:
        logger.error("Error saving %s to %s: %s", label.lower(), file_name, error)
        return False
