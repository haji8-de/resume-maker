const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
} = require("docx");

const IN = process.argv[2] || "sample_record.json";
const OUT = process.argv[3] || "이력서_자동생성_예시.docx";
const rec = JSON.parse(fs.readFileSync(IN, "utf-8"));
const G = rec.gold, O = rec.observed, M = rec.missingness;

const W = 9360;                      // 본문 폭(DXA)
const NAVY = "1F3864", GREY = "666666", RED = "B03A2E", GREEN = "1E7A4C";

const P = (text, o = {}) => new Paragraph({
  spacing: { before: o.before ?? 0, after: o.after ?? 60 },
  alignment: o.align,
  indent: o.indent ? { left: o.indent } : undefined,
  children: [new TextRun({
    text, bold: o.bold, italics: o.italics, size: o.size ?? 20,
    color: o.color, font: "맑은 고딕",
  })],
});

const Runs = (parts, o = {}) => new Paragraph({
  spacing: { before: o.before ?? 0, after: o.after ?? 60 },
  indent: o.indent ? { left: o.indent } : undefined,
  children: parts.map(p => new TextRun({
    text: p.t, bold: p.b, italics: p.i, color: p.c, size: p.s ?? 20, font: "맑은 고딕",
  })),
});

const H1 = (t, brk = false) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  pageBreakBefore: brk,
  spacing: { before: 320, after: 160 },
  children: [new TextRun({ text: t, bold: true, size: 28, color: NAVY, font: "맑은 고딕" })],
});

const SectionBar = (t) => new Paragraph({
  spacing: { before: 260, after: 120 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: NAVY, space: 4 } },
  children: [new TextRun({ text: t, bold: true, size: 22, color: NAVY, font: "맑은 고딕" })],
});

const MISSING = (label) => new TextRun({
  text: `〔${label} 미기재〕`, bold: true, color: RED, size: 20, font: "맑은 고딕",
});

// 실제 주입된 결측 라벨만 문서에 표시한다 (원래부터 없던 값은 결측이 아님)
const MISSKEY = new Set();
for (const lb of M) {
  const L = lb.locator;
  if (lb.type === "ROLE_OMISSION") MISSKEY.add(`role:${L.career_id}`);
  if (lb.type === "ACHIEVEMENT_OMISSION")
    for (const f of lb.missing_fields) MISSKEY.add(`proj:${L.project_id}:${f}`);
  if (lb.type === "EXTRACURRICULAR_OMISSION")
    for (const f of lb.missing_fields) MISSKEY.add(`act:${L.activity_id}:${f}`);
  if (lb.type === "THESIS_OMISSION") MISSKEY.add(`thesis:${L.degree}`);
}
const isMissing = (k) => MISSKEY.has(k);

// 받침 유무에 따른 목적격 조사
const eul = (w) => {
  const ch = w.charCodeAt(w.length - 1);
  if (ch < 0xac00 || ch > 0xd7a3) return "를";
  return (ch - 0xac00) % 28 === 0 ? "를" : "을";
};
const joinKo = (arr) => arr.join(", ") + eul(arr[arr.length - 1]);
// 받침에 따른 부사격 조사 (로 / 으로)
const ro = (w) => {
  const ch = w.charCodeAt(w.length - 1);
  if (ch < 0xac00 || ch > 0xd7a3) return "으로";
  const jong = (ch - 0xac00) % 28;
  return (jong === 0 || jong === 8) ? "로" : "으로";
};

const metricText = (m) => {
  const up = m.direction === "up";
  const pct = m.unit === "%" || m.unit === "%p";
  const dir = pct ? (up ? "개선" : "절감") : (up ? "증가" : "감소");
  return `${m.name} ${m.value}${m.unit} ${dir}`;
};

// ---------------------------------------------------------------- 이력서 본문
function resumeBody(r, { markMissing }) {
  const out = [];

  out.push(new Paragraph({
    spacing: { after: 40 },
    children: [new TextRun({ text: r.profile.name, bold: true, size: 36, color: NAVY, font: "맑은 고딕" })],
  }));
  out.push(P(`${r.profile.target_job} 지원`, { color: GREY, size: 20, after: 40 }));
  out.push(P(`${r.profile.email}  |  ${r.profile.phone}`, { color: GREY, size: 18, after: 200 }));

  // 학력
  out.push(SectionBar("학력"));
  for (const e of r.education) {
    out.push(Runs([
      { t: `${e.period.start} ~ ${e.period.end}   `, c: GREY },
      { t: `${e.school} ${e.major}`, b: true },
      { t: `  (${e.degree}, 학점 ${e.gpa})`, c: GREY },
    ]));
    if (e.thesis) {
      if (e.research_topic) {
        out.push(P(`연구 주제: ${e.research_topic}`, { indent: 360, color: "333333" }));
      } else if (markMissing && isMissing(`thesis:${e.degree}`)) {
        out.push(new Paragraph({
          indent: { left: 360 }, spacing: { after: 60 },
          children: [new TextRun({ text: "연구 주제: ", size: 20, font: "맑은 고딕" }), MISSING("학위논문 주제")],
        }));
      }
    }
  }

  // 경력
  out.push(SectionBar("경력"));
  for (const c of r.careers) {
    const head = [
      { t: `${c.period.start} ~ ${c.period.end}   `, c: GREY },
      { t: c.company, b: true },
      { t: `  (${c.company_scale})`, c: GREY },
    ];
    out.push(new Paragraph({
      spacing: { before: 100, after: 40 },
      children: head.map(p => new TextRun({ text: p.t, bold: p.b, color: p.c, size: 20, font: "맑은 고딕" }))
        .concat(c.role
          ? [new TextRun({ text: `  ${c.role} ${c.position || ""}`, size: 20, font: "맑은 고딕" })]
          : (markMissing && isMissing(`role:${c.career_id}`) ? [MISSING("직무")] : [])),
    }));
    for (const p of c.projects) {
      out.push(P(`▪ ${p.name}  (${p.period.start}~${p.period.end})`, { indent: 280, after: 30 }));
      if (p.role) out.push(P(`담당  ${p.role}`, { indent: 560, color: "333333", after: 20 }));
      else if (markMissing && isMissing(`proj:${p.project_id}:role`)) out.push(new Paragraph({
        indent: { left: 560 }, spacing: { after: 20 },
        children: [new TextRun({ text: "담당  ", size: 20, font: "맑은 고딕" }), MISSING("담당 역할")],
      }));
      if (p.metrics && p.metrics.length) {
        out.push(P(`성과  ${p.metrics.map(metricText).join(", ")}`, { indent: 560, color: GREEN, after: 20 }));
      } else if (markMissing && isMissing(`proj:${p.project_id}:metrics`)) out.push(new Paragraph({
        indent: { left: 560 }, spacing: { after: 20 },
        children: [new TextRun({ text: "성과  ", size: 20, font: "맑은 고딕" }), MISSING("정량 성과")],
      }));
      if (p.result) out.push(P(`결과  ${p.result}`, { indent: 560, color: "333333", after: 60 }));
      else if (markMissing && isMissing(`proj:${p.project_id}:result`)) out.push(new Paragraph({
        indent: { left: 560 }, spacing: { after: 60 },
        children: [new TextRun({ text: "결과  ", size: 20, font: "맑은 고딕" }), MISSING("수행 결과")],
      }));
    }
  }

  // 대외활동
  if (r.extracurricular && r.extracurricular.length) {
    out.push(SectionBar("대외활동"));
    for (const a of r.extracurricular) {
      out.push(new Paragraph({
        spacing: { before: 60, after: 30 },
        children: [
          new TextRun({ text: `${a.period.start} ~ ${a.period.end}   `, color: GREY, size: 20, font: "맑은 고딕" }),
          new TextRun({ text: `[${a.category}] ${a.name}`, bold: true, size: 20, font: "맑은 고딕" }),
        ].concat(a.role
          ? [new TextRun({ text: `  ${a.role}`, size: 20, font: "맑은 고딕" })]
          : (markMissing && isMissing(`act:${a.activity_id}:role`) ? [MISSING("역할")] : [])),
      }));
      if (a.result) out.push(P(`성과  ${a.result}`, { indent: 560, color: GREEN, after: 30 }));
      else if (markMissing && isMissing(`act:${a.activity_id}:result`)) out.push(new Paragraph({
        indent: { left: 560 }, spacing: { after: 30 },
        children: [new TextRun({ text: "성과  ", size: 20, font: "맑은 고딕" }), MISSING("활동 성과")],
      }));
    }
  }

  // 해외 경험
  if (r.overseas && r.overseas.length) {
    out.push(SectionBar("해외 경험"));
    for (const o of r.overseas) {
      out.push(Runs([
        { t: `${o.period.start} ~ ${o.period.end}   `, c: GREY },
        { t: `${o.country} ${o.kind}`, b: true },
        { t: ` — ${o.detail}` },
      ]));
    }
  }

  // 어학 / 기술 / 자격
  out.push(SectionBar("어학 · 기술 · 자격"));
  if (r.languages && r.languages.length) {
    out.push(P(`어학   ${r.languages.map(x => `${x.test} ${x.score}`).join(", ")}`));
  }
  out.push(P(`기술   ${r.skills.join(", ")}`));
  out.push(P(`자격   ${r.certificates.join(", ")}`));
  return out;
}

// ---------------------------------------------------------------- 결측 리포트
const TYPE_KO = {
  TEMPORAL_GAP: "기간적 공백기",
  ROLE_OMISSION: "직무 정보 누락",
  ACHIEVEMENT_OMISSION: "성과 누락",
  THESIS_OMISSION: "학위 연구주제 누락",
  EXTRACURRICULAR_OMISSION: "대외활동 상세 누락",
  DATE_INCOMPLETE: "기간 정보 불완전",
  POST_GRAD_GAP: "졸업 후 구직 공백",
};
const PRIORITY = {
  ROLE_OMISSION: "높음", TEMPORAL_GAP: "높음", ACHIEVEMENT_OMISSION: "보통",
  THESIS_OMISSION: "보통", EXTRACURRICULAR_OMISSION: "낮음", DATE_INCOMPLETE: "보통",
  POST_GRAD_GAP: "높음",
};
function locatorText(lb) {
  const L = lb.locator;
  if (L.project_id) return `${L.career_id} / ${L.project_id}`;
  if (L.career_id) return L.career_id;
  if (L.activity_id) return `${L.activity_id} — ${L.name}`;
  if (L.degree) return `${L.school} ${L.degree}`;
  if (L.between) return `${L.between[0]} → ${L.between[1]}`;
  return "-";
}
function questionText(lb) {
  switch (lb.type) {
    case "ROLE_OMISSION":
      return "해당 재직 기간에 수행한 직무명과 담당 업무를 입력해 주세요.";
    case "ACHIEVEMENT_OMISSION":
      return `해당 프로젝트의 ${joinKo((lb.missing_fields || []).map(f => ({ role: "담당 역할", metrics: "정량 성과", result: "수행 결과" }[f])))} 입력해 주세요. 가능하면 수치를 함께 적어 주세요.`;
    case "THESIS_OMISSION":
      return "학위 과정에서 수행한 연구 주제 또는 학위논문 제목을 입력해 주세요.";
    case "EXTRACURRICULAR_OMISSION":
      return `해당 활동에서 맡은 ${joinKo((lb.missing_fields || []).map(f => ({ role: "역할", result: "성과" }[f])))} 입력해 주세요.`;
    case "TEMPORAL_GAP":
    case "POST_GRAD_GAP":
      return "해당 공백 기간에 수행한 학업, 근무, 프로젝트 또는 기타 활동을 입력해 주세요.";
    case "DATE_INCOMPLETE":
      return "해당 경력의 정확한 시작 연월과 종료 연월을 입력해 주세요.";
    default:
      return "누락된 정보를 입력해 주세요.";
  }
}

// ---------------------------------------------------------------- 사용자 답변 시뮬레이션
// gold_answer 를 사용자가 대화형 인터페이스에 입력했을 법한 구어체 문장으로 바꾼다.
function userAnswer(lb) {
  const g = lb.gold_answer;
  switch (lb.type) {
    case "ROLE_OMISSION": {
      const bits = [];
      if (g.role) bits.push(`${g.role}${ro(g.role)} 일했습니다`);
      if (g.department) bits.push(`소속은 ${g.department}였고요`);
      if (g.position) bits.push(`직급은 ${g.position}이었습니다`);
      return bits.join(", ") + ".";
    }
    case "ACHIEVEMENT_OMISSION": {
      const s = [];
      if (g.role) s.push(`제가 ${g.role} 맡았습니다.`);
      if (g.metrics && g.metrics.length)
        s.push(g.metrics.map(metricText).join(", ") + " 했습니다.");
      if (g.result) s.push(`최종적으로는 ${g.result}됐어요.`);
      return s.join(" ");
    }
    case "THESIS_OMISSION":
      return `학위논문 주제는 "${g}"였습니다.`;
    case "EXTRACURRICULAR_OMISSION": {
      const bits = [];
      if (g.role) bits.push(`${g.role}${ro(g.role)} 참여했습니다`);
      if (g.result) bits.push(`결과는 ${g.result}였습니다`);
      return bits.join(", ") + ".";
    }
    case "TEMPORAL_GAP":
    case "POST_GRAD_GAP":
      return `그 기간에는 ${g} 했습니다.`;
    case "DATE_INCOMPLETE":
      return `정확히는 ${g.start}부터 ${g.end}까지입니다.`;
    default:
      return "-";
  }
}

// 답변 파싱부(131)가 추출하는 필드 단위 결과
function parsedFields(lb) {
  const g = lb.gold_answer, out = [];
  switch (lb.type) {
    case "ROLE_OMISSION":
      if (g.role) out.push(["직무", g.role]);
      if (g.department) out.push(["부서", g.department]);
      if (g.position) out.push(["직급", g.position]);
      break;
    case "ACHIEVEMENT_OMISSION":
      if (g.role) out.push(["담당 역할", g.role]);
      if (g.metrics) for (const m of g.metrics) out.push(["정량 성과", metricText(m)]);
      if (g.result) out.push(["수행 결과", g.result]);
      break;
    case "THESIS_OMISSION":
      out.push(["연구 주제", g]);
      break;
    case "EXTRACURRICULAR_OMISSION":
      if (g.role) out.push(["활동 역할", g.role]);
      if (g.result) out.push(["활동 성과", g.result]);
      break;
    case "TEMPORAL_GAP":
    case "POST_GRAD_GAP":
      out.push(["공백기 활동", g]);
      break;
    case "DATE_INCOMPLETE":
      out.push(["시작일", g.start]); out.push(["종료일", g.end]);
      break;
  }
  return out;
}

function reportTable() {
  const hdr = ["No", "결측 유형", "위치", "우선순위"];
  const widths = [700, 2100, 4260, 1200];
  const rows = [new TableRow({
    tableHeader: true,
    children: hdr.map((h, i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: "E8EDF5" },
      children: [P(h, { bold: true, size: 18 })],
    })),
  })];
  M.forEach((lb, i) => {
    const cells = [
      String(i + 1), TYPE_KO[lb.type] || lb.type, locatorText(lb), PRIORITY[lb.type] || "보통",
    ];
    rows.push(new TableRow({
      children: cells.map((c, j) => new TableCell({
        width: { size: widths[j], type: WidthType.DXA },
        children: [P(c, { size: 18 })],
      })),
    }));
  });
  return new Table({ columnWidths: widths, rows });
}

// ---------------------------------------------------------------- 문서 조립
const children = [];

children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 60 },
  children: [new TextRun({ text: "이력 결측치 탐색 및 데이터 통합 기반", size: 22, color: GREY, font: "맑은 고딕" })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 80 },
  children: [new TextRun({ text: "상호작용형 이력서 자동 생성 — 동작 예시", bold: true, size: 34, color: NAVY, font: "맑은 고딕" })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 320 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "CCCCCC", space: 6 } },
  children: [new TextRun({
    text: `합성 데이터셋 SynRes-KR · 샘플 ${rec.resume_id} (${rec.domain})`,
    size: 18, color: GREY, font: "맑은 고딕",
  })],
}));

children.push(H1("Ⅰ. 초기 이력서 데이터"));
children.push(P("사용자 입력을 공통 이력서 데이터 형식으로 변환한 결과입니다. 붉은 표시는 시스템이 탐색한 결측 항목입니다.",
  { color: GREY, size: 18, after: 200 }));
children.push(...resumeBody(O, { markMissing: true }));

children.push(H1("Ⅱ. 결측 탐색 결과 및 질의 프롬프트", true));
children.push(P(`총 ${M.length}건의 이력 결측치가 탐색되었습니다.`, { color: GREY, size: 18, after: 160 }));
children.push(reportTable());
children.push(P("", { after: 200 }));
children.push(SectionBar("질의 프롬프트 · 사용자 답변 · 파싱 결과"));
children.push(P("Q는 시스템이 생성한 질의, A는 사용자가 대화형 인터페이스에 입력한 답변, "
  + "추출은 답변 파싱부가 이력 항목별 필드로 분해한 결과입니다.",
  { color: GREY, size: 17, after: 120 }));
M.forEach((lb, i) => {
  children.push(Runs([
    { t: `Q${i + 1}. `, b: true, c: NAVY },
    { t: questionText(lb) },
  ], { before: 160, after: 20 }));
  children.push(P(`대상  ${locatorText(lb)}  ·  ${TYPE_KO[lb.type]}`,
    { indent: 360, color: GREY, size: 17, after: 50 }));
  children.push(Runs([
    { t: `A${i + 1}. `, b: true, c: GREEN },
    { t: userAnswer(lb), i: true },
  ], { indent: 360, after: 30 }));
  const fields = parsedFields(lb);
  if (fields.length) {
    children.push(P(
      "추출  " + fields.map(([k, v]) => `${k}: ${v}`).join("   |   "),
      { indent: 360, color: "555555", size: 17, after: 40 }));
  }
});

children.push(H1("Ⅲ. 보완 후 최종 이력서", true));
children.push(P("질의 프롬프트에 대한 사용자 답변을 병합하여 결측이 해소된 상태입니다.",
  { color: GREY, size: 18, after: 200 }));
children.push(...resumeBody(G, { markMissing: false }));

const doc = new Document({
  styles: { default: { document: { run: { font: "맑은 고딕", size: 20 } } } },
  sections: [{
    properties: { page: { margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
    children,
  }],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync(OUT, b);
  console.log("작성 완료");
});
