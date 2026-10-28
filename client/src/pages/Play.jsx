import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'
import ConnectionBanner from '../components/ConnectionBanner'
import Leaderboard from '../components/Leaderboard'
import AnswerOptions from '../components/play/AnswerOptions'
import PlayerReveal from '../components/play/PlayerReveal'
import WaitingScreen from '../components/play/WaitingScreen'
import { useGameSocket } from '../hooks/useGameSocket'
import { playerSocketUrl } from '../lib/ws'
import { getPlayerSession, normalizeQuestion, pendingOptionAfterSnapshot, saveSession } from '../lib/session'

function Play() {
  const location = useLocation()
  const navigate = useNavigate()
  const [session] = useState(() => getPlayerSession(location.state))
  const [hasJoined, setHasJoined] = useState(false)
  const [playerId, setPlayerId] = useState(null)
  const [stage, setStage] = useState('lobby')
  const [players, setPlayers] = useState([])
  const [question, setQuestion] = useState(null)
  const questionRef = useRef(null)
  const [selectedOption, setSelectedOption] = useState(null)
  const [pendingOption, setPendingOption] = useState(null)
  const pendingRef = useRef(null)
  const [answerError, setAnswerError] = useState('')
  const [reveal, setReveal] = useState(null)
  const [finalLeaderboard, setFinalLeaderboard] = useState([])

  useEffect(() => {
    if (!session) navigate('/join', { replace: true })
  }, [session, navigate])

  const socketUrl = useMemo(
    () => session ? playerSocketUrl(session.roomCode, session.name, session.playerToken) : null,
    [session],
  )
  function clearPending() {
    pendingRef.current = null
    setPendingOption(null)
  }
  function handleMessage(message) {
    switch (message.type) {
      case 'room_state': {
        const current = normalizeQuestion(message.question)
        const pending = pendingOptionAfterSnapshot(pendingRef.current, questionRef.current?.index, message)
        setHasJoined(true)
        setPlayerId(message.player_id)
        setPlayers(message.players)
        setQuestion(current)
        questionRef.current = current
        setSelectedOption(message.selected_option ?? null)
        pendingRef.current = pending
        setPendingOption(pending)
        setAnswerError('')
        setReveal(message.reveal)
        setFinalLeaderboard(message.leaderboard || [])
        setStage(message.state)
        break
      }
      case 'player_joined':
      case 'player_left':
        setPlayers(message.players)
        break
      case 'question': {
        const current = normalizeQuestion(message)
        setQuestion(current)
        questionRef.current = current
        setSelectedOption(null)
        clearPending()
        setAnswerError('')
        setReveal(null)
        setStage('question')
        break
      }
      case 'answer_ack':
        if (message.question_index === questionRef.current?.index) {
          setSelectedOption(message.option_index)
          clearPending()
          setAnswerError('')
        }
        break
      case 'answer_rejected':
        clearPending()
        setAnswerError(message.reason || 'Your answer could not be accepted.')
        break
      case 'reveal':
        clearPending()
        setReveal(message)
        setStage('reveal')
        break
      case 'game_over':
        clearPending()
        setFinalLeaderboard(message.leaderboard)
        setStage('ended')
        break
      default:
        break
    }
  }
  const { status, closeCode, send } = useGameSocket(socketUrl, handleMessage, clearPending)

  function handleAnswer(optionIndex) {
    if (selectedOption !== null || pendingRef.current !== null || status !== 'open') return
    if (Date.now() >= question.deadline) return
    setAnswerError('')
    if (send({ type: 'answer', question_index: question.index, option_index: optionIndex })) {
      pendingRef.current = optionIndex
      setPendingOption(optionIndex)
    } else {
      setAnswerError('Reconnecting. Your answer has not been sent yet.')
    }
  }

  function leaveRoom() {
    saveSession('player', null)
    navigate('/join', { replace: true, state: null })
  }
  if (!session) return null
  const closedMessage = closeCode === 4002
    ? 'This player session is open in another tab.'
    : closeCode === 4003
      ? 'This game has already started. Ask your host for the next room code.'
      : 'This room is unavailable. Check the code or ask your host to start a new quiz.'
  const myEntry = reveal?.leaderboard.find((p) => p.id === playerId)
  const myRank = reveal ? reveal.leaderboard.findIndex((p) => p.id === playerId) + 1 : null

  return (
    <AppShell compact roomCode={session.roomCode} label={session.name}>
      <ConnectionBanner status={status} message={status === 'closed' ? closedMessage : undefined} />
      {status === 'closed' && (
        <section className="card centered stack"><div><div className="waiting-symbol" aria-hidden="true">↗</div><p className="eyebrow">Let’s find your next game</p><h1 className="reveal-answer">Your next round is waiting.</h1><p className="muted">Head back to the join screen when you have a room code.</p></div><button type="button" className="btn btn-primary full-width" onClick={leaveRoom}>Back to join <span aria-hidden="true">→</span></button></section>
      )}
      {!hasJoined && status !== 'closed' && (
        <section className="card centered" role="status"><div className="waiting-symbol" aria-hidden="true">↻</div><p className="eyebrow">Making your entrance</p><h1 className="reveal-answer">Finding your place in the room.</h1><p className="muted">Hang tight, {session.name}. We’re connecting you to the game.</p></section>
      )}
      {hasJoined && stage === 'lobby' && status !== 'closed' && <WaitingScreen name={session.name} players={players} />}
      {hasJoined && stage === 'question' && question && status !== 'closed' && (
        <>
          <AnswerOptions question={question} selectedOption={selectedOption} pendingOption={pendingOption}
            connected={status === 'open'} onAnswer={handleAnswer} />
          {answerError && <p role="alert" className="error-notice" style={{ marginTop: 16 }}>{answerError}</p>}
        </>
      )}
      {hasJoined && stage === 'reveal' && reveal && status !== 'closed' && (
        <PlayerReveal didNotAnswer={selectedOption === null}
          wasCorrect={selectedOption !== null && selectedOption === reveal.correct_index}
          score={myEntry?.score} rank={myRank} explanation={reveal.explanation} />
      )}
      {hasJoined && stage === 'ended' && status !== 'closed' && (
        <div className="stack">
          <div className="results-heading">
            <div className="trophy-icon" aria-hidden="true">✦</div>
            <p className="eyebrow">That's a wrap</p>
            <h1>Knowledge wins.</h1>
            <p className="muted">Every round is another thing you know.</p>
          </div>
          <section className="card"><div className="roster-header"><h2>Final standings</h2><span className="badge">{finalLeaderboard.length} players</span></div><Leaderboard players={finalLeaderboard} /></section>
          <button type="button" className="btn btn-primary full-width" onClick={leaveRoom}>Join another quiz <span aria-hidden="true">→</span></button>
          <Link to="/" className="back-link centered">← Back home</Link>
        </div>
      )}
    </AppShell>
  )
}
export default Play
