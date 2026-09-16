#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
예시 답변 생성.

## 설계 원칙: 사실을 지어내지 않는다

이력서는 고용주에게 제출하는 문서다. 그럴듯한 경력 사실을 자동으로 만들어 주면
사용자가 그대로 제출할 위험이 있고, 그 순간 이 시스템은 이력서 보완 도구가 아니라
허위 기재 도구가 된다. 근거 없는 정량 주장은 문체 문제가 아니라 허위 진술이다.

그래서 여기서 만드는 것은 **완성된 답변이 아니라 빈칸이 있는 문장 틀**이다.

    ✗  "파이프라인을 재설계해 처리 시간을 35% 줄였습니다"   ← 수치를 지어냄
    ✓  "○○를 재설계해 처리 시간을 __% 줄였습니다"          ← 사용자가 채움

틀은 질문 유형과 해당 항목의 이름(회사명·프로젝트명)만 활용한다. 숫자, 성과,
직무명처럼 사용자만 아는 값은 언제나 빈칸으로 남긴다.
"""
from __future__ import annotations

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BLANK = "____"

# 유형별 문장 틀. {name} 에는 회사명·프로젝트명 등 화면에 이미 보이는 값만 들어간다.
TEMPLATES = {
    "ROLE_OMISSION": [
        "{blank} 직무로 일했고, 주로 {blank} 업무를 담당했습니다.",
        "{blank}팀에서 {blank}로 근무했습니다.",
        "직무는 {blank}였고 {blank}을(를) 맡았습니다.",
        "{blank} 포지션이었고, {blank}와(과) {blank}을(를) 책임졌습니다.",
    ],
    "DATE_INCOMPLETE": [
        "정확히는 {blank}년 {blank}월부터 {blank}년 {blank}월까지입니다.",
        "{blank}-{blank} 부터 {blank}-{blank} 까지 재직했습니다.",
    ],
    "ACHIEVEMENT_OMISSION": [
        "제가 {blank}을(를) 맡았고, {blank}을(를) {blank}% 개선했습니다.",
        "{blank} 부분을 담당했습니다. {blank}이(가) {blank}에서 {blank}(으)로 바뀌었습니다.",
        "{blank}을(를) 수행했고 최종적으로 {blank}되었습니다.",
        "역할은 {blank}였고, {blank}을(를) {blank} 줄였습니다. 결과는 {blank}입니다.",
    ],
    "THESIS_OMISSION": [
        '학위논문 주제는 "{blank}"였습니다.',
        "{blank}을(를) 주제로 연구했습니다.",
        '"{blank}"(으)로 학위를 받았습니다.',
    ],
    "EXTRACURRICULAR_OMISSION": [
        "{blank}(으)로 참여했고, 결과는 {blank}였습니다.",
        "{blank} 역할을 맡았습니다. {blank}을(를) 했습니다.",
        "{blank}(으)로 활동했으며 {blank}에 기여했습니다.",
    ],
    "TEMPORAL_GAP": [
        "그 기간에는 {blank}을(를) 했습니다.",
        "{blank} 준비로 쉬었습니다.",
        "{blank} 과정을 수강했습니다.",
        "{blank} 사정으로 공백이 있었고, 그동안 {blank}을(를) 했습니다.",
    ],
    "POST_GRAD_GAP": [
        "졸업 후에는 {blank}을(를) 했습니다.",
        "{blank} 준비에 집중했습니다.",
        "{blank} 과정을 수료했고 {blank}을(를) 진행했습니다.",
    ],
}

def entity_name(inst, record):
    """질문 대상의 표시 이름. 화면에 이미 보이는 값만 사용한다."""
    t, loc = inst["type"], inst["locator"]
    if t in ("ROLE_OMISSION", "DATE_INCOMPLETE"):
        c = next((c for c in record["careers"]
                  if c["career_id"] == loc.get("career_id")), None)
        return c["company"] if c else ""
    if t == "ACHIEVEMENT_OMISSION":
        for c in record["careers"]:
            for p in c["projects"]:
                if p["project_id"] == loc.get("project_id"):
                    return p["name"]
        for p in record.get("personal_projects", []):
            if p["project_id"] == loc.get("project_id"):
                return p["name"]
    if t == "EXTRACURRICULAR_OMISSION":
        a = next((a for a in record.get("extracurricular", [])
                  if a["activity_id"] == loc.get("activity_id")), None)
        return a["name"] if a else ""
    if t == "THESIS_OMISSION":
        return loc.get("school", "")
    return ""


def rule_suggestions(inst, record, n=3, exclude=(), rng=None):
    """문장 틀 기반 예시. 외부 호출 없이 항상 동작한다."""
    rng = rng or random
    pool = list(TEMPLATES.get(inst["type"], ["{blank}"]))
    rng.shuffle(pool)
    # 항목명은 질문 문장에 이미 들어 있으므로 초안에 다시 붙이지 않는다.
    # 붙이면 "로그 파이프라인 구축은 역할은 ____였고" 처럼 주어가 겹친다.
    texts = [t.replace("{blank}", BLANK) for t in pool]
    fresh = [t for t in texts if t not in exclude]
    # 틀을 다 소진하면 처음부터 다시 돌린다. 버튼을 계속 눌러도 빈 화면이
    # 나오지 않도록, 반환이 비는 경우를 만들지 않는다.
    if not fresh:
        fresh = texts
    return fresh[:n]


# ------------------------------------------------------------------ LLM 경로
LLM_SYSTEM = """You draft *answer scaffolds* for a Korean resume assistant.

Absolute rule: never invent facts. You do not know the applicant's job titles,
numbers, outcomes, or dates, so every such value must be left as a blank marked
____ for the applicant to fill in. A scaffold containing an invented number or
an invented achievement is a failure, not a help.

You may use only the entity name given to you (a company, project, school or
activity name) because it is already on the applicant's screen.

Write natural spoken Korean, the way a person types into a chat box. Vary the
sentence shape across the drafts. Output ONLY a JSON array of strings."""


def llm_suggestions(inst, record, question, n=3, exclude=()):
    """모델로 문장 틀을 만든다. 실패하면 None 을 돌려 규칙 경로로 넘긴다."""
    from normalize import call_llm, parse_json, config
    cfg = config()
    if not cfg["api_key"]:
        return None
    name = entity_name(inst, record)
    avoid = "\n".join(f"- {e}" for e in exclude) if exclude else "(없음)"
    prompt = (f"질문: {question}\n"
              f"대상 항목 이름: {name or '(없음)'}\n"
              f"필요한 초안 수: {n}\n"
              f"이미 보여준 초안(다른 문장으로 만들 것):\n{avoid}\n")
    try:
        raw = call_llm(prompt, cfg, system=LLM_SYSTEM, max_tokens=800,
                       prefix="")
        arr = parse_json(raw, array=True)
        if isinstance(arr, list):
            out = [str(x).strip() for x in arr if str(x).strip()]
            return [o for o in out if o not in exclude][:n] or None
    except Exception:                                  # noqa: BLE001
        return None
    return None


def suggest(inst, record, question, n=3, exclude=(), mode=None):
    """(초안 목록, 경로) 반환. 경로는 'llm' 또는 'rules'."""
    mode = (mode or os.environ.get("SUGGESTER", "auto")).lower()
    if mode in ("auto", "llm"):
        got = llm_suggestions(inst, record, question, n=n, exclude=exclude)
        if got:
            return got, "llm"
        if mode == "llm":
            return [], "failed"
    return rule_suggestions(inst, record, n=n, exclude=exclude), "rules"
