#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
날짜 보정 규칙과 공백 탐지의 상호작용 (절제 실험).

기간이 '2021년'처럼 연 단위로만 기재된 경력을 월 단위로 되돌리는 방법은 하나가
아니다. 그리고 어떤 규칙을 고르느냐가 그 구간 안에 있던 경력 공백을 살리거나
지운다. 정규화 단계의 사소해 보이는 관례가 탐지 결과를 바꾼다는 것을 보인다.

비교하는 세 가지 관례
  drop    연 단위 항목을 아예 구간 목록에서 제외한다
  expand  시작은 그 해 1월, 종료는 그 해 12월로 넓힌다 (가장 흔한 선택)
  narrow  시작은 그 해 12월, 종료는 그 해 1월로 좁힌다 (보수적)

사용:
  python3 src/date_ablation.py --data output/resumes.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict

GAP_THRESHOLD = 3


def mon(v):
    return int(v[:4]) * 12 + int(v[5:7])


def coarse(v):
    return not (len(v) == 7 and v[4] == "-")


def resolve(period, rule):
    """연 단위 기간을 관례에 따라 월 단위로 되돌린다. None 이면 구간에서 제외."""
    s, e = period["start"], period["end"]
    cs, ce = coarse(s), coarse(e)
    if not cs and not ce:
        return mon(s), mon(e)
    if rule == "drop":
        return None
    y_s, y_e = int(s[:4]), int(e[:4])
    if rule == "expand":
        return (y_s * 12 + 1 if cs else mon(s), y_e * 12 + 12 if ce else mon(e))
    if rule == "narrow":
        return (y_s * 12 + 12 if cs else mon(s), y_e * 12 + 1 if ce else mon(e))
    raise ValueError(rule)


def detect_gaps(obs, rule):
    spans = []
    for c in obs["careers"]:
        r = resolve(c["period"], rule)
        if r:
            spans.append((r[0], r[1], c["career_id"]))
    for a in obs["activities"]:
        spans.append((mon(a["period"]["start"]), mon(a["period"]["end"]),
                      a["activity_id"]))
    spans.sort()
    out = set()
    for i in range(len(spans) - 1):
        latest = max(x[1] for x in spans[:i + 1])
        if spans[i + 1][0] - latest >= GAP_THRESHOLD:
            out.add((spans[i][2], spans[i + 1][2]))
    return out


def gold_gaps(rec):
    return {tuple(lb["locator"]["between"]) for lb in rec["missingness"]
            if lb["type"] == "TEMPORAL_GAP"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="output/resumes.jsonl")
    args = ap.parse_args()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    recs = [json.loads(l) for l in open(os.path.join(root, args.data), encoding="utf-8")]

    # 연 단위 기간을 가진 레코드와 그렇지 않은 레코드를 나눠 본다
    def has_coarse(r):
        return any(coarse(c["period"]["start"]) or coarse(c["period"]["end"])
                   for c in r["observed"]["careers"])

    groups = {"all": recs,
              "precise dates": [r for r in recs if not has_coarse(r)],
              "year-only present": [r for r in recs if has_coarse(r)]}

    print(f"이력서 {len(recs)}건 "
          f"(연 단위 기간 포함 {len(groups['year-only present'])}건)\n")
    print(f"{'group':20s} {'rule':8s} {'TP':>5s} {'FP':>5s} {'FN':>5s} "
          f"{'P':>6s} {'R':>6s} {'F1':>6s}")
    print("-" * 62)
    table = {}
    for gname, pool in groups.items():
        for rule in ("drop", "expand", "narrow"):
            tp = fp = fn = 0
            for r in pool:
                pred, gold = detect_gaps(r["observed"], rule), gold_gaps(r)
                tp += len(pred & gold)
                fp += len(pred - gold)
                fn += len(gold - pred)
            p = tp / (tp + fp) if tp + fp else 0.0
            rc = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * p * rc / (p + rc) if p + rc else 0.0
            table[(gname, rule)] = (tp, fp, fn, p, rc, f1)
            print(f"{gname:20s} {rule:8s} {tp:5d} {fp:5d} {fn:5d} "
                  f"{p:6.3f} {rc:6.3f} {f1:6.3f}")
        print("-" * 62)

    # 연 단위 기간이 실제로 몇 개의 공백을 삼키는가
    swallowed = 0
    total_coarse_gap = 0
    for r in groups["year-only present"]:
        gold = gold_gaps(r)
        total_coarse_gap += len(gold)
        swallowed += len(gold - detect_gaps(r["observed"], "expand"))
    if total_coarse_gap:
        print(f"\n연 단위 기간이 있는 레코드의 공백 {total_coarse_gap}건 중 "
              f"expand 규칙이 삼킨 것 {swallowed}건 "
              f"({100*swallowed/total_coarse_gap:.1f}%)")


if __name__ == "__main__":
    main()
