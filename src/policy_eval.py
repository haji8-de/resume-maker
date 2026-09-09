#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
질문 예산 정책 비교 (논문 실험 C).

라벨의 gold_answer 를 모의 응답자로 사용해, 정책별로 앞의 k개 질문만 던졌을 때
이력서 완성도가 어떻게 오르는지 측정한다.

완성도 phi
----------
gold 레코드는 구성상 완전하므로, '근거 슬롯'의 전체 집합을 gold 에서 셀 수 있다.
관측 레코드에서 비어 있는 슬롯은 정확히 결측 라벨에 대응한다. 따라서

    phi(R_k) = (전체 슬롯 가중치 - 미해소 슬롯 가중치) / 전체 슬롯 가중치

슬롯 가중치는 유형별 중요도를 따른다. 하나의 결측 인스턴스가 여러 필드를 덮는
경우(성과 누락은 역할·수치·결과를 동시에 지울 수 있다) 필드 수만큼 가중된다.

정책
----
  ask_all    전량 질의 (순서 무관, 상한 확인용)
  random     무작위 순서
  sweep      문서 순차 스윕 (학력 -> 경력 -> 프로젝트 -> 활동)
  severity   유형 중요도 정렬 (제안 정책)
  oracle     매 단계 가중치 최대인 질문 선택 (탐욕적 상한)

사용:
  python3 src/policy_eval.py --data output/resumes.jsonl --budget 10
"""
from __future__ import annotations

import argparse
import json
import os
import random
from collections import defaultdict

# 유형별 슬롯 가중치 (검토자 관점의 중요도)
WEIGHT = {
    "TEMPORAL_GAP": 3.0,
    "POST_GRAD_GAP": 3.0,
    "ROLE_OMISSION": 3.0,
    "DATE_INCOMPLETE": 2.0,
    "ACHIEVEMENT_OMISSION": 2.0,   # 필드당
    "THESIS_OMISSION": 2.0,
    "EXTRACURRICULAR_OMISSION": 1.0,  # 필드당
}

# 중요도 정렬 정책이 사용하는 유형 우선순위 (작을수록 먼저)
PRIORITY = {
    "ROLE_OMISSION": 0,
    "TEMPORAL_GAP": 1,
    "POST_GRAD_GAP": 1,
    "DATE_INCOMPLETE": 2,
    "ACHIEVEMENT_OMISSION": 3,
    "THESIS_OMISSION": 4,
    "EXTRACURRICULAR_OMISSION": 5,
}

# 문서 순차 스윕이 사용하는 섹션 순서
SECTION = {
    "THESIS_OMISSION": 0,          # 학력
    "ROLE_OMISSION": 1,            # 경력 헤더
    "DATE_INCOMPLETE": 1,
    "ACHIEVEMENT_OMISSION": 2,     # 경력 내 프로젝트
    "TEMPORAL_GAP": 3,             # 경력 사이
    "POST_GRAD_GAP": 3,
    "EXTRACURRICULAR_OMISSION": 4,  # 대외활동
}


def n_fields(lb) -> int:
    """이 인스턴스가 덮는 필드 수."""
    return max(1, len(lb.get("missing_fields") or []))


def gain(lb) -> float:
    """이 질문에 답했을 때 회복되는 가중치."""
    return WEIGHT[lb["type"]] * n_fields(lb)


def total_slot_weight(rec) -> float:
    """gold 기준 전체 근거 슬롯 가중치."""
    g = rec["gold"]
    w = 0.0
    for c in g["careers"]:
        w += WEIGHT["ROLE_OMISSION"]        # 직무
        w += WEIGHT["DATE_INCOMPLETE"]      # 기간 해상도
        for _ in c["projects"]:
            w += WEIGHT["ACHIEVEMENT_OMISSION"] * 3   # 역할·수치·결과
    for p in g.get("personal_projects", []):
        w += WEIGHT["ACHIEVEMENT_OMISSION"] * 3
    for e in g["education"]:
        if e.get("thesis"):
            w += WEIGHT["THESIS_OMISSION"]
    for a in g.get("extracurricular", []):
        w += WEIGHT["EXTRACURRICULAR_OMISSION"] * 2   # 역할·성과
    for a in g["activities"]:                          # 공백을 메우는 활동
        w += (WEIGHT["POST_GRAD_GAP"]
              if a["covers_gap_between"][0] == "EDU" else WEIGHT["TEMPORAL_GAP"])
    return max(w, 1.0)


# ------------------------------------------------------------------ 정책
def order_random(M, rng):
    m = list(M)
    rng.shuffle(m)
    return m


def order_sweep(M, rng):
    """문서에 나타나는 순서대로 훑는다 (사람이 양식을 위에서부터 채우는 방식)."""
    def key(lb):
        loc = lb["locator"]
        cid = loc.get("career_id") or (loc.get("between") or [""])[0] or ""
        return (SECTION[lb["type"]], str(cid), str(loc.get("project_id", "")),
                str(loc.get("activity_id", "")))
    return sorted(M, key=key)


def order_severity(M, rng):
    """유형 중요도 우선, 같은 유형 안에서는 덮는 필드가 많은 것부터."""
    return sorted(M, key=lambda lb: (PRIORITY[lb["type"]], -n_fields(lb)))


def order_gain(M, rng):
    """회복 가중치가 큰 질문부터. 가중치와 필드 수 모두 관측 가능하다."""
    return sorted(M, key=lambda lb: -gain(lb))


def order_gain_dep(M, rng):
    """이득 정렬하되, 다른 질문을 잠금 해제하는 질문을 앞으로 당긴다."""
    return sorted(M, key=lambda lb: (0 if lb["type"] == "DATE_INCOMPLETE" else 1,
                                     -gain(lb)))


POLICIES = {
    "random": order_random,
    "sweep": order_sweep,
    "severity": order_severity,
    "gain": order_gain,
    "gain+dep": order_gain_dep,
}


# ------------------------------------------------------------------ 탐지
def label_key(lb):
    t, L = lb["type"], lb["locator"]
    if t in ("TEMPORAL_GAP", "POST_GRAD_GAP"):
        return (t, tuple(L["between"]))
    if t == "ACHIEVEMENT_OMISSION":
        return (t, (L["career_id"], L["project_id"]))
    if t == "THESIS_OMISSION":
        return (t, (L["degree"], L["school"]))
    if t == "EXTRACURRICULAR_OMISSION":
        return (t, (L["activity_id"],))
    return (t, (L["career_id"],))


def visible(rec, answered_dates):
    """현재 상태에서 탐지기가 찾아내는 결측 라벨. 날짜 질문에 답한 만큼 시야가 열린다."""
    from detect_eval import detect
    obs = rec["observed"]
    if answered_dates:
        obs = json.loads(json.dumps(obs, ensure_ascii=False))
        for lb in rec["missingness"]:
            if lb["type"] == "DATE_INCOMPLETE" and label_key(lb) in answered_dates:
                for c in obs["careers"]:
                    if c["career_id"] == lb["locator"]["career_id"]:
                        c["period"] = dict(lb["gold_answer"])
    return detect(obs, 3)


# ------------------------------------------------------------------ 평가
def curve(rec, order, budget):
    """결측 목록을 모두 안다고 가정한 완성도 곡선."""
    W = total_slot_weight(rec)
    missing = sum(gain(lb) for lb in rec["missingness"])
    phi = [(W - missing) / W]
    recovered = 0.0
    for k in range(1, budget + 1):
        if k <= len(order):
            recovered += gain(order[k - 1])
        phi.append((W - missing + recovered) / W)
    return phi


def curve_discovery(rec, order_fn, rng, budget):
    """탐지기가 찾은 것만 물을 수 있는, 현실적인 곡선."""
    W = total_slot_weight(rec)
    missing = sum(gain(lb) for lb in rec["missingness"])
    by_key = {label_key(lb): lb for lb in rec["missingness"]}
    answered, answered_dates = set(), set()
    recovered = 0.0
    phi = [(W - missing) / W]
    for _ in range(budget):
        seen = visible(rec, answered_dates)
        queue = [by_key[k] for k in seen if k in by_key and k not in answered]
        if queue:
            pick = order_fn(queue, rng)[0]
            k = label_key(pick)
            answered.add(k)
            if pick["type"] == "DATE_INCOMPLETE":
                answered_dates.add(k)
            recovered += gain(pick)
        phi.append((W - missing + recovered) / W)
    return phi


def summarize(curves, budget, thresholds=(0.8, 0.95)):
    n = len(curves)
    mean = [sum(c[k] for c in curves) / n for k in range(budget + 1)]
    auc = sum(mean[1:]) / budget
    ks = {}
    for th in thresholds:
        hits = []
        for c in curves:
            k = next((i for i, v in enumerate(c) if v >= th), None)
            hits.append(k if k is not None else budget + 1)
        ks[th] = sum(hits) / n
    return mean, auc, ks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="output/resumes.jsonl")
    ap.add_argument("--budget", type=int, default=10)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--fig", default="output/figures/budget_curve.pdf")
    ap.add_argument("--discovery", action="store_true",
                    help="탐지기가 찾은 것만 물을 수 있는 현실적 시뮬레이션")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    records = [json.loads(l) for l in open(os.path.join(root, args.data), encoding="utf-8")]

    groups = {
        "all": records,
        "experienced": [r for r in records if r["gold"]["entry_type"] == "경력"],
        "entry-level": [r for r in records if r["gold"]["entry_type"] == "신입"],
        # 결측이 예산보다 많은 구간 — 정책 차이가 실제로 드러나는 영역
        "high-missingness": [r for r in records if len(r["missingness"]) >= 6],
        # 연 단위 기간이 있어 질문 간 의존관계가 발생하는 구간
        "year-only dates": [r for r in records if any(
            m["type"] == "DATE_INCOMPLETE" for m in r["missingness"])],
    }

    results = {}
    for gname, recs in groups.items():
        for pname, fn in POLICIES.items():
            all_curves = []
            seeds = args.seeds if pname == "random" else 1
            for s in range(seeds):
                rng = random.Random(1000 + s)
                if args.discovery:
                    all_curves += [curve_discovery(r, fn, rng, args.budget)
                                   for r in recs]
                else:
                    all_curves += [curve(r, fn(r["missingness"], rng), args.budget)
                                   for r in recs]
            mean, auc, ks = summarize(all_curves, args.budget)
            results[(gname, pname)] = {"mean": mean, "auc": auc, "ks": ks}
        # 전량 질의: 모든 질문을 던졌을 때 (예산 무시)
        results[(gname, "ask_all")] = {
            "mean": None, "auc": 1.0,
            "ks": {0.8: sum(len(r["missingness"]) for r in recs) / len(recs),
                   0.95: sum(len(r["missingness"]) for r in recs) / len(recs)},
        }

    # ---------------------------------------------------------- 출력
    B = args.budget
    print(f"질문 예산 K={B}, 이력서 {len(records)}건\n")
    for gname in ("all", "experienced", "entry-level", "high-missingness",
                  "year-only dates"):
        recs = groups[gname]
        base = sum(curve(r, [], B)[0] for r in recs) / len(recs)
        print(f"[{gname}]  n={len(recs)}  질문 전 완성도 phi(R_0)={base:.3f}")
        print(f"  {'policy':10s} {'AUC_K':>7s} {'k*(0.8)':>8s} {'k*(0.95)':>9s} "
              f"{'phi(1)':>7s} {'phi(2)':>7s} {'phi(3)':>7s} {'phi(5)':>7s}")
        for pname in ("ask_all", "random", "sweep", "severity", "gain",
                      "gain+dep"):
            r = results[(gname, pname)]
            if r["mean"] is None:
                print(f"  {pname:10s} {r['auc']:7.3f} {r['ks'][0.8]:8.2f} "
                      f"{r['ks'][0.95]:9.2f}" + f" {'—':>7s}" * 4)
            else:
                print(f"  {pname:10s} {r['auc']:7.3f} {r['ks'][0.8]:8.2f} "
                      f"{r['ks'][0.95]:9.2f} {r['mean'][1]:7.3f} {r['mean'][2]:7.3f} "
                      f"{r['mean'][3]:7.3f} {r['mean'][5]:7.3f}")
        print()

    # ---------------------------------------------------------- 그림
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7), sharey=True)
        style = {"random": ("--", "#888888"), "sweep": (":", "#555555"),
                 "severity": ("-", "#1f3864"), "gain": ("-.", "#b03a2e"),
                 "gain+dep": ("-", "#1e7a4c")}
        label = {"random": "Random", "sweep": "Field-by-field sweep",
                 "severity": "Severity-ordered", "gain": "Gain-ordered",
                 "gain+dep": "Gain + dependency"}
        for ax, gname, title in zip(axes, ("high-missingness", "year-only dates"),
                                    (r"High-missingness ($|M|\geq 6$)",
                                     "Year-only dates present")):
            for pname in ("random", "sweep", "severity", "gain", "gain+dep"):
                ls, col = style[pname]
                ax.plot(range(B + 1), results[(gname, pname)]["mean"],
                        ls, color=col, linewidth=1.4, label=label[pname])
            ax.set_title(title, fontsize=9)
            ax.set_xlabel("questions asked $k$", fontsize=8)
            ax.grid(alpha=0.25, linewidth=0.5)
            ax.tick_params(labelsize=7)
            ax.set_xlim(0, B)
        axes[0].set_ylabel(r"completion $\phi(R_k)$", fontsize=8)
        axes[0].legend(fontsize=6.5, loc="lower right", framealpha=0.9)
        fig.tight_layout()
        out = os.path.join(root, args.fig)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        fig.savefig(out, bbox_inches="tight")
        print(f"그림 저장: {args.fig}")
    except ImportError:
        print("matplotlib 없음 — 그림 생략")


if __name__ == "__main__":
    main()
