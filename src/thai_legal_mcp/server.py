from __future__ import annotations

import os
from mcp.server import MCPServer

from .settings import CONFIG
from .sources import (
    search_official,
    fetch_source,
    verify_citation,
    research_case as _research_case,
)
from .workflow import legal_research_workflow, SYSTEM_POLICY

mcp = MCPServer(
    "Thai Legal Research MCP",
    instructions=SYSTEM_POLICY,
)

@mcp.tool()
async def search_law(query: str, limit: int = 10) -> dict:
    """ค้นกฎหมายไทยจากแหล่งทางการที่ whitelist ไว้"""
    return (await search_official(query, "ocs", limit)).model_dump()

@mcp.tool()
async def search_supreme_court(query: str, limit: int = 10) -> dict:
    """ค้นคำพิพากษา/คำสั่ง/คำวินิจฉัยศาลฎีกา โดยผลค้นหาต้องตรวจต้นฉบับก่อนอ้าง"""
    return (await search_official(query, "supreme_court", limit)).model_dump()

@mcp.tool()
async def search_gazette(query: str, limit: int = 10) -> dict:
    """ค้นราชกิจจานุเบกษาเพื่อยืนยันการประกาศใช้หรือแก้ไขกฎหมาย"""
    return (await search_official(query, "gazette", limit)).model_dump()

@mcp.tool()
async def fetch_official_source(url: str) -> dict:
    """ดึงข้อมูลจาก URL ทางการที่ whitelist พร้อม SHA-256"""
    return await fetch_source(url)

@mcp.tool()
async def verify_source(url: str, expected_text: str = "", expected_title: str = "") -> dict:
    """ตรวจ URL ชื่อเรื่อง และข้อความกับข้อมูลที่ดึงจากแหล่งทางการ"""
    return await verify_citation(url, expected_text or None, expected_title or None)

@mcp.tool()
async def research_case(facts: str, issue_hint: str = "", law_limit: int = 10, case_limit: int = 10) -> dict:
    """ค้นกฎหมายและฎีกาอย่างเป็นระบบจากข้อเท็จจริง/ประเด็นที่ให้มา โดยยังไม่สรุปผลทางกฎหมายแทนผู้ใช้"""
    return await _research_case(facts, issue_hint, law_limit, case_limit)

@mcp.tool()
async def run_legal_workflow(facts: str, issue_hint: str = "") -> dict:
    """เริ่ม workflow: ข้อเท็จจริง -> ประเด็น -> ค้นกฎหมาย/ฎีกา -> verification gate -> พร้อมสำหรับการวิเคราะห์"""
    return await legal_research_workflow(facts, issue_hint)

@mcp.tool()
async def source_policy() -> dict:
    """แสดงแหล่งข้อมูลที่อนุญาตและกฎการตรวจสอบ"""
    return {"config": CONFIG, "policy": SYSTEM_POLICY}


def _run_stdio() -> None:
    mcp.run(transport="stdio")


def _run_http() -> None:
    # Streamable HTTP is the current deployment transport for remote MCP hosts.
    # Authentication is enforced by the small ASGI wrapper in http_server.py.
    from .http_server import create_app
    import uvicorn

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("PORT", os.getenv("MCP_PORT", "8000")))
    token = os.getenv("MCP_AUTH_TOKEN", "")
    if not token:
        raise RuntimeError("MCP_AUTH_TOKEN is required for HTTP mode")
    app = create_app(mcp, token)
    uvicorn.run(app, host=host, port=port, log_level="info")


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    if transport in {"http", "streamable-http"}:
        _run_http()
    else:
        _run_stdio()


if __name__ == "__main__":
    main()
