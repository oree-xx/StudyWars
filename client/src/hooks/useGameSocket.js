import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Connects to a game WebSocket (host or player) and exposes the latest
 * parsed message plus a `send` helper. Pass `null`/`undefined` as the url
 * to hold off connecting (e.g. before a room code is known).
 *
 * @param {string | null} url
 */
export function useGameSocket(url) {
  const wsRef = useRef(null)
  const [lastMessage, setLastMessage] = useState(null)
  const [status, setStatus] = useState('idle') // idle | connecting | open | closed | error

  useEffect(() => {
    if (!url) {
      setStatus('idle')
      return
    }

    setStatus('connecting')
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setStatus('open')
    ws.onclose = () => setStatus('closed')
    ws.onerror = () => setStatus('error')
    ws.onmessage = (event) => {
      try {
        setLastMessage(JSON.parse(event.data))
      } catch {
        // Ignore malformed frames rather than crashing the UI.
      }
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [url])

  const send = useCallback((message) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message))
    }
  }, [])

  return { lastMessage, status, send }
}
