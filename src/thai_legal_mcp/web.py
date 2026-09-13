import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse, quote_plus
import httpx
from bs4 import BeautifulSoup
try:
    import trafilatura
except ImportError:  # optional fallback for minimal installs
    trafilatura = None
from .security import assert_allowed_url
from .settings import HTTP_TIMEOUT

HEADERS = {
    "User-Agent": "ThaiLegalMCP/0.1 (+legal-research; official-source-only)",
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.5",
}

async def fetch(url: str) -> tuple[str, str]:
    assert_allowed_url(url)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
        r = await client.get(url)
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "text/html" not in ct and "application/xhtml" not in ct:
            text = r.text
        else:
            text = (trafilatura.extract(r.text, include_links=True, include_tables=True) if trafilatura else None) or BeautifulSoup(r.text, "html.parser").get_text("\n", strip=True)
        return text, str(r.url)

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

async def discover(query: str, domains: list[str], limit: int = 10) -> list[dict]:
    # Discovery only. Evidence is never accepted from the search engine.
    site = " OR ".join(f"site:{d}" for d in domains)
    q = f"{query} {site}"
    url = "https://www.bing.com/search?q=" + quote_plus(q) + f"&count={limit}"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
        r = await client.get(url)
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for li in soup.select("li.b_algo"):
        a = li.select_one("h2 a")
        if not a or not a.get("href"):
            continue
        href = a["href"]
        host = (urlparse(href).hostname or "").lower()
        if host not in {d.lower() for d in domains}:
            continue
        p = li.select_one(".b_caption p")
        out.append({"title": a.get_text(" ", strip=True), "url": href, "snippet": p.get_text(" ", strip=True) if p else ""})
        if len(out) >= limit:
            break
    return out
