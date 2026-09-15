import React, { useEffect, useState } from 'react'
import {
  createSession, nextQuestion, sendAnswer, getPreview, confirmResume,
} from './api.js'

/* ------------------------------------------------------------------ 공통 */
function Progress({ p }) {
  if (!p) return null
  const pct = Math.round(p.ratio * 100)
  return (
    <div className="progress">
      <div className="bar"><div className="fill" style={{ width: `${pct}%` }} /></div>
      <span className="pct">
        {p.answered} / {p.total} 보완 · 남은 질문 {p.remaining}개
      </span>
    </div>
  )
}

/* 미리보기에서 아직 비어 있는 항목은 회색 표시로 남겨 사용자가 확인할 수 있게 한다 */
function Slot({ value }) {
  if (value && typeof value === 'object' && value.missing) {
    return <span className="missing">{value.missing} 미기재</span>
  }
  return <>{value}</>
}

/* ------------------------------------------------- 화면 1: 질의 · 응답 (120→130) */
function AskScreen({ sid, onDone, progress, setProgress }) {
  const [q, setQ] = useState(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [last, setLast] = useState(null)
  const [err, setErr] = useState(null)

  const load = async () => {
    try {
      const d = await nextQuestion(sid)
      setProgress(d.progress)
      if (!d.questions.length) { onDone(); return }
      setQ(d.questions[0]); setText('')
    } catch (e) { setErr(String(e)) }
  }

  useEffect(() => { load() }, [sid])

  const submit = async () => {
    if (!text.trim() || busy) return
    setBusy(true); setErr(null)
    try {
      const d = await sendAnswer(sid, q.key, text)
      setLast({ question: q, parsed: d.parsed, ok: d.ok })
      setProgress(d.progress)
      await load()
    } catch (e) { setErr(String(e)) } finally { setBusy(false) }
  }

  if (err) return <div className="error">오류: {err}</div>
  if (!q) return <div className="muted">질문을 불러오는 중…</div>

  return (
    <div className="ask">
      <Progress p={progress} />

      <div className="qcard">
        <div className="qmeta">
          <span className="tag">{q.type_ko}</span>
          <span className="gain">회복 가중치 {q.gain}</span>
        </div>
        <p className="qtext">{q.text}</p>
        <textarea
          value={text} rows={4} autoFocus
          placeholder="편하게 말하듯 적어주세요. 정해진 형식은 없습니다."
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit()
          }}
        />
        <div className="row">
          <span className="hint">⌘/Ctrl + Enter 로 제출</span>
          <div>
            <button className="ghost" onClick={load} disabled={busy}>건너뛰기</button>
            <button className="primary" onClick={submit} disabled={busy || !text.trim()}>
              {busy ? '처리 중…' : '답변 제출'}
            </button>
          </div>
        </div>
      </div>

      {last && (
        <div className="parsed">
          <div className="plabel">직전 답변에서 추출한 항목</div>
          {Object.keys(last.parsed || {}).length === 0
            ? <div className="muted">추출된 필드가 없습니다. 조금 더 구체적으로 적어주세요.</div>
            : <ul>
                {Object.entries(last.parsed).map(([k, v]) => (
                  <li key={k}>
                    <b>{k}</b>
                    <span>{typeof v === 'object' ? JSON.stringify(v, null, 0) : String(v)}</span>
                  </li>
                ))}
              </ul>}
        </div>
      )}

      <button className="link" onClick={onDone}>남은 질문 건너뛰고 미리보기 →</button>
    </div>
  )
}

/* ------------------------------------------- 화면 2: 미리보기 · 확정 (136/137) */
function PreviewScreen({ sid, onBack }) {
  const [data, setData] = useState(null)
  const [confirmed, setConfirmed] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getPreview(sid).then(setData).catch(() => {})
  }, [sid])

  const doConfirm = async () => {
    setBusy(true)
    try { setConfirmed(await confirmResume(sid)) } finally { setBusy(false) }
  }

  if (!data) return <div className="muted">미리보기를 준비하는 중…</div>
  const { preview, progress } = data
  const remaining = progress.remaining

  return (
    <div className="preview">
      <Progress p={progress} />

      {confirmed ? (
        <div className="confirmed">
          확정되었습니다 · {new Date(confirmed.confirmed_at).toLocaleString('ko-KR')}
        </div>
      ) : remaining > 0 && (
        <div className="warn">
          아직 {remaining}개 항목이 비어 있습니다. 이대로 확정하면 비어 있는 채로 남습니다.
        </div>
      )}

      <div className="sheet">
        <h2>{preview.profile?.name || '이력서'}</h2>
        {preview.profile?.target_job && <p className="sub">{preview.profile.target_job} 지원</p>}

        {preview.sections.map((sec) => (
          <section key={sec.name}>
            <h3>{sec.name}</h3>
            {sec.items.map((it, i) => (
              <div className="item" key={i}>
                <div className="head">
                  {it.period && <span className="period">{it.period}</span>}
                  {it.title && <b>{it.title}</b>}
                  {it.meta && <span className="meta"><Slot value={it.meta} /></span>}
                </div>
                {it.lines.map((l, j) => (
                  <div className="line" key={j}>· <Slot value={l} /></div>
                ))}
              </div>
            ))}
          </section>
        ))}
      </div>

      <div className="actions">
        <button className="ghost" onClick={onBack} disabled={!!confirmed}>
          질문으로 돌아가기
        </button>
        <button className="primary" onClick={doConfirm} disabled={busy || !!confirmed}>
          {confirmed ? '확정 완료' : busy ? '확정하는 중…' : '이 내용으로 확정'}
        </button>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ 앱 */
export default function App() {
  const [sid, setSid] = useState(null)
  const [screen, setScreen] = useState('ask')
  const [progress, setProgress] = useState(null)
  const [source, setSource] = useState('')
  const [text, setText] = useState('')
  const [err, setErr] = useState(null)

  const start = async (body) => {
    setErr(null)
    try {
      const d = await createSession(body)
      setSid(d.session_id); setSource(d.source)
      setProgress(d.progress); setScreen('ask')
    } catch (e) { setErr(String(e)) }
  }

  if (!sid) {
    return (
      <div className="wrap start">
        <h1>상호작용형 이력서 자동 생성</h1>
        <p className="lead">
          이력서에서 빠진 정보를 찾아 질문하고, 답변을 항목으로 분해해 다시 채워 넣습니다.
        </p>
        {err && <div className="error">{err}</div>}
        <button className="primary big" onClick={() => start({ mode: 'sample' })}>
          샘플 이력서로 시작
        </button>
        <div className="or">또는 이력서 본문을 붙여넣기</div>
        <textarea
          rows={8} value={text} onChange={(e) => setText(e.target.value)}
          placeholder={'[학력]\n2019-03 ~ 2023-02  OO대학교 ...\n\n[경력]\n2023-03 ~ 2026-09  OO회사 ...'}
        />
        <button className="ghost" disabled={!text.trim()}
                onClick={() => start({ mode: 'document', text })}>
          이 내용으로 시작
        </button>
      </div>
    )
  }

  return (
    <div className="wrap">
      <header>
        <h1>상호작용형 이력서 자동 생성</h1>
        <div className="tabs">
          <button className={screen === 'ask' ? 'on' : ''} onClick={() => setScreen('ask')}>
            질의 · 응답
          </button>
          <button className={screen === 'preview' ? 'on' : ''}
                  onClick={() => setScreen('preview')}>
            미리보기 · 확정
          </button>
        </div>
        <div className="sid">{source}</div>
      </header>

      {screen === 'ask'
        ? <AskScreen sid={sid} progress={progress} setProgress={setProgress}
                     onDone={() => setScreen('preview')} />
        : <PreviewScreen sid={sid} onBack={() => setScreen('ask')} />}
    </div>
  )
}
