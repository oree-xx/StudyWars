function Leaderboard({ players }) {
  if (players.length === 0) {
    return <p className="text-center text-slate-500">No players yet.</p>
  }

  return (
    <ol className="space-y-2 max-w-md mx-auto text-left">
      {players.map((p, i) => (
        <li key={p.id} className="flex items-center justify-between bg-slate-800 rounded-xl px-4 py-3">
          <span className="flex items-center gap-3">
            <span className="text-slate-500 font-mono w-6">{i + 1}</span>
            <span className="font-medium">{p.name}</span>
          </span>
          <span className="font-bold text-indigo-400">{p.score}</span>
        </li>
      ))}
    </ol>
  )
}

export default Leaderboard
