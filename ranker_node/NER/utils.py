import re
import string

def normalize(text: str) -> str:
    """
    Normalizes text by:
    1. Converting to lowercase
    2. Removing punctuation
    3. Stripping extra whitespace
    """
    if not isinstance(text, str):
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text
