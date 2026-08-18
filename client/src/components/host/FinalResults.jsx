import Leaderboard from '../Leaderboard'

function FinalResults({ leaderboard, onRestart }) {
  return (
    <div className="mt-6 space-y-8 text-center">
      <h2 className="text-3xl font-bold">🏆 Final Results</h2>
      <Leaderboard players={leaderboard} />
      <button
        type="button"
        onClick={onRestart}
        className="bg-indigo-500 hover:bg-indigo-400 rounded-xl px-6 py-4 font-semibold text-lg transition-colors"
      >
        Host Another Quiz
      </button>
    </div>
  )
}

export default FinalResults
