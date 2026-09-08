#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
규칙 기반 결측치 탐지기 + 평가.

이 스크립트는 '구조화된 observed JSON' 을 입력으로 받는다. 즉 명세서의
데이터 형식 변환부(114)가 완벽하게 동작했다고 가정한 상황이며, 여기서 나오는
F1 은 사실상 **상한선(ceiling)** 이자 라벨 정합성 검증용이다.

논문의 실제 태스크는 renders(chat/file/url) 원문 텍스트에서 곧바로 결측치를
탐지하는 것이며, 그 설정에서 LLM 베이스라인과 비교하면 된다.

사용:
  python3 src/detect_eval.py --data output/resumes.jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict


def months_between(a: str, b: str) -> int:
    return (int(b[:4]) * 12 + int(b[5:7])) - (int(a[:4]) * 12 + int(a[5:7]))


def normalize_period(p):
    """명세서 1211 의 '날짜 변환 기준' 적용: 'YYYY년' -> 시작 YYYY-01 / 종료 YYYY-12."""
    def fix(v, is_end):
        if len(v) == 7 and v[4] == "-":
            return v
        y = v[:4]
        return f"{y}-12" if is_end else f"{y}-01"
    return fix(p["start"], False), fix(p["end"], True)


TODAY = "2026-09"


def detect(obs, gap_threshold=3):
    """구조화된 관측 이력서에서 결측치를 탐지."""
    found = []

    # 0) 졸업 후 현재까지의 공백 (무경력 신입에서 특히 중요)
    if not obs["careers"] and obs["education"]:
        last_edu = max(e["period"]["end"] for e in obs["education"])
        covered = max((a["period"]["end"] for a in obs["activities"]), default=last_edu)
        anchor = max(last_edu, covered)
        if months_between(anchor, TODAY) >= gap_threshold:
            found.append(("POST_GRAD_GAP", ("EDU", "NOW")))

    # 1) 기간적 공백기 (1211) — 불완전 기간은 보정 후 포함
    spans = []
    for c in obs["careers"]:
        s, e = normalize_period(c["period"])
        spans.append((s, e, c["career_id"]))
    for a in obs["activities"]:
        spans.append((a["period"]["start"], a["period"]["end"], a["activity_id"]))
    spans.sort()
    for i in range(len(spans) - 1):
        if months_between(spans[i][1], spans[i + 1][0]) >= gap_threshold:
            found.append(("TEMPORAL_GAP", (spans[i][2], spans[i + 1][2])))

    # 2) 직무 정보 누락 (1212)
    for c in obs["careers"]:
        if not c.get("role"):
            found.append(("ROLE_OMISSION", (c["career_id"],)))

    # 3) 성과 누락 (1213) — 경력 프로젝트 + 신입의 개인/졸업 프로젝트
    scoped = [(c["career_id"], p) for c in obs["careers"] for p in c["projects"]]
    scoped += [("PERSONAL", p) for p in obs.get("personal_projects", [])]
    for cid, p in scoped:
        if (not p.get("metrics")) or (not p.get("role")) or (not p.get("result")):
            found.append(("ACHIEVEMENT_OMISSION", (cid, p["project_id"])))

    # 3-b) 학위 연구주제 누락
    for e in obs["education"]:
        if e.get("thesis") and not e.get("research_topic"):
            found.append(("THESIS_OMISSION", (e["degree"], e["school"])))

    # 3-c) 대외활동 상세 누락 — 라벨은 필드 단위이므로 활동 단위로 정규화
    for a in obs.get("extracurricular", []):
        if not a.get("role") or not a.get("result"):
            found.append(("EXTRACURRICULAR_OMISSION", (a["activity_id"],)))

    # 4) 기간 정보 불완전
    for c in obs["careers"]:
        if len(c["period"]["start"]) != 7 or len(c["period"]["end"]) != 7:
            found.append(("DATE_INCOMPLETE", (c["career_id"],)))

    return set(found)


def gold_set(rec):
    out = set()
    for lb in rec["missingness"]:
        t, loc = lb["type"], lb["locator"]
        if t in ("TEMPORAL_GAP", "POST_GRAD_GAP"):
            out.add((t, tuple(loc["between"])))
        elif t in ("ROLE_OMISSION", "DATE_INCOMPLETE"):
            out.add((t, (loc["career_id"],)))
        elif t == "ACHIEVEMENT_OMISSION":
            out.add((t, (loc["career_id"], loc["project_id"])))
        elif t == "THESIS_OMISSION":
            out.add((t, (loc["degree"], loc["school"])))
        elif t == "EXTRACURRICULAR_OMISSION":
            out.add((t, (loc["activity_id"],)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="output/resumes.jsonl")
    ap.add_argument("--gap-threshold", type=int, default=3)
    args = ap.parse_args()

    tp = defaultdict(int); fp = defaultdict(int); fn = defaultdict(int)
    n = 0
    for line in open(args.data, encoding="utf-8"):
        rec = json.loads(line)
        n += 1
        pred = detect(rec["observed"], args.gap_threshold)
        gold = gold_set(rec)
        for item in pred - gold:
            fp[item[0]] += 1
        for item in gold - pred:
            fn[item[0]] += 1
        for item in pred & gold:
            tp[item[0]] += 1

    print(f"이력서 {n}건\n")
    print(f"{'유형':24s} {'TP':>5s} {'FP':>5s} {'FN':>5s} {'P':>7s} {'R':>7s} {'F1':>7s}")
    print("-" * 62)
    for t in ["TEMPORAL_GAP", "POST_GRAD_GAP", "ROLE_OMISSION",
              "ACHIEVEMENT_OMISSION", "THESIS_OMISSION",
              "EXTRACURRICULAR_OMISSION", "DATE_INCOMPLETE"]:
        p = tp[t] / (tp[t] + fp[t]) if tp[t] + fp[t] else 0.0
        r = tp[t] / (tp[t] + fn[t]) if tp[t] + fn[t] else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        print(f"{t:24s} {tp[t]:5d} {fp[t]:5d} {fn[t]:5d} {p:7.3f} {r:7.3f} {f1:7.3f}")

    T, F, N = sum(tp.values()), sum(fp.values()), sum(fn.values())
    p = T / (T + F) if T + F else 0.0
    r = T / (T + N) if T + N else 0.0
    print("-" * 62)
    print(f"{'MICRO':24s} {T:5d} {F:5d} {N:5d} {p:7.3f} {r:7.3f} "
          f"{2 * p * r / (p + r) if p + r else 0:7.3f}")


if __name__ == "__main__":
    main()
