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

export const createSession = (body) => call('/api/sessions', json(body))
export const nextQuestion = (id) => call(`/api/sessions/${id}/next`)
export const sendAnswer = (id, key, answer) =>
  call(`/api/sessions/${id}/answer`, json({ key, answer }))
export const getPreview = (id) => call(`/api/sessions/${id}/preview`)
export const confirmResume = (id) => call(`/api/sessions/${id}/confirm`, json({}))
