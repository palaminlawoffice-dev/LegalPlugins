from __future__ import annotations

import os
from pathlib import Path
from contextlib import asynccontextmanager
from starlette.responses import HTMLResponse, JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.routing import Route, Mount
from starlette.applications import Starlette

from .sources import search_official, fetch_source, verify_citation
from .workflow import legal_research_workflow
from .research_engine import cache_get, cache_set, init_db

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"


class BearerAuthMiddleware:
    def __init__(self, app: ASGIApp, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        if path == "/health" or path == "/":
            return await self.app(scope, receive, send)
        auth = ""
        for key, value in scope.get("headers", []):
            if key.lower() == b"authorization":
                auth = value.decode("latin-1")
                break
        if auth != f"Bearer {self.token}":
            response = JSONResponse({"error": "Unauthorized"}, status_code=401)
            return await response(scope, receive, send)
        return await self.app(scope, receive, send)


def create_app(mcp, token: str):
    init_db()

    # Mounted Streamable HTTP apps do not run their child lifespan automatically.
    # Enter the MCP session manager from the parent ASGI application's lifespan.
    @asynccontextmanager
    async def lifespan(app):
        async with mcp.session_manager.run():
            yield
    async def health(request):
        return JSONResponse({"status": "ok", "service": "thai-legal-mcp"})

    async def index(request):
        html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(html)

    async def search_law(request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return JSONResponse({"error": "q is required"}, status_code=400)
        limit = min(max(int(request.query_params.get("limit", "10")), 1), 20)
        result = await search_official(q, "ocs", limit)
        return JSONResponse(result.model_dump())

    async def search_case(request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return JSONResponse({"error": "q is required"}, status_code=400)
        limit = min(max(int(request.query_params.get("limit", "10")), 1), 20)
        result = await search_official(q, "supreme_court", limit)
        return JSONResponse(result.model_dump())

    async def research(request):
        if request.method != "POST":
            return JSONResponse({"error": "POST required"}, status_code=405)
        body = await request.json()
        facts = str(body.get("facts", "")).strip()
        issue = str(body.get("issue_hint", "")).strip()
        if not facts:
            return JSONResponse({"error": "facts is required"}, status_code=400)
        result = await legal_research_workflow(facts, issue)
        return JSONResponse(result)

    async def fetch(request):
        url = request.query_params.get("url", "").strip()
        if not url:
            return JSONResponse({"error": "url is required"}, status_code=400)
        return JSONResponse(await fetch_source(url))

    async def cache_status(request):
        return JSONResponse({"status": "ok", "database": "sqlite", "path": os.getenv("LEGAL_DB_PATH", "data/legal_research.sqlite3")})

    async def verify(request):
        url = request.query_params.get("url", "").strip()
        expected_text = request.query_params.get("expected_text", "")
        expected_title = request.query_params.get("expected_title", "")
        if not url:
            return JSONResponse({"error": "url is required"}, status_code=400)
        return JSONResponse(await verify_citation(url, expected_text or None, expected_title or None))

    routes = [
        Route("/", index, methods=["GET"]),
        Route("/health", health, methods=["GET"]),
        Route("/api/law", search_law, methods=["GET"]),
        Route("/api/cases", search_case, methods=["GET"]),
        Route("/api/research", research, methods=["POST"]),
        Route("/api/fetch", fetch, methods=["GET"]),
        Route("/api/verify", verify, methods=["GET"]),
        Route("/api/cache", cache_status, methods=["GET"]),
        Mount("/mcp", app=mcp.streamable_http_app(stateless_http=True, host="0.0.0.0")),
    ]
    app = Starlette(routes=routes, lifespan=lifespan)
    app.add_middleware(BearerAuthMiddleware, token=token)
    return app
