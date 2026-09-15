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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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


@app.get("/api/health")
def health():
    c = norm_config()
    return {"ok": True, "sessions": len(SESSIONS), "corpus": len(corpus()),
            "normalizer": {"mode": c["mode"], "model": c["model"],
                           "api_key": bool(c["api_key"])}}


# ------------------------------------------------------------------ 정적 파일
DIST = os.path.join(ROOT, "app", "frontend", "dist")
if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")),
              name="assets")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(DIST, "index.html"))
