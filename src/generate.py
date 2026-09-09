#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
합성 이력서 데이터셋 생성기 (ICEIC 2027 / 이력 결측치 탐색 연구용)

파이프라인
  1) gold  : 결측이 전혀 없는 '완전한' 이력서를 직군별 사전으로 생성
  2) inject: 3종 결측치를 통제된 비율로 주입하고 위치·유형·정답을 라벨로 기록
  3) render: 동일 이력서를 대화체 / 파일(문서) / 웹프로필(URL) 3채널로 렌더링
             -> 명세서 청구항 2의 다중 입력 경로 실험용

결측치 유형 (명세서 1211/1212/1213 대응)
  TEMPORAL_GAP        기간적 공백기      : 공백을 메우던 활동 항목을 제거
  ROLE_OMISSION       직무 정보 누락     : 경력 구간의 직무/역할 필드를 제거
  ACHIEVEMENT_OMISSION 성과 누락         : 프로젝트의 정량 수치/역할/결과를 제거
  DATE_INCOMPLETE     기간 정보 불완전   : 'YYYY-MM' -> 'YYYY년' 로 해상도 저하 (선택)

사용
  python3 src/generate.py --n 400 --seed 42 --out output/resumes.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import random
from dataclasses import dataclass, field, asdict
from datetime import date

from domains import (
    DOMAINS, COMPANY_PREFIX, COMPANY_SUFFIX, COMPANY_FORM, COMPANY_SCALE,
    UNIV, UNIV_TYPE, SURNAME, GIVEN, MAJOR, GAP_REASONS,
    DEGREE_TRACK, RESEARCH_TOPIC, EXTRACURRICULAR, OVERSEAS,
    LANG_TESTS, OPIC_GRADE,
    HIGH_SCHOOL, HS_TYPE, HS_MAJOR, HS_EXTRA, PERSONAL_PROJECT,
)

TODAY = date(2026, 9, 1)

# 대외활동 카테고리별로 자연스러운 성과 문구
# gold 이력서는 '결측이 전혀 없는 완전판'이어야 하므로 None 을 두지 않는다.
# 모든 결측은 inject() 단계에서만 발생한다.
ACTIVITY_RESULT = {
    "공모전": ["최우수상 수상", "장려상 수상", "본선 진출", "예선 통과"],
    "대회": ["입상", "본선 진출", "장려상 수상", "완주"],
    "봉사": ["누적 봉사시간 100시간 이상", "우수 봉사자 표창", "정기 활동 완료"],
    "인턴": ["정규 인턴십 수료", "우수 인턴 선정", "최종 결과보고 발표"],
    "현장실습": ["현장실습 수료", "실습 평가 우수"],
    "학생자치": ["임기 완수", "연간 사업 계획 완료", "행사 기획·운영"],
    "동아리": ["정기 발표회 참가", "활동 결과물 전시", "운영진 활동"],
    "서포터즈": ["우수 활동자 선정", "콘텐츠 제작 완료", "활동 수료"],
    "교육과정": ["과정 수료", "우수 수료자 선정", "수료 프로젝트 발표"],
    "자격취득": ["자격증 취득", "과정 수료"],
    "기본": ["활동 수료", "우수 활동자 선정"],
}


# ------------------------------------------------------------------ 유틸
def weighted(rng: random.Random, pairs):
    items, ws = zip(*pairs)
    return rng.choices(items, weights=ws, k=1)[0]


def ym(y: int, m: int) -> str:
    return f"{y:04d}-{m:02d}"


def add_months(y: int, m: int, delta: int):
    total = (y * 12 + (m - 1)) + delta
    return total // 12, total % 12 + 1


def josa_ro(word: str) -> str:
    """받침에 따라 '로' / '으로' 선택. 'ㄹ' 받침은 '로'."""
    ch = word[-1]
    if not ("\uac00" <= ch <= "\ud7a3"):
        return "으로"
    jong = (ord(ch) - 0xAC00) % 28
    return "로" if jong in (0, 8) else "으로"


def months_between(a: str, b: str) -> int:
    ay, am = int(a[:4]), int(a[5:7])
    by, bm = int(b[:4]), int(b[5:7])
    return (by * 12 + bm) - (ay * 12 + am)


# ------------------------------------------------------------------ gold 생성
PUBLIC_ORG = ["한국{f}진흥원", "한국{f}연구원", "{f}산업진흥공단", "국가{f}센터"]
PUBLIC_FIELD = ["소프트웨어", "데이터", "산업기술", "직업능력", "물류", "콘텐츠", "품질"]


def make_company(rng, scale=None):
    if scale == "공공기관":
        return rng.choice(PUBLIC_ORG).format(f=rng.choice(PUBLIC_FIELD))
    p = rng.choice(COMPANY_PREFIX)
    s = rng.choice(COMPANY_SUFFIX)
    return rng.choice(COMPANY_FORM).format(p=p, s=s)


def make_metric(rng, dom_key):
    name, (unit, lo, hi, direction) = rng.choice(list(DOMAINS[dom_key]["metrics"].items()))
    if unit in ("%", "%p"):
        value = rng.randint(lo, hi)
    elif unit == "배":
        value = rng.randint(lo, hi)
    else:
        value = rng.randint(lo, hi)
    return {"name": name, "value": value, "unit": unit, "direction": direction}


def metric_phrase(m):
    """단위 성격에 맞는 서술어를 고른다. 비율은 개선/절감, 개수는 증가/감소."""
    up = m["direction"] == "up"
    if m["unit"] == "배":
        verb = "증가" if up else "감소"
    elif m["unit"] in ("%", "%p"):
        verb = "개선" if up else "절감"
    else:                       # 건, 명, 시간, 일, 점 등 개수 단위
        verb = "증가" if up else "감소"
    return f"{m['name']} {m['value']}{m['unit']} {verb}"


def make_project(rng, dom_key, pid, period, n_metrics=None):
    d = DOMAINS[dom_key]
    tmpl, roles = rng.choice(d["projects"])
    name = tmpl.format(domain=rng.choice(d["domains"]))
    n_metrics = n_metrics if n_metrics is not None else rng.choices([1, 2, 3], weights=[5, 4, 1])[0]
    metrics, seen = [], set()
    for _ in range(n_metrics):
        m = make_metric(rng, dom_key)
        if m["name"] in seen:
            continue
        seen.add(m["name"])
        metrics.append(m)
    return {
        "project_id": pid,
        "name": name,
        "period": period,
        "role": rng.choice(roles),
        "result": rng.choice([
            "정상 오픈 및 운영 이관 완료",
            "사내 표준 프로세스로 채택",
            "고객사 최종 검수 통과",
            "전사 확대 적용",
            "목표 지표 달성 후 정식 배포",
        ]),
        "metrics": metrics,
    }


def make_career_block(rng, dom_key, idx, start_y, start_m, months):
    d = DOMAINS[dom_key]
    end_y, end_m = add_months(start_y, start_m, months)
    period = {"start": ym(start_y, start_m), "end": ym(end_y, end_m)}
    n_proj = 1 if months < 18 else rng.choices([1, 2, 3], weights=[4, 4, 2])[0]
    projects = []
    for j in range(n_proj):
        # 프로젝트 기간은 재직 구간 내부에 배치
        off = rng.randint(0, max(0, months - 4))
        dur = rng.randint(3, max(4, min(14, months - off)))
        py, pm = add_months(start_y, start_m, off)
        pey, pem = add_months(py, pm, dur)
        projects.append(make_project(
            rng, dom_key, f"C{idx}-P{j + 1}",
            {"start": ym(py, pm), "end": ym(pey, pem)},
        ))
    scale = weighted(rng, COMPANY_SCALE)
    return {
        "career_id": f"C{idx}",
        "period": period,
        "company": make_company(rng, scale),
        "company_scale": scale,
        "role": rng.choice(d["jobs"]),
        "department": rng.choice(["개발본부", "서비스운영팀", "전략기획실", "사업부", "기술연구소", "고객지원팀"]),
        "position": weighted(rng, [("사원", .35), ("주임", .2), ("대리", .25), ("과장", .13), ("팀장", .07)]),
        "projects": projects,
    }


def hs_profile(rng, dom_key):
    """고교 유형과 그에 맞는 학과/계열을 함께 결정한다."""
    hs_type = weighted(rng, HS_TYPE)
    if hs_type == "일반고":
        return hs_type, rng.choice(["인문계열", "자연계열"])
    return hs_type, rng.choice(HS_MAJOR.get(dom_key, ["일반계열"]))


# ------------------------------------------------------------------ 무경력 신입
def make_fresh(rng, dom_key, resume_id, now, hs_ok):
    """경력이 없는 신입 이력서. 학력·대외활동·개인 프로젝트가 서사의 중심이 된다."""
    d = DOMAINS[dom_key]
    major = rng.choice(MAJOR[dom_key])

    track = [("전문학사", 0.22), ("학사", 0.54), ("석사", 0.08)]
    if hs_ok:
        track.append(("고졸", 0.20))
    degree = weighted(rng, track)

    # 졸업은 최근 0~20개월 이내 (그 사이는 구직 기간)
    grad_m = now - rng.choices([0, 2, 4, 7, 11, 16, 20],
                               weights=[10, 14, 16, 14, 10, 6, 4])[0]
    education = []

    def push(end_m, years, sch, maj, deg, lo, hi, extra=None):
        y0, m0 = end_m // 12, end_m % 12 + 1
        end_y = y0 if m0 >= 2 else y0 - 1
        e = {"period": {"start": ym(end_y - years, 3), "end": ym(end_y, 2)},
             "school": sch, "major": maj, "degree": deg,
             "gpa": round(rng.uniform(lo, hi), 2)}
        if extra:
            e.update(extra)
        education.append(e)
        return (end_y - years) * 12 + 2

    if degree == "고졸":
        hs_type, hs_major = hs_profile(rng, dom_key)
        push(grad_m, 3, rng.choice(HIGH_SCHOOL), hs_major, "고졸", 2.8, 4.5,
             {"school_type": hs_type})
    elif degree == "석사":
        s = push(grad_m, 2, rng.choice(UNIV), major + " 대학원", "석사", 3.2, 4.3,
                 {"research_topic": rng.choice(RESEARCH_TOPIC[dom_key]), "thesis": True})
        push(s - rng.randint(0, 4), 4, rng.choice(UNIV), major, "학사", 2.8, 4.2)
    elif degree == "전문학사":
        push(grad_m, 2, rng.choice(UNIV), major, "전문학사", 2.8, 4.2)
    else:
        push(grad_m, 4, rng.choice(UNIV), major, "학사", 2.8, 4.2)
    education.reverse()

    base = education[0]
    us_m = int(base["period"]["start"][:4]) * 12 + int(base["period"]["start"][5:7])
    ue_m = int(base["period"]["end"][:4]) * 12 + int(base["period"]["end"][5:7])

    # 대외활동: 신입 이력서의 핵심. 재학 중에 배치
    pool = HS_EXTRA if degree == "고졸" else EXTRACURRICULAR
    extracurricular = []
    for k in range(rng.choices([1, 2, 3, 4, 5], weights=[3, 7, 8, 5, 2])[0]):
        cat, names, roles, (dlo, dhi) = rng.choice(pool)
        dur = rng.randint(dlo, dhi)
        hi = max(us_m + 7, ue_m - dur + 2)
        st = rng.randint(us_m + 6, hi)
        sy, sm = st // 12, st % 12 + 1
        ey, em = add_months(sy, sm, dur)
        extracurricular.append({
            "activity_id": f"E{k + 1}",
            "category": cat,
            "name": rng.choice(names).format(
                dept=major,
                topic=rng.choice(["프로그래밍", "데이터 분석", "창업", "마케팅",
                                  "디자인", "AI", "금융", "전기", "기계"]),
                scale=rng.choice(["대기업", "중견기업", "중소기업", "공공기관"])),
            "period": {"start": ym(sy, sm), "end": ym(ey, em)},
            "role": rng.choice(roles),
            "result": rng.choice(ACTIVITY_RESULT.get(cat, ACTIVITY_RESULT["기본"])),
        })

    # 개인/졸업 프로젝트 — 경력 대신 실무 역량을 보여주는 자리
    personal_projects = []
    used_proj = set()
    for k in range(rng.choices([0, 1, 2, 3], weights=[2, 6, 7, 3])[0]):
        tmpl, roles = rng.choice(PERSONAL_PROJECT[dom_key])
        if tmpl in used_proj:
            continue
        used_proj.add(tmpl)
        dur = rng.randint(2, 8)
        lo_p = max(us_m + 10, ue_m - 30)
        st = rng.randint(lo_p, max(lo_p + 1, ue_m - dur))
        sy, sm = st // 12, st % 12 + 1
        ey, em = add_months(sy, sm, dur)
        n_met = rng.choices([1, 2], weights=[7, 3])[0]
        metrics, seen = [], set()
        for _ in range(n_met):
            mt = make_metric(rng, dom_key)
            if mt["name"] in seen:
                continue
            seen.add(mt["name"])
            if isinstance(mt["value"], int) and mt["value"] > 2:
                mt["value"] = max(1, int(mt["value"] * 0.4))   # 교내 규모에 맞게 축소
            metrics.append(mt)
        personal_projects.append({
            "project_id": f"PP{k + 1}",
            "name": tmpl.format(domain=rng.choice(d["domains"])),
            "period": {"start": ym(sy, sm), "end": ym(ey, em)},
            "role": rng.choice(roles),
            "result": rng.choice(
                ["교내 전시 출품", "우수과제 선정", "발표 및 시연 완료", "GitHub 공개"]
                if dom_key in ("개발", "데이터·AI")
                else ["교내 전시 출품", "우수과제 선정", "발표 및 시연 완료", "보고서 제출"]),
            "metrics": metrics,
        })

    # 졸업 후 구직 공백. 일정 길이 이상이면 활동으로 메운다
    activities = []
    edu_end = education[-1]["period"]["end"]
    edu_end_m = int(edu_end[:4]) * 12 + (int(edu_end[5:7]) - 1)
    gap = now - edu_end_m
    if gap >= 3:
        gy, gm = edu_end_m // 12, edu_end_m % 12 + 1
        ey, em = add_months(gy, gm, gap)
        activities.append({
            "activity_id": "A0",
            "period": {"start": ym(gy, gm), "end": ym(ey, em)},
            "title": rng.choice([
                "직무 전환을 위한 국비 교육과정 수강", "자격증 취득 준비",
                "개인 프로젝트 및 포트폴리오 제작", "어학 연수", "구직 활동",
                "인턴십 참여", "학원 수강 및 취업 준비",
            ]),
            "covers_gap_between": ["EDU", "NOW"],
        })

    overseas = []
    if degree != "고졸" and rng.random() < 0.22:
        kind, countries, (dlo, dhi), acts = rng.choice(OVERSEAS[:3])
        dur = rng.randint(dlo, dhi)
        st = rng.randint(us_m + 12, max(us_m + 13, ue_m - dur - 2))
        sy, sm = st // 12, st % 12 + 1
        ey, em = add_months(sy, sm, dur)
        overseas.append({"activity_id": "O1", "kind": kind,
                         "country": rng.choice(countries),
                         "period": {"start": ym(sy, sm), "end": ym(ey, em)},
                         "detail": rng.choice(acts)})

    languages = []
    n_lang = (rng.choices([0, 1], weights=[6, 4])[0] if degree == "고졸"
              else rng.choices([0, 1, 2], weights=[2, 6, 4])[0])
    for name, lo, hi, unit in rng.sample(LANG_TESTS, k=n_lang):
        if name == "OPIc":
            pool_g = OPIC_GRADE[:4] if degree == "고졸" else OPIC_GRADE
            languages.append({"test": name, "score": rng.choice(pool_g)})
        elif name in ("JLPT", "HSK"):
            languages.append({"test": name, "score": f"{rng.randint(2, 4)}급"})
        elif degree == "고졸":
            languages.append({"test": name, "score": str(rng.randint(lo, int(lo + (hi - lo) * 0.45)))})
        else:
            languages.append({"test": name, "score": str(rng.randint(lo, hi))})

    n_cert = rng.randint(2, 3) if degree == "고졸" else rng.randint(1, 3)
    return {
        "resume_id": resume_id,
        "domain": dom_key,
        "domain_en": d["label_en"],
        "profile": {
            "name": rng.choice(SURNAME) + rng.choice(GIVEN),
            "email": f"user{rng.randint(1000, 9999)}@example.com",
            "phone": "010-0000-0000",
            "target_job": rng.choice(d["jobs"]),
        },
        "education": education,
        "final_degree": degree,
        "entry_type": "신입",
        "careers": [],
        "activities": activities,
        "extracurricular": extracurricular,
        "personal_projects": personal_projects,
        "overseas": overseas,
        "languages": languages,
        "skills": rng.sample(d["skills"], k=min(len(d["skills"]), rng.randint(3, 6))),
        "certificates": rng.sample(d["certs"], k=min(len(d["certs"]), n_cert)),
    }


def make_gold(rng, dom_key, resume_id):
    d = DOMAINS[dom_key]
    major = rng.choice(MAJOR[dom_key])
    # --- 진입 유형: 경력직 / 무경력 신입 ---------------------------------
    now = TODAY.year * 12 + (TODAY.month - 1)
    hs_ok = dom_key in HS_MAJOR                 # 고졸 채용이 현실적인 직군인가
    entry = weighted(rng, [("경력", 0.82), ("신입", 0.18)])

    if entry == "신입":
        return make_fresh(rng, dom_key, resume_id, now, hs_ok)

    # --- 경력 생성: '현재'를 기준점으로 과거로 역산한다 -------------------
    # 마지막 경력은 재직 중이거나 최근에 종료된 상태여야 구직자 이력서로 현실적이다.
    ongoing = rng.random() < 0.55                      # 55% 는 현재 재직 중
    anchor = now if ongoing else now - rng.randint(1, 9)

    # 목표 총 경력 연차 — 실제 채용 풀에 맞춰 시니어 구간을 두껍게
    years = weighted(rng, [
        (rng.uniform(0.5, 2), 0.12),     # 주니어
        (rng.uniform(2, 5), 0.26),
        (rng.uniform(5, 8), 0.24),
        (rng.uniform(8, 12), 0.22),      # 미들·시니어
        (rng.uniform(12, 18), 0.16),     # 시니어
    ])
    target = int(round(years * 12))
    n_career = min(7, max(1, round(target / rng.uniform(18, 34))))

    blocks, gaps_used, remaining, cursor = [], [], target, anchor
    for i in range(n_career):
        last = (i == n_career - 1)
        if last:
            months = max(6, remaining)
        else:
            share = remaining / (n_career - i)
            months = int(max(6, min(60, rng.gauss(share, share * 0.35))))
            months = min(months, remaining - 6 * (n_career - i - 1))
            months = max(6, months)
        start = cursor - months
        blocks.append((start, months))
        remaining -= months
        cursor = start
        if not last:
            gap = rng.choices([0, 1, 2, 4, 6, 9, 12, 15], weights=[18, 12, 10, 9, 8, 6, 5, 3])[0]
            gaps_used.append(gap)
            cursor -= gap

    blocks.reverse()
    gaps_used.reverse()

    careers, activities = [], []
    for i, (start, months) in enumerate(blocks, 1):
        cy, cm = start // 12, start % 12 + 1
        careers.append(make_career_block(rng, dom_key, i, cy, cm, months))
        if i <= len(gaps_used):
            gap = gaps_used[i - 1]
            ey, em = add_months(cy, cm, months)
            if gap >= 3:
                gy, gm = add_months(ey, em, gap)
                activities.append({
                    "activity_id": f"A{i}",
                    "period": {"start": ym(ey, em), "end": ym(gy, gm)},
                    "title": rng.choice(GAP_REASONS),
                    "covers_gap_between": [f"C{i}", f"C{i + 1}"],
                })

    # 첫 경력 시작에 맞춰 학력 기간을 역산 (졸업 후 0~10개월 내 취업)
    first = blocks[0][0]
    grad_year = (first - rng.randint(0, 10)) // 12

    # --- 학력: 최종 학위를 먼저 정하고 졸업 시점에서 역산 -----------------
    total_years_pre = target / 12
    track = list(DEGREE_TRACK)
    if hs_ok:                        # 고졸 채용이 있는 직군에는 고졸 경력자도 존재한다
        track = track + [("고졸", 0.14)]
    if total_years_pre < 2:          # 갓 졸업한 사람 중 박사는 드물다
        track = [(d, w * (0.2 if d == "박사" else 1.0)) for d, w in track]
    degree = weighted(rng, track)
    school = rng.choice(UNIV)
    grad_m = first - rng.randint(0, 10)          # 최종 졸업 시점(개월 단위)
    education = []

    def push(y0, m0, months, sch, maj, deg, gpa_lo, gpa_hi, extra=None):
        # 한국 대학 학사일정: 3월 입학, 2월 졸업으로 정렬
        end_y = y0 if m0 >= 2 else y0 - 1   # 졸업이 첫 경력보다 뒤로 가지 않도록
        start_y = end_y - max(1, round(months / 12))
        e = {"period": {"start": ym(start_y, 3), "end": ym(end_y, 2)},
             "school": sch, "major": maj, "degree": deg,
             "gpa": round(rng.uniform(gpa_lo, gpa_hi), 2)}
        if extra:
            e.update(extra)
        education.append(e)

    gy, gm = grad_m // 12, grad_m % 12 + 1
    if degree == "박사":
        push(gy, gm, 48, rng.choice(UNIV), major + " 대학원", "박사", 3.5, 4.4,
             {"research_topic": rng.choice(RESEARCH_TOPIC[dom_key]), "thesis": True})
        gy, gm = add_months(gy, gm, -(48 + rng.randint(0, 6)))
        push(gy, gm, 24, school, major + " 대학원", "석사", 3.3, 4.3,
             {"research_topic": rng.choice(RESEARCH_TOPIC[dom_key]), "thesis": True})
        gy, gm = add_months(gy, gm, -(24 + rng.randint(0, 4)))
        push(gy, gm, 48, school, major, "학사", 2.9, 4.2)
    elif degree == "석사":
        push(gy, gm, 24, rng.choice(UNIV), major + " 대학원", "석사", 3.2, 4.3,
             {"research_topic": rng.choice(RESEARCH_TOPIC[dom_key]), "thesis": True})
        gy, gm = add_months(gy, gm, -(24 + rng.randint(0, 6)))
        push(gy, gm, 48, school, major, "학사", 2.8, 4.2)
    elif degree == "전문학사":
        push(gy, gm, 24, school, major, "전문학사", 2.8, 4.2)
    elif degree == "고졸":
        hs_type, hs_major = hs_profile(rng, dom_key)
        push(gy, gm, 36, rng.choice(HIGH_SCHOOL), hs_major, "고졸", 2.8, 4.5,
             {"school_type": hs_type})
    else:
        push(gy, gm, 48, school, major, "학사", 2.8, 4.2)
    education.reverse()

    # --- 대외활동: 학부 재학 구간(± 여유)에 배치. 주니어일수록 많이 ----------
    total_years = target / 12
    n_extra = rng.choices([0, 1, 2, 3, 4],
                          weights=([2, 6, 8, 7, 4] if total_years < 3 else
                                   [5, 8, 6, 3, 1] if total_years < 8 else
                                   [10, 6, 3, 1, 0]))[0]
    undergrad = next((e for e in education
                      if e["degree"] in ("학사", "전문학사", "고졸")), education[0])
    us, ue = undergrad["period"]["start"], undergrad["period"]["end"]
    us_m = int(us[:4]) * 12 + int(us[5:7])
    ue_m = int(ue[:4]) * 12 + int(ue[5:7])

    extracurricular = []
    used_cat = set()
    pool = HS_EXTRA if degree == "고졸" else EXTRACURRICULAR
    for k in range(n_extra):
        cat, names, roles, (dlo, dhi) = rng.choice(pool)
        if cat in used_cat and rng.random() < 0.7:
            continue
        used_cat.add(cat)
        dur = rng.randint(dlo, dhi)
        # 대외활동은 재학 기간 안에서 종료되도록 배치
        hi = max(us_m + 7, ue_m - dur + 2)
        st = rng.randint(us_m + 6, hi)
        name = rng.choice(names).format(
            dept=major, topic=rng.choice(["프로그래밍", "데이터 분석", "창업", "마케팅",
                                          "디자인", "AI", "봉사", "금융"]),
            scale=rng.choice(["대기업", "중견기업", "스타트업", "공공기관"]))
        sy, sm = st // 12, st % 12 + 1
        ey, em = add_months(sy, sm, dur)
        extracurricular.append({
            "activity_id": f"E{k + 1}",
            "category": cat,
            "name": name,
            "period": {"start": ym(sy, sm), "end": ym(ey, em)},
            "role": rng.choice(roles),
            "result": rng.choice(ACTIVITY_RESULT.get(cat, ACTIVITY_RESULT["기본"])),
        })

    # --- 해외 경험 -------------------------------------------------------
    overseas = []
    if degree != "고졸" and rng.random() < (0.30 if total_years < 8 else 0.16):
        kind, countries, (dlo, dhi), acts = rng.choice(OVERSEAS)
        dur = rng.randint(dlo, dhi)
        # 대학원 진학자는 학부 재학 중에, 그 외에는 졸업 직후까지 배치해
        # 상위 학위 재학 기간과 겹치지 않게 한다.
        has_grad = any(e["degree"] in ("석사", "박사") for e in education)
        hi = (ue_m - dur - 2) if has_grad else (ue_m + 8)
        lo = us_m + 12
        st = rng.randint(lo, max(lo + 1, hi))
        sy, sm = st // 12, st % 12 + 1
        ey, em = add_months(sy, sm, dur)
        overseas.append({
            "activity_id": "O1",
            "kind": kind,
            "country": rng.choice(countries),
            "period": {"start": ym(sy, sm), "end": ym(ey, em)},
            "detail": rng.choice(acts),
        })

    # --- 어학 성적 -------------------------------------------------------
    languages = []
    for name, lo, hi, unit in rng.sample(LANG_TESTS, k=rng.choices([0, 1, 2], weights=[3, 6, 3])[0]):
        if name == "OPIc":
            languages.append({"test": name, "score": rng.choice(OPIC_GRADE)})
        elif name in ("JLPT", "HSK"):
            languages.append({"test": name, "score": f"{rng.randint(1, 3)}급"})
        else:
            languages.append({"test": name, "score": str(rng.randint(lo, hi))})
    if overseas and not languages:
        languages.append({"test": "OPIc", "score": rng.choice(["IM3", "IH", "AL"])})


    return {
        "resume_id": resume_id,
        "domain": dom_key,
        "domain_en": d["label_en"],
        "profile": {
            "name": rng.choice(SURNAME) + rng.choice(GIVEN),
            "email": f"user{rng.randint(1000, 9999)}@example.com",
            "phone": "010-0000-0000",
            "target_job": rng.choice(d["jobs"]),
        },
        "education": education,
        "final_degree": degree,
        "entry_type": "경력",
        "personal_projects": [],
        "careers": careers,
        "activities": activities,
        "extracurricular": extracurricular,
        "overseas": overseas,
        "languages": languages,
        "skills": rng.sample(d["skills"], k=min(len(d["skills"]), rng.randint(5, 9))),
        "certificates": rng.sample(d["certs"], k=min(len(d["certs"]), rng.randint(1, 3))),
    }


# ------------------------------------------------------------------ 결측 주입
def inject(rng, gold, cfg):
    """gold 를 복사해 결측을 주입하고 (observed, labels) 반환."""
    obs = json.loads(json.dumps(gold, ensure_ascii=False))
    labels = []

    # 1) TEMPORAL_GAP : 공백을 메우던 활동 항목 제거
    kept = []
    for act in obs["activities"]:
        c_prev, c_next = act["covers_gap_between"]
        gap_m = months_between(act["period"]["start"], act["period"]["end"])
        if gap_m >= cfg["gap_threshold"] and rng.random() < cfg["p_gap"]:
            labels.append({
                "type": "POST_GRAD_GAP" if c_prev == "EDU" else "TEMPORAL_GAP",
                "locator": {"between": [c_prev, c_next]},
                "gap_months": gap_m,
                "gap_period": act["period"],
                "gold_answer": act["title"],
            })
        else:
            kept.append(act)
    obs["activities"] = kept

    # 2) ROLE_OMISSION : 경력 구간의 직무 정보 제거
    for c in obs["careers"]:
        if rng.random() < cfg["p_role"]:
            labels.append({
                "type": "ROLE_OMISSION",
                "locator": {"career_id": c["career_id"]},
                "gold_answer": {
                    "role": c["role"], "department": c["department"], "position": c["position"],
                },
            })
            c["role"] = None
            c["department"] = None
            c["position"] = None

    # 3) ACHIEVEMENT_OMISSION : 프로젝트의 성과 요소 제거
    #    (경력 프로젝트 + 신입의 개인/졸업 프로젝트를 함께 다룬다)
    scoped = [(c["career_id"], p) for c in obs["careers"] for p in c["projects"]]
    scoped += [("PERSONAL", p) for p in obs.get("personal_projects", [])]
    for c in [{"career_id": cid, "projects": [p]} for cid, p in scoped]:
        for p in c["projects"]:
            if rng.random() >= cfg["p_ach"]:
                continue
            # 어떤 성과 요소를 지울지: metrics / role / result 중 1~3개
            targets = rng.sample(["metrics", "role", "result"],
                                 k=rng.choices([1, 2, 3], weights=[5, 4, 2])[0])
            gold_answer = {}
            for t in targets:
                gold_answer[t] = p[t]
                p[t] = [] if t == "metrics" else None
            labels.append({
                "type": "ACHIEVEMENT_OMISSION",
                "locator": {"career_id": c["career_id"], "project_id": p["project_id"]},
                "missing_fields": targets,
                "gold_answer": gold_answer,
            })

    # 3-b) THESIS_OMISSION : 석·박사 학력의 연구 주제 제거
    for e in obs["education"]:
        if e.get("thesis") and rng.random() < cfg["p_thesis"]:
            labels.append({
                "type": "THESIS_OMISSION",
                "locator": {"degree": e["degree"], "school": e["school"]},
                "gold_answer": e.get("research_topic"),
            })
            e["research_topic"] = None

    # 3-c) EXTRACURRICULAR_OMISSION : 대외활동의 역할/성과 제거
    for a in obs["extracurricular"]:
        if rng.random() >= cfg["p_extra"]:
            continue
        targets = [t for t in ("role", "result") if a.get(t)]
        if not targets:
            continue
        pick = rng.sample(targets, k=rng.randint(1, len(targets)))
        gold_answer = {t: a[t] for t in pick}
        for t in pick:
            a[t] = None
        labels.append({
            "type": "EXTRACURRICULAR_OMISSION",
            "locator": {"activity_id": a["activity_id"], "name": a["name"]},
            "missing_fields": pick,
            "gold_answer": gold_answer,
        })

    # 4) DATE_INCOMPLETE : 기간 해상도 저하 (연도만 남김)
    if cfg["p_date"] > 0:
        for c in obs["careers"]:
            if rng.random() < cfg["p_date"]:
                labels.append({
                    "type": "DATE_INCOMPLETE",
                    "locator": {"career_id": c["career_id"]},
                    "gold_answer": dict(c["period"]),
                })
                c["period"] = {
                    "start": c["period"]["start"][:4] + "년",
                    "end": c["period"]["end"][:4] + "년",
                }

    return obs, labels


# ------------------------------------------------------------------ 파생 사실
def derive_gaps(resume, threshold):
    """관측 이력서에서 '실제로 존재하는' 기간 공백을 계산 (탐지기 정답 대조용)."""
    spans = []
    for c in resume["careers"]:
        s, e = c["period"]["start"], c["period"]["end"]
        if len(s) != 7 or len(e) != 7:
            continue  # DATE_INCOMPLETE 구간은 제외
        spans.append((s, e, c["career_id"]))
    for a in resume["activities"]:
        spans.append((a["period"]["start"], a["period"]["end"], a["activity_id"]))
    spans.sort()
    gaps = []
    for i in range(len(spans) - 1):
        gap = months_between(spans[i][1], spans[i + 1][0])
        if gap >= threshold:
            gaps.append({"after": spans[i][2], "before": spans[i + 1][2], "months": gap})
    return gaps


# ------------------------------------------------------------------ 3채널 렌더링
def render_file(r):
    """문서형 이력서 텍스트 (파일 업로드 경로 시뮬레이션)."""
    L = [f"{r['profile']['name']} 이력서", f"희망 직무: {r['profile']['target_job']}", "", "[학력]"]
    for e in r["education"]:
        tag = e["degree"] + (f"·{e['school_type']}" if e.get("school_type") else "")
        line = (f"{e['period']['start']} ~ {e['period']['end']}  "
                f"{e['school']} {e['major']} ({tag}, 학점 {e['gpa']})")
        L.append(line)
        if e.get("thesis"):
            L.append(f"    연구 주제: {e.get('research_topic') or '(미기재)'}")
    L += ["", "[경력]"]
    if not r["careers"]:
        L.append("  해당 없음 (신입)")
    for c in r["careers"]:
        head = f"{c['period']['start']} ~ {c['period']['end']}  {c['company']} ({c['company_scale']})"
        if c["role"]:
            head += f" / {c['role']}"
        if c["position"]:
            head += f" {c['position']}"
        L.append(head)
        for p in c["projects"]:
            L.append(f"  - {p['name']} ({p['period']['start']}~{p['period']['end']})")
            if p["role"]:
                L.append(f"    담당: {p['role']}")
            if p["metrics"]:
                L.append("    성과: " + ", ".join(metric_phrase(m) for m in p["metrics"]))
            if p["result"]:
                L.append(f"    결과: {p['result']}")
    if r["activities"]:
        L += ["", "[기타 활동]"]
        for a in r["activities"]:
            L.append(f"{a['period']['start']} ~ {a['period']['end']}  {a['title']}")
    if r.get("personal_projects"):
        L += ["", "[프로젝트]"]
        for p in r["personal_projects"]:
            L.append(f"{p['period']['start']} ~ {p['period']['end']}  {p['name']}")
            if p.get("role"):
                L.append(f"    담당: {p['role']}")
            if p.get("metrics"):
                L.append("    성과: " + ", ".join(metric_phrase(m) for m in p["metrics"]))
            if p.get("result"):
                L.append(f"    결과: {p['result']}")
    if r.get("extracurricular"):
        L += ["", "[대외활동]"]
        for a in r["extracurricular"]:
            line = (f"{a['period']['start']} ~ {a['period']['end']}  "
                    f"[{a['category']}] {a['name']}")
            if a.get("role"):
                line += f" / {a['role']}"
            L.append(line)
            if a.get("result"):
                L.append(f"    성과: {a['result']}")
    if r.get("overseas"):
        L += ["", "[해외 경험]"]
        for o in r["overseas"]:
            L.append(f"{o['period']['start']} ~ {o['period']['end']}  "
                     f"{o['country']} {o['kind']} — {o['detail']}")
    if r.get("languages"):
        L += ["", "[어학]", ", ".join(f"{x['test']} {x['score']}" for x in r["languages"])]
    L += ["", "[기술]", ", ".join(r["skills"]), "", "[자격]", ", ".join(r["certificates"])]
    return "\n".join(L)


def render_chat(rng, r):
    """대화형 인터페이스 자유 입력 (구어체, 정보 순서 뒤섞임)."""
    outs = [f"안녕하세요, {r['profile']['target_job']} 쪽으로 지원하려고 해요."]
    for e in r["education"]:
        outs.append(f"{e['school']} {e['major']} {e['period']['end'][:4]}년에 "
                    f"{'수료' if e['degree'] == '비학위' else '졸업'}했습니다({e['degree']}).")
    for c in r["careers"]:
        s, en = c["period"]["start"], c["period"]["end"]
        base = f"{s}부터 {en}까지 {c['company']}에서 일했고"
        base += f" {c['role']}{josa_ro(c['role'])} 있었어요." if c["role"] else " 근무했어요."
        outs.append(base)
        for p in c["projects"]:
            frag = f"{p['name']} 했는데"
            if p["role"]:
                frag += f" 제가 {p['role']} 맡았고"
            if p["metrics"]:
                frag += " " + ", ".join(metric_phrase(m) for m in p["metrics"]) + " 했습니다."
            else:
                frag += " 그거 참여했습니다."
            outs.append(frag)
    for a in r["activities"]:
        outs.append(f"{a['period']['start']}~{a['period']['end']}에는 {a['title']} 했어요.")
    for p in r.get("personal_projects", []):
        s = f"{p['name']} 라는 프로젝트를 했어요"
        if p.get("role"):
            s += f", {p['role']} 맡았고요"
        if p.get("metrics"):
            s += ". " + ", ".join(metric_phrase(m) for m in p["metrics"]) + " 나왔습니다"
        outs.append(s + ".")
    if not r["careers"]:
        outs.append("아직 정식 경력은 없고 신입으로 지원합니다.")
    for a in r.get("extracurricular", []):
        s = f"학교 다닐 때 {a['name']} 활동했어요"
        if a.get("role"):
            s += f", {a['role']} 맡았고요"
        if a.get("result"):
            s += f". {a['result']} 했습니다"
        outs.append(s + ".")
    for o in r.get("overseas", []):
        outs.append(f"{o['period']['start']}부터 {o['country']}에서 {o['kind']} 했어요.")
    if r.get("languages"):
        outs.append("어학은 " + ", ".join(f"{x['test']} {x['score']}" for x in r["languages"]) + " 있어요.")
    outs.append("쓸 줄 아는 건 " + ", ".join(r["skills"][:5]) + " 정도예요.")
    rng.shuffle(outs[1:])
    return outs


def render_url(r):
    """외부 웹 프로필 페이지 (URL 수집 경로 시뮬레이션)."""
    L = [f"# {r['profile']['name']}", f"> {r['profile']['target_job']}", "", "## Experience"]
    for c in r["careers"]:
        L.append(f"### {c['company']}" + (f" — {c['role']}" if c["role"] else ""))
        L.append(f"{c['period']['start']} – {c['period']['end']}")
        for p in c["projects"]:
            line = f"* **{p['name']}**"
            bits = []
            if p["role"]:
                bits.append(p["role"])
            if p["metrics"]:
                bits.append(" / ".join(metric_phrase(m) for m in p["metrics"]))
            if bits:
                line += " — " + " · ".join(bits)
            L.append(line)
    if r.get("personal_projects"):
        L += ["", "## Projects"]
        for p in r["personal_projects"]:
            bits = [x for x in (p.get("role"),
                                ", ".join(metric_phrase(m) for m in p.get("metrics", [])) or None) if x]
            L.append(f"* **{p['name']}**" + (" — " + " · ".join(bits) if bits else ""))
    if r.get("extracurricular"):
        L += ["", "## Activities"]
        for a in r["extracurricular"]:
            bits = [x for x in (a.get("role"), a.get("result")) if x]
            L.append(f"* **{a['name']}** ({a['category']})"
                     + (" — " + " · ".join(bits) if bits else ""))
    if r.get("overseas"):
        for o in r["overseas"]:
            L.append(f"* {o['kind']} in {o['country']} ({o['period']['start']}–{o['period']['end']})")
    L += ["", "## Skills", " · ".join(r["skills"])]
    return "\n".join(L)


# ------------------------------------------------------------------ 메인
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300, help="생성할 이력서 수")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="output/resumes.jsonl")
    ap.add_argument("--gap-threshold", type=int, default=3, help="기간적 공백기 판단 기준값(개월)")
    ap.add_argument("--p-gap", type=float, default=0.75, help="공백 은폐(활동 항목 제거) 확률")
    ap.add_argument("--p-role", type=float, default=0.30, help="직무 정보 누락 주입 확률(경력 단위)")
    ap.add_argument("--p-ach", type=float, default=0.45, help="성과 누락 주입 확률(프로젝트 단위)")
    ap.add_argument("--p-date", type=float, default=0.10, help="기간 해상도 저하 확률(경력 단위)")
    ap.add_argument("--p-thesis", type=float, default=0.40, help="학위 연구주제 누락 확률")
    ap.add_argument("--p-extra", type=float, default=0.45, help="대외활동 상세 누락 확률")
    ap.add_argument("--p-clean", type=float, default=0.18,
                    help="결측이 전혀 없는 음성 샘플 비율")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    cfg = {"gap_threshold": args.gap_threshold, "p_gap": args.p_gap,
           "p_role": args.p_role, "p_ach": args.p_ach, "p_date": args.p_date,
           "p_thesis": args.p_thesis, "p_extra": args.p_extra}
    # 음성 샘플용 설정: 어떤 결측도 주입하지 않는다
    cfg_clean = dict(cfg, p_gap=0.0, p_role=0.0, p_ach=0.0,
                     p_date=0.0, p_thesis=0.0, p_extra=0.0)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    keys = list(DOMAINS.keys())

    stats = {k: 0 for k in ["TEMPORAL_GAP", "POST_GRAD_GAP", "ROLE_OMISSION",
                            "ACHIEVEMENT_OMISSION", "THESIS_OMISSION",
                            "EXTRACURRICULAR_OMISSION", "DATE_INCOMPLETE"]}
    per_domain = {k: 0 for k in keys}

    with open(args.out, "w", encoding="utf-8") as f:
        for i in range(args.n):
            dom = keys[i % len(keys)]            # 직군 균등 배분
            rid = f"R{i + 1:05d}"
            gold = make_gold(rng, dom, rid)
            # 이미 잘 작성된 이력서(결측 0건)를 일정 비율 섞어야
            # 정밀도 평가가 관대해지지 않는다
            is_clean = rng.random() < args.p_clean
            obs, labels = inject(rng, gold, cfg_clean if is_clean else cfg)
            for lb in labels:
                stats[lb["type"]] += 1
            per_domain[dom] += 1

            rec = {
                "resume_id": rid,
                "domain": dom,
                "clean": is_clean,
                "config": cfg_clean if is_clean else cfg,
                "gold": gold,
                "observed": obs,
                "missingness": labels,
                "derived_gaps": derive_gaps(obs, args.gap_threshold),
                "renders": {
                    "chat": render_chat(rng, obs),
                    "file": render_file(obs),
                    "url": render_url(obs),
                },
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    total_lab = sum(stats.values())
    print(f"생성 완료: {args.out}  ({args.n}건, 직군 {len(keys)}종)")
    print(f"음성 샘플(결측 0건) 비율 목표 {args.p_clean:.0%}")
    print(f"결측 라벨 총 {total_lab}개 (이력서당 평균 {total_lab / args.n:.2f}개)")
    for k, v in stats.items():
        print(f"  - {k:22s} {v:5d}")


if __name__ == "__main__":
    main()
