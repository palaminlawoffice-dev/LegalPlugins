from urllib.parse import urlparse
from .settings import CONFIG

ALLOWED = {h.lower() for h in CONFIG["policy"]["allowed_hosts"]}

def assert_allowed_url(url: str) -> None:
    p = urlparse(url)
    if p.scheme != "https":
        raise ValueError("Only HTTPS URLs are permitted")
    host = (p.hostname or "").lower()
    if host not in ALLOWED:
        raise ValueError(f"Blocked non-whitelisted host: {host}")
