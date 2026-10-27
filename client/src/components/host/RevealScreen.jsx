import Leaderboard from '../Leaderboard'

export default function RevealScreen({ question, reveal, isLastQuestion, onNext, connected = true }) {
  const correctText = question?.options?.[reveal.correct_index]
  return <div className="stack">
    <section className="card centered"><span className="correct-badge">✓ The correct answer</span><h1 className="reveal-answer">{correctText || `Option ${String.fromCharCode(65 + reveal.correct_index)}`}</h1><p className="muted">{reveal.explanation}</p></section>
    <section className="card"><div className="roster-header"><h2>The leaderboard</h2><span className="badge">Round {(question?.index ?? 0) + 1}</span></div><Leaderboard players={reveal.leaderboard} /></section>
    <button type="button" onClick={onNext} disabled={!connected} className="btn btn-primary full-width">{isLastQuestion ? 'See the final standings' : 'Next question'} <span aria-hidden="true">→</span></button>
  </div>
}
