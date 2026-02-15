"""
Text cleaning utilities for consistent extraction.
"""

import re
from typing import List


def clean_text(text: str) -> str:
    """
    Clean and normalize text
    
    Args:
        text: Raw text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = " ".join(text.split())
    
    # Fix common OCR errors
    text = text.replace("�", "")
    text = text.replace("\x00", "")
    
    # Normalize quotes
    text = text.replace(""", '"').replace(""", '"')
    text = text.replace("'", "'").replace("'", "'")
    
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def normalize_area_name(area: str) -> str:
    """Normalize area names for consistency"""
    area = clean_text(area)
    
    # Common replacements
    replacements = {
        "master bed room": "master bedroom",
        "master br": "master bedroom",
        "m bedroom": "master bedroom",
        "common bed room": "common bedroom",
        "common br": "common bedroom",
        "c bedroom": "common bedroom",
        "bath room": "bathroom",
        "common bathroom": "common bathroom",
        "master bathroom": "master bathroom",
        "car park": "parking",
        "living room": "hall",
        "drawing room": "hall",
    }
    
    area_lower = area.lower()
    for old, new in replacements.items():
        if old in area_lower:
            area_lower = area_lower.replace(old, new)
    
    return area_lower.title()


def extract_numbers(text: str) -> List[float]:
    """Extract numeric values from text"""
    pattern = r'[-+]?\d*\.?\d+'
    matches = re.findall(pattern, text)
    return [float(m) for m in matches]


def remove_special_chars(text: str, keep: str = "") -> str:
    """
    Remove special characters except specified ones
    
    Args:
        text: Input text
        keep: Characters to keep (e.g., ".-")
        
    Returns:
        Text with special chars removed
    """
    pattern = f'[^a-zA-Z0-9\s{re.escape(keep)}]'
    return re.sub(pattern, '', text)


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences"""
    # Simple sentence splitter
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]
