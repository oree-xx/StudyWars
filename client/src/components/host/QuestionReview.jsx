function QuestionReview({ questions, onBack, onCreateRoom, creatingRoom, error }) {
  return (
    <div className="mt-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Review Questions</h1>
        <p className="text-slate-400 mt-2">{questions.length} questions generated. Ready to go live?</p>
      </div>

      <ol className="space-y-4">
        {questions.map((q, i) => (
          <li key={i} className="bg-slate-800 rounded-xl p-4">
            <p className="font-semibold">
              {i + 1}. {q.question}
            </p>
            <ul className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
              {q.options.map((opt, idx) => (
                <li
                  key={idx}
                  className={`rounded-lg px-3 py-2 ${
                    idx === q.correct_index
                      ? 'bg-emerald-600/30 text-emerald-300'
                      : 'bg-slate-700/50 text-slate-300'
                  }`}
                >
                  {opt}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="flex gap-3">
        <button
          type="button"
          onClick={onBack}
          className="flex-1 bg-slate-800 hover:bg-slate-700 rounded-xl px-6 py-4 font-semibold transition-colors"
        >
          Back
        </button>
        <button
          type="button"
          onClick={onCreateRoom}
          disabled={creatingRoom}
          className="flex-1 bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 rounded-xl px-6 py-4 font-semibold transition-colors"
        >
          {creatingRoom ? 'Creating room…' : 'Start Live Game'}
        </button>
      </div>
    </div>
  )
}

export default QuestionReview
