function PlayerReveal({ didNotAnswer, wasCorrect, score, rank, explanation }) {
  const heading = didNotAnswer ? "Time's up!" : wasCorrect ? 'Correct!' : 'Not quite'
  const headingColor = didNotAnswer ? 'text-slate-400' : wasCorrect ? 'text-emerald-400' : 'text-red-400'

  return (
    <div className="text-center space-y-4">
      <p className={`text-4xl font-extrabold ${headingColor}`}>{heading}</p>
      <p className="text-slate-400">{explanation}</p>

      <div className="flex justify-center gap-8 pt-4">
        <div>
          <p className="text-slate-500 text-sm">Score</p>
          <p className="text-2xl font-bold">{score ?? 0}</p>
        </div>
        {rank != null && (
          <div>
            <p className="text-slate-500 text-sm">Rank</p>
            <p className="text-2xl font-bold">#{rank}</p>
          </div>
        )}
      </div>

      <p className="text-slate-500 text-sm">Waiting for host to continue…</p>
    </div>
  )
}

export default PlayerReveal
