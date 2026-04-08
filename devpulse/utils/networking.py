import requests
from devpulse.config import config

def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': config.get('user_agent', 'devpulse/1.0')
    })
    return session

def fetch_url(url, timeout=None):
    if timeout is None:
        timeout = config.get('timeout', 10)
    
    session = get_session()
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as e:
        # Log error or return None
        return None

def sanitize_text(text):
    if not text:
        return ""
    # Basic sanitization
    return text.strip().replace("\n", " ").replace("\r", "")
