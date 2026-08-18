function Lobby({ roomCode, players, socketStatus, onStart }) {
  return (
    <div className="mt-6 space-y-8 text-center">
      <div>
        <p className="text-slate-400">Room Code</p>
        <p className="text-6xl font-extrabold tracking-widest mt-2">{roomCode}</p>
        <p className="text-slate-500 text-sm mt-2">Players join at /join with this code.</p>
      </div>

      <div>
        <p className="text-slate-400 mb-3">
          {players.length} player{players.length === 1 ? '' : 's'} joined
        </p>
        <div className="flex flex-wrap gap-2 justify-center">
          {players.map((p) => (
            <span key={p.id} className="bg-slate-800 rounded-full px-4 py-2 text-sm font-medium">
              {p.name}
            </span>
          ))}
        </div>
      </div>

      <button
        type="button"
        onClick={onStart}
        disabled={players.length === 0 || socketStatus !== 'open'}
        className="w-full bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl px-6 py-4 font-semibold text-lg transition-colors"
      >
        Start Game
      </button>
    </div>
  )
}

export default Lobby
