import { OPTION_COLORS } from '../../lib/optionColors'

function AnswerOptions({ question, selectedOption, onAnswer }) {
  const hasAnswered = selectedOption !== null

  return (
    <div className="space-y-6">
      <div className="text-center">
        <p className="text-slate-400">
          Question {question.index + 1} of {question.total}
        </p>
        <h2 className="text-2xl font-bold mt-2">{question.question}</h2>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {question.options.map((opt, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onAnswer(idx)}
            disabled={hasAnswered}
            className={`${OPTION_COLORS[idx]} rounded-xl px-4 py-8 font-semibold text-center transition-opacity disabled:cursor-not-allowed ${
              hasAnswered && selectedOption !== idx ? 'opacity-40' : ''
            }`}
          >
            {opt}
          </button>
        ))}
      </div>

      {hasAnswered && (
        <p className="text-center text-slate-400">Answer locked in — waiting for other players…</p>
      )}
    </div>
  )
}

export default AnswerOptions
