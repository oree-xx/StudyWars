import Countdown from '../Countdown'
import { useCountdown } from '../../hooks/useCountdown'
import { OPTION_COLORS } from '../../lib/optionColors'

export default function AnswerOptions({ question, selectedOption = null, pendingOption = null, connected = true, onAnswer }) {
  const { expired } = useCountdown(question)
  const hasAnswered = selectedOption !== null
  const isPending = pendingOption !== null
  const highlighted = selectedOption ?? pendingOption
  const disabled = hasAnswered || isPending || !connected || expired
  const message = hasAnswered ? '✓ Answer locked in. Let’s see how you did.' : isPending ? 'Sending your answer…' : !connected ? 'Reconnecting. Your answer buttons will be ready shortly.' : expired ? 'Time’s up. Waiting for the answer…' : 'Pick one. Faster correct answers earn more points.'
  return <section className="card" aria-label="Answer the quiz question">
    <Countdown question={question} />
    <h1 className="question-prompt">{question.question}</h1>
    <div className="answer-grid">{question.options.map((option, index) => <button key={index} type="button" className={`answer-tile ${OPTION_COLORS[index]}${highlighted === index ? ' selected' : highlighted !== null ? ' faded' : ''}`} disabled={disabled} aria-pressed={selectedOption === index} onClick={() => onAnswer(index)}><span className="answer-letter">{String.fromCharCode(65 + index)}</span><span>{option}</span></button>)}</div>
    <p className={`answer-status${hasAnswered ? ' confirmed' : ''}`} role="status">{message}</p>
  </section>
}
