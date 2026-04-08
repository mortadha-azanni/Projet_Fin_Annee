"""Normalization helpers for structured retrieval vectorization."""

from __future__ import annotations

import re
import unicodedata
from typing import Any



class Normalizer:
    @staticmethod
    def stripAccents(value: str) -> str:
        return "".join(
            ch for ch in unicodedata.normalize("NFD", value) if unicodedata.category(ch) != "Mn"
        )

    @staticmethod
    def normText(value: Any) -> str:
        if not isinstance(value, str):
            return ""
        text = re.sub(r"\s+", " ", value).strip().lower()
        return Normalizer.stripAccents(text)

    @staticmethod
    def normalizeBrand(brand: Any) -> str:
        value = Normalizer.normText(brand)
        if not value:
            return ""
        return value.replace(" ", "-")

    @staticmethod
    def normalizeCategoryId(category_id: Any) -> str:
        if category_id is None:
            return ""
        return Normalizer.normText(str(category_id))

    @staticmethod
    def normalizeClassification(classification: Any) -> str:
        return Normalizer.normalizeCategoryId(classification)

    @staticmethod
    def normalizeColor(color: Any) -> str:
        return Normalizer.normText(color)

    @staticmethod
    def normalizeOs(os_text: Any) -> str:
        value = Normalizer.normText(os_text)
        if not value:
            return ""
        if "windows" in value:
            return "windows"
        if "mac" in value:
            return "macos"
        if "linux" in value:
            return "linux"
        if "android" in value:
            return "android"
        if "ios" in value:
            return "ios"
        return value

    @staticmethod
    def normalizeCpuFamily(cpu_text: Any) -> str:
        value = Normalizer.normText(cpu_text)
        if not value:
            return ""

        if re.search(r"\bi3\b", value):
            return "intel_i3"
        if re.search(r"\bi5\b", value):
            return "intel_i5"
        if re.search(r"\bi7\b", value):
            return "intel_i7"
        if re.search(r"\bi9\b", value):
            return "intel_i9"
        if "ultra 5" in value:
            return "intel_ultra_5"
        if "ultra 7" in value:
            return "intel_ultra_7"
        if "ultra 9" in value:
            return "intel_ultra_9"
        if "ryzen 3" in value:
            return "amd_ryzen_3"
        if "ryzen 5" in value:
            return "amd_ryzen_5"
        if "ryzen 7" in value:
            return "amd_ryzen_7"
        if "ryzen 9" in value:
            return "amd_ryzen_9"

        m = re.search(r"\bm([1-5])\b", value)
        if m:
            return f"apple_m{m.group(1)}"

        return value

    @staticmethod
    def normalizeGpuFamily(gpu_text: Any) -> str:
        value = Normalizer.normText(gpu_text)
        if not value:
            return ""

        if "rtx" in value:
            return "nvidia_rtx"
        if "gtx" in value:
            return "nvidia_gtx"
        if "geforce" in value:
            return "nvidia_geforce"
        if "radeon" in value or re.search(r"\brx\s*\d{4}\b", value):
            return "amd_radeon"
        if "iris xe" in value:
            return "intel_iris_xe"
        if "uhd graphics" in value or "hd graphics" in value:
            return "intel_integrated"
        if "integrated graphics" in value:
            return "integrated"

        return value

    @staticmethod
    def sizeToGb(size: float, unit: str) -> float:
        return size * 1024.0 if unit.lower() in {"tb", "to"} else size

    @staticmethod
    def ramSizeGb(ram: Any) -> float | None:
        if isinstance(ram, dict):
            size = ram.get("size")
            unit = Normalizer.normText(ram.get("unit"))
            if isinstance(size, (int, float)):
                return Normalizer.sizeToGb(float(size), unit)

        text = Normalizer.normText(ram)
        if not text:
            return None

        m = re.search(r"(\d+(?:\.\d+)?)\s*(go|gb|to|tb)", text)
        if not m:
            return None
        return Normalizer.sizeToGb(float(m.group(1)), m.group(2))

    @staticmethod
    def storageSizeGb(storage: Any) -> float | None:
        if isinstance(storage, dict):
            size = storage.get("size")
            unit = Normalizer.normText(storage.get("unit"))
            if isinstance(size, (int, float)):
                return Normalizer.sizeToGb(float(size), unit)

        text = Normalizer.normText(storage)
        if not text:
            return None

        m = re.search(r"(\d+(?:\.\d+)?)\s*(go|gb|to|tb)", text)
        if not m:
            return None
        return Normalizer.sizeToGb(float(m.group(1)), m.group(2))

    @staticmethod
    def displaySizeIn(display: Any) -> float | None:
        text = Normalizer.normText(display)
        if not text:
            return None

        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:inches|inch|in|\")", text)
        if m:
            return float(m.group(1))

        m = re.search(r"\b(1[0-9](?:\.\d+)?)\b", text)
        if m:
            return float(m.group(1))

        return None
