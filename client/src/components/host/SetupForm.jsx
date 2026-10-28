import { useState } from 'react'
import { pdfUploadError } from '../../lib/upload'

const NUM_QUESTIONS_OPTIONS = [3, 5, 8, 10]

export default function SetupForm({ onGenerate, generating, error }) {
  const [inputMode, setInputMode] = useState('notes')
  const [notes, setNotes] = useState('')
  const [file, setFile] = useState(null)
  const [numQuestions, setNumQuestions] = useState(5)
  const fileError = inputMode === 'file' ? pdfUploadError(file) : ''
  const canSubmit = inputMode === 'notes' ? notes.trim().length > 0 : !!file && !fileError

  function handleSubmit(event) {
    event.preventDefault()
    if (!canSubmit || generating) return
    onGenerate({ notes: inputMode === 'notes' ? notes : undefined, file: inputMode === 'file' ? file : undefined, numQuestions })
  }

  return <>
    <div className="step-strip" aria-label="Quiz setup steps"><span className="active">01 · Add your notes</span><span className="step-line" /><span>02 · Review</span><span className="step-line" /><span>03 · Go live</span></div>
    <div className="page-heading"><p className="eyebrow">You bring the knowledge</p><h1>Let’s build your next battle.</h1></div>
    <form onSubmit={handleSubmit} className="card stack" aria-busy={generating}>
      <div className="segmented" aria-label="Choose your study material">
        <button type="button" aria-pressed={inputMode === 'notes'} onClick={() => setInputMode('notes')} disabled={generating}>≡ Paste notes</button>
        <button type="button" aria-pressed={inputMode === 'file'} onClick={() => setInputMode('file')} disabled={generating}>↑ Upload a PDF</button>
      </div>
      {inputMode === 'notes' ? <div>
        <label htmlFor="study-notes" className="field-label">Your study notes</label>
        <textarea id="study-notes" className="text-input" value={notes} onChange={event => setNotes(event.target.value)} rows={8} placeholder="Start with what you’re learning. Paste your notes here…" disabled={generating} />
        <div className="helper"><span>More context makes better questions.</span><span>{notes.length.toLocaleString()} characters</span></div>
      </div> : <div className="upload-zone">
        <input id="study-pdf" type="file" aria-label="Upload a PDF" aria-describedby="pdf-upload-help" aria-invalid={!!fileError} accept="application/pdf,.pdf" onChange={event => setFile(event.target.files?.[0] ?? null)} disabled={generating} />
        <p id="pdf-upload-help" className="small muted" style={{ marginTop: 12 }}>PDF files up to 4 MiB.</p>
        {file && <p className="small muted" style={{ marginTop: 12, overflowWrap: 'anywhere' }}>{file.name}</p>}
      </div>}
      <fieldset><legend className="field-label">How many questions?</legend><div className="count-pills">{NUM_QUESTIONS_OPTIONS.map(count => <button type="button" key={count} aria-pressed={numQuestions === count} onClick={() => setNumQuestions(count)} disabled={generating}>{count}</button>)}</div><p className="helper">20 seconds per question. Faster correct answers earn more points.</p></fieldset>
      {(fileError || error) && <p className="error-notice" role="alert">{fileError || error}</p>}
      <button type="submit" disabled={!canSubmit || generating} className="btn btn-primary full-width">{generating ? 'Building your questions…' : 'Generate my quiz'}<span aria-hidden="true">{generating ? '↻' : '✦'}</span></button>
      {generating && <p className="muted small centered" role="status">Finding the key ideas in your notes. This can take a moment.</p>}
    </form>
  </>
}
