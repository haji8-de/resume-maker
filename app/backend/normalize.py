#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
원문 텍스트 → 공통 이력서 레코드 정규화 (데이터 형식 변환부, 114).

두 가지 경로를 제공한다.

  rules   정규식 파서(`src/text_rules.py`). 외부 의존이 없고 즉시 동작하지만
          표기가 조금만 흔들려도 무너진다. 실제 입력에서 '~.' 같은 오타 하나로
          경력 두 건이 누락되는 것을 확인했다.

  llm     언어 모델에게 **정규화만** 시킨다. 무엇이 빠졌는지 판단시키지 않고
          있는 것을 그대로 옮기게 한 뒤, 부재 판단은 결정적 탐지기가 맡는다.
          논문 실험에서 이 구성이 직접 탐지(F1 0.31~0.38)보다 크게 앞섰다
          (F1 0.87~0.93).

기본값은 `auto` 로, 키가 있으면 llm 을 쓰고 실패하면 rules 로 되돌아간다.
어느 경로를 탔는지는 반환 메타에 남아 화면과 증빙에서 확인할 수 있다.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from text_rules import parse_document, norm_date  # noqa: E402

API_URL = "https://api.anthropic.com/v1/messages"

NORMALIZE_PROMPT = """Convert the Korean resume below into JSON. Copy what is
written; do NOT infer, complete, or guess anything. Use null when a value is
absent from the text --- absence is the signal we care about.

{
 "name": "applicant name or null",
 "target_job": "desired position or null",
 "education": [{"school": "...", "major": "... or null",
                "degree": "고졸|전문학사|학사|석사|박사|null",
                "period_start": "YYYY-MM|YYYY|null",
                "period_end": "YYYY-MM|YYYY|null",
                "research_topic": "... or null"}],
 "careers": [{"company": "...", "role": "job title or null",
              "period_start": "YYYY-MM|YYYY|null",
              "period_end": "YYYY-MM|YYYY|현재|null",
              "projects": [{"name": "...", "role": "who did what, or null",
                            "metrics": "quantitative outcome, or null",
                            "result": "final result, or null"}]}],
 "personal_projects": [{"name": "...", "role": null, "metrics": null, "result": null}],
 "activities": [{"title": "...", "period_start": "...", "period_end": "..."}],
 "extracurricular": [{"name": "...", "role": "... or null", "result": "... or null"}]
}

Rules:
- Separators vary. '~', '~.', '-', '부터' all mean a period range, and
  '2014.02', '2014-02', '2014년 2월' all mean the same month.
- A line like '2016-07 ~ 2018-09 네이버. 데이터 엔지니어' has company '네이버'
  and role '데이터 엔지니어'. Do not merge them.
- "activities" is only for non-employment periods used to fill a gap (study,
  training, job search). Club, contest and internship entries go in
  "extracurricular".
- Keep names verbatim. Output ONLY the JSON object, no prose, no code fence."""


# ------------------------------------------------------------------ 설정
def load_env(path=None):
    """.env 를 읽어 os.environ 에 채운다. 이미 설정된 값은 덮지 않는다."""
    path = path or os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def config():
    load_env()
    return {
        "api_key": os.environ.get("ANTHROPIC_API_KEY", "").strip(),
        "model": os.environ.get("NORMALIZER_MODEL", "claude-sonnet-5").strip(),
        "mode": os.environ.get("NORMALIZER", "auto").strip().lower(),
        "timeout": int(os.environ.get("NORMALIZER_TIMEOUT", "60")),
    }


# ------------------------------------------------------------------ LLM 호출
def call_llm(text, cfg):
    body = json.dumps({
        "model": cfg["model"],
        "max_tokens": 8000,
        "system": NORMALIZE_PROMPT,
        "messages": [{"role": "user", "content": "Resume:\n\n" + text}],
    }).encode()
    req = urllib.request.Request(API_URL, data=body, headers={
        "x-api-key": cfg["api_key"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=cfg["timeout"]) as r:
        d = json.loads(r.read())
    return "".join(b.get("text", "") for b in d.get("content", []))


def parse_json(raw):
    s = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


# ------------------------------------------------------------------ 스키마 변환
def to_record(parsed):
    """정규화 결과(이름 기반)를 내부 레코드 스키마로 옮긴다."""
    rec = {
        "profile": {"name": parsed.get("name") or "",
                    "target_job": parsed.get("target_job") or ""},
        "education": [], "careers": [], "activities": [],
        "extracurricular": [], "personal_projects": [],
        "skills": parsed.get("skills") or [],
        "certificates": parsed.get("certificates") or [],
        "languages": parsed.get("languages") or [],
    }

    for e in parsed.get("education") or []:
        deg = e.get("degree")
        rec["education"].append({
            "period": {"start": norm_date(e.get("period_start") or ""),
                       "end": norm_date(e.get("period_end") or "")},
            "school": e.get("school") or "", "major": e.get("major") or "",
            "degree": deg, "gpa": None,
            "thesis": deg in ("석사", "박사"),
            "research_topic": e.get("research_topic"),
        })

    for i, c in enumerate(parsed.get("careers") or [], 1):
        projects = []
        for j, p in enumerate(c.get("projects") or [], 1):
            projects.append({
                "project_id": f"C{i}-P{j}", "name": p.get("name") or "",
                "period": {"start": norm_date(c.get("period_start") or ""),
                           "end": norm_date(c.get("period_end") or "")},
                "role": p.get("role"),
                "metrics": as_metrics(p.get("metrics")),
                "result": p.get("result"),
            })
        rec["careers"].append({
            "career_id": f"C{i}", "company": c.get("company") or "",
            "company_scale": "",
            "period": {"start": norm_date(c.get("period_start") or ""),
                       "end": norm_date(c.get("period_end") or "")},
            "role": c.get("role"), "department": None, "position": None,
            "projects": projects,
        })

    for j, p in enumerate(parsed.get("personal_projects") or [], 1):
        rec["personal_projects"].append({
            "project_id": f"PP{j}", "name": p.get("name") or "",
            "period": {"start": "", "end": ""},
            "role": p.get("role"), "metrics": as_metrics(p.get("metrics")),
            "result": p.get("result"),
        })

    for k, a in enumerate(parsed.get("activities") or [], 1):
        rec["activities"].append({
            "activity_id": f"A{k}",
            "period": {"start": norm_date(a.get("period_start") or ""),
                       "end": norm_date(a.get("period_end") or "")},
            "title": a.get("title") or "",
            "covers_gap_between": ["", ""],
        })

    for k, a in enumerate(parsed.get("extracurricular") or [], 1):
        rec["extracurricular"].append({
            "activity_id": f"E{k}", "category": a.get("category") or "활동",
            "name": a.get("name") or "",
            "period": {"start": norm_date(a.get("period_start") or ""),
                       "end": norm_date(a.get("period_end") or "")},
            "role": a.get("role"), "result": a.get("result"),
        })
    return rec


def as_metrics(v):
    """정규화기가 성과를 문자열로 주면 원문 그대로 보존한다."""
    if not v:
        return []
    if isinstance(v, list):
        return v
    return [{"name": str(v), "value": "", "unit": "", "direction": "up", "raw": True}]


# ------------------------------------------------------------------ 진입점
def normalize(text, mode=None):
    """(record, meta) 를 반환한다. meta.path 는 'llm' 또는 'rules'."""
    cfg = config()
    mode = (mode or cfg["mode"]).lower()
    t0 = time.time()

    if mode in ("auto", "llm") and cfg["api_key"]:
        try:
            parsed = parse_json(call_llm(text, cfg))
            if parsed:
                rec = to_record(parsed)
                if rec["careers"] or rec["education"]:
                    return rec, {"path": "llm", "model": cfg["model"],
                                 "elapsed": round(time.time() - t0, 2)}
            reason = "응답을 레코드로 해석하지 못했습니다."
        except Exception as e:                      # noqa: BLE001
            reason = f"{type(e).__name__}: {e}"
        if mode == "llm":
            return None, {"path": "failed", "reason": reason}
    else:
        reason = "API 키가 없어 규칙 파서를 사용했습니다." if mode != "rules" else ""

    rec = to_record(rules_to_parsed(parse_document(text)))
    return rec, {"path": "rules", "reason": reason,
                 "elapsed": round(time.time() - t0, 2)}


def rules_to_parsed(d):
    """규칙 파서 출력을 LLM 출력과 같은 모양으로 맞춘다."""
    return {
        "name": d.get("name"),
        "education": d.get("education") or [],
        "careers": d.get("careers") or [],
        "personal_projects": d.get("personal_projects") or [],
        "activities": d.get("activities") or [],
        "extracurricular": d.get("extracurricular") or [],
    }
