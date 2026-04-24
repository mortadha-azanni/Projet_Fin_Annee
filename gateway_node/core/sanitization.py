import re
import html
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
import bleach


class SanitizationConfig:
    """Configuration for input sanitization"""

    # Maximum lengths
    MAX_QUERY_LENGTH = 500
    MAX_NAME_LENGTH = 100
    MAX_DESCRIPTION_LENGTH = 2000
    MAX_URL_LENGTH = 2048

    # Allowed HTML tags for rich text (if needed)
    ALLOWED_HTML_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote', 'code', 'pre'
    ]

    ALLOWED_HTML_ATTRIBUTES = {
        '*': ['class'],
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title']
    }

    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',                # JavaScript URLs
        r'data:',                      # Data URLs (potential XSS)
        r'vbscript:',                  # VBScript
        r'on\w+\s*=',                  # Event handlers
        r'<iframe[^>]*>.*?</iframe>',  # Iframes
        r'<object[^>]*>.*?</object>',  # Object tags
        r'<embed[^>]*>.*?</embed>',    # Embed tags
    ]


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize plain text input"""
    if not text:
        return ""

    # Convert to string if not already
    text = str(text)

    # Remove null bytes and other control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

    # Escape HTML entities
    text = html.escape(text, quote=True)

    # Apply length limit if specified
    if max_length and len(text) > max_length:
        text = text[:max_length].rstrip()

    return text.strip()


def sanitize_html(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize HTML content while preserving allowed tags"""
    if not text:
        return ""

    text = str(text)

    # First, check for dangerous patterns
    for pattern in SanitizationConfig.DANGEROUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            # Replace dangerous content with safe placeholder
            text = re.sub(pattern, '[BLOCKED CONTENT]', text, flags=re.IGNORECASE | re.DOTALL)

    # Use bleach to clean HTML
    cleaned = bleach.clean(
        text,
        tags=SanitizationConfig.ALLOWED_HTML_TAGS,
        attributes=SanitizationConfig.ALLOWED_HTML_ATTRIBUTES,
        strip=True
    )

    # Apply length limit if specified
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip()

    return cleaned.strip()


def sanitize_url(url: str) -> str:
    """Sanitize URL input"""
    if not url:
        return ""

    url = str(url).strip()

    # Basic URL validation
    if not re.match(r'^https?://', url, re.IGNORECASE):
        return ""

    # Check for dangerous protocols
    dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
    if any(url.lower().startswith(proto) for proto in dangerous_protocols):
        return ""

    # Length check
    if len(url) > SanitizationConfig.MAX_URL_LENGTH:
        return ""

    return url


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    if not filename:
        return ""

    filename = str(filename).strip()

    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)

    # Remove dangerous patterns like ".." or starting with "/"
    filename = re.sub(r'^\.+', '', filename)
    filename = re.sub(r'^/+', '', filename)

    return filename[:255]  # Reasonable filename length limit


class SanitizedSearchQuery(BaseModel):
    """Sanitized search query model"""
    query: str = Field(..., min_length=1, max_length=SanitizationConfig.MAX_QUERY_LENGTH)

    @validator('query')
    def validate_and_sanitize_query(cls, v):
        return sanitize_text(v, SanitizationConfig.MAX_QUERY_LENGTH)


class SanitizedProductData(BaseModel):
    """Sanitized product data model"""
    name: Optional[str] = Field(None, max_length=SanitizationConfig.MAX_NAME_LENGTH)
    title: Optional[str] = Field(None, max_length=SanitizationConfig.MAX_NAME_LENGTH)
    description: Optional[str] = Field(None, max_length=SanitizationConfig.MAX_DESCRIPTION_LENGTH)
    price: Optional[Union[float, str]] = None
    category_id: Optional[str] = Field(None, max_length=100)
    source_type: Optional[str] = Field(None, max_length=50)

    @validator('name', 'title')
    def sanitize_name_fields(cls, v):
        return sanitize_text(v, SanitizationConfig.MAX_NAME_LENGTH) if v else v

    @validator('description')
    def sanitize_description(cls, v):
        return sanitize_text(v, SanitizationConfig.MAX_DESCRIPTION_LENGTH) if v else v

    @validator('category_id', 'source_type')
    def sanitize_identifiers(cls, v):
        return sanitize_text(v, 100) if v else v

    @validator('price')
    def validate_price(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            # Try to convert string price to float
            try:
                # Remove currency symbols and extra spaces
                cleaned = re.sub(r'[^\d.,]', '', str(v))
                return float(cleaned.replace(',', '.'))
            except (ValueError, TypeError):
                return None
        return float(v) if isinstance(v, (int, float)) else None


class SanitizedConstraints(BaseModel):
    """Sanitized search constraints"""
    max_price: Optional[float] = Field(default=None, ge=0, le=1000000)
    location: Optional[str] = Field(default=None, max_length=100)
    filters: Optional[List[str]] = Field(default=None, max_length=10)

    @validator('location')
    def sanitize_location(cls, v):
        return sanitize_text(v, 100) if v else v

    @validator('filters')
    def sanitize_filters(cls, v):
        if not v:
            return v
        return [sanitize_text(f, 50) for f in v if f and len(f.strip()) > 0][:10]


class SanitizedEntities(BaseModel):
    """Sanitized NER entities"""
    products: Optional[List[str]] = Field(default=None, max_length=5)
    brands: Optional[List[str]] = Field(default=None, max_length=5)
    categories: Optional[List[str]] = Field(default=None, max_length=5)
    dates: Optional[List[str]] = Field(default=None, max_length=3)

    @validator('products', 'brands', 'categories', 'dates')
    def sanitize_entity_lists(cls, v):
        if not v:
            return v
        return [sanitize_text(item, 50) for item in v if item and len(item.strip()) > 0][:5]


def sanitize_dict_input(data: Any) -> Any:
    """Recursively sanitize dictionary input"""
    if not isinstance(data, dict):
        return data

    sanitized: Dict[str, Any] = {}
    for key, value in data.items():
        # Sanitize key
        clean_key = sanitize_text(str(key), 100)

        if isinstance(value, dict):
            sanitized[clean_key] = sanitize_dict_input(value)
        elif isinstance(value, list):
            sanitized[clean_key] = [
                sanitize_dict_input(item) if isinstance(item, dict) else sanitize_text(str(item), 500)
                for item in value
            ]
        elif isinstance(value, str):
            sanitized[clean_key] = sanitize_text(value, 1000)
        else:
            sanitized[clean_key] = value

    return sanitized


def validate_and_sanitize_input(data: Any, model_class: type[BaseModel] | None = None) -> Any:
    """Main validation and sanitization function"""
    if model_class and hasattr(model_class, '__fields__') and isinstance(data, dict):
        # Use Pydantic model validation
        try:
            return model_class(**data)
        except Exception as e:
            raise ValueError(f"Input validation failed: {str(e)}")

    if isinstance(data, dict):
        return sanitize_dict_input(data)
    elif isinstance(data, str):
        return sanitize_text(data, 1000)
    elif isinstance(data, list):
        return [validate_and_sanitize_input(item) for item in data]

    return data
