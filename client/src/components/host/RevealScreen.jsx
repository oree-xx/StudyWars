import Leaderboard from '../Leaderboard'
import { OPTION_COLORS } from '../../lib/optionColors'

function RevealScreen({ question, reveal, isLastQuestion, onNext }) {
  const correctText = question?.options?.[reveal.correct_index]

  return (
    <div className="mt-6 space-y-8">
      <div className="text-center space-y-2">
        <p className="text-emerald-400 font-semibold">Correct Answer</p>
        {correctText && (
          <p
            className={`${OPTION_COLORS[reveal.correct_index]} inline-block rounded-lg px-4 py-2 font-semibold`}
          >
            {correctText}
          </p>
        )}
        <p className="text-slate-400">{reveal.explanation}</p>
      </div>

      <Leaderboard players={reveal.leaderboard} />

      <button
        type="button"
        onClick={onNext}
        className="w-full bg-indigo-500 hover:bg-indigo-400 rounded-xl px-6 py-4 font-semibold text-lg transition-colors"
      >
        {isLastQuestion ? 'Show Final Results' : 'Next Question'}
      </button>
    </div>
  )
}

export default RevealScreen
