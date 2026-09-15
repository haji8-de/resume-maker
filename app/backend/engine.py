#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
상호작용 세션 엔진.

명세서 구성요소와의 대응은 다음과 같다.

    121  결측치 탐색부        Session.detect()
    122  질의 프롬프트 생성부  Session.next_questions()  (이득 정렬)
    131  답변 파싱부          parse_answer()
    132  이력 항목 추출부      parse_answer() 가 반환하는 필드 집합
    133  결측 데이터 보완부    Session.submit()
    134  데이터 병합부        Session.submit() 의 레코드 갱신
    135  문장 생성부          render_sentences()
    136  템플릿 배치부        build_preview()
    137  렌더링부 / 미리보기   build_preview() → Session.confirm()

각 단계는 trace 에 기록되어 UI에서 그대로 확인할 수 있다. 우선심사
설명서의 실시 증빙으로 쓰기 위한 것이다.
"""
from __future__ import annotations

import copy
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src"))

from detect_eval import detect                      # noqa: E402
from policy_eval import WEIGHT, PRIORITY, label_key  # noqa: E402
from text_rules import parse_document                # noqa: E402

NOW = "2026-09"

TYPE_KO = {
    "TEMPORAL_GAP": "기간적 공백기",
    "POST_GRAD_GAP": "졸업 후 구직 공백",
    "ROLE_OMISSION": "직무 정보 누락",
    "ACHIEVEMENT_OMISSION": "성과 누락",
    "THESIS_OMISSION": "학위 연구주제 누락",
    "EXTRACURRICULAR_OMISSION": "대외활동 상세 누락",
    "DATE_INCOMPLETE": "기간 정보 불완전",
}

FIELD_KO = {"role": "담당 역할", "metrics": "정량 성과", "result": "수행 결과"}


def josa(word, pair="을/를"):
    """받침 유무에 따라 조사를 고른다. pair 는 '받침있음/받침없음' 순서."""
    a, b = pair.split("/")
    if not word:
        return a
    ch = word[-1]
    if not ("\uac00" <= ch <= "\ud7a3"):
        return a
    return a if (ord(ch) - 0xAC00) % 28 else b


# ------------------------------------------------------------------ 질의 생성
def question_text(inst, rec):
    t, loc = inst["type"], inst["locator"]
    if t == "ROLE_OMISSION":
        c = find_career(rec, loc["career_id"])
        name = c["company"] if c else "해당 경력"
        return f"{name} 재직 기간에 어떤 직무를 맡으셨나요? 직무명과 담당 업무를 알려주세요."
    if t == "DATE_INCOMPLETE":
        c = find_career(rec, loc["career_id"])
        name = c["company"] if c else "해당 경력"
        return f"{name} 재직 기간의 정확한 시작·종료 연월을 알려주세요. (예: 2021-03 ~ 2023-08)"
    if t == "ACHIEVEMENT_OMISSION":
        p = find_project(rec, loc["project_id"])
        name = p["name"] if p else "해당 프로젝트"
        miss = [FIELD_KO[f] for f in loc.get("missing_fields", [])] or ["성과"]
        joined = ", ".join(miss)
        return (f"'{name}'의 {joined}{josa(joined)} 알려주세요. "
                f"가능하면 수치를 함께 적어주시면 좋습니다.")
    if t == "THESIS_OMISSION":
        return f"{loc.get('school', '대학원')} {loc.get('degree', '학위')} 과정의 연구 주제나 학위논문 제목을 알려주세요."
    if t == "EXTRACURRICULAR_OMISSION":
        a = find_activity(rec, loc["activity_id"])
        name = a["name"] if a else "해당 활동"
        return f"'{name}'에서 맡으신 역할과 성과를 알려주세요."
    if t == "POST_GRAD_GAP":
        return "졸업 이후 지금까지의 기간에 어떤 활동을 하셨나요? 학업, 근무, 프로젝트 무엇이든 좋습니다."
    if t == "TEMPORAL_GAP":
        a, b = loc["between"]
        ca, cb = find_career(rec, a), find_career(rec, b)
        if ca and cb:
            return (f"{ca['company']} 퇴사({ca['period']['end']}) 이후 "
                    f"{cb['company']} 입사({cb['period']['start']}) 전까지의 기간에 "
                    f"무엇을 하셨나요?")
        return "경력 사이 공백 기간에 어떤 활동을 하셨나요?"
    return "누락된 정보를 알려주세요."


def find_career(rec, cid):
    return next((c for c in rec["careers"] if c["career_id"] == cid), None)


def find_project(rec, pid):
    for c in rec["careers"]:
        for p in c["projects"]:
            if p["project_id"] == pid:
                return p
    for p in rec.get("personal_projects", []):
        if p["project_id"] == pid:
            return p
    return None


def find_activity(rec, aid):
    return next((a for a in rec.get("extracurricular", [])
                 if a["activity_id"] == aid), None)


# ------------------------------------------------------------------ 답변 파싱 (131/132)
METRIC_RE = re.compile(r"([가-힣A-Za-z()\s]+?)\s*([\d.]+)\s*(%p|%|배|건|명|시간|일|점)\s*"
                       r"(개선|절감|증가|감소|향상|단축|달성)?")
PERIOD_RE = re.compile(r"(\d{4})[-./년]\s*(\d{1,2})")


TAIL_RE = re.compile(r"(?:을|를|이|가|은|는)?\s*$")
END_RE = re.compile(r"(?:이었습니다|였습니다|입니다|이다|했습니다|됐어요|됐습니다|이에요|예요)\s*$")


def strip_tail(x):
    """조사와 종결어미를 떼어 필드 값만 남긴다."""
    x = x.strip().rstrip(".。 ")
    x = END_RE.sub("", x).strip()
    return TAIL_RE.sub("", x).strip()


def parse_answer(inst, text):
    """자유 텍스트 답변에서 타입 지정 필드를 추출한다. 실패하면 빈 dict."""
    t = inst["type"]
    text = text.strip()
    if not text:
        return {}

    if t == "ROLE_OMISSION":
        role = text.split(".")[0].split(",")[0].strip()
        role = re.sub(r"(으)?로\s*(일했|근무|있었).*$", "", role).strip()
        return {"role": strip_tail(role) or text}

    if t == "DATE_INCOMPLETE":
        found = PERIOD_RE.findall(text)
        if len(found) >= 2:
            return {"period": {"start": f"{found[0][0]}-{int(found[0][1]):02d}",
                               "end": f"{found[1][0]}-{int(found[1][1]):02d}"}}
        return {}

    if t == "ACHIEVEMENT_OMISSION":
        out = {}
        metrics = []
        for name, val, unit, direction in METRIC_RE.findall(text):
            name = name.strip(" ,.·").strip()
            if not name:
                continue
            metrics.append({"name": name, "value": float(val) if "." in val else int(val),
                            "unit": unit,
                            "direction": "down" if direction in ("절감", "감소", "단축") else "up"})
        if metrics:
            out["metrics"] = metrics
        want = inst["locator"].get("missing_fields", [])
        if "role" in want:
            head = re.split(r"[.。]", text)[0]
            m = re.search(r"(?:제가\s*)?(.+?)\s*(?:맡았|담당|수행)", head)
            out["role"] = strip_tail(m.group(1) if m else head)
        if "result" in want:
            m = re.search(r"(?:최종적으로는?|결과(?:는|적으로)?)\s*(.+?)(?:[.。]|$)", text)
            if m:
                out["result"] = strip_tail(m.group(1))
            elif "metrics" not in out and "role" not in out:
                out["result"] = text
        return out

    if t == "THESIS_OMISSION":
        m = re.search(r"[\"'\u201c\u2018](.+?)[\"'\u201d\u2019]", text)
        return {"research_topic": (m.group(1) if m else
                                   re.split(r"(?:였습니다|입니다|이다)", text)[0]).strip()}

    if t == "EXTRACURRICULAR_OMISSION":
        out = {}
        want = inst["locator"].get("missing_fields", [])
        parts = re.split(r"[,、]", text)
        if "role" in want:
            m = re.search(r"(.+?)(?:으)?로\s*(?:참여|활동|맡)", parts[0])
            out["role"] = strip_tail(m.group(1) if m else parts[0])
        if "result" in want:
            m = re.search(r"결과는?\s*(.+?)(?:[.。]|$)", text)
            out["result"] = strip_tail(m.group(1) if m else parts[-1])
        return out

    if t in ("TEMPORAL_GAP", "POST_GRAD_GAP"):
        title = re.split(r"[.。]", text)[0]
        title = re.sub(r"^(그\s*기간에는?|그때는?)\s*", "", title).strip()
        title = re.sub(r"\s*했(습니다|어요|고요)$", "", title).strip()
        return {"activity_title": title or text}

    return {}


# ------------------------------------------------------------------ 병합 (133/134)
def merge(rec, inst, fields):
    t, loc = inst["type"], inst["locator"]
    if not fields:
        return False
    if t == "ROLE_OMISSION":
        c = find_career(rec, loc["career_id"])
        if c:
            c["role"] = fields.get("role")
            return True
    elif t == "DATE_INCOMPLETE":
        c = find_career(rec, loc["career_id"])
        if c and "period" in fields:
            c["period"] = fields["period"]
            return True
    elif t == "ACHIEVEMENT_OMISSION":
        p = find_project(rec, loc["project_id"])
        if p:
            for k in ("role", "metrics", "result"):
                if k in fields:
                    p[k] = fields[k]
            return True
    elif t == "THESIS_OMISSION":
        for e in rec["education"]:
            if e.get("school") == loc.get("school") and e.get("degree") == loc.get("degree"):
                e["research_topic"] = fields.get("research_topic")
                return True
    elif t == "EXTRACURRICULAR_OMISSION":
        a = find_activity(rec, loc["activity_id"])
        if a:
            for k in ("role", "result"):
                if k in fields:
                    a[k] = fields[k]
            return True
    elif t in ("TEMPORAL_GAP", "POST_GRAD_GAP"):
        rec.setdefault("activities", []).append({
            "activity_id": f"A-{uuid.uuid4().hex[:6]}",
            "period": gap_period(rec, loc),
            "title": fields.get("activity_title", ""),
            "covers_gap_between": list(loc.get("between", ["EDU", "NOW"])),
        })
        return True
    return False


def gap_period(rec, loc):
    between = loc.get("between", ["EDU", "NOW"])
    if between[0] == "EDU":
        start = max((e["period"]["end"] for e in rec["education"]), default=NOW)
        return {"start": start, "end": NOW}
    a, b = find_career(rec, between[0]), find_career(rec, between[1])
    return {"start": a["period"]["end"] if a else NOW,
            "end": b["period"]["start"] if b else NOW}


# ------------------------------------------------------------------ 문장 생성·배치 (135/136/137)
def metric_phrase(m):
    up = m["direction"] == "up"
    unit = m.get("unit", "")
    verb = ("개선" if up else "절감") if unit in ("%", "%p") else ("증가" if up else "감소")
    return f"{m['name']} {m['value']}{unit} {verb}"


def render_sentences(p):
    """프로젝트 항목을 한 문장으로 구성한다. 레코드에 있는 필드만 사용한다."""
    bits = []
    if p.get("role"):
        bits.append(f"{p['role']}{josa(p['role'])} 담당")
    if p.get("metrics"):
        bits.append(", ".join(metric_phrase(m) for m in p["metrics"]))
    if p.get("result"):
        bits.append(p["result"])
    return " · ".join(bits) if bits else None


def build_preview(rec, missing_keys):
    """템플릿 배치 결과. 미해소 항목은 표시해 사용자가 확인할 수 있게 한다."""
    sections = []

    edu = []
    for e in rec["education"]:
        edu.append({
            "period": f"{e['period']['start']} ~ {e['period']['end']}",
            "title": f"{e['school']} {e['major']}",
            "meta": e.get("degree", ""),
            "lines": ([f"연구 주제: {e['research_topic']}"] if e.get("research_topic")
                      else ([{"missing": "연구 주제"}]
                            if ("THESIS_OMISSION", (e.get("degree"), e.get("school"))) in missing_keys
                            else [])),
        })
    sections.append({"name": "학력", "items": edu})

    car = []
    for c in rec["careers"]:
        lines = []
        for p in c["projects"]:
            s = render_sentences(p)
            lines.append(f"{p['name']} — {s}" if s else {"missing": f"{p['name']} 성과"})
        car.append({
            "period": f"{c['period']['start']} ~ {c['period']['end']}",
            "title": c["company"],
            "meta": c.get("role") or {"missing": "직무"},
            "lines": lines,
        })
    sections.append({"name": "경력", "items": car})

    if rec.get("personal_projects"):
        pp = []
        for p in rec["personal_projects"]:
            s = render_sentences(p)
            pp.append({"period": "", "title": p["name"], "meta": "",
                       "lines": [s] if s else [{"missing": "성과"}]})
        sections.append({"name": "프로젝트", "items": pp})

    if rec.get("activities"):
        act = [{"period": f"{a['period']['start']} ~ {a['period']['end']}",
                "title": a["title"], "meta": "", "lines": []}
               for a in rec["activities"]]
        sections.append({"name": "기타 활동", "items": act})

    if rec.get("extracurricular"):
        ex = []
        for a in rec["extracurricular"]:
            meta = a.get("role") or {"missing": "역할"}
            lines = [a["result"]] if a.get("result") else []
            ex.append({"period": f"{a['period']['start']} ~ {a['period']['end']}",
                       "title": f"[{a.get('category', '활동')}] {a['name']}",
                       "meta": meta, "lines": lines})
        sections.append({"name": "대외활동", "items": ex})

    flat = []
    if rec.get("languages"):
        flat.append("어학  " + ", ".join(f"{x['test']} {x['score']}" for x in rec["languages"]))
    if rec.get("skills"):
        flat.append("기술  " + ", ".join(rec["skills"]))
    if rec.get("certificates"):
        flat.append("자격  " + ", ".join(rec["certificates"]))
    if flat:
        sections.append({"name": "기술 · 자격", "items": [
            {"period": "", "title": "", "meta": "", "lines": flat}]})

    return {"profile": rec.get("profile", {}), "sections": sections}


# ------------------------------------------------------------------ 세션
class Session:
    def __init__(self, record, source="upload"):
        self.id = uuid.uuid4().hex[:12]
        self.record = record
        self.source = source
        self.answered = set()
        self.trace = []
        self.confirmed_at = None
        self.created_at = datetime.now(timezone.utc).isoformat()

    # --- 121 결측치 탐색
    def detect(self):
        found = detect(self.record, 3)
        out = []
        for t, loc in sorted(found):
            inst = self._instance(t, loc)
            if inst and label_key_of(inst) not in self.answered:
                out.append(inst)
        return out

    def _instance(self, t, loc):
        if t in ("TEMPORAL_GAP", "POST_GRAD_GAP"):
            locator = {"between": list(loc)}
        elif t == "ACHIEVEMENT_OMISSION":
            cid, pid = loc
            p = find_project(self.record, pid)
            if not p:
                return None
            miss = [f for f in ("role", "metrics", "result") if not p.get(f)]
            locator = {"career_id": cid, "project_id": pid, "missing_fields": miss}
        elif t == "THESIS_OMISSION":
            locator = {"degree": loc[0], "school": loc[1]}
        elif t == "EXTRACURRICULAR_OMISSION":
            a = find_activity(self.record, loc[0])
            if not a:
                return None
            miss = [f for f in ("role", "result") if not a.get(f)]
            locator = {"activity_id": loc[0], "missing_fields": miss}
        else:
            locator = {"career_id": loc[0]}
        return {"type": t, "locator": locator}

    # --- 122 질의 프롬프트 생성 (이득 정렬)
    def next_questions(self, limit=1):
        insts = self.detect()
        insts.sort(key=lambda i: (-gain(i), PRIORITY.get(i["type"], 9)))
        return [{"key": label_key_of(i), "type": i["type"],
                 "type_ko": TYPE_KO.get(i["type"], i["type"]),
                 "gain": gain(i), "instance": i, "text": question_text(i, self.record)}
                for i in insts[:limit]]

    # --- 131~134 파싱 · 보완 · 병합
    def submit(self, key, answer_text):
        inst = next((q["instance"] for q in self.next_questions(limit=99)
                     if q["key"] == key), None)
        if inst is None:
            return {"ok": False, "reason": "해당 질의를 찾을 수 없습니다."}
        fields = parse_answer(inst, answer_text)
        ok = merge(self.record, inst, fields)
        self.answered.add(key)
        self.trace.append({
            "at": datetime.now(timezone.utc).isoformat(),
            "type": inst["type"], "type_ko": TYPE_KO.get(inst["type"]),
            "question": question_text(inst, self.record),
            "answer": answer_text, "parsed": fields, "merged": ok,
        })
        return {"ok": ok, "parsed": fields}

    # --- 135~137 미리보기
    def preview(self):
        keys = {label_key_of(i) for i in self.detect()}
        return build_preview(self.record, keys)

    def progress(self):
        remaining = self.detect()
        answered = len(self.trace)
        total = answered + len(remaining)
        return {"answered": answered, "remaining": len(remaining),
                "total": total,
                "ratio": (answered / total) if total else 1.0}

    # --- 137 확정
    def confirm(self):
        self.confirmed_at = datetime.now(timezone.utc).isoformat()
        return {"confirmed_at": self.confirmed_at,
                "record": self.record, "trace": self.trace}


def gain(inst):
    n = max(1, len(inst["locator"].get("missing_fields") or []))
    return WEIGHT.get(inst["type"], 1.0) * n


def label_key_of(inst):
    t, L = inst["type"], inst["locator"]
    if t in ("TEMPORAL_GAP", "POST_GRAD_GAP"):
        return f"{t}|{'>'.join(L['between'])}"
    if t == "ACHIEVEMENT_OMISSION":
        return f"{t}|{L['career_id']}|{L['project_id']}"
    if t == "THESIS_OMISSION":
        return f"{t}|{L['degree']}|{L['school']}"
    if t == "EXTRACURRICULAR_OMISSION":
        return f"{t}|{L['activity_id']}"
    return f"{t}|{L['career_id']}"
