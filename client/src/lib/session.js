const PREFIX = 'studywars:'

export function readSession(role) {
  try {
    const value = JSON.parse(sessionStorage.getItem(PREFIX + role))
    if (!value || typeof value.roomCode !== 'string') return null
    if (role === 'host' && typeof value.hostToken !== 'string') return null
    if (role === 'player' && (typeof value.name !== 'string' || typeof value.playerToken !== 'string')) return null
    return value
  } catch {
    return null
  }
}

export function saveSession(role, value) {
  try {
    if (value) sessionStorage.setItem(PREFIX + role, JSON.stringify(value))
    else sessionStorage.removeItem(PREFIX + role)
  } catch {
    // Games still work when browser storage is unavailable.
  }
}

export function getPlayerSession(requested) {
  const previous = readSession('player')
  if (!requested?.roomCode || !requested?.name) return previous
  const roomCode = requested.roomCode.trim().toUpperCase()
  const name = requested.name.trim().slice(0, 20)
  if (previous?.roomCode === roomCode && previous.name === name) return previous
  // This also works on a local-network HTTP origin.
  const bytes = crypto.getRandomValues(new Uint8Array(24))
  const playerToken = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
  const session = { roomCode, name, playerToken }
  saveSession('player', session)
  return session
}

// Tolerate an inaccurate device clock. Resuming never grants a fresh 20 seconds.
export function normalizeQuestion(question) {
  if (!question) return null
  return {
    ...question,
    deadline: Date.now() + Math.max(0, question.ends_at - question.server_time),
  }
}

// Other players can trigger a snapshot while our answer is still in flight.
// Only a receipt, accepted answer, or question transition resolves that send.
export function pendingOptionAfterSnapshot(pendingOption, questionIndex, snapshot) {
  return snapshot.state === 'question'
    && snapshot.question?.index === questionIndex
    && snapshot.selected_option == null
    ? pendingOption
    : null
}
