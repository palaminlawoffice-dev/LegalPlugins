from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .settings import ROOT

DB_PATH = Path(__import__('os').getenv('LEGAL_DB_PATH', str(ROOT / 'data' / 'legal_research.sqlite3')))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def init_db() -> None:
    with _connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS cache (
            cache_key TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS research_runs (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            facts_hash TEXT NOT NULL,
            issue_hint TEXT NOT NULL,
            status TEXT NOT NULL,
            result_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            event TEXT NOT NULL,
            source TEXT,
            url TEXT,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_events(run_id);
        ''')


def cache_get(key: str) -> Any | None:
    with _connect() as db:
        row = db.execute('SELECT payload, expires_at FROM cache WHERE cache_key=?', (key,)).fetchone()
        if not row:
            return None
        if row['expires_at'] <= now_iso():
            db.execute('DELETE FROM cache WHERE cache_key=?', (key,))
            return None
        return json.loads(row['payload'])


def cache_set(key: str, source: str, payload: Any, ttl_seconds: int = 900) -> None:
    from datetime import timedelta
    created = datetime.now(timezone.utc)
    expires = created + timedelta(seconds=ttl_seconds)
    with _connect() as db:
        db.execute(
            'INSERT OR REPLACE INTO cache(cache_key,source,payload,created_at,expires_at) VALUES(?,?,?,?,?)',
            (key, source, json.dumps(payload, ensure_ascii=False), created.isoformat(), expires.isoformat()),
        )


def cache_key(*parts: str) -> str:
    raw = '\x1f'.join(parts)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8', errors='ignore')).hexdigest()


def decompose_issues(facts: str, issue_hint: str = '') -> list[dict[str, Any]]:
    """Deterministic first-pass issue decomposition. The LLM can refine this later."""
    text = f'{issue_hint} {facts}'.strip()
    patterns = [
        ('องค์ประกอบความผิด/การกระทำ', r'ทำร้าย|ฟัน|แทง|ยิง|ตี|ชก|ทำให้บาดเจ็บ|เสียชีวิต'),
        ('เจตนา/สภาพจิตใจ', r'เจตนา|ประมาท|รู้|ย่อมเล็งเห็น|ตั้งใจ'),
        ('ความสัมพันธ์ของคู่กรณี', r'พ่อ|แม่|บิดา|มารดา|บุตร|สามี|ภริยา|ญาติ|บุพการี'),
        ('ผลของการกระทำ/ระดับความเสียหาย', r'บาดเจ็บ|แผล|อันตรายแก่กาย|อันตรายสาหัส|เสียชีวิต'),
        ('อำนาจฟ้อง/สิทธิผู้เสียหาย', r'ฟ้อง|ร้องทุกข์|ผู้เสียหาย|อุทลุม|อำนาจฟ้อง'),
        ('กฎหมายที่ใช้บังคับตามเวลา', r'เกิดเหตุ|วันที่|พ\.ศ\.|แก้ไข|ฉบับ|ใช้บังคับ'),
    ]
    out: list[dict[str, Any]] = []
    for label, pattern in patterns:
        if re.search(pattern, text, re.I):
            out.append({'issue': label, 'trigger': pattern, 'status': 'candidate'})
    if not out:
        out.append({'issue': 'ประเด็นกฎหมายที่ต้องกำหนดจากข้อเท็จจริง', 'trigger': None, 'status': 'candidate'})
    return out


def evidence_grade(source: str, verified: bool) -> str:
    if verified and source in {'ocs', 'supreme_court', 'gazette'}:
        return 'A'
    if source in {'ocs', 'supreme_court', 'gazette'}:
        return 'B'
    return 'X'


def save_run(run_id: str, facts: str, issue_hint: str, status: str, result: dict[str, Any]) -> None:
    with _connect() as db:
        db.execute(
            'INSERT OR REPLACE INTO research_runs(id,created_at,facts_hash,issue_hint,status,result_json) VALUES(?,?,?,?,?,?)',
            (run_id, now_iso(), hash_text(facts), issue_hint, status, json.dumps(result, ensure_ascii=False)),
        )


def audit(run_id: str, event: str, source: str = '', url: str = '', **details: Any) -> None:
    with _connect() as db:
        db.execute(
            'INSERT INTO audit_events(run_id,event,source,url,details_json,created_at) VALUES(?,?,?,?,?,?)',
            (run_id, event, source, url, json.dumps(details, ensure_ascii=False), now_iso()),
        )


def contradiction_check(result: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for section in ('law_search', 'case_search'):
        data = result.get(section, {}) or {}
        for hit in data.get('hits', []):
            if hit.get('source') not in {'ocs', 'supreme_court', 'gazette'}:
                warnings.append(f"แหล่ง {hit.get('url','')} ไม่ใช่ official source ที่ยืนยันได้")
    for citation in result.get('citations', []):
        if citation.get('verified') is False and citation.get('content_hash'):
            warnings.append(f"Citation {citation.get('id')} มีข้อมูลที่ดึงแล้วแต่ยังไม่ผ่าน verification")
    return warnings


init_db()
