#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
원문 텍스트로부터의 결측치 탐지 평가 (논문 실험 B).

detect_eval.py 가 구조화된 JSON을 입력으로 받는 것과 달리, 여기서는
renders 의 세 채널(대화 / 문서 / 웹 프로필) 원문을 그대로 모델에 준다.
즉 데이터 형식 변환부(114)가 완벽하다는 가정을 걷어낸, 실제 과제 설정이다.

위치자 표기
-----------
모델은 내부 ID(C1, C1-P2 …)를 알 수 없으므로, 화면에 보이는 **이름**으로
대상을 지목하게 한다. 채점 시 정답 라벨의 내부 ID를 같은 이름으로 변환해
(유형, 정규화된 이름) 집합으로 비교한다.

사용:
  export ANTHROPIC_API_KEY=...
  python3 src/llm_detect.py --data output/resumes.jsonl --n 60 --workers 10
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

API_URL = "https://api.anthropic.com/v1/messages"

TAXONOMY = """You are auditing a Korean resume for MISSING evidence.
Return every place where required information is absent.

Types:
- TEMPORAL_GAP: a gap of 3 months or more between two consecutive jobs that is
  not covered by any listed activity. entity = company name of the job BEFORE
  the gap.
- POST_GRAD_GAP: the applicant has no work history at all, and 3 months or more
  passed between final graduation and now (2026-09), uncovered. entity = "EDU".
- ROLE_OMISSION: a job entry has no job title / role stated. entity = company name.
- ACHIEVEMENT_OMISSION: a project entry is missing any of {role in charge,
  quantitative outcome, result}. entity = project name.
- THESIS_OMISSION: a master's or doctoral entry has no research topic.
  entity = school name of that degree.
- EXTRACURRICULAR_OMISSION: an extracurricular / activity entry is missing its
  role or its result. entity = activity name.
- DATE_INCOMPLETE: a job period is written with year only, not year-month.
  entity = company name.

Rules:
- Report an item ONLY if the information is genuinely absent. Many resumes are
  complete; returning an empty list is a correct and expected answer.
- One item per affected entry. Do not report the same (type, entity) twice.
- entity must be copied verbatim from the resume text.

Output ONLY a JSON array, no prose, no markdown fence:
[{"type": "...", "entity": "..."}]"""


def call_api(key, model, text, max_retries=4):
    body = json.dumps({
        "model": model,
        "max_tokens": 1500,
        "system": TAXONOMY,
        "messages": [{"role": "user", "content": "Resume:\n\n" + text}],
    }).encode()
    req = urllib.request.Request(
        API_URL, data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read())
            return "".join(b.get("text", "") for b in d.get("content", []))
        except Exception as e:
            if attempt == max_retries - 1:
                return f"__ERROR__ {e}"
            time.sleep(2 ** attempt + random.random())
    return "__ERROR__"


def parse_items(raw):
    if raw.startswith("__ERROR__"):
        return None
    s = raw.strip()
    s = re.sub(r"^```(?:json)?|```$", "", s, flags=re.MULTILINE).strip()
    m = re.search(r"\[.*\]", s, flags=re.DOTALL)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out = []
    for it in arr:
        if isinstance(it, dict) and it.get("type"):
            out.append((str(it["type"]).strip().upper(),
                        norm(str(it.get("entity", "")))))
    return out


def norm(s):
    s = re.sub(r"\(\d{4}-\d{2}[~–-]+\d{4}-\d{2}\)", "", s)
    s = re.sub(r"[\s\u3000]+", "", s)
    s = re.sub(r"[·,\.\-—–_/\(\)\[\]{}«»\"'`]", "", s)
    return s.lower()


# ------------------------------------------------------------------ 정답 변환
def gold_named(rec):
    """내부 ID 기반 라벨을 이름 기반 (type, entity) 집합으로 변환."""
    obs = rec["observed"]
    career = {c["career_id"]: c for c in obs["careers"]}
    proj = {}
    for c in obs["careers"]:
        for p in c["projects"]:
            proj[p["project_id"]] = p
    for p in obs.get("personal_projects", []):
        proj[p["project_id"]] = p
    act = {a["activity_id"]: a for a in obs.get("extracurricular", [])}

    out = set()
    for lb in rec["missingness"]:
        t, L = lb["type"], lb["locator"]
        if t in ("ROLE_OMISSION", "DATE_INCOMPLETE"):
            c = career.get(L["career_id"])
            if c:
                out.add((t, norm(c["company"])))
        elif t == "ACHIEVEMENT_OMISSION":
            p = proj.get(L["project_id"])
            if p:
                out.add((t, norm(p["name"])))
        elif t == "THESIS_OMISSION":
            out.add((t, norm(L["school"])))
        elif t == "EXTRACURRICULAR_OMISSION":
            a = act.get(L["activity_id"])
            if a:
                out.add((t, norm(a["name"])))
        elif t == "TEMPORAL_GAP":
            c = career.get(L["between"][0])
            if c:
                out.add((t, norm(c["company"])))
        elif t == "POST_GRAD_GAP":
            out.add((t, norm("EDU")))
    return out


TYPES = ["TEMPORAL_GAP", "POST_GRAD_GAP", "ROLE_OMISSION", "ACHIEVEMENT_OMISSION",
         "THESIS_OMISSION", "EXTRACURRICULAR_OMISSION", "DATE_INCOMPLETE"]

# 채널별로 렌더링되는 정보가 다르다. 웹 프로필에는 학력 섹션이 없으므로
# 학위 연구주제와 졸업 후 공백은 원리적으로 탐지할 수 없다.
# 채널이 담지 않은 근거를 못 찾았다고 감점하는 것은 부당하므로 채점에서 제외한다.
VISIBLE = {
    "chat": set(TYPES),
    "file": set(TYPES),
    "url": set(TYPES) - {"THESIS_OMISSION", "POST_GRAD_GAP"},
}


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="output/resumes.jsonl")
    ap.add_argument("--n", type=int, default=60, help="표본 이력서 수")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="output/llm_detect.json")
    args = ap.parse_args()

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY 가 설정되지 않았습니다.")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    recs = [json.loads(l) for l in open(os.path.join(root, args.data), encoding="utf-8")]

    # 층화 표본: 경력직 / 신입 / 음성(결측 0건)
    rng = random.Random(args.seed)
    strata = {
        "experienced": [r for r in recs if r["gold"]["entry_type"] == "경력" and r["missingness"]],
        "entry": [r for r in recs if r["gold"]["entry_type"] == "신입" and r["missingness"]],
        "clean": [r for r in recs if not r["missingness"]],
    }
    quota = {"experienced": int(args.n * 0.55), "entry": int(args.n * 0.20)}
    quota["clean"] = args.n - sum(quota.values())
    sample = []
    for k, q in quota.items():
        pool = strata[k]
        sample += rng.sample(pool, min(q, len(pool)))
    rng.shuffle(sample)
    print(f"표본 {len(sample)}건 "
          f"(경력 {quota['experienced']} / 신입 {quota['entry']} / 음성 {quota['clean']}), "
          f"모델 {args.model}")

    jobs = []
    for rec in sample:
        for ch in ("chat", "file", "url"):
            r = rec["renders"][ch]
            text = "\n".join(r) if isinstance(r, list) else r
            jobs.append((rec, ch, text))

    results = {}
    done = [0]

    def work(job):
        rec, ch, text = job
        raw = call_api(key, args.model, text)
        done[0] += 1
        if done[0] % 20 == 0:
            print(f"  {done[0]}/{len(jobs)}", flush=True)
        return (rec["resume_id"], ch), (rec, parse_items(raw), raw)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for k, v in ex.map(work, jobs):
            results[k] = v
    print(f"호출 완료 {len(jobs)}건, {time.time()-t0:.0f}초\n")

    # ---------------------------------------------------------- 채점
    agg = {ch: defaultdict(lambda: [0, 0, 0]) for ch in ("chat", "file", "url")}
    errors = defaultdict(int)
    clean_fp = defaultdict(int)
    for (rid, ch), (rec, pred, raw) in results.items():
        if pred is None:
            errors[ch] += 1
            continue
        vis = VISIBLE[ch]
        gold = {x for x in gold_named(rec) if x[0] in vis}
        pred = {x for x in set(pred) if x[0] in vis}
        for t, e in (pred & gold):
            agg[ch][t][0] += 1
        for t, e in (pred - gold):
            agg[ch][t][1] += 1
            if not rec["missingness"]:
                clean_fp[ch] += 1
        for t, e in (gold - pred):
            agg[ch][t][2] += 1

    print(f"{'channel':8s} {'type':26s} {'TP':>4s} {'FP':>4s} {'FN':>4s} "
          f"{'P':>6s} {'R':>6s} {'F1':>6s}")
    print("-" * 70)
    summary = {}
    for ch in ("chat", "file", "url"):
        for t in TYPES:
            if t not in VISIBLE[ch]:
                continue
            tp, fp, fn = agg[ch][t]
            if tp + fp + fn == 0:
                continue
            p, r, f = prf(tp, fp, fn)
            print(f"{ch:8s} {t:26s} {tp:4d} {fp:4d} {fn:4d} {p:6.3f} {r:6.3f} {f:6.3f}")
        T = sum(v[0] for v in agg[ch].values())
        F = sum(v[1] for v in agg[ch].values())
        N = sum(v[2] for v in agg[ch].values())
        p, r, f = prf(T, F, N)
        summary[ch] = {"tp": T, "fp": F, "fn": N, "P": p, "R": r, "F1": f,
                       "clean_fp": clean_fp[ch], "errors": errors[ch]}
        print(f"{ch:8s} {'MICRO':26s} {T:4d} {F:4d} {N:4d} "
              f"{p:6.3f} {r:6.3f} {f:6.3f}")
        print("-" * 70)

    print("\n음성 샘플에서의 오탐 (결측 0건 이력서):")
    for ch in ("chat", "file", "url"):
        print(f"  {ch:8s} {clean_fp[ch]:3d}건   (API 오류 {errors[ch]}건)")

    out = os.path.join(root, args.out)
    json.dump({"model": args.model, "n": len(sample), "summary": summary,
               "per_type": {ch: {t: agg[ch][t] for t in TYPES}
                            for ch in ("chat", "file", "url")}},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n저장: {args.out}")


if __name__ == "__main__":
    main()
