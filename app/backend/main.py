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
from text_rules import parse_document  # noqa: E402

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
    mode: str = "sample"          # sample | document | record
    resume_id: str | None = None  # mode=sample
    text: str | None = None       # mode=document (파일/붙여넣기 경로)
    record: dict | None = None    # mode=record


@app.post("/api/sessions")
def create_session(req: CreateReq):
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
        parsed = parse_document(req.text)
        record = to_internal(parsed)
        source = "document"
    elif req.mode == "record":
        if not req.record:
            raise HTTPException(400, "record 가 필요합니다.")
        record = req.record
        source = "record"
    else:
        raise HTTPException(400, f"알 수 없는 mode: {req.mode}")

    s = Session(record, source=source)
    SESSIONS[s.id] = s
    return {"session_id": s.id, "source": s.source,
            "progress": s.progress(), "profile": record.get("profile", {})}


def to_internal(parsed):
    """text_rules 파서 출력(이름 기반)을 내부 레코드 스키마로 변환한다."""
    rec = {"profile": {"name": "", "target_job": ""},
           "education": [], "careers": [], "activities": [],
           "extracurricular": [], "personal_projects": [],
           "skills": [], "certificates": [], "languages": []}
    for i, e in enumerate(parsed.get("education", []), 1):
        rec["education"].append({
            "period": {"start": e.get("period_start"), "end": e.get("period_end")},
            "school": e.get("school"), "major": "", "degree": e.get("degree"),
            "thesis": e.get("degree") in ("석사", "박사"),
            "research_topic": e.get("research_topic")})
    for i, c in enumerate(parsed.get("careers", []), 1):
        projects = []
        for j, p in enumerate(c.get("projects", []), 1):
            projects.append({
                "project_id": f"C{i}-P{j}", "name": p.get("name"),
                "period": {"start": c.get("period_start"), "end": c.get("period_end")},
                "role": p.get("role"),
                "metrics": [] if not p.get("metrics") else [
                    {"name": p["metrics"], "value": 0, "unit": "", "direction": "up"}],
                "result": p.get("result")})
        rec["careers"].append({
            "career_id": f"C{i}", "company": c.get("company"), "company_scale": "",
            "period": {"start": c.get("period_start"), "end": c.get("period_end")},
            "role": c.get("role"), "department": None, "position": None,
            "projects": projects})
    for i, a in enumerate(parsed.get("extracurricular", []), 1):
        rec["extracurricular"].append({
            "activity_id": f"E{i}", "category": "활동", "name": a.get("name"),
            "period": {"start": "", "end": ""},
            "role": a.get("role"), "result": a.get("result")})
    for i, a in enumerate(parsed.get("activities", []), 1):
        rec["activities"].append({
            "activity_id": f"A{i}",
            "period": {"start": a.get("period_start"), "end": a.get("period_end")},
            "title": a.get("title"), "covers_gap_between": ["", ""]})
    return rec


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
    return {"ok": True, "sessions": len(SESSIONS), "corpus": len(corpus())}


# ------------------------------------------------------------------ 정적 파일
DIST = os.path.join(ROOT, "app", "frontend", "dist")
if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")),
              name="assets")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(DIST, "index.html"))
