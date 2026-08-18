import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import Leaderboard from '../components/Leaderboard'
import AnswerOptions from '../components/play/AnswerOptions'
import PlayerReveal from '../components/play/PlayerReveal'
import WaitingScreen from '../components/play/WaitingScreen'
import { useGameSocket } from '../hooks/useGameSocket'
import { playerSocketUrl } from '../lib/ws'

const STAGE = {
  LOBBY: 'lobby',
  QUESTION: 'question',
  REVEAL: 'reveal',
  ENDED: 'ended',
}

function Play() {
  const location = useLocation()
  const navigate = useNavigate()
  const { roomCode, name } = location.state || {}

  useEffect(() => {
    if (!roomCode || !name) {
      navigate('/join', { replace: true })
    }
  }, [roomCode, name, navigate])

  const socketUrl = useMemo(
    () => (roomCode && name ? playerSocketUrl(roomCode, name) : null),
    [roomCode, name],
  )
  const { lastMessage, status, send } = useGameSocket(socketUrl)

  const [hasJoined, setHasJoined] = useState(false)
  const [playerId, setPlayerId] = useState(null)
  const [stage, setStage] = useState(STAGE.LOBBY)
  const [players, setPlayers] = useState([])
  const [question, setQuestion] = useState(null)
  const [selectedOption, setSelectedOption] = useState(null)
  const [reveal, setReveal] = useState(null)
  const [finalLeaderboard, setFinalLeaderboard] = useState([])

  useEffect(() => {
    if (!lastMessage) return

    switch (lastMessage.type) {
      case 'joined':
        setHasJoined(true)
        setPlayerId(lastMessage.player_id)
        break
      case 'player_joined':
      case 'player_left':
        setPlayers(lastMessage.players)
        break
      case 'question':
        setQuestion(lastMessage)
        setSelectedOption(null)
        setReveal(null)
        setStage(STAGE.QUESTION)
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

  function handleAnswer(optionIndex) {
    if (selectedOption !== null) return
    setSelectedOption(optionIndex)
    send({ type: 'answer', option_index: optionIndex })
  }

  if (!roomCode || !name) {
    return null // redirecting to /join
  }

  if (status === 'closed' && !hasJoined) {
    return (
      <CenteredMessage>
        <p className="text-red-400 font-semibold text-lg">Couldn't join this room</p>
        <p className="text-slate-400 mt-2">
          Check the room code and make sure the game hasn't already started.
        </p>
        <Link
          to="/join"
          className="inline-block mt-6 bg-indigo-500 hover:bg-indigo-400 rounded-xl px-6 py-3 font-semibold transition-colors"
        >
          Try Again
        </Link>
      </CenteredMessage>
    )
  }

  if (!hasJoined) {
    return (
      <CenteredMessage>
        <p className="text-slate-400">Connecting…</p>
      </CenteredMessage>
    )
  }

  const myEntry = reveal?.leaderboard.find((p) => p.id === playerId)
  const myRank = reveal ? reveal.leaderboard.findIndex((p) => p.id === playerId) + 1 : null

  return (
    <div className="min-h-screen bg-slate-900 text-white px-4 py-10">
      <div className="max-w-md mx-auto">
        {status === 'closed' && (
          <p className="text-center text-amber-400 text-sm mb-4">
            Connection lost — try refreshing if the game doesn't continue.
          </p>
        )}

        {stage === STAGE.LOBBY && <WaitingScreen name={name} players={players} />}

        {stage === STAGE.QUESTION && question && (
          <AnswerOptions question={question} selectedOption={selectedOption} onAnswer={handleAnswer} />
        )}

        {stage === STAGE.REVEAL && reveal && (
          <PlayerReveal
            didNotAnswer={selectedOption === null}
            wasCorrect={selectedOption !== null && selectedOption === reveal.correct_index}
            score={myEntry?.score}
            rank={myRank}
            explanation={reveal.explanation}
          />
        )}

        {stage === STAGE.ENDED && (
          <div className="space-y-6 text-center">
            <h2 className="text-3xl font-bold">🏁 Game Over</h2>
            <Leaderboard players={finalLeaderboard} />
          </div>
        )}
      </div>
    </div>
  )
}

function CenteredMessage({ children }) {
  return (
    <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center px-4">
      <div className="text-center max-w-sm">{children}</div>
    </div>
  )
}

export default Play
