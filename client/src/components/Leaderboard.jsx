export default function Leaderboard({ players = [] }) {
  if (!players.length) return <p className="muted small centered">No players on the board yet.</p>
  return <ol className="leaderboard" aria-label="Player rankings">{players.map((player, index) => <li className="leaderboard-row" key={player.id}>
    <span className="rank-number">{String(index + 1).padStart(2, '0')}</span><span className="player-avatar" aria-hidden="true">{player.name.slice(0, 1).toUpperCase()}</span><span className="player-name">{player.name}</span><span className="player-points">{player.score.toLocaleString()}<small>pts</small></span>
  </li>)}</ol>
}
