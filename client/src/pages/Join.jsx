import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'

export default function Join() {
  const [roomCode, setRoomCode] = useState('')
  const [name, setName] = useState('')
  const navigate = useNavigate()
  const canSubmit = roomCode.trim().length === 6 && name.trim().length > 0
  function handleSubmit(event) {
    event.preventDefault()
    if (canSubmit) navigate('/play', { state: { roomCode: roomCode.trim().toUpperCase(), name: name.trim() } })
  }
  return <AppShell compact label="Join a quiz">
    <Link to="/" className="back-link">← Back to home</Link>
    <div className="page-heading"><p className="eyebrow">Your next study session starts here</p><h1>Got a code? You’re in.</h1><p className="muted">Grab the six-character room code from your host and pick a name for the leaderboard.</p></div>
    <form className="card join-card stack" onSubmit={handleSubmit}>
      <div><label className="field-label" htmlFor="room-code">Room code</label><input id="room-code" className="text-input join-code-input" value={roomCode} onChange={event => setRoomCode(event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ''))} maxLength={6} placeholder="ABCDEF" autoComplete="off" autoCapitalize="characters" spellCheck={false} required /></div>
      <div><label className="field-label" htmlFor="player-name">Your name</label><input id="player-name" className="text-input" value={name} onChange={event => setName(event.target.value)} maxLength={20} placeholder="What should we call you?" autoComplete="nickname" required /></div>
      <button type="submit" className="btn btn-primary full-width" disabled={!canSubmit}>Let’s play <span aria-hidden="true">→</span></button>
    </form>
  </AppShell>
}
