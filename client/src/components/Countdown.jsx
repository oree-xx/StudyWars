import { useEffect } from 'react'
import { useCountdown } from '../hooks/useCountdown'

export default function Countdown({ question, onExpire }) {
  const { seconds, fraction, expired } = useCountdown(question)
  useEffect(() => { if (expired) onExpire?.() }, [expired, onExpire])
  return <>
    <div className="question-topline"><span className="question-label">Question {question.index + 1} / {question.total}</span><div className={`countdown${seconds <= 5 ? ' urgent' : ''}`} role="timer" aria-label={`${seconds} seconds remaining`}><span className="muted">{expired ? "Time’s up" : 'Time left'}</span><span className="countdown-number">{seconds}<span className="sr-only"> seconds</span></span></div></div>
    <div className={`time-track${seconds <= 5 ? ' urgent' : ''}`} aria-hidden="true"><span style={{ width: `${fraction * 100}%` }} /></div>
  </>
}
