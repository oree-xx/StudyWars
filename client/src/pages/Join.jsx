import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

function Join() {
  const [roomCode, setRoomCode] = useState('')
  const [name, setName] = useState('')
  const navigate = useNavigate()

  const canSubmit = roomCode.trim().length > 0 && name.trim().length > 0

  function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit) return
    navigate('/play', { state: { roomCode: roomCode.trim().toUpperCase(), name: name.trim() } })
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white px-4 py-10">
      <div className="max-w-md mx-auto">
        <Link to="/" className="text-slate-400 hover:text-white text-sm">
          &larr; Back
        </Link>

        <form onSubmit={handleSubmit} className="mt-6 space-y-6">
          <div>
            <h1 className="text-3xl font-bold">Join a Quiz</h1>
            <p className="text-slate-400 mt-2">Enter the room code from your host's screen.</p>
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Room Code</label>
            <input
              value={roomCode}
              onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
              maxLength={6}
              placeholder="ABC123"
              className="w-full rounded-xl bg-slate-800 border border-slate-700 p-4 text-center text-2xl font-bold tracking-widest uppercase placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Your Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={20}
              placeholder="Alex"
              className="w-full rounded-xl bg-slate-800 border border-slate-700 p-4 text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl px-6 py-4 font-semibold text-lg transition-colors"
          >
            Join Game
          </button>
        </form>
      </div>
    </div>
  )
}

export default Join
