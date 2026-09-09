#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
규칙 기반 텍스트 파서와, 이름 기반 결측 탐지기.

두 가지 용도로 쓰인다.

  1) 비교군 "규칙 기반 추출기": 문서 채널의 알려진 템플릿을 정규식으로 파싱해
     레코드를 복원한 뒤 탐지한다. 이 파서는 **한 형식에 맞춰 작성된 것**이며,
     다른 채널에 적용하면 무너진다. 그것이 이 비교군의 요점이다.

  2) 비교군 "하이브리드": LLM이 원문을 정규화해 만든 레코드를 같은 탐지기에
     통과시킨다. 정규화만 모델에 맡기고 판단은 결정적으로 수행하는 구성이다.

두 경우 모두 탐지 결과는 (유형, 정규화된 엔티티 이름) 집합으로 반환되어
llm_detect.py 의 채점 로직과 그대로 호환된다.
"""
from __future__ import annotations

import re

NOW = "2026-09"
GAP_THRESHOLD = 3


def norm(s):
    s = re.sub(r"\(\d{4}-\d{2}[~–-]+\d{4}-\d{2}\)", "", str(s))
    s = re.sub(r"[\s\u3000]+", "", s)
    s = re.sub(r"[·,\.\-—–_/\(\)\[\]{}«»\"'`]", "", s)
    return s.lower()


def to_month(v):
    """'2021-03' -> 24255, '2021년' -> 연 단위 보정."""
    if not v:
        return None
    m = re.match(r"^(\d{4})-(\d{2})$", str(v))
    if m:
        return int(m.group(1)) * 12 + int(m.group(2))
    m = re.match(r"^(\d{4})", str(v))
    if m:
        return int(m.group(1)) * 12 + 1
    return None


# ================================================================ 파서
PERIOD = r"(\d{4}-\d{2}|\d{4}년)\s*~\s*(\d{4}-\d{2}|\d{4}년|현재)"


def parse_document(text):
    """문서 채널(render_file) 템플릿을 레코드로 복원한다."""
    rec = {"education": [], "careers": [], "personal_projects": [],
           "activities": [], "extracurricular": []}
    section = None
    cur_career = None
    cur_proj = None
    cur_edu = None

    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        m = re.match(r"^\[(.+)\]$", line.strip())
        if m:
            section = m.group(1)
            cur_career = cur_proj = cur_edu = None
            continue

        if section == "학력":
            m = re.match(r"^" + PERIOD + r"\s+(.+?)\s+\((.+?),", line.strip())
            if m:
                cur_edu = {"school": m.group(3).split()[0],
                           "degree": m.group(4),
                           "period_start": m.group(1), "period_end": m.group(2),
                           "research_topic": None}
                rec["education"].append(cur_edu)
            elif cur_edu is not None and "연구 주제" in line:
                cur_edu["research_topic"] = line.split(":", 1)[1].strip()

        elif section == "경력":
            m = re.match(r"^" + PERIOD + r"\s+(.+)$", line.strip())
            if m and not line.startswith("  "):
                tail = m.group(3)
                role = None
                if "/" in tail:
                    company, role = tail.split("/", 1)
                    role = role.strip() or None
                else:
                    company = tail
                company = re.sub(r"\s*\(.*?\)\s*$", "", company).strip()
                cur_career = {"company": company, "role": role,
                              "period_start": m.group(1), "period_end": m.group(2),
                              "projects": []}
                rec["careers"].append(cur_career)
                cur_proj = None
                continue
            m = re.match(r"^\s*-\s+(.+?)\s*\(([\d\-~]+)\)\s*$", line)
            if m and cur_career is not None:
                cur_proj = {"name": m.group(1).strip(), "role": None,
                            "metrics": None, "result": None}
                cur_career["projects"].append(cur_proj)
                continue
            if cur_proj is not None:
                for key, field in (("담당", "role"), ("성과", "metrics"),
                                   ("결과", "result")):
                    if line.strip().startswith(key + ":"):
                        cur_proj[field] = line.split(":", 1)[1].strip()

        elif section == "프로젝트":
            m = re.match(r"^" + PERIOD + r"\s+(.+)$", line.strip())
            if m and not line.startswith("    "):
                cur_proj = {"name": m.group(3).strip(), "role": None,
                            "metrics": None, "result": None}
                rec["personal_projects"].append(cur_proj)
                continue
            if cur_proj is not None:
                for key, field in (("담당", "role"), ("성과", "metrics"),
                                   ("결과", "result")):
                    if line.strip().startswith(key + ":"):
                        cur_proj[field] = line.split(":", 1)[1].strip()

        elif section == "대외활동":
            m = re.match(r"^" + PERIOD + r"\s+\[(.+?)\]\s*(.+)$", line.strip())
            if m and not line.startswith("    "):
                tail = m.group(4)
                role = None
                if "/" in tail:
                    name, role = tail.split("/", 1)
                    role = role.strip() or None
                else:
                    name = tail
                cur_proj = {"name": name.strip(), "role": role, "result": None}
                rec["extracurricular"].append(cur_proj)
                continue
            if cur_proj is not None and line.strip().startswith("성과:"):
                cur_proj["result"] = line.split(":", 1)[1].strip()

        elif section == "기타 활동":
            m = re.match(r"^" + PERIOD + r"\s+(.+)$", line.strip())
            if m:
                rec["activities"].append({"title": m.group(3).strip(),
                                          "period_start": m.group(1),
                                          "period_end": m.group(2)})
    return rec


# ================================================================ 탐지
def detect_named(rec):
    """정규화된 레코드에서 (유형, 정규화된 엔티티) 집합을 만든다."""
    found = set()

    # 학위 연구 주제
    for e in rec.get("education", []):
        deg = str(e.get("degree") or "")
        if ("석사" in deg or "박사" in deg or "master" in deg.lower()
                or "doctor" in deg.lower() or "phd" in deg.lower()):
            if not e.get("research_topic"):
                found.add(("THESIS_OMISSION", norm(e.get("school", ""))))

    # 경력 직무 / 기간 해상도
    for c in rec.get("careers", []):
        if not c.get("role"):
            found.add(("ROLE_OMISSION", norm(c.get("company", ""))))
        for k in ("period_start", "period_end"):
            v = str(c.get(k) or "")
            if v and not re.match(r"^\d{4}-\d{2}$", v) and v != "현재":
                found.add(("DATE_INCOMPLETE", norm(c.get("company", ""))))
                break

    # 프로젝트 성과
    for c in rec.get("careers", []):
        for p in c.get("projects", []):
            if not (p.get("role") and p.get("metrics") and p.get("result")):
                found.add(("ACHIEVEMENT_OMISSION", norm(p.get("name", ""))))
    for p in rec.get("personal_projects", []):
        if not (p.get("role") and p.get("metrics") and p.get("result")):
            found.add(("ACHIEVEMENT_OMISSION", norm(p.get("name", ""))))

    # 대외활동
    for a in rec.get("extracurricular", []):
        if not (a.get("role") and a.get("result")):
            found.add(("EXTRACURRICULAR_OMISSION", norm(a.get("name", ""))))

    # 기간적 공백
    spans = []
    for c in rec.get("careers", []):
        s, e = to_month(c.get("period_start")), to_month(c.get("period_end"))
        if c.get("period_end") == "현재":
            e = to_month(NOW)
        if s and e:
            spans.append((s, e, c.get("company", "")))
    covers = []
    for a in rec.get("activities", []):
        s, e = to_month(a.get("period_start")), to_month(a.get("period_end"))
        if s and e:
            covers.append((s, e))
    spans.sort()
    for i in range(len(spans) - 1):
        latest = max(x[1] for x in spans[:i + 1])
        gap0, gap1 = latest, spans[i + 1][0]
        if gap1 - gap0 < GAP_THRESHOLD:
            continue
        if any(cs <= gap0 + 1 and ce >= gap1 - 1 for cs, ce in covers):
            continue
        found.add(("TEMPORAL_GAP", norm(spans[i][2])))

    # 졸업 후 공백 (무경력자)
    if not spans and rec.get("education"):
        ends = [to_month(e.get("period_end")) for e in rec["education"]]
        ends = [x for x in ends if x]
        if ends:
            last = max(ends)
            covered = max([ce for _, ce in covers], default=last)
            if to_month(NOW) - max(last, covered) >= GAP_THRESHOLD:
                found.add(("POST_GRAD_GAP", norm("EDU")))
    return found


def detect_from_document(text):
    return detect_named(parse_document(text))
