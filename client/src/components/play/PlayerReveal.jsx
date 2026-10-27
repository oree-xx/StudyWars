export default function PlayerReveal({ didNotAnswer, wasCorrect, score, rank, explanation }) {
  const heading = didNotAnswer ? 'The clock got there first.' : wasCorrect ? 'You nailed it.' : 'One to remember.'
  return <div className="stack">
    <section className="card centered"><div className="waiting-symbol" aria-hidden="true">{wasCorrect ? '✓' : didNotAnswer ? '◷' : '✦'}</div><p className="eyebrow">{didNotAnswer ? 'No answer this round' : wasCorrect ? 'Correct answer' : 'Keep learning. Keep playing.'}</p><h1 className={`reveal-answer ${wasCorrect ? 'status-positive' : 'status-neutral'}`}>{heading}</h1><p className="muted">{explanation}</p>
      <div className="stats-grid"><div className="stat"><span className="question-label">Your score</span><strong>{(score ?? 0).toLocaleString()}</strong></div><div className="stat"><span className="question-label">Your place</span><strong>{rank ? `#${rank}` : '—'}</strong></div></div>
    </section>
    <p className="muted small centered" role="status">Take a breath. Your host will start the next round.</p>
  </div>
}
