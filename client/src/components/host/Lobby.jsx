import { useState } from 'react'

export default function Lobby({ roomCode, players, socketStatus, onStart }) {
  const [copyStatus, setCopyStatus] = useState('')
  async function copyCode() {
    try { await navigator.clipboard.writeText(roomCode); setCopyStatus('Copied!') }
    catch { setCopyStatus('Select the code above to copy it.') }
  }
  return <div className="stack">
    <div className="page-heading centered" style={{ marginBottom: 0 }}><p className="eyebrow">The room is yours</p><h1>Assemble your study squad.</h1><p className="muted">Share the code. Get everyone in. Let the friendly rivalry begin.</p></div>
    <div className="card room-card"><p className="question-label">Your room code</p><p className="room-code">{roomCode}</p><button className="room-code-copy" type="button" onClick={copyCode}>Copy room code ⧉</button><p className="small muted" style={{ marginTop: 15 }}>Open <strong>{window.location.host}/join</strong> and enter this code.</p><p className="small" role="status">{copyStatus}</p></div>
    <div className="card"><div className="roster-header"><h2>Your players</h2><span className="badge">{players.length} joined</span></div>
      {players.length ? <div className="player-chips">{players.map(player => <span className="player-chip" key={player.id}><span className="player-avatar">{player.name.slice(0, 1).toUpperCase()}</span><span style={{ overflowWrap: 'anywhere', minWidth: 0 }}>{player.name}</span>{player.connected === false && <span className="muted">· offline</span>}</span>)}</div> : <div className="empty-state"><p className="muted small">A great quiz needs a little company.</p><p className="muted small">Players will appear here as they join.</p></div>}
    </div>
    <button type="button" className="btn btn-primary full-width" disabled={players.length === 0 || socketStatus !== 'open'} onClick={onStart}>Everyone ready? Start the game <span aria-hidden="true">→</span></button>
    <p className="muted small centered">Keep this screen open. You’re in charge of the next question.</p>
  </div>
}
