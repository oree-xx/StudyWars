// Thin fetch wrapper for the FastAPI backend. In dev, Vite proxies /api
// straight through to the backend (see vite.config.js), so these paths
// work unchanged in both dev and a same-origin production deployment.

async function readErrorDetail(res) {
  try {
    const data = await res.json()
    return data.detail
  } catch {
    return null
  }
}

/**
 * Generate quiz questions from either a PDF file or pasted notes text.
 * @param {{ file?: File, notes?: string, numQuestions?: number }} input
 * @returns {Promise<Array>} the generated questions
 */
export async function generateQuestions({ file, notes, numQuestions = 5 }) {
  if (!file && !notes) {
    throw new Error('Provide either a PDF file or notes text.')
  }

  const formData = new FormData()
  if (file) formData.append('file', file)
  if (notes) formData.append('notes', notes)
  formData.append('num_questions', String(numQuestions))

  const res = await fetch('/api/generate-questions', {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    throw new Error((await readErrorDetail(res)) || `Failed to generate questions (${res.status})`)
  }

  const data = await res.json()
  return data.questions
}

/**
 * Create a live game room from a set of questions.
 * @param {Array} questions
 * @returns {Promise<{ room_code: string, host_token: string }>}
 */
export async function createRoom(questions) {
  const res = await fetch('/api/rooms', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ questions }),
  })

  if (!res.ok) {
    throw new Error((await readErrorDetail(res)) || `Failed to create room (${res.status})`)
  }

  return res.json()
}
