export default function WaitingScreen({ name, players }) {
  return <section className="card centered stack">
    <div><div className="waiting-symbol" aria-hidden="true">✓</div><p className="eyebrow">You’re on the team sheet</p><h1 className="reveal-answer">You’re in, {name}.</h1><p className="muted">Get your thinking cap on. The game begins when your host presses start.</p></div>
    <div><div className="roster-header"><h2>Your competition</h2><span className="badge">{players.length} players</span></div><div className="player-chips">{players.map(player => <span className="player-chip" key={player.id}><span className="player-avatar">{player.name.slice(0, 1).toUpperCase()}</span><span style={{ overflowWrap: 'anywhere', minWidth: 0 }}>{player.name}</span></span>)}</div></div>
    <p className="muted small">20 seconds. Four options. One right answer.</p>
  </section>
}
