from __future__ import annotations

from urllib.parse import urlparse

from .settings import CONFIG, MAX_RESULTS
from .web import discover, fetch, now_iso, sha256
from .models import Citation, SearchHit, ResearchBundle
from .research_engine import cache_get, cache_key, cache_set, evidence_grade

DOMAINS = CONFIG["policy"]["discovery_domains"]


def _domains_for(source: str) -> list[str]:
    if source == "ocs":
        return CONFIG["sources"]["ocs"]["domains"]
    if source == "supreme_court":
        return CONFIG["sources"]["supreme_court"]["domains"]
    if source == "gazette":
        return CONFIG["sources"]["gazette"]["domains"]
    return DOMAINS


def _classify(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for name, cfg in CONFIG["sources"].items():
        if host in {h.lower() for h in cfg["domains"]}:
            return name
    return "unknown"


async def search_official(query: str, source: str = "all", limit: int | None = None) -> ResearchBundle:
    limit = max(1, min(limit or MAX_RESULTS, MAX_RESULTS))
    domains = _domains_for(source)
    key = cache_key('search', source, query.strip(), str(limit), CONFIG['name'])
    cached = cache_get(key)
    if cached:
        return ResearchBundle.model_validate(cached)
    raw = await discover(query, domains, limit)
    hits: list[SearchHit] = []
    cites: list[Citation] = []
    for i, x in enumerate(raw, 1):
        cid = f"{source.upper()}-{i}"
        actual_source = source if source != "all" else _classify(x["url"])
        c = Citation(id=cid, source=actual_source, title=x["title"], url=x["url"], retrieved_at=now_iso(), verified=False)
        hits.append(SearchHit(source=actual_source, title=x["title"], url=x["url"], snippet=x["snippet"], citation_id=cid))
        cites.append(c)
    result = ResearchBundle(query=query, hits=hits, citations=cites, warnings=[
        "ผลค้นหาเป็น discovery เท่านั้น; ต้อง fetch + verify ก่อนอ้างอิง",
        f"แหล่งค้นที่อนุญาต: {', '.join(domains)}",
    ])
    cache_set(key, 'search', result.model_dump(), ttl_seconds=600)
    return result


async def fetch_source(url: str, title: str = "") -> dict:
    key = cache_key('fetch', url)
    cached = cache_get(key)
    if cached:
        cached['cache'] = True
        return cached
    text, final_url = await fetch(url)
    source = _classify(final_url)
    result = {
        "title": title,
        "url": final_url,
        "source": source,
        "retrieved_at": now_iso(),
        "sha256": sha256(text),
        "evidence_grade": evidence_grade(source, False),
        "verified": False,
        "text": text,
        "provenance": {"discovery": "official-domain-restricted", "verification_required": True},
    }
    cache_set(key, 'fetch', result, ttl_seconds=300)
    return result


async def verify_citation(url: str, expected_text: str | None = None, expected_title: str | None = None) -> dict:
    text, final_url = await fetch(url)
    source = _classify(final_url)
    normalized = " ".join(text.split()).lower()
    checks = {"url_allowed": True, "reachable": True, "title_match": None, "text_found": None}
    if expected_title:
        checks["title_match"] = " ".join(expected_title.split()).lower() in normalized
    if expected_text:
        checks["text_found"] = " ".join(expected_text.split()).lower() in normalized
    verified = all(v is not False for v in checks.values()) and source != 'unknown'
    return {
        "verified": verified,
        "url": final_url,
        "source": source,
        "retrieved_at": now_iso(),
        "sha256": sha256(text),
        "evidence_grade": evidence_grade(source, verified),
        "checks": checks,
        "provenance": {"source_class": "official", "content_hash": sha256(text)},
        "note": "การ verify นี้ยืนยันว่าหน้าและข้อความที่ระบุพบใน official source; ต้องตรวจสถานะกฎหมายและวันที่มีผลใช้บังคับแยกต่างหาก",
    }


async def research_case(facts: str, issue_hint: str = "", law_limit: int = 10, case_limit: int = 10) -> dict:
    query = issue_hint.strip() or facts[:1200]
    laws = await search_official(query, "ocs", law_limit)
    cases = await search_official(query, "supreme_court", case_limit)
    return {"query": query, "facts": facts, "law": laws.model_dump(), "supreme_court": cases.model_dump(),
            "next": "เลือกผลที่เกี่ยวข้อง -> fetch_official_source -> verify_source -> วิเคราะห์/ร่างความเห็น"}
