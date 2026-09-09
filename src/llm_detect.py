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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from text_rules import detect_named, detect_from_document  # noqa: E402

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


NORMALIZE = """Convert the Korean resume below into JSON. Copy what is written;
do NOT infer, complete, or guess anything. Use null when a value is absent from
the text --- absence is the signal we care about.

{
 "education": [{"school": "...", "degree": "학사|전문학사|석사|박사|고졸",
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

"activities" is only for non-employment periods the person used to fill a gap
(study, training, job search). Extracurricular club/contest/internship entries
go in "extracurricular". Keep names verbatim. Output ONLY the JSON object."""


def call_api(key, model, text, system, max_tokens=1500, max_retries=4):
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
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


def parse_record(raw):
    if raw.startswith("__ERROR__"):
        return None
    s = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", s, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


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
    ap.add_argument("--method", default="all",
                    choices=["rules", "direct", "hybrid", "all"])
    ap.add_argument("--out", default="output/llm_detect.json")
    ap.add_argument("--cache", default="output/llm_cache.jsonl",
                    help="완료된 (이력서, 채널, 방법) 결과를 누적 저장해 재실행 시 건너뛴다")
    ap.add_argument("--limit", type=int, default=0,
                    help="이번 실행에서 처리할 최대 작업 수 (0이면 전부)")
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

    methods = (["rules", "direct", "hybrid"] if args.method == "all"
               else [args.method])

    jobs = []
    for rec in sample:
        for ch in ("chat", "file", "url"):
            r = rec["renders"][ch]
            text = "\n".join(r) if isinstance(r, list) else r
            for meth in methods:
                jobs.append((rec, ch, text, meth))

    n_api = sum(1 for j in jobs if j[3] != "rules")
    print(f"작업 {len(jobs)}건 (API 호출 {n_api}건), 방법 {methods}")

    # ---- 체크포인트: 이미 끝난 작업은 건너뛴다
    cache_path = os.path.join(root, args.cache)
    cache = {}
    if os.path.exists(cache_path):
        for line in open(cache_path, encoding="utf-8"):
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            cache[(d["rid"], d["ch"], d["meth"])] = (
                None if d["pred"] is None else {tuple(x) for x in d["pred"]})
    pending = [j for j in jobs if (j[0]["resume_id"], j[1], j[3]) not in cache]
    if args.limit:
        pending = pending[:args.limit]
    print(f"캐시 {len(cache)}건, 이번 실행 {len(pending)}건")

    results = {}
    done = [0]

    def work(job):
        rec, ch, text, meth = job
        if meth == "rules":
            pred = detect_from_document(text)
        elif meth == "direct":
            pred = parse_items(call_api(key, args.model, text, TAXONOMY))
            pred = set(pred) if pred is not None else None
        else:
            r = parse_record(call_api(key, args.model, text, NORMALIZE,
                                      max_tokens=8000))
            pred = detect_named(r) if r is not None else None
        done[0] += 1
        if done[0] % 50 == 0:
            print(f"  {done[0]}/{len(jobs)}", flush=True)
        return (rec["resume_id"], ch, meth), (rec, pred)

    t0 = time.time()
    if pending:
        fh = open(cache_path, "a", encoding="utf-8")
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            for k, v in ex.map(work, pending):
                cache[k] = v[1]
                fh.write(json.dumps(
                    {"rid": k[0], "ch": k[1], "meth": k[2],
                     "pred": None if v[1] is None else [list(x) for x in v[1]]},
                    ensure_ascii=False) + "\n")
                fh.flush()
        fh.close()
    print(f"이번 실행 {len(pending)}건, {time.time()-t0:.0f}초")

    by_id = {r["resume_id"]: r for r in sample}
    for (rid, ch, meth), pred in cache.items():
        if rid in by_id:
            results[(rid, ch, meth)] = (by_id[rid], pred)
    remaining = len(jobs) - len([k for k in cache if k[0] in by_id])
    print(f"채점 대상 {len(results)}건 (남은 작업 {max(0, remaining)}건)\n")

    # ---------------------------------------------------------- 채점
    agg = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    errors = defaultdict(int)
    clean_fp = defaultdict(int)
    for (rid, ch, meth), (rec, pred) in results.items():
        key_ = (meth, ch)
        if pred is None:
            errors[key_] += 1
            continue
        vis = VISIBLE[ch]
        gold = {x for x in gold_named(rec) if x[0] in vis}
        pred = {x for x in set(pred) if x[0] in vis}
        for t, e in (pred & gold):
            agg[key_][t][0] += 1
        for t, e in (pred - gold):
            agg[key_][t][1] += 1
            if not rec["missingness"]:
                clean_fp[key_] += 1
        for t, e in (gold - pred):
            agg[key_][t][2] += 1

    print(f"{'method':8s} {'channel':8s} {'TP':>5s} {'FP':>5s} {'FN':>5s} "
          f"{'P':>6s} {'R':>6s} {'F1':>6s} {'FPclean':>8s}")
    print("-" * 68)
    summary = {}
    for meth in methods:
        for ch in ("chat", "file", "url"):
            k = (meth, ch)
            T = sum(v[0] for v in agg[k].values())
            F = sum(v[1] for v in agg[k].values())
            N = sum(v[2] for v in agg[k].values())
            p, r, f = prf(T, F, N)
            summary[f"{meth}/{ch}"] = {
                "tp": T, "fp": F, "fn": N, "P": p, "R": r, "F1": f,
                "clean_fp": clean_fp[k], "errors": errors[k],
                "per_type": {t: agg[k][t] for t in TYPES if t in VISIBLE[ch]}}
            print(f"{meth:8s} {ch:8s} {T:5d} {F:5d} {N:5d} "
                  f"{p:6.3f} {r:6.3f} {f:6.3f} {clean_fp[k]:8d}")
        print("-" * 68)

    print("\n실패 (응답 파싱 불가 · 채점 제외)")
    for meth in methods:
        e = sum(errors[(meth, ch)] for ch in ("chat", "file", "url"))
        if e:
            print(f"  {meth:8s} {e}건")

    print("\n유형별 재현율")
    print(f"{'type':26s} " + " ".join(f"{m:>9s}" for m in methods))
    for t in TYPES:
        row = []
        for meth in methods:
            tp = sum(agg[(meth, ch)][t][0] for ch in ("chat", "file", "url")
                     if t in VISIBLE[ch])
            fn = sum(agg[(meth, ch)][t][2] for ch in ("chat", "file", "url")
                     if t in VISIBLE[ch])
            row.append(f"{tp/(tp+fn):9.3f}" if tp + fn else f"{'—':>9s}")
        print(f"{t:26s} " + " ".join(row))

    out = os.path.join(root, args.out)
    json.dump({"model": args.model, "n": len(sample), "methods": methods,
               "summary": summary},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n저장: {args.out}")


if __name__ == "__main__":
    main()
