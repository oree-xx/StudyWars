function WaitingScreen({ name, players }) {
  return (
    <div className="text-center space-y-6">
      <div>
        <p className="text-slate-400">You're in as</p>
        <p className="text-2xl font-bold mt-1">{name}</p>
      </div>
      <p className="text-slate-400">Waiting for the host to start the game…</p>
      <div className="flex flex-wrap gap-2 justify-center">
        {players.map((p) => (
          <span key={p.id} className="bg-slate-800 rounded-full px-4 py-2 text-sm font-medium">
            {p.name}
          </span>
        ))}
      </div>
    </div>
  )
}

export default WaitingScreen
