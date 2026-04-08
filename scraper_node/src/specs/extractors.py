"""Spec extraction helpers from product names."""

from __future__ import annotations

import re


def sanitizeProductName(product_name: str) -> str:
    if isinstance(product_name, str):
        return product_name
    return ""


def extractRam(product_name: str):
    product_name = sanitizeProductName(product_name)
    match = re.search(r"(\d+)\s*Go\s*(DDR\d|LPDDR\d)?", product_name, re.IGNORECASE)
    if match:
        size = int(match.group(1))
        ram_type = match.group(2) if match.group(2) else "Unknown"
        return {"size": size, "unit": "Go", "type": ram_type}
    return None


def extractStorage(product_name: str):
    product_name = sanitizeProductName(product_name)
    matches = list(re.finditer(r"(\d+)\s*(Go|To)\s*(SSD|HDD|NVMe)", product_name, re.IGNORECASE))
    if matches:
        match = matches[-1] if len(matches) > 1 else matches[0]
        size = int(match.group(1))
        unit = match.group(2).upper()
        storage_type = match.group(3).upper() if match.group(3) else "Unknown"
        return {"size": size, "unit": unit, "type": storage_type}
    return None


def extractCpu(product_name: str):
    product_name = sanitizeProductName(product_name)
    intel_match = re.search(r"(Core\s+)?i[3579]\s*-?\s*\d+[A-Z]?", product_name, re.IGNORECASE)
    if intel_match:
        return intel_match.group(0).strip()

    apple_match = re.search(r"[Mm]\d+\s*(Pro|Max|Ultra)?", product_name)
    if apple_match:
        return apple_match.group(0).strip()

    amd_match = re.search(r"(Ryzen\s+[357]\s*\d+[A-Z]?|Ryzen\s+\d+)", product_name, re.IGNORECASE)
    if amd_match:
        return amd_match.group(0).strip()

    return None


def extractGpu(product_name: str):
    product_name = sanitizeProductName(product_name)
    nvidia_match = re.search(r"(RTX|GTX|GeForce)\s*\d{4}", product_name, re.IGNORECASE)
    if nvidia_match:
        return nvidia_match.group(0).strip()

    amd_match = re.search(r"Radeon\s+(RX\s*\d{4}|Vega)", product_name, re.IGNORECASE)
    if amd_match:
        return amd_match.group(0).strip()

    intel_match = re.search(r"Intel\s+(Iris\s+Xe|UHD\s+Graphics|HD\s+Graphics)", product_name, re.IGNORECASE)
    if intel_match:
        return intel_match.group(0).strip()

    integrated_match = re.search(r"Integrated\s+Graphics", product_name, re.IGNORECASE)
    if integrated_match:
        return "Integrated Graphics"

    return None


def extractDisplay(product_name: str):
    product_name = sanitizeProductName(product_name)
    match = re.search(r"(\d+(?:\.\d+)?)\s*[\"\"″'`]", product_name)
    if match:
        return f"{match.group(1)}"
    return None


def extractColor(product_name: str):
    product_name = sanitizeProductName(product_name)
    colors = [
        (r"\bGris\s+sidéral\b", "Gray"),
        (r"\bGris\s+Sidéral\b", "Gray"),
        (r"\bSpace\s+Gray\b", "Gray"),
        (r"\bSpace\s+Grey\b", "Gray"),
        (r"\bNoir\b", "Black"),
        (r"\bBlack\b", "Black"),
        (r"\bBlanc\b", "White"),
        (r"\bWhite\b", "White"),
        (r"\bArgent\b", "Silver"),
        (r"\bSilver\b", "Silver"),
        (r"\bOr\b", "Gold"),
        (r"\bGold\b", "Gold"),
        (r"\bDoré\b", "Gold"),
        (r"\bRose(?:\s+Gold)?\b", "Pink"),
        (r"\bPink\b", "Pink"),
        (r"\bRose\s+Gold\b", "Pink"),
        (r"\bBleu\b", "Blue"),
        (r"\bBlue\b", "Blue"),
        (r"\bVert\b", "Green"),
        (r"\bGreen\b", "Green"),
        (r"\bRouge\b", "Red"),
        (r"\bRed\b", "Red"),
        (r"\bPourpre\b", "Purple"),
        (r"\bPurple\b", "Purple"),
        (r"\bMarron\b", "Brown"),
        (r"\bBrown\b", "Brown"),
    ]

    for color_pattern, color_name in colors:
        match = re.search(color_pattern, product_name, re.IGNORECASE)
        if match:
            return color_name

    return None


def extractOs(product_name: str):
    product_name = sanitizeProductName(product_name)
    windows_match = re.search(r"Windows\s+\d+\s*(Pro|Home|Education|Enterprise)?", product_name, re.IGNORECASE)
    if windows_match:
        return windows_match.group(0).strip()

    macos_match = re.search(r"[Mm]ac([OSos]{2})?", product_name)
    if macos_match:
        return "macOS"

    linux_match = re.search(r"Linux", product_name, re.IGNORECASE)
    if linux_match:
        return "Linux"

    return None