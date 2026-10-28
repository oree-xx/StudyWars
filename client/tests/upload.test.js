import { test } from 'node:test'
import assert from 'node:assert/strict'
import { generateQuestions } from '../src/lib/api.js'
import { MAX_PDF_BYTES, pdfUploadError } from '../src/lib/upload.js'

test('oversized PDFs are rejected before any upload starts', async (context) => {
  const fetch = context.mock.method(globalThis, 'fetch', () => {
    throw new Error('Oversized PDFs must not reach the network')
  })
  const file = new File([new Uint8Array(MAX_PDF_BYTES + 1)], 'notes.pdf', { type: 'application/pdf' })
  assert.match(pdfUploadError(file), /4 MiB/)
  await assert.rejects(generateQuestions({ file }), /4 MiB/)
  assert.equal(fetch.mock.callCount(), 0)
})

test('a PDF at the cap fits within the platform limit including multipart overhead', async (context) => {
  const file = new File([new Uint8Array(MAX_PDF_BYTES)], 'lecture-notes.pdf', { type: 'application/pdf' })
  const questions = [{ question: 'Example question' }]
  context.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/generate-questions')
    assert.equal(options.body.get('file').size, MAX_PDF_BYTES)
    assert.equal(options.body.get('num_questions'), '5')
    const request = new Request('https://studywars.example/api/generate-questions', options)
    assert.ok((await request.arrayBuffer()).byteLength < 4_500_000)
    return Response.json({ questions })
  })
  assert.equal(pdfUploadError(file), '')
  assert.deepEqual(await generateQuestions({ file }), questions)
})

test('pasted notes remain usable without a PDF', async (context) => {
  context.mock.method(globalThis, 'fetch', async (_url, options) => {
    assert.equal(options.body.get('file'), null)
    assert.equal(options.body.get('notes'), 'Study notes')
    return Response.json({ questions: [] })
  })
  assert.equal(pdfUploadError(null), '')
  assert.deepEqual(await generateQuestions({ notes: 'Study notes' }), [])
})
