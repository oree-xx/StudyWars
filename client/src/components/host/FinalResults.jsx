import Leaderboard from '../Leaderboard'

export default function FinalResults({ leaderboard, onRestart }) {
  return <div className="stack">
    <div className="results-heading"><div className="trophy-icon" aria-hidden="true">✦</div><p className="eyebrow">That’s a wrap</p><h1>{leaderboard[0] ? `${leaderboard[0].name} takes the top spot.` : 'A round well played.'}</h1><p className="muted">A little competition. A lot more knowledge.</p></div>
    <section className="card"><div className="roster-header"><h2>Final standings</h2><span className="badge">{leaderboard.length} players</span></div><Leaderboard players={leaderboard} /></section>
    <button type="button" onClick={onRestart} className="btn btn-primary full-width">One more round? Host another quiz <span aria-hidden="true">↗</span></button>
  </div>
}
