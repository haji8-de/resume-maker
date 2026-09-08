# 샘플 미리보기

직군별 1건 + 신입 유형별 1건


---

## 마케팅 · 경력 — R00041 (마케팅)

### 파일 채널
```
서지아 이력서
희망 직무: 콘텐츠 마케터

[학력]
2015-03 ~ 2017-02  백양대학교 경영학과 (전문학사, 학점 3.47)

[경력]
2017-11 ~ 2022-06  산업기술산업진흥공단 (공공기관) / 콘텐츠 마케터 대리
  - 게임 신규 고객 유입 캠페인 (2019-08~2020-07)
    담당: 소재 기획
    성과: 이메일 오픈율 13%p 개선
    결과: 고객사 최종 검수 통과
2022-07 ~ 2024-05  ㈜퀀텀네트웍스 (중소기업)
  - 이커머스 브랜드 캠페인 집행 (2023-04~2024-04)
    담당: 예산 운영
  - SEO 개선 프로젝트 (2022-07~2023-02)
    담당: 콘텐츠 구조 개선
    성과: 광고 전환당 비용(CPA) 27% 절감
    결과: 사내 표준 프로세스로 채택
2024년 ~ 2026년  온새시스템즈 (중견기업)
  - SEO 개선 프로젝트 (2024-09~2025-10)
    담당: 키워드 리서치
    성과: 신규 가입자 수 45% 개선, 이메일 오픈율 8%p 개선
    결과: 고객사 최종 검수 통과
  - 구독 제휴 마케팅 확대 (2024-07~2024-12)
    담당: 제휴 성과 관리
    성과: 이메일 오픈율 16%p 개선

[어학]
OPIc AL, HSK 3급

[기술]
Excel, GA4, Google Ads, Appsflyer, SQL, Notion, Braze, Looker Studio, Meta Ads

[자격]
사회조사분석사 2급, GAIQ, 컴퓨터활용능력 1급
```

### 정답 결측 라벨
```json
[
 {
  "type": "ROLE_OMISSION",
  "locator": {
   "career_id": "C2"
  },
  "gold_answer": {
   "role": "퍼포먼스 마케터",
   "department": "기술연구소",
   "position": "사원"
  }
 },
 {
  "type": "ROLE_OMISSION",
  "locator": {
   "career_id": "C3"
  },
  "gold_answer": {
   "role": "퍼포먼스 마케터",
   "department": "고객지원팀",
   "position": "사원"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C2",
   "project_id": "C2-P1"
  },
  "missing_fields": [
   "result",
   "metrics"
  ],
  "gold_answer": {
   "result": "목표 지표 달성 후 정식 배포",
   "metrics": [
    {
     "name": "자연 유입 트래픽",
     "value": 63,
     "unit": "%",
     "direction": "up"
    }
   ]
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C3",
   "project_id": "C3-P2"
  },
  "missing_fields": [
   "result"
  ],
  "gold_answer": {
   "result": "사내 표준 프로세스로 채택"
  }
 },
 {
  "type": "DATE_INCOMPLETE",
  "locator": {
   "career_id": "C3"
  },
  "gold_answer": {
   "start": "2024-05",
   "end": "2026-04"
  }
 }
]
```


---

## 기획·PM · 경력 — R00171 (기획·PM)

### 파일 채널
```
안다인 이력서
희망 직무: PMO 담당

[학력]
2022-03 ~ 2024-02  하늘재대학교 경영학과 (전문학사, 학점 3.92)

[경력]
2025-04 ~ 2026-07  픽셀테크㈜ (중소기업) / 사업기획 담당 대리
  - 콘텐츠 신규 서비스 런칭 기획 (2025-11~2026-02)
    결과: 정상 오픈 및 운영 이관 완료

[대외활동]
2022-12 ~ 2023-11  [학생자치] 단과대학 학생회
    성과: 임기 완수

[어학]
TOEIC 823, OPIc IM3

[기술]
SQL, Notion, Jira, Excel, Amplitude, Figma, GA4

[자격]
컴퓨터활용능력 1급, 정보처리기사, PMP
```

### 정답 결측 라벨
```json
[
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C1",
   "project_id": "C1-P1"
  },
  "missing_fields": [
   "role",
   "metrics"
  ],
  "gold_answer": {
   "role": "일정 및 리소스 관리",
   "metrics": [
    {
     "name": "월간 활성 이용자",
     "value": 18,
     "unit": "%",
     "direction": "up"
    }
   ]
  }
 },
 {
  "type": "EXTRACURRICULAR_OMISSION",
  "locator": {
   "activity_id": "E1",
   "name": "단과대학 학생회"
  },
  "missing_fields": [
   "role"
  ],
  "gold_answer": {
   "role": "총무"
  }
 }
]
```


---

## 회계·재무 · 경력 — R00332 (회계·재무)

### 파일 채널
```
정성민 이력서
희망 직무: 재무 담당

[학력]
2011-03 ~ 2013-02  이현대학교 경영학과 (전문학사, 학점 3.99)

[경력]
2014-02 ~ 2016-05  하람테크 (스타트업) / 세무 담당 주임
  - 자금 수지 관리 개선 (2014-08~2015-02)
    성과: 회계 오류 건수 30건 절감
  - 원가 관리 체계 구축 (2016-01~2016-04)
    담당: 원가 항목 재분류
    성과: 리포팅 공수 28시간 절감
    결과: 목표 지표 달성 후 정식 배포
2016-11 ~ 2020-06  넥스파트너스 주식회사 (스타트업)
  - ERP 회계 모듈 전환 (2019-07~2019-12)
    결과: 정상 오픈 및 운영 이관 완료
2021-06 ~ 2023-09  넥스플랫폼㈜ (중소기업) / 세무 담당 대리
  - 자금 수지 관리 개선 (2022-03~2022-12)
    성과: 운영비 10% 절감
  - ERP 회계 모듈 전환 (2022-11~2023-05)
    담당: 계정 체계 매핑
2024-03 ~ 2026-09  퀀텀랩스 (중소기업)
  - 결산 프로세스 자동화 (2025-11~2026-06)
  - 결산 프로세스 자동화 (2025-11~2026-06)
    담당: 자동화 로직 도입
    성과: 자금 회수 기간 22% 절감
    결과: 목표 지표 달성 후 정식 배포
  - 세무 신고 대응 (2024-03~2025-04)
    담당: 신고 자료 작성
    성과: 운영비 23% 절감, 자금 회수 기간 17% 절감
    결과: 사내 표준 프로세스로 채택

[기타 활동]
2016-05 ~ 2016-11  이직 준비 및 구직 활동

[대외활동]
2011-10 ~ 2013-05  [동아리] 마케팅 소모임 / 회장
    성과: 운영진 활동

[어학]
OPIc IL, HSK 2급

[기술]
더존, ERP, Power BI, SAP FI, Excel

[자격]
재경관리사, 전산회계 1급, 세무회계 2급
```

### 정답 결측 라벨
```json
[
 {
  "type": "TEMPORAL_GAP",
  "locator": {
   "between": [
    "C2",
    "C3"
   ]
  },
  "gap_months": 12,
  "gap_period": {
   "start": "2020-06",
   "end": "2021-06"
  },
  "gold_answer": "자격증 취득 준비"
 },
 {
  "type": "TEMPORAL_GAP",
  "locator": {
   "between": [
    "C3",
    "C4"
   ]
  },
  "gap_months": 6,
  "gap_period": {
   "start": "2023-09",
   "end": "2024-03"
  },
  "gold_answer": "개인 프로젝트 및 포트폴리오 제작"
 },
 {
  "type": "ROLE_OMISSION",
  "locator": {
   "career_id": "C2"
  },
  "gold_answer": {
   "role": "회계 담당",
   "department": "기술연구소",
   "position": "주임"
  }
 },
 {
  "type": "ROLE_OMISSION",
  "locator": {
   "career_id": "C4"
  },
  "gold_answer": {
   "role": "세무 담당",
   "department": "서비스운영팀",
   "position": "팀장"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C1",
   "project_id": "C1-P1"
  },
  "missing_fields": [
   "role",
   "result"
  ],
  "gold_answer": {
   "role": "지출 통제 기준 마련",
   "result": "목표 지표 달성 후 정식 배포"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C2",
   "project_id": "C2-P1"
  },
  "missing_fields": [
   "metrics",
   "role"
  ],
  "gold_answer": {
   "metrics": [
    {
     "name": "회계 오류 건수",
     "value": 26,
     "unit": "건",
     "direction": "down"
    }
   ],
   "role": "계정 체계 매핑"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C3",
   "project_id": "C3-P1"
  },
  "missing_fields": [
   "role",
   "result"
  ],
  "gold_answer": {
   "role": "자금 계획 수립",
   "result": "고객사 최종 검수 통과"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C3",
   "project_id": "C3-P2"
  },
  "missing_fields": [
   "result",
   "metrics"
  ],
  "gold_answer": {
   "result": "사내 표준 프로세스로 채택",
   "metrics": [
    {
     "name": "월 결산 소요 일수",
     "value": 10,
     "unit": "일",
     "direction": "down"
    },
    {
     "name": "자금 회수 기간",
     "value": 26,
     "unit": "%",
     "direction": "down"
    }
   ]
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C4",
   "project_id": "C4-P1"
  },
  "missing_fields": [
   "result",
   "metrics",
   "role"
  ],
  "gold_answer": {
   "result": "사내 표준 프로세스로 채택",
   "metrics": [
    {
     "name": "월 결산 소요 일수",
     "value": 7,
     "unit": "일",
     "direction": "down"
    },
    {
     "name": "운영비",
     "value": 28,
     "unit": "%",
     "direction": "down"
    }
   ],
   "role": "자동화 로직 도입"
  }
 }
]
```


---

## 생산·품질 · 신입 — R00153 (생산·품질)

### 파일 채널
```
류지우 이력서
희망 직무: 생산관리 담당

[학력]
2020-03 ~ 2024-02  동림대학교 화학공학과 (학사, 학점 3.06)
2024-03 ~ 2026-02  소로대학교 화학공학과 대학원 (석사, 학점 3.39)
    연구 주제: 설비 진동 데이터 기반 고장 예지

[경력]
  해당 없음 (신입)

[기타 활동]
2026-02 ~ 2026-09  학원 수강 및 취업 준비

[대외활동]
2023-08 ~ 2023-12  [교육과정] 국비지원 AI 부트캠프 / 교육생
    성과: 우수 수료자 선정
2023-09 ~ 2023-12  [인턴] 체험형 인턴

[어학]
OPIc IL, JLPT 3급

[기술]
AutoCAD, SPC, Excel, MES, ISO 9001, 6시그마

[자격]
6시그마 GB, 품질경영기사, 산업안전기사
```

### 정답 결측 라벨
```json
[
 {
  "type": "EXTRACURRICULAR_OMISSION",
  "locator": {
   "activity_id": "E2",
   "name": "체험형 인턴"
  },
  "missing_fields": [
   "result",
   "role"
  ],
  "gold_answer": {
   "result": "최종 결과보고 발표",
   "role": "인턴"
  }
 }
]
```


---

## 물류·유통 · 경력 — R00250 (물류·유통)

### 파일 채널
```
임시우 이력서
희망 직무: MD

[학력]
2020-03 ~ 2024-02  서원대학교 물류학과 (학사, 학점 2.9)

[경력]
2024-05 ~ 2026-02  세움시스템즈 주식회사 (중소기업)
  - 가전 재고 관리 체계 개선 (2024-12~2025-07)

[대외활동]
2020-12 ~ 2022-08  [학생자치] 물류학과 학생회 / 회장
    성과: 연간 사업 계획 완료

[해외 경험]
2024-05 ~ 2026-09  영국 해외 대학원 — 석사 과정 수학

[어학]
JLPT 1급, OPIc IL

[기술]
무역실무, SAP MM, Excel, WMS, Power BI, SQL

[자격]
지게차운전기능사, 물류관리사
```

### 정답 결측 라벨
```json
[
 {
  "type": "ROLE_OMISSION",
  "locator": {
   "career_id": "C1"
  },
  "gold_answer": {
   "role": "SCM 담당",
   "department": "전략기획실",
   "position": "사원"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C1",
   "project_id": "C1-P1"
  },
  "missing_fields": [
   "role",
   "result",
   "metrics"
  ],
  "gold_answer": {
   "role": "발주 로직 개선",
   "result": "전사 확대 적용",
   "metrics": [
    {
     "name": "배송 리드타임",
     "value": 21,
     "unit": "%",
     "direction": "down"
    }
   ]
  }
 }
]
```


---

## 교육 · 경력 — R00096 (교육)

### 파일 채널
```
이나연 이력서
희망 직무: 학습설계(ID) 담당

[학력]
2013-03 ~ 2017-02  남강대학교 국어교육과 (학사, 학점 3.32)

[경력]
2017-08 ~ 2019-11  브릿지솔루션 주식회사 (중견기업)
  - 이러닝 콘텐츠 제작 (2019-03~2019-08)
    담당: 콘텐츠 기획
    성과: 재수강률 9%p 개선
    결과: 고객사 최종 검수 통과
  - LMS 도입 및 운영 (2019-04~2019-08)
    결과: 고객사 최종 검수 통과
2020-11 ~ 2022-08  세움다이나믹스㈜ (대기업)
  - LMS 도입 및 운영 (2021-09~2022-03)
    담당: 운영 프로세스 수립
    결과: 사내 표준 프로세스로 채택
2022-12 ~ 2025-11  세움웍스 (중견기업) / 교육기획 담당 사원
  - 공공 직무 교육과정 개발 (2024-08~2025-07)
    담당: 교안 제작
    성과: 교육 운영 공수 20% 절감, 수강 만족도 3점 향상
  - 공공 신입 온보딩 교육 설계 (2024-05~2024-09)
    성과: 누적 수강 인원 1507명 향상, 과정 수료율 16%p 개선
  - 금융 직무 교육과정 개발 (2024-03~2024-09)
    담당: 강의 운영
    결과: 사내 표준 프로세스로 채택
2026-01 ~ 2026-09  넥스네트웍스 (중소기업) / 교육기획 담당 사원
  - LMS 도입 및 운영 (2026-05~2026-08)
    담당: 요구사항 정의
    성과: 과정 수료율 21%p 개선, 교육 운영 공수 19% 절감
    결과: 전사 확대 적용

[기타 활동]
2022-08 ~ 2022-12  창업 준비

[대외활동]
2015-06 ~ 2017-02  [동아리] 창업 소모임 / 스터디 리더
    성과: 정기 발표회 참가
2015-03 ~ 2015-08  [공모전] 금융 아이디어 공모전 / 팀원
    성과: 장려상 수상

[기술]
Camtasia, Notion, LMS 운영, Python, Articulate Storyline, Excel

[자격]
정보처리기사, 직업능력개발훈련교사, 평생교육사 2급
```

### 정답 결측 라벨
```json
[
 {
  "type": "TEMPORAL_GAP",
  "locator": {
   "between": [
    "C1",
    "C2"
   ]
  },
  "gap_months": 12,
  "gap_period": {
   "start": "2019-11",
   "end": "2020-11"
  },
  "gold_answer": "가족 간병"
 },
 {
  "type": "ROLE_OMISSION",
  "locator": {
   "career_id": "C1"
  },
  "gold_answer": {
   "role": "교육 강사",
   "department": "개발본부",
   "position": "주임"
  }
 },
 {
  "type": "ROLE_OMISSION",
  "locator": {
   "career_id": "C2"
  },
  "gold_answer": {
   "role": "교육기획 담당",
   "department": "서비스운영팀",
   "position": "주임"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C1",
   "project_id": "C1-P2"
  },
  "missing_fields": [
   "metrics",
   "role"
  ],
  "gold_answer": {
   "metrics": [
    {
     "name": "재수강률",
     "value": 6,
     "unit": "%p",
     "direction": "up"
    },
    {
     "name": "교육 운영 공수",
     "value": 14,
     "unit": "%",
     "direction": "down"
    }
   ],
   "role": "운영 프로세스 수립"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C2",
   "project_id": "C2-P1"
  },
  "missing_fields": [
   "metrics"
  ],
  "gold_answer": {
   "metrics": [
    {
     "name": "교육 운영 공수",
     "value": 20,
     "unit": "%",
     "direction": "down"
    }
   ]
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C3",
   "project_id": "C3-P1"
  },
  "missing_fields": [
   "result"
  ],
  "gold_answer": {
   "result": "전사 확대 적용"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C3",
   "project_id": "C3-P2"
  },
  "missing_fields": [
   "role",
   "result"
  ],
  "gold_answer": {
   "role": "교육 목표 수립",
   "result": "전사 확대 적용"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C3",
   "project_id": "C3-P3"
  },
  "missing_fields": [
   "metrics"
  ],
  "gold_answer": {
   "metrics": [
    {
     "name": "교육 운영 공수",
     "value": 25,
     "unit": "%",
     "direction": "down"
    }
   ]
  }
 }
]
```


---

## 영업 · 경력 — R00126 (영업)

### 파일 채널
```
한민준 이력서
희망 직무: 영업관리 담당

[학력]
2011-03 ~ 2015-02  서원대학교 기계공학과 (학사, 학점 3.23)

[경력]
2015-08 ~ 2018-10  퀀텀커머스㈜ (중견기업) / B2B 영업 담당 과장
  - 의료기기 대리점 채널 확대 (2018-06~2018-10)
    담당: 채널 정책 수립
    성과: 고객 이탈률 10%p 절감
    결과: 목표 지표 달성 후 정식 배포
  - 화학 해외 바이어 발굴 (2015-11~2016-06)
    담당: 전시회 참가
    성과: 신규 계약 건수 58건 향상, 영업 사이클 기간 13% 절감
    결과: 전사 확대 적용
2018-12 ~ 2021-06  ㈜그리드소프트 (스타트업)
  - IT솔루션 해외 바이어 발굴 (2020-05~2021-02)
    성과: 신규 계약 건수 58건 향상
    결과: 목표 지표 달성 후 정식 배포
  - IT솔루션 대리점 채널 확대 (2020-02~2020-07)
    담당: 채널 정책 수립
    성과: 연간 매출 29% 개선
    결과: 목표 지표 달성 후 정식 배포
  - 영업 프로세스 표준화 (2020-03~2020-06)
    성과: 고객 이탈률 5%p 절감, 신규 계약 건수 38건 향상
2021-08 ~ 2023-09  실린다이나믹스 주식회사 (중소기업)
  - 화학 대리점 채널 확대 (2021-10~2022-12)
    담당: 채널 정책 수립
    성과: 영업 사이클 기간 13% 절감
    결과: 정상 오픈 및 운영 이관 완료
2023-09 ~ 2026-09  ㈜코어인더스트리 (중견기업)
  - 화학 해외 바이어 발굴 (2025-03~2025-09)
    담당: 전시회 참가
    성과: 계약 갱신율 6%p 개선, 신규 계약 건수 40건 향상
    결과: 고객사 최종 검수 통과

[대외활동]
2013-12 ~ 2015-01  [봉사] 해외 봉사단 / 봉사단원
    성과: 누적 봉사시간 100시간 이상
2014-03 ~ 2014-07  [서포터즈] 정부기관 대학생 기자단 / 콘텐츠 제작 담당

[어학]
TOEFL 88, HSK 1급

[기술]
SQL, PowerPoint, 영문 커뮤니케이션, HubSpot, Salesforce, Excel

[자격]
TOEIC 900
```

### 정답 결측 라벨
```json
[
 {
  "type": "ROLE_OMISSION",
  "locator": {
   "career_id": "C2"
  },
  "gold_answer": {
   "role": "기술영업 담당",
   "department": "서비스운영팀",
   "position": "사원"
  }
 },
 {
  "type": "ROLE_OMISSION",
  "locator": {
   "career_id": "C3"
  },
  "gold_answer": {
   "role": "영업관리 담당",
   "department": "개발본부",
   "position": "사원"
  }
 },
 {
  "type": "ROLE_OMISSION",
  "locator": {
   "career_id": "C4"
  },
  "gold_answer": {
   "role": "영업관리 담당",
   "department": "전략기획실",
   "position": "주임"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C2",
   "project_id": "C2-P1"
  },
  "missing_fields": [
   "role"
  ],
  "gold_answer": {
   "role": "시장 조사"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C2",
   "project_id": "C2-P3"
  },
  "missing_fields": [
   "result",
   "role"
  ],
  "gold_answer": {
   "result": "사내 표준 프로세스로 채택",
   "role": "파이프라인 정의"
  }
 },
 {
  "type": "EXTRACURRICULAR_OMISSION",
  "locator": {
   "activity_id": "E2",
   "name": "정부기관 대학생 기자단"
  },
  "missing_fields": [
   "result"
  ],
  "gold_answer": {
   "result": "콘텐츠 제작 완료"
  }
 }
]
```


---

## 디자인 · 경력 — R00388 (디자인)

### 파일 채널
```
강준서 이력서
희망 직무: 영상 디자이너

[학력]
2020-03 ~ 2023-02  백양고등학교 미디어콘텐츠과 (고졸·특성화고, 학점 3.52)

[경력]
2024-06 ~ 2026-08  포레랩스 (스타트업) / 그래픽 디자이너 대리
  - 패션 앱 UI 전면 리뉴얼 (2024-11~2026-01)
    담당: 와이어프레임 설계
    성과: 콘텐츠 조회수 22% 개선, 디자인 산출 소요 시간 15% 절감
    결과: 정상 오픈 및 운영 이관 완료
  - 교육 프로모션 영상 제작 (2025-01~2026-02)
    담당: 스토리보드 구성
    성과: 콘텐츠 조회수 112% 개선
    결과: 목표 지표 달성 후 정식 배포

[대외활동]
2021-12 ~ 2023-05  [동아리] 교내 마케팅 동아리
    성과: 운영진 활동
2022-01 ~ 2022-05  [대회] 전국기능경기대회

[어학]
TOEIC 908

[기술]
Illustrator, Photoshop, Zeplin, Sketch, Blender, Premiere Pro

[자격]
웹디자인기능사, GTQ 1급
```

### 정답 결측 라벨
```json
[
 {
  "type": "EXTRACURRICULAR_OMISSION",
  "locator": {
   "activity_id": "E1",
   "name": "교내 마케팅 동아리"
  },
  "missing_fields": [
   "role"
  ],
  "gold_answer": {
   "role": "부원"
  }
 },
 {
  "type": "EXTRACURRICULAR_OMISSION",
  "locator": {
   "activity_id": "E2",
   "name": "전국기능경기대회"
  },
  "missing_fields": [
   "role",
   "result"
  ],
  "gold_answer": {
   "role": "팀원",
   "result": "완주"
  }
 }
]
```


---

## 개발 · 경력 — R00013 (개발)

### 파일 채널
```
한도윤 이력서
희망 직무: 서버 개발자

[학력]
2012-03 ~ 2016-02  한빛대학교 컴퓨터공학과 (학사, 학점 3.9)

[경력]
2016년 ~ 2020년  브릿지테크 (중견기업) / 게임 클라이언트 개발자 과장
  - 이커머스 웹 프론트엔드 리뉴얼 (2017-04~2017-12)
    담당: 반응형 UI 구현
    성과: API 응답 속도 60% 절감
2020-11 ~ 2022-11  ㈜포레인더스트리 (스타트업) / 안드로이드 개발자 사원
  - 사내 관리자 페이지 구축 (2022-02~2022-08)
    담당: 권한 체계 설계
    성과: API 응답 속도 31% 절감, 서버 비용 19% 절감, 동시 접속 처리량 6배 증가
    결과: 정상 오픈 및 운영 이관 완료
  - 레거시 시스템 마이크로서비스 전환 (2021-08~2022-02)
    성과: 장애 발생 건수 23건 절감
2023-11 ~ 2026-04  한국직업능력진흥원 (공공기관) / 게임 클라이언트 개발자 대리
  - 사내 관리자 페이지 구축 (2024-10~2025-04)
    담당: 권한 체계 설계
    성과: 테스트 커버리지 20%p 개선
    결과: 정상 오픈 및 운영 이관 완료

[어학]
TOEFL 107

[기술]
Swift, Node.js, Docker, Kubernetes, Jenkins, PostgreSQL, Python, Spring Boot, MySQL

[자격]
정보처리기사, SQLD
```

### 정답 결측 라벨
```json
[
 {
  "type": "TEMPORAL_GAP",
  "locator": {
   "between": [
    "C2",
    "C3"
   ]
  },
  "gap_months": 12,
  "gap_period": {
   "start": "2022-11",
   "end": "2023-11"
  },
  "gold_answer": "가족 간병"
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C1",
   "project_id": "C1-P1"
  },
  "missing_fields": [
   "result"
  ],
  "gold_answer": {
   "result": "고객사 최종 검수 통과"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C2",
   "project_id": "C2-P2"
  },
  "missing_fields": [
   "role",
   "result"
  ],
  "gold_answer": {
   "role": "배포 파이프라인 구성",
   "result": "전사 확대 적용"
  }
 },
 {
  "type": "DATE_INCOMPLETE",
  "locator": {
   "career_id": "C1"
  },
  "gold_answer": {
   "start": "2016-11",
   "end": "2020-10"
  }
 }
]
```


---

## 고객상담·CS · 경력 — R00347 (고객상담·CS)

### 파일 채널
```
김주원 이력서
희망 직무: 고객경험(CX) 담당

[학력]
2011-03 ~ 2014-02  백양고등학교 서비스마케팅과 (고졸·특성화고, 학점 4.24)

[경력]
2015-01 ~ 2019-08  인디고파트너스㈜ (중소기업)
  - 상담 품질 관리 체계 수립 (2016-03~2016-10)
    담당: QA 평가표 설계
    결과: 사내 표준 프로세스로 채택
2019-12 ~ 2022-02  다온다이나믹스 (중견기업)
  - 고객 문의 응대 프로세스 개선 (2021-03~2021-07)
    담당: FAQ 재구성
    성과: 1차 해결률 7%p 개선
2022-04 ~ 2023-02  다온시스템즈㈜ (대기업) / 콜센터 QA 담당 사원
  - 상담 품질 관리 체계 수립 (2022-04~2022-08)
    담당: 상담사 코칭
    성과: 고객 만족도(CSAT) 14%p 개선, 1차 해결률 19%p 개선, 평균 응답 시간 59% 절감
    결과: 고객사 최종 검수 통과
2023-02 ~ 2026-04  세움시스템즈 주식회사 (대기업) / 콜센터 QA 담당 사원
  - 챗봇 도입 프로젝트 (2025-12~2026-03)
    담당: 도입 효과 측정
    성과: 반복 문의 비율 7%p 절감
    결과: 고객사 최종 검수 통과
  - 금융 VOC 분석 체계 구축 (2023-04~2023-09)
    담당: VOC 분류 체계 설계
    성과: 반복 문의 비율 16%p 절감
    결과: 목표 지표 달성 후 정식 배포
  - 상담 품질 관리 체계 수립 (2025-10~2026-01)
    담당: QA 평가표 설계
    성과: 1차 해결률 24%p 개선
    결과: 정상 오픈 및 운영 이관 완료

[기술]
CRM, Zendesk, Notion, Excel, SQL, Channel Talk

[자격]
CS리더스관리사, 텔레마케팅관리사
```

### 정답 결측 라벨
```json
[
 {
  "type": "TEMPORAL_GAP",
  "locator": {
   "between": [
    "C1",
    "C2"
   ]
  },
  "gap_months": 4,
  "gap_period": {
   "start": "2019-08",
   "end": "2019-12"
  },
  "gold_answer": "어학 연수"
 },
 {
  "type": "ROLE_OMISSION",
  "locator": {
   "career_id": "C1"
  },
  "gold_answer": {
   "role": "콜센터 QA 담당",
   "department": "개발본부",
   "position": "주임"
  }
 },
 {
  "type": "ROLE_OMISSION",
  "locator": {
   "career_id": "C2"
  },
  "gold_answer": {
   "role": "고객경험(CX) 담당",
   "department": "개발본부",
   "position": "대리"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C1",
   "project_id": "C1-P1"
  },
  "missing_fields": [
   "metrics"
  ],
  "gold_answer": {
   "metrics": [
    {
     "name": "1차 해결률",
     "value": 8,
     "unit": "%p",
     "direction": "up"
    }
   ]
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C2",
   "project_id": "C2-P1"
  },
  "missing_fields": [
   "result"
  ],
  "gold_answer": {
   "result": "고객사 최종 검수 통과"
  }
 }
]
```


---

## 데이터·AI · 경력 — R00170 (데이터·AI)

### 파일 채널
```
임태윤 이력서
희망 직무: 데이터 엔지니어

[학력]
2018-03 ~ 2022-02  가온대학교 컴퓨터공학과 (학사, 학점 3.56)
2023-03 ~ 2025-02  청람대학교 컴퓨터공학과 대학원 (석사, 학점 3.25)
    연구 주제: (미기재)

[경력]
2025-12 ~ 2026-08  한국직업능력연구원 (공공기관) / BI 분석가 과장
  - 금융 대시보드 구축 (2026-01~2026-08)
    담당: 지표 정의
    결과: 고객사 최종 검수 통과

[대외활동]
2018-11 ~ 2020-08  [학생자치] 컴퓨터공학과 학생회 / 홍보부장
    성과: 임기 완수
2019-03 ~ 2019-09  [공모전] 봉사 아이디어 공모전 / 개발 담당
    성과: 최우수상 수상

[기술]
AWS, Tableau, Docker, PyTorch, SQL, Kubernetes

[자격]
ADsP, 정보처리기사, 빅데이터분석기사
```

### 정답 결측 라벨
```json
[
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C1",
   "project_id": "C1-P1"
  },
  "missing_fields": [
   "metrics"
  ],
  "gold_answer": {
   "metrics": [
    {
     "name": "모델 정확도",
     "value": 5,
     "unit": "%p",
     "direction": "up"
    },
    {
     "name": "데이터 처리 시간",
     "value": 34,
     "unit": "%",
     "direction": "down"
    }
   ]
  }
 },
 {
  "type": "THESIS_OMISSION",
  "locator": {
   "degree": "석사",
   "school": "청람대학교"
  },
  "gold_answer": "시계열 이상탐지를 위한 준지도 학습 기법"
 }
]
```


---

## 인사·총무 · 경력 — R00343 (인사·총무)

### 파일 채널
```
윤태윤 이력서
희망 직무: 총무 담당

[학력]
2007-03 ~ 2011-02  서원대학교 행정학과 (학사, 학점 3.35)

[경력]
2012-07 ~ 2014-09  터닝웍스 주식회사 (중견기업)
  - 조직문화 개선 프로젝트 (2013-06~2014-02)
    담당: 개선 과제 실행
    성과: 급여 처리 오류 건수 17건 절감, 채용 소요 기간 18% 절감
    결과: 정상 오픈 및 운영 이관 완료
2015-06 ~ 2016-09  인디고테크 주식회사 (스타트업) / 노무 담당 대리
  - 인사평가 제도 개편 (2016-05~2016-09)
    담당: 제도 설명회 운영
    성과: 채용 확정 인원 60명 향상
    결과: 정상 오픈 및 운영 이관 완료
2016-09 ~ 2019-03  링크인더스트리 (중소기업) / 노무 담당 사원
  - 근태·급여 시스템 도입 (2017-02~2018-04)
    담당: 요구사항 정의
    성과: 채용 확정 인원 57명 향상
    결과: 정상 오픈 및 운영 이관 완료
2019-03 ~ 2020-11  루미인더스트리 주식회사 (대기업) / 인사 담당 사원
  - 인사평가 제도 개편 (2020-02~2020-10)
    담당: 제도 설명회 운영
    성과: 채용 소요 기간 19% 절감
    결과: 정상 오픈 및 운영 이관 완료
  - 인사평가 제도 개편 (2019-12~2020-05)
    성과: 신입 조기 퇴사율 10%p 절감, 채용 확정 인원 15명 향상
    결과: 사내 표준 프로세스로 채택
  - 근태·급여 시스템 도입 (2019-09~2020-01)
    담당: 데이터 이관
    성과: 급여 처리 오류 건수 17건 절감
    결과: 고객사 최종 검수 통과
2020-12 ~ 2022-10  온새커머스 (중소기업) / 채용 담당 주임
  - 신규 채용 프로세스 개선 (2022-04~2022-09)
  - 신규 채용 프로세스 개선 (2021-07~2022-07)
    담당: 면접 가이드 제작
    성과: 교육 만족도 3점 향상
    결과: 목표 지표 달성 후 정식 배포
2022-10 ~ 2025-01  퀀텀웍스 주식회사 (스타트업) / HRD 담당 주임
  - 조직문화 개선 프로젝트 (2023-07~2024-03)
2025-01 ~ 2026-09  밸런인더스트리 (중견기업) / 채용 담당 사원
  - 신규 채용 프로세스 개선 (2026-03~2026-06)
    담당: 채용 프로세스 재설계
    결과: 전사 확대 적용

[기타 활동]
2014-09 ~ 2015-06  이직 준비 및 구직 활동

[대외활동]
2010-08 ~ 2010-12  [공모전] 전국 대학생 금융 경진대회 / 팀장
2010-07 ~ 2010-09  [인턴] 하계 인턴십 / 인턴
2010-03 ~ 2010-10  [교육과정] 봉사 아카데미 수료

[어학]
OPIc AL

[기술]
Excel, SAP HR, Notion, 더존, Google Workspace, 노동법 실무

[자격]
인사관리사
```

### 정답 결측 라벨
```json
[
 {
  "type": "ROLE_OMISSION",
  "locator": {
   "career_id": "C1"
  },
  "gold_answer": {
   "role": "총무 담당",
   "department": "고객지원팀",
   "position": "주임"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C4",
   "project_id": "C4-P2"
  },
  "missing_fields": [
   "role"
  ],
  "gold_answer": {
   "role": "제도 설명회 운영"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C5",
   "project_id": "C5-P1"
  },
  "missing_fields": [
   "metrics",
   "result",
   "role"
  ],
  "gold_answer": {
   "metrics": [
    {
     "name": "급여 처리 오류 건수",
     "value": 19,
     "unit": "건",
     "direction": "down"
    }
   ],
   "result": "사내 표준 프로세스로 채택",
   "role": "면접 가이드 제작"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C6",
   "project_id": "C6-P1"
  },
  "missing_fields": [
   "metrics",
   "result",
   "role"
  ],
  "gold_answer": {
   "metrics": [
    {
     "name": "교육 만족도",
     "value": 3,
     "unit": "점",
     "direction": "up"
    },
    {
     "name": "급여 처리 오류 건수",
     "value": 20,
     "unit": "건",
     "direction": "down"
    }
   ],
   "result": "전사 확대 적용",
   "role": "설문 설계"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "C7",
   "project_id": "C7-P1"
  },
  "missing_fields": [
   "metrics"
  ],
  "gold_answer": {
   "metrics": [
    {
     "name": "교육 만족도",
     "value": 2,
     "unit": "점",
     "direction": "up"
    },
    {
     "name": "채용 소요 기간",
     "value": 13,
     "unit": "%",
     "direction": "down"
    }
   ]
  }
 },
 {
  "type": "EXTRACURRICULAR_OMISSION",
  "locator": {
   "activity_id": "E1",
   "name": "전국 대학생 금융 경진대회"
  },
  "missing_fields": [
   "result"
  ],
  "gold_answer": {
   "result": "최우수상 수상"
  }
 },
 {
  "type": "EXTRACURRICULAR_OMISSION",
  "locator": {
   "activity_id": "E2",
   "name": "하계 인턴십"
  },
  "missing_fields": [
   "result"
  ],
  "gold_answer": {
   "result": "우수 인턴 선정"
  }
 },
 {
  "type": "EXTRACURRICULAR_OMISSION",
  "locator": {
   "activity_id": "E3",
   "name": "봉사 아카데미 수료"
  },
  "missing_fields": [
   "result",
   "role"
  ],
  "gold_answer": {
   "result": "우수 수료자 선정",
   "role": "프로젝트 팀장"
  }
 }
]
```


---

## 대졸 신입 — R00100 (디자인)

### 파일 채널
```
권혜원 이력서
희망 직무: UI/UX 디자이너

[학력]
2021-03 ~ 2025-02  이현대학교 예술학과 (학사, 학점 3.25)

[경력]
  해당 없음 (신입)

[프로젝트]
2024-06 ~ 2024-08  여행 브랜드 리디자인 습작
    담당: 로고·컬러 시스템 설계
    성과: 클릭률(CTR) 4%p 개선, 화면 이탈률 6%p 절감
    결과: 보고서 제출

[대외활동]
2023-12 ~ 2025-03  [봉사] IT 교육 재능기부 / 봉사단원
    성과: 정기 활동 완료
2023-08 ~ 2025-03  [학생자치] 단과대학 학생회 / 기획국장
    성과: 임기 완수
2022-09 ~ 2024-01  [동아리] 디자인 소모임 / 스터디 리더

[어학]
HSK 3급

[기술]
After Effects, Sketch, Adobe XD, Photoshop, Premiere Pro, Blender

[자격]
제품디자인기사, 웹디자인기능사, GTQ 1급
```

### 정답 결측 라벨
```json
[
 {
  "type": "POST_GRAD_GAP",
  "locator": {
   "between": [
    "EDU",
    "NOW"
   ]
  },
  "gap_months": 19,
  "gap_period": {
   "start": "2025-02",
   "end": "2026-09"
  },
  "gold_answer": "구직 활동"
 },
 {
  "type": "EXTRACURRICULAR_OMISSION",
  "locator": {
   "activity_id": "E3",
   "name": "디자인 소모임"
  },
  "missing_fields": [
   "result"
  ],
  "gold_answer": {
   "result": "정기 발표회 참가"
  }
 }
]
```


---

## 고졸 신입 — R00380 (회계·재무)

### 파일 채널
```
김지훈 이력서
희망 직무: 재무 담당

[학력]
2023-03 ~ 2026-02  백양고등학교 자연계열 (고졸·일반고, 학점 2.97)

[경력]
  해당 없음 (신입)

[기타 활동]
2026-02 ~ 2026-09  직무 전환을 위한 국비 교육과정 수강

[프로젝트]
2025-01 ~ 2025-04  교내 동아리 회계 관리
    담당: 예산 편성 및 결산
2024-09 ~ 2025-04  모의 재무제표 분석 과제
    담당: 재무비율 분석

[대외활동]
2024-11 ~ 2025-04  [대회] 데이터 분석 교내 경진대회 / 팀장
2024-02 ~ 2024-11  [동아리] 교내 전기 동아리 / 부장
2024-04 ~ 2025-08  [동아리] 금융 자율동아리 / 팀장
    성과: 운영진 활동

[기술]
SAP FI, Power BI, K-IFRS, Excel, ERP

[자격]
재경관리사, FAT 1급
```

### 정답 결측 라벨
```json
[
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "PERSONAL",
   "project_id": "PP1"
  },
  "missing_fields": [
   "metrics",
   "result"
  ],
  "gold_answer": {
   "metrics": [
    {
     "name": "운영비",
     "value": 3,
     "unit": "%",
     "direction": "down"
    }
   ],
   "result": "발표 및 시연 완료"
  }
 },
 {
  "type": "ACHIEVEMENT_OMISSION",
  "locator": {
   "career_id": "PERSONAL",
   "project_id": "PP2"
  },
  "missing_fields": [
   "result",
   "metrics"
  ],
  "gold_answer": {
   "result": "보고서 제출",
   "metrics": [
    {
     "name": "리포팅 공수",
     "value": 14,
     "unit": "시간",
     "direction": "down"
    }
   ]
  }
 },
 {
  "type": "EXTRACURRICULAR_OMISSION",
  "locator": {
   "activity_id": "E1",
   "name": "데이터 분석 교내 경진대회"
  },
  "missing_fields": [
   "result"
  ],
  "gold_answer": {
   "result": "입상"
  }
 },
 {
  "type": "EXTRACURRICULAR_OMISSION",
  "locator": {
   "activity_id": "E2",
   "name": "교내 전기 동아리"
  },
  "missing_fields": [
   "result"
  ],
  "gold_answer": {
   "result": "운영진 활동"
  }
 }
]
```


---

## 석사 신입 — R00153 (생산·품질)

### 파일 채널
```
류지우 이력서
희망 직무: 생산관리 담당

[학력]
2020-03 ~ 2024-02  동림대학교 화학공학과 (학사, 학점 3.06)
2024-03 ~ 2026-02  소로대학교 화학공학과 대학원 (석사, 학점 3.39)
    연구 주제: 설비 진동 데이터 기반 고장 예지

[경력]
  해당 없음 (신입)

[기타 활동]
2026-02 ~ 2026-09  학원 수강 및 취업 준비

[대외활동]
2023-08 ~ 2023-12  [교육과정] 국비지원 AI 부트캠프 / 교육생
    성과: 우수 수료자 선정
2023-09 ~ 2023-12  [인턴] 체험형 인턴

[어학]
OPIc IL, JLPT 3급

[기술]
AutoCAD, SPC, Excel, MES, ISO 9001, 6시그마

[자격]
6시그마 GB, 품질경영기사, 산업안전기사
```

### 정답 결측 라벨
```json
[
 {
  "type": "EXTRACURRICULAR_OMISSION",
  "locator": {
   "activity_id": "E2",
   "name": "체험형 인턴"
  },
  "missing_fields": [
   "result",
   "role"
  ],
  "gold_answer": {
   "result": "최종 결과보고 발표",
   "role": "인턴"
  }
 }
]
```
