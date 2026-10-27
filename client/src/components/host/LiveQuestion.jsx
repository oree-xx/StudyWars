import Countdown from '../Countdown'
import { OPTION_COLORS } from '../../lib/optionColors'

export default function LiveQuestion({ question, answeredCount, totalPlayers, onRevealNow, connected = true }) {
  return <section className="card" aria-label="Live quiz question">
    <Countdown question={question} />
    <h1 className="question-prompt">{question.question}</h1>
    <div className="answer-grid">{question.options.map((option, index) => <div className={`answer-tile ${OPTION_COLORS[index]}`} key={index}><span className="answer-letter">{String.fromCharCode(65 + index)}</span><span>{option}</span></div>)}</div>
    <div className="question-controls"><p><strong>{answeredCount}</strong> / {totalPlayers} answers in</p><button type="button" onClick={onRevealNow} disabled={!connected} className="btn btn-secondary">Reveal answer <span aria-hidden="true">→</span></button></div>
    <p className="helper">The answer reveals when everyone responds or the timer runs out.</p>
  </section>
}
