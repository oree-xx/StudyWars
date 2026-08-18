// Builds a same-origin WebSocket URL so it works through the Vite dev
// proxy in development and unchanged behind a reverse proxy in production.
export function wsUrl(path) {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}${path}`
}

export function hostSocketUrl(roomCode, hostToken) {
  return wsUrl(`/ws/host/${roomCode}?token=${encodeURIComponent(hostToken)}`)
}

export function playerSocketUrl(roomCode, name) {
  return wsUrl(`/ws/player/${roomCode}?name=${encodeURIComponent(name)}`)
}
