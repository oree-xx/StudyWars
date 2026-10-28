import { useMemo, useState } from 'react'
import AppShell from '../components/AppShell'
import ConnectionBanner from '../components/ConnectionBanner'
import FinalResults from '../components/host/FinalResults'
import Lobby from '../components/host/Lobby'
import LiveQuestion from '../components/host/LiveQuestion'
import QuestionReview from '../components/host/QuestionReview'
import RevealScreen from '../components/host/RevealScreen'
import SetupForm from '../components/host/SetupForm'
import { useGameSocket } from '../hooks/useGameSocket'
import { createRoom, generateQuestions } from '../lib/api'
import { hostSocketUrl } from '../lib/ws'
import { normalizeQuestion, readSession, saveSession } from '../lib/session'

function Host() {
  const [session, setSession] = useState(() => readSession('host'))
  const [stage, setStage] = useState(() => session ? 'lobby' : 'setup')
  const [error, setError] = useState('')
  const [generating, setGenerating] = useState(false)
  const [questions, setQuestions] = useState([])
  const [creatingRoom, setCreatingRoom] = useState(false)
  const [players, setPlayers] = useState([])
  const [currentQuestion, setCurrentQuestion] = useState(null)
  const [answeredCount, setAnsweredCount] = useState(0)
  const [reveal, setReveal] = useState(null)
  const [finalLeaderboard, setFinalLeaderboard] = useState([])
  const [ready, setReady] = useState(false)
  const socketUrl = useMemo(
    () => session ? hostSocketUrl(session.roomCode, session.hostToken) : null,
    [session],
  )

  function handleMessage(message) {
    switch (message.type) {
      case 'room_state':
        setPlayers(message.players)
        setCurrentQuestion(normalizeQuestion(message.question))
        setAnsweredCount(message.answered_count || 0)
        setReveal(message.reveal)
        setFinalLeaderboard(message.leaderboard || [])
        setStage(message.state)
        setReady(true)
        break
      case 'player_joined':
      case 'player_left':
        setPlayers(message.players)
        break
      case 'question':
        setCurrentQuestion(normalizeQuestion(message))
        setAnsweredCount(0)
        setReveal(null)
        setStage('question')
        break
      case 'player_answered':
        setAnsweredCount(message.answered_count)
        break
      case 'reveal':
        setReveal(message)
        setStage('reveal')
        break
      case 'game_over':
        setFinalLeaderboard(message.leaderboard)
        setStage('ended')
        break
      default:
        break
    }
  }
  const { status, closeCode, send } = useGameSocket(socketUrl, handleMessage)
  const connected = status === 'open' && ready

  async function handleGenerate(input) {
    setError('')
    setGenerating(true)
    try {
      setQuestions(await generateQuestions(input))
      setStage('review')
    } catch (err) {
      setError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  async function handleCreateRoom() {
    setError('')
    setCreatingRoom(true)
    try {
      const room = await createRoom(questions)
      const next = { roomCode: room.room_code, hostToken: room.host_token }
      saveSession('host', next)
      setReady(false)
      setSession(next)
      setStage('lobby')
    } catch (err) {
      setError(err.message)
    } finally {
      setCreatingRoom(false)
    }
  }

  function handleRestart() {
    saveSession('host', null)
    setSession(null)
    setStage('setup')
    setError('')
    setQuestions([])
    setPlayers([])
    setCurrentQuestion(null)
    setAnsweredCount(0)
    setReveal(null)
    setFinalLeaderboard([])
    setReady(false)
  }

  const isLastQuestion = currentQuestion ? currentQuestion.index + 1 >= currentQuestion.total : false
  const closedMessage = closeCode === 4002
    ? 'This host session is open in another tab.'
    : 'This room is no longer available. Start a new quiz to play again.'

  return (
    <AppShell roomCode={session?.roomCode} label="Host studio">
      {session && <ConnectionBanner status={status} message={status === 'closed' ? closedMessage : undefined} />}
      {session && status === 'closed' && (
        <section className="card centered stack">
          <div><div className="waiting-symbol" aria-hidden="true">↗</div><p className="eyebrow">Ready for a fresh round?</p><h1 className="reveal-answer">Let’s get you hosting again.</h1><p className="muted">Open a new room and bring your group back together.</p></div>
          <button type="button" className="btn btn-primary full-width" onClick={handleRestart}>Start a new quiz <span aria-hidden="true">→</span></button>
        </section>
      )}
      {session && !ready && status !== 'closed' && (
        <section className="card centered" role="status"><div className="waiting-symbol" aria-hidden="true">↻</div><h1 className="reveal-answer">Getting your room ready.</h1><p className="muted">Restoring your quiz and gathering the latest game state.</p></section>
      )}
      {/* Keep the form mounted so Back from review retains notes and the PDF. */}
      <div style={{ display: stage === 'setup' ? 'block' : 'none' }}>
        <SetupForm onGenerate={handleGenerate} generating={generating} error={error} />
      </div>
      {stage === 'review' && (
        <QuestionReview questions={questions} creatingRoom={creatingRoom} error={error}
          onBack={() => setStage('setup')} onCreateRoom={handleCreateRoom} />
      )}
      {stage === 'lobby' && session && ready && status !== 'closed' && (
        <Lobby roomCode={session.roomCode} players={players} socketStatus={connected ? 'open' : status}
          onStart={() => connected && send({ type: 'start_game' })} />
      )}
      {stage === 'question' && currentQuestion && status !== 'closed' && (
        <LiveQuestion question={currentQuestion} answeredCount={answeredCount}
          totalPlayers={players.length} connected={connected}
          onRevealNow={() => send({ type: 'reveal_now', question_index: currentQuestion.index })} />
      )}
      {stage === 'reveal' && reveal && status !== 'closed' && (
        <RevealScreen question={currentQuestion} reveal={reveal} isLastQuestion={isLastQuestion}
          connected={connected} onNext={() => send({ type: 'next_question', question_index: currentQuestion?.index })} />
      )}
      {stage === 'ended' && status !== 'closed' && <FinalResults leaderboard={finalLeaderboard} onRestart={handleRestart} />}
    </AppShell>
  )
}
export default Host
