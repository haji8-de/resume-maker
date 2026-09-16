import React, { useEffect, useState } from 'react'
import {
  listSamples, createSession, getInfo,
  nextQuestion, sendAnswer, getPreview, confirmResume,
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

/* 데이터 형식 변환부(114)가 어느 경로를 탔는지 표시한다.
   llm / rules / corpus 가 눈에 보이지 않으면, 키를 잘못 넣고도 규칙 파서로
   돌고 있다는 사실을 알 수 없다. */
const PATH_LABEL = {
  llm: { text: 'LLM 정규화', cls: 'llm' },
  rules: { text: '규칙 파서', cls: 'rules' },
  corpus: { text: '말뭉치 레코드', cls: 'corpus' },
  failed: { text: '정규화 실패', cls: 'failed' },
  'n/a': { text: '변환 없음', cls: 'corpus' },
}

function NormBadge({ info }) {
  if (!info) return null
  const { normalizer: n, config: c } = info
  const l = PATH_LABEL[n.path] || { text: n.path, cls: 'rules' }
  const title = [
    `설정 모드: ${c.mode}`,
    `모델: ${c.model}`,
    `API 키: ${c.api_key ? '설정됨' : '없음'}`,
    n.reason ? `사유: ${n.reason}` : null,
    n.elapsed != null ? `소요: ${n.elapsed}초` : null,
  ].filter(Boolean).join('\n')
  return (
    <span className={`normbadge ${l.cls}`} title={title}>
      <b>{l.text}</b>
      <span className="mode">mode={c.mode}{c.api_key ? '' : ' · 키 없음'}</span>
    </span>
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
function SourcePanel({ info }) {
  const [open, setOpen] = useState(false)
  if (!info?.document) return null
  return (
    <div className="source">
      <button className="srchead" onClick={() => setOpen(!open)}>
        <span>{open ? '▾' : '▸'} 지금 보완 중인 이력서</span>
        <NormBadge info={info} />
      </button>
      {open && <pre className="srcbody">{info.document}</pre>}
    </div>
  )
}

function AskScreen({ sid, onDone, progress, setProgress, info, reloadInfo }) {
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
      reloadInfo && reloadInfo()
    } catch (e) { setErr(String(e)) } finally { setBusy(false) }
  }

  if (err) return <div className="error">오류: {err}</div>
  if (!q) return <div className="muted">질문을 불러오는 중…</div>

  return (
    <div className="ask">
      <SourcePanel info={info} />
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

/* -------------------------------------------- 시작 화면: 샘플을 보고 고른다 */
function StartScreen({ onStart, err }) {
  const [samples, setSamples] = useState(null)
  const [picked, setPicked] = useState(null)
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadErr, setLoadErr] = useState(null)

  const draw = async () => {
    setLoading(true); setLoadErr(null); setPicked(null)
    try { setSamples((await listSamples(3)).samples) }
    catch (e) { setLoadErr(String(e)) }
    finally { setLoading(false) }
  }

  useEffect(() => { draw() }, [])

  return (
    <div className="wrap start">
      <h1>상호작용형 이력서 자동 생성</h1>
      <p className="lead">
        이력서에서 빠진 정보를 찾아 질문하고, 답변을 항목으로 분해해 다시 채워 넣습니다.
      </p>
      {err && <div className="error">{err}</div>}

      <div className="row">
        <h2 className="h2">샘플 이력서 고르기</h2>
        <button className="ghost" onClick={draw} disabled={loading}>
          {loading ? '뽑는 중…' : '다시 뽑기'}
        </button>
      </div>
      {loadErr && <div className="error">{loadErr}</div>}

      <div className="cards">
        {(samples || []).map((s) => (
          <div key={s.resume_id}
               className={`card ${picked === s.resume_id ? 'on' : ''}`}
               onClick={() => setPicked(picked === s.resume_id ? null : s.resume_id)}>
            <div className="chead">
              <b>{s.name || s.resume_id}</b>
              <span className="cid">{s.resume_id}</span>
            </div>
            <div className="cmeta">
              {s.domain} · {s.target_job} · {s.entry_type}
              {s.careers > 0 && ` · 경력 ${s.careers}건`}
            </div>
            <div className="ctags">
              <span className="count">결측 {s.missing_count}건</span>
              {s.missing_types.slice(0, 3).map((t) => (
                <span className="ctag" key={t}>{t}</span>
              ))}
              {s.missing_types.length > 3 && (
                <span className="ctag">외 {s.missing_types.length - 3}종</span>
              )}
            </div>
            <pre className="cdoc">{s.document}</pre>
            <button className="primary wide"
                    onClick={(e) => { e.stopPropagation()
                                      onStart({ mode: 'sample', resume_id: s.resume_id }) }}>
              이 이력서로 시작
            </button>
          </div>
        ))}
      </div>

      <div className="or">또는 이력서 본문을 직접 붙여넣기</div>
      <textarea
        rows={7} value={text} onChange={(e) => setText(e.target.value)}
        placeholder={'[학력]\n2019-03 ~ 2023-02  OO대학교 ...\n\n[경력]\n2023-03 ~ 2026-09  OO회사 ...'}
      />
      <button className="ghost" disabled={!text.trim()}
              onClick={() => onStart({ mode: 'document', text })}>
        이 내용으로 시작
      </button>
      <p className="note">
        붙여넣기로 시작하면 데이터 형식 변환부(114)가 동작합니다. API 키가 설정되어
        있으면 LLM 정규화를, 없으면 규칙 파서를 사용하며 어느 경로를 탔는지 상단에
        표시됩니다.
      </p>
    </div>
  )
}

/* ------------------------------------------------------------------ 앱 */
export default function App() {
  const [sid, setSid] = useState(null)
  const [screen, setScreen] = useState('ask')
  const [progress, setProgress] = useState(null)
  const [source, setSource] = useState('')
  const [info, setInfo] = useState(null)
  const [err, setErr] = useState(null)

  const reloadInfo = async (id) => {
    try { setInfo(await getInfo(id || sid)) } catch { /* 표시용이라 무시 */ }
  }

  const start = async (body) => {
    setErr(null)
    try {
      const d = await createSession(body)
      setSid(d.session_id); setSource(d.source)
      setProgress(d.progress); setScreen('ask')
      reloadInfo(d.session_id)
    } catch (e) { setErr(String(e)) }
  }

  if (!sid) {
    return <StartScreen onStart={start} err={err} />
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
        <div className="sid">
          <span>{source}</span>
          <NormBadge info={info} />
        </div>
      </header>

      {screen === 'ask'
        ? <AskScreen sid={sid} progress={progress} setProgress={setProgress}
                     info={info} reloadInfo={() => reloadInfo()}
                     onDone={() => setScreen('preview')} />
        : <PreviewScreen sid={sid} onBack={() => setScreen('ask')} />}
    </div>
  )
}
