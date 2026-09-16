#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
상호작용형 이력서 자동 생성 — API 서버.

명세서 도 1의 110/120/130 을 HTTP 경계로 노출한다.

    POST /api/sessions              수집부(110): 레코드로 세션 생성
    GET  /api/sessions/{id}/next    분석부(120): 다음 질의 프롬프트
    POST /api/sessions/{id}/answer  생성부(130): 답변 파싱 → 병합
    GET  /api/sessions/{id}/preview 미리보기 화면 데이터
    POST /api/sessions/{id}/confirm 확정 신호 수신
    GET  /api/sessions/{id}/trace   질의-답변-파싱 이력

실행:
    uvicorn app.backend.main:app --reload --port 8000
"""
from __future__ import annotations

import json
import os
import random
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from engine import Session, TYPE_KO  # noqa: E402
from normalize import normalize, config as norm_config  # noqa: E402

app = FastAPI(title="Interactive Resume Generator", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SESSIONS: dict[str, Session] = {}
CORPUS_PATH = os.path.join(ROOT, "output", "resumes.jsonl")
_corpus: list[dict] | None = None


def corpus():
    global _corpus
    if _corpus is None:
        if not os.path.exists(CORPUS_PATH):
            _corpus = []
        else:
            _corpus = [json.loads(l) for l in open(CORPUS_PATH, encoding="utf-8")]
    return _corpus


# ------------------------------------------------------------------ 샘플 목록
def render_document(rec):
    """말뭉치 레코드를 사람이 읽을 수 있는 이력서 본문으로 되돌린다."""
    L = [f"[학력]"]
    for e in rec.get("education", []):
        L.append(f"{e['period']['start']} ~ {e['period']['end']}  "
                 f"{e['school']} {e.get('major','')} ({e.get('degree','')})")
        if e.get("research_topic"):
            L.append(f"    연구 주제: {e['research_topic']}")
    L += ["", "[경력]"]
    if not rec.get("careers"):
        L.append("  해당 없음 (신입)")
    for c in rec.get("careers", []):
        head = f"{c['period']['start']} ~ {c['period']['end']}  {c['company']}"
        if c.get("role"):
            head += f" / {c['role']}"
        L.append(head)
        for p in c.get("projects", []):
            L.append(f"  - {p['name']}")
            if p.get("role"):
                L.append(f"    담당: {p['role']}")
            if p.get("metrics"):
                L.append("    성과: " + ", ".join(
                    f"{m['name']} {m['value']}{m.get('unit','')}" for m in p["metrics"]))
            if p.get("result"):
                L.append(f"    결과: {p['result']}")
    for key, title in (("personal_projects", "[프로젝트]"),):
        if rec.get(key):
            L += ["", title]
            for p in rec[key]:
                L.append(f"  - {p['name']}")
    if rec.get("extracurricular"):
        L += ["", "[대외활동]"]
        for a in rec["extracurricular"]:
            line = f"{a['period']['start']} ~ {a['period']['end']}  [{a.get('category','활동')}] {a['name']}"
            if a.get("role"):
                line += f" / {a['role']}"
            L.append(line)
    if rec.get("skills"):
        L += ["", "[기술]", ", ".join(rec["skills"])]
    return "\n".join(L)


@app.get("/api/samples")
def samples(n: int = 3, seed: int | None = None):
    """무작위 샘플 후보를 본문과 함께 돌려준다. 사용자가 보고 고를 수 있게 한다."""
    pool = [r for r in corpus() if r["missingness"]]
    if not pool:
        raise HTTPException(503, "말뭉치가 없습니다. src/generate.py 를 먼저 실행하세요.")
    rng = random.Random(seed) if seed is not None else random
    picked = rng.sample(pool, min(n, len(pool)))
    out = []
    for r in picked:
        obs = r["observed"]
        types = sorted({m["type"] for m in r["missingness"]})
        out.append({
            "resume_id": r["resume_id"],
            "domain": r["domain"],
            "name": obs.get("profile", {}).get("name", ""),
            "target_job": obs.get("profile", {}).get("target_job", ""),
            "entry_type": r["gold"].get("entry_type", ""),
            "careers": len(obs.get("careers", [])),
            "missing_count": len(r["missingness"]),
            "missing_types": [TYPE_KO.get(t, t) for t in types],
            "document": render_document(obs),
        })
    return {"samples": out}


# ------------------------------------------------------------------ 수집부(110)
class CreateReq(BaseModel):
    mode: str = "sample"           # sample | document | record
    resume_id: str | None = None   # mode=sample
    text: str | None = None        # mode=document (파일/붙여넣기 경로)
    record: dict | None = None     # mode=record
    normalizer: str | None = None  # auto | llm | rules  (mode=document)


@app.post("/api/sessions")
def create_session(req: CreateReq):
    norm_meta = {"path": "n/a"}
    if req.mode == "sample":
        pool = [r for r in corpus() if r["missingness"]]
        if not pool:
            raise HTTPException(503, "말뭉치가 없습니다. generate.py 를 먼저 실행하세요.")
        rec = (next((r for r in pool if r["resume_id"] == req.resume_id), None)
               if req.resume_id else random.choice(pool))
        if rec is None:
            raise HTTPException(404, "해당 이력서를 찾을 수 없습니다.")
        record = json.loads(json.dumps(rec["observed"], ensure_ascii=False))
        source = f"sample:{rec['resume_id']}"
        norm_meta = {"path": "corpus",
                     "reason": "말뭉치의 구조화 레코드라 정규화 단계를 거치지 않습니다."}
    elif req.mode == "document":
        if not req.text or not req.text.strip():
            raise HTTPException(400, "본문이 비어 있습니다.")
        record, meta = normalize(req.text, mode=req.normalizer)
        if record is None:
            raise HTTPException(502, f"정규화에 실패했습니다: {meta.get('reason')}")
        source = f"document({meta['path']})"
        norm_meta = meta
    elif req.mode == "record":
        if not req.record:
            raise HTTPException(400, "record 가 필요합니다.")
        record = req.record
        source = "record"
    else:
        raise HTTPException(400, f"알 수 없는 mode: {req.mode}")

    s = Session(record, source=source)
    s.norm_meta = norm_meta
    SESSIONS[s.id] = s
    return {"session_id": s.id, "source": s.source, "normalizer": norm_meta,
            "progress": s.progress(), "profile": record.get("profile", {})}


# ------------------------------------------------------------------ 분석부(120)
def get(sid) -> Session:
    s = SESSIONS.get(sid)
    if s is None:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    return s


@app.get("/api/sessions/{sid}/next")
def next_question(sid: str, limit: int = 1):
    s = get(sid)
    qs = s.next_questions(limit=limit)
    return {"questions": [{k: v for k, v in q.items() if k != "instance"} for q in qs],
            "progress": s.progress()}


# ------------------------------------------------------------------ 생성부(130)
class AnswerReq(BaseModel):
    key: str
    answer: str


@app.post("/api/sessions/{sid}/answer")
def answer(sid: str, req: AnswerReq):
    s = get(sid)
    res = s.submit(req.key, req.answer)
    return {**res, "progress": s.progress(), "trace": s.trace[-1] if s.trace else None}


@app.get("/api/sessions/{sid}/info")
def info(sid: str):
    """세션 개요. 화면 상단 배지에 쓰인다."""
    s = get(sid)
    c = norm_config()
    return {"source": s.source,
            "normalizer": getattr(s, "norm_meta", {"path": "n/a"}),
            "config": {"mode": c["mode"], "model": c["model"],
                       "api_key": bool(c["api_key"])},
            "document": render_document(s.record),
            "progress": s.progress()}


@app.get("/api/sessions/{sid}/preview")
def preview(sid: str):
    s = get(sid)
    return {"preview": s.preview(), "progress": s.progress(),
            "confirmed_at": s.confirmed_at}


@app.get("/api/sessions/{sid}/trace")
def trace(sid: str):
    s = get(sid)
    return {"trace": s.trace, "source": s.source, "created_at": s.created_at}


@app.post("/api/sessions/{sid}/confirm")
def confirm(sid: str):
    s = get(sid)
    return s.confirm()


def dist_info():
    """현재 서빙 중인 프런트엔드 빌드 정보. 화면이 갱신되지 않을 때 확인용."""
    index = os.path.join(DIST, "index.html")
    if not os.path.isfile(index):
        return {"built": False}
    import datetime
    assets_dir = os.path.join(DIST, "assets")
    files = sorted(os.listdir(assets_dir)) if os.path.isdir(assets_dir) else []
    return {"built": True,
            "built_at": datetime.datetime.fromtimestamp(
                os.path.getmtime(index)).isoformat(timespec="seconds"),
            "assets": files}


@app.get("/api/health")
def health():
    c = norm_config()
    return {"ok": True, "sessions": len(SESSIONS), "corpus": len(corpus()),
            "frontend": dist_info(),
            "normalizer": {"mode": c["mode"], "model": c["model"],
                           "api_key": bool(c["api_key"])}}


# ------------------------------------------------------------------ 정적 파일
#
# 프런트엔드 빌드 산출물(app/frontend/dist)을 백엔드가 함께 서빙한다.
# 존재 여부를 요청 시점에 확인하므로, 서버를 먼저 띄운 뒤 빌드해도 재시작이
# 필요 없다. dist 가 없으면 빌드 방법을 안내하는 페이지를 대신 보여준다.

DIST = os.path.join(ROOT, "app", "frontend", "dist")

NO_BUILD_PAGE = """<!doctype html><html lang="ko"><meta charset="utf-8">
<title>프런트엔드 빌드 필요</title>
<body style="font-family:system-ui,sans-serif;max-width:640px;margin:80px auto;
             line-height:1.7;color:#14171c">
<h1 style="color:#1f3864;font-size:20px">프런트엔드가 아직 빌드되지 않았습니다</h1>
<p>API 서버는 정상 동작 중입니다. 화면을 보려면 아래를 실행하세요.</p>
<pre style="background:#f6f7f9;border-left:3px solid #1f3864;padding:12px">
cd app/frontend
npm ci
npm run build</pre>
<p>빌드가 끝나면 이 페이지를 새로고침하면 됩니다. 서버를 다시 띄울 필요는 없습니다.</p>
<p style="color:#6b7280;font-size:14px">개발 중에는
<code>npm run dev</code> (http://localhost:5173) 를 쓰는 편이 편합니다.
해당 서버가 <code>/api</code> 요청을 이 백엔드로 프록시합니다.</p>
</body></html>"""


@app.get("/assets/{path:path}")
def assets(path: str):
    """Vite 가 생성한 해시 파일명 자산(js/css)을 서빙한다.

    파일명에 내용 해시가 들어가므로 내용이 바뀌면 이름도 바뀐다. 따라서
    오래 캐시해도 안전하다.
    """
    full = os.path.normpath(os.path.join(DIST, "assets", path))
    if not full.startswith(os.path.join(DIST, "assets")) or not os.path.isfile(full):
        raise HTTPException(404, "asset not found")
    return FileResponse(full, headers={"cache-control": "public, max-age=31536000, immutable"})


@app.get("/{path:path}")
def spa(path: str):
    """SPA 진입점. /api 로 시작하지 않는 모든 경로는 index.html 로 보낸다."""
    if path.startswith("api/"):
        raise HTTPException(404, "not found")
    index = os.path.join(DIST, "index.html")
    if not os.path.isfile(index):
        return HTMLResponse(NO_BUILD_PAGE, status_code=503)
    direct = os.path.normpath(os.path.join(DIST, path))
    if path and direct.startswith(DIST) and os.path.isfile(direct):
        return FileResponse(direct)
    # index.html 은 절대 캐시하지 않는다. 캐시되면 다시 빌드해도 브라우저가
    # 예전 자산 해시를 계속 요청해, 소스를 고쳤는데 화면이 그대로인 상태가 된다.
    return FileResponse(index, headers={
        "cache-control": "no-store, no-cache, must-revalidate",
        "pragma": "no-cache"})
