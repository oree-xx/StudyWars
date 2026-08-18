import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import FinalResults from '../components/host/FinalResults'
import Lobby from '../components/host/Lobby'
import LiveQuestion from '../components/host/LiveQuestion'
import QuestionReview from '../components/host/QuestionReview'
import RevealScreen from '../components/host/RevealScreen'
import SetupForm from '../components/host/SetupForm'
import { useGameSocket } from '../hooks/useGameSocket'
import { createRoom, generateQuestions } from '../lib/api'
import { hostSocketUrl } from '../lib/ws'

const STAGE = {
  SETUP: 'setup',
  REVIEW: 'review',
  LOBBY: 'lobby',
  QUESTION: 'question',
  REVEAL: 'reveal',
  ENDED: 'ended',
}

function Host() {
  const [stage, setStage] = useState(STAGE.SETUP)
  const [error, setError] = useState('')

  const [generating, setGenerating] = useState(false)
  const [questions, setQuestions] = useState([])

  const [creatingRoom, setCreatingRoom] = useState(false)
  const [roomCode, setRoomCode] = useState(null)
  const [hostToken, setHostToken] = useState(null)

  const [players, setPlayers] = useState([])
  const [currentQuestion, setCurrentQuestion] = useState(null)
  const [answeredCount, setAnsweredCount] = useState(0)
  const [reveal, setReveal] = useState(null)
  const [finalLeaderboard, setFinalLeaderboard] = useState([])

  const socketUrl = useMemo(
    () => (roomCode && hostToken ? hostSocketUrl(roomCode, hostToken) : null),
    [roomCode, hostToken],
  )
  const { lastMessage, status: socketStatus, send } = useGameSocket(socketUrl)

  useEffect(() => {
    if (!lastMessage) return

    switch (lastMessage.type) {
      case 'room_state':
      case 'player_joined':
      case 'player_left':
        setPlayers(lastMessage.players)
        break
      case 'question':
        setCurrentQuestion(lastMessage)
        setAnsweredCount(0)
        setReveal(null)
        setStage(STAGE.QUESTION)
        break
      case 'player_answered':
        setAnsweredCount(lastMessage.answered_count)
        break
      case 'reveal':
        setReveal(lastMessage)
        setStage(STAGE.REVEAL)
        break
      case 'game_over':
        setFinalLeaderboard(lastMessage.leaderboard)
        setStage(STAGE.ENDED)
        break
      default:
        break
    }
  }, [lastMessage])

  async function handleGenerate({ notes, file, numQuestions }) {
    setError('')
    setGenerating(true)
    try {
      const generated = await generateQuestions({ notes, file, numQuestions })
      setQuestions(generated)
      setStage(STAGE.REVIEW)
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
      const { room_code, host_token } = await createRoom(questions)
      setRoomCode(room_code)
      setHostToken(host_token)
      setStage(STAGE.LOBBY)
    } catch (err) {
      setError(err.message)
    } finally {
      setCreatingRoom(false)
    }
  }

  function handleRestart() {
    setStage(STAGE.SETUP)
    setError('')
    setQuestions([])
    setRoomCode(null)
    setHostToken(null)
    setPlayers([])
    setCurrentQuestion(null)
    setAnsweredCount(0)
    setReveal(null)
    setFinalLeaderboard([])
  }

  const isLastQuestion = currentQuestion ? currentQuestion.index + 1 >= currentQuestion.total : false

  return (
    <div className="min-h-screen bg-slate-900 text-white px-4 py-10">
      <div className="max-w-2xl mx-auto">
        {stage === STAGE.SETUP && (
          <Link to="/" className="text-slate-400 hover:text-white text-sm">
            &larr; Back
          </Link>
        )}

        {stage === STAGE.SETUP && (
          <SetupForm onGenerate={handleGenerate} generating={generating} error={error} />
        )}

        {stage === STAGE.REVIEW && (
          <QuestionReview
            questions={questions}
            creatingRoom={creatingRoom}
            error={error}
            onBack={() => setStage(STAGE.SETUP)}
            onCreateRoom={handleCreateRoom}
          />
        )}

        {stage === STAGE.LOBBY && (
          <Lobby roomCode={roomCode} players={players} socketStatus={socketStatus} onStart={() => send({ type: 'start_game' })} />
        )}

        {stage === STAGE.QUESTION && currentQuestion && (
          <LiveQuestion
            question={currentQuestion}
            answeredCount={answeredCount}
            totalPlayers={players.length}
            onRevealNow={() => send({ type: 'reveal_now' })}
          />
        )}

        {stage === STAGE.REVEAL && reveal && (
          <RevealScreen
            question={currentQuestion}
            reveal={reveal}
            isLastQuestion={isLastQuestion}
            onNext={() => send({ type: 'next_question' })}
          />
        )}

        {stage === STAGE.ENDED && (
          <FinalResults leaderboard={finalLeaderboard} onRestart={handleRestart} />
        )}
      </div>
    </div>
  )
}

export default Host
