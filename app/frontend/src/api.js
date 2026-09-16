const B = ''

async function call(path, opts) {
  const res = await fetch(B + path, opts)
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json()
}

const json = (body) => ({
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify(body),
})

export const listSamples = (n = 3) => call(`/api/samples?n=${n}&_=${Date.now()}`)
export const createSession = (body) => call('/api/sessions', json(body))
export const getInfo = (id) => call(`/api/sessions/${id}/info`)
export const nextQuestion = (id) => call(`/api/sessions/${id}/next`)
export const suggestAnswers = (id, key, exclude = [], n = 3) =>
  call(`/api/sessions/${id}/suggest`, json({ key, n, exclude }))
export const sendAnswer = (id, key, answer) =>
  call(`/api/sessions/${id}/answer`, json({ key, answer }))
export const getPreview = (id) => call(`/api/sessions/${id}/preview`)
export const confirmResume = (id) => call(`/api/sessions/${id}/confirm`, json({}))
