#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터셋에서 대표 샘플을 골라 예시 Word 문서를 일괄 생성한다.

  output/examples/by-domain/   직군별 1건 (12종)
  output/examples/by-profile/  프로필 유형별 1건 (신입 / 고졸 / 경력 3·8·14년차)

선정 기준은 '결측 유형이 많고 프로젝트·활동이 풍부한 이력서'다.
동일 조건이면 resume_id 오름차순으로 고정해 재현성을 보장한다.

사용:
  python3 src/build_examples.py --data output/resumes.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def months(v: str) -> int:
    return int(v[:4]) * 12 + int(v[5:7])


def career_years(g) -> float:
    return sum(months(c["period"]["end"]) - months(c["period"]["start"])
               for c in g["careers"]) / 12


def richness(rec) -> tuple:
    """결측 유형 수 → 결측 건수 → 프로젝트 수 순으로 풍부한 샘플을 선호."""
    g = rec["gold"]
    n_proj = sum(len(c["projects"]) for c in g["careers"]) + len(g.get("personal_projects", []))
    return (len({m["type"] for m in rec["missingness"]}),
            len(rec["missingness"]),
            n_proj + len(g.get("extracurricular", [])))


def pick(records, cond):
    cands = [r for r in records if cond(r)]
    if not cands:
        return None
    cands.sort(key=lambda r: (-richness(r)[0], -richness(r)[1], -richness(r)[2], r["resume_id"]))
    return cands[0]


def slug(s: str) -> str:
    return s.replace("·", "-").replace("/", "-").replace(" ", "")


def render(rec, out_path):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False)
        tmp = f.name
    try:
        subprocess.run(["node", os.path.join(HERE, "make_doc.js"), tmp, out_path],
                       check=True, cwd=ROOT, capture_output=True)
    finally:
        os.unlink(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="output/resumes.jsonl")
    args = ap.parse_args()

    records = [json.loads(l) for l in open(os.path.join(ROOT, args.data), encoding="utf-8")]

    by_domain = os.path.join(ROOT, "output/examples/by-domain")
    by_profile = os.path.join(ROOT, "output/examples/by-profile")
    os.makedirs(by_domain, exist_ok=True)
    os.makedirs(by_profile, exist_ok=True)

    made = []

    # --- 직군별 -------------------------------------------------------
    domains = sorted({r["domain"] for r in records})
    for i, dom in enumerate(domains, 1):
        rec = pick(records, lambda r, d=dom: r["domain"] == d)
        if not rec:
            continue
        path = os.path.join(by_domain, f"{i:02d}_{slug(dom)}_{rec['resume_id']}.docx")
        render(rec, path)
        made.append((f"직군 · {dom}", rec, path))

    # --- 프로필 유형별 -------------------------------------------------
    def near(y, lo, hi):
        return lambda r: (r["gold"]["entry_type"] == "경력"
                          and lo <= career_years(r["gold"]) <= hi)

    profiles = [
        ("대졸신입", lambda r: r["gold"]["entry_type"] == "신입"
                                and r["gold"]["final_degree"] in ("학사", "전문학사")),
        ("고졸신입", lambda r: r["gold"]["entry_type"] == "신입"
                                and r["gold"]["final_degree"] == "고졸"),
        ("경력3년차", near(3, 2.5, 3.6)),
        ("경력8년차", near(8, 7.4, 8.7)),
        ("경력14년차", near(14, 13.0, 15.2)),
    ]
    for i, (name, cond) in enumerate(profiles, 1):
        rec = pick(records, cond)
        if not rec:
            print(f"  ! {name}: 조건에 맞는 샘플 없음")
            continue
        path = os.path.join(by_profile, f"{i}_{name}_{rec['resume_id']}.docx")
        render(rec, path)
        made.append((f"프로필 · {name}", rec, path))

    print(f"예시 문서 {len(made)}건 생성\n")
    for label, rec, path in made:
        g = rec["gold"]
        yrs = career_years(g)
        print(f"  {label:22s} {rec['resume_id']}  "
              f"{g['final_degree']:4s} {g['entry_type']:2s} "
              f"{yrs:5.1f}년  결측 {len(rec['missingness']):2d}건  "
              f"→ {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
