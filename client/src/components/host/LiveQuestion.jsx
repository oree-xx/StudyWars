import { OPTION_COLORS } from '../../lib/optionColors'

function LiveQuestion({ question, answeredCount, totalPlayers, onRevealNow }) {
  return (
    <div className="mt-6 space-y-8">
      <div className="text-center">
        <p className="text-slate-400">
          Question {question.index + 1} of {question.total}
        </p>
        <h2 className="text-2xl font-bold mt-2">{question.question}</h2>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {question.options.map((opt, idx) => (
          <div key={idx} className={`${OPTION_COLORS[idx]} rounded-xl px-4 py-6 font-semibold text-center`}>
            {opt}
          </div>
        ))}
      </div>

      <div className="text-center space-y-3">
        <p className="text-slate-400">
          {answeredCount} / {totalPlayers} answered
        </p>
        <button
          type="button"
          onClick={onRevealNow}
          className="bg-slate-800 hover:bg-slate-700 rounded-xl px-6 py-3 font-semibold transition-colors"
        >
          Reveal Now
        </button>
      </div>
    </div>
  )
}

export default LiveQuestion
