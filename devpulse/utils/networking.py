"""HTTP networking utilities for DevPulse.

This module provides HTTP utilities for fetching content:
- Connection pooling via reusable session
- Configurable timeouts
- Error handling for network issues
- Text sanitization

Example:
    from devpulse.utils.networking import fetch_url
    content = fetch_url('https://example.com')
"""

import requests
from typing import Optional
from devpulse.config import config
from devpulse.core.logging_config import get_logger

logger = get_logger(__name__)

# Global session for connection pooling
_session: Optional[requests.Session] = None


def get_session() -> requests.Session:
    """Get or create a reusable HTTP session for connection pooling.
    
    Returns a singleton requests.Session object that persists
    across calls, enabling connection reuse and better performance.
    
    Returns:
        requests.Session instance with configured User-Agent header.
    """
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            'User-Agent': config.get('user_agent', 'devpulse/1.0')
        })
        logger.debug("HTTP session created for connection pooling")
    return _session


def fetch_url(url: str, timeout: Optional[int] = None) -> Optional[str]:
    """Fetch URL content with timeout and error handling.
    
    Args:
        url: URL to fetch
        timeout: Optional timeout in seconds. Defaults to config value.
    
    Returns:
        Response text as string, or None if request fails.
    
    Example:
        >>> fetch_url('https://example.com', timeout=5)
        '<html>...</html>'
    """
    if timeout is None:
        timeout = config.get('timeout', 10)
    
    session = get_session()
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.Timeout:
        logger.warning(f"Timeout fetching {url}")
        return None
    except requests.RequestException as e:
        logger.warning(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}", exc_info=True)
        return None


def sanitize_text(text: Optional[str]) -> str:
    """Sanitize text by removing extra whitespace.
    
    Removes newlines and carriage returns, replacing them with spaces.
    Also strips leading/trailing whitespace.
    
    Args:
        text: Text to sanitize
    
    Returns:
        Sanitized text string.
    
    Example:
        >>> sanitize_text('Line 1\nLine 2\rLine 3')
        'Line 1 Line 2 Line 3'
    """
    if not text:
        return ""
    return text.strip().replace("\n", " ").replace("\r", "")
