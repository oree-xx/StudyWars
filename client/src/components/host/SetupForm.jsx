import { useState } from 'react'

const NUM_QUESTIONS_OPTIONS = [3, 5, 8, 10]

function SetupForm({ onGenerate, generating, error }) {
  const [inputMode, setInputMode] = useState('notes') // 'notes' | 'file'
  const [notes, setNotes] = useState('')
  const [file, setFile] = useState(null)
  const [numQuestions, setNumQuestions] = useState(5)

  const canSubmit = inputMode === 'notes' ? notes.trim().length > 0 : !!file

  function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit) return
    onGenerate({
      notes: inputMode === 'notes' ? notes : undefined,
      file: inputMode === 'file' ? file : undefined,
      numQuestions,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="mt-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Host a Quiz</h1>
        <p className="text-slate-400 mt-2">
          Upload a PDF or paste your notes — AI will turn them into a live quiz.
        </p>
      </div>

      <div className="flex gap-2">
        <TabButton active={inputMode === 'notes'} onClick={() => setInputMode('notes')}>
          Paste Notes
        </TabButton>
        <TabButton active={inputMode === 'file'} onClick={() => setInputMode('file')}>
          Upload PDF
        </TabButton>
      </div>

      {inputMode === 'notes' ? (
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Paste your study notes here..."
          rows={10}
          className="w-full rounded-xl bg-slate-800 border border-slate-700 p-4 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      ) : (
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="w-full rounded-xl bg-slate-800 border border-slate-700 p-4 text-white file:mr-4 file:rounded-lg file:border-0 file:bg-indigo-500 file:px-4 file:py-2 file:text-white file:font-medium"
        />
      )}

      <div>
        <label className="block text-sm text-slate-400 mb-2">Number of questions</label>
        <div className="flex gap-2">
          {NUM_QUESTIONS_OPTIONS.map((n) => (
            <button
              type="button"
              key={n}
              onClick={() => setNumQuestions(n)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                numQuestions === n ? 'bg-indigo-500' : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
              }`}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <button
        type="submit"
        disabled={!canSubmit || generating}
        className="w-full bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl px-6 py-4 font-semibold text-lg transition-colors"
      >
        {generating ? 'Generating questions…' : 'Generate Questions'}
      </button>
    </form>
  )
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
        active ? 'bg-indigo-500' : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
      }`}
    >
      {children}
    </button>
  )
}

export default SetupForm
