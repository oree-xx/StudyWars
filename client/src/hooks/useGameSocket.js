import { useCallback, useEffect, useEffectEvent, useRef, useState } from 'react'

// Deliver every frame directly: React may batch an ack with a following reveal.
export function useGameSocket(url, onMessage, onDisconnect) {
  const socketRef = useRef(null)
  const deliverMessage = useEffectEvent((message) => onMessage?.(message))
  const disconnected = useEffectEvent(() => onDisconnect?.())
  const [connection, setConnection] = useState({ url: null, status: 'idle', closeCode: null })
  const status = connection.url === url ? connection.status : (url ? 'connecting' : 'idle')
  const closeCode = connection.url === url ? connection.closeCode : null

  useEffect(() => {
    if (!url) return
    let disposed = false
    let attempts = 0
    let retryTimer
    let heartbeat
    let pongTimeout
    let socket

    function clearHeartbeat() {
      clearInterval(heartbeat)
      clearTimeout(pongTimeout)
    }

    function connect() {
      if (disposed) return
      socket = new WebSocket(url)
      socketRef.current = socket
      socket.onopen = () => {
        if (disposed) return
        attempts = 0
        heartbeat = setInterval(() => {
          if (socket.readyState !== WebSocket.OPEN) return
          socket.send(JSON.stringify({ type: 'ping' }))
          pongTimeout = setTimeout(() => socket.close(), 10000)
        }, 15000)
      }
      socket.onmessage = (event) => {
        if (disposed) return
        let message
        try { message = JSON.parse(event.data) } catch { return }
        if (message.type === 'pong') {
          clearTimeout(pongTimeout)
          return
        }
        // Enable controls only after the authoritative snapshot has arrived.
        if (message.type === 'room_state') {
          setConnection({ url, status: 'open', closeCode: null })
        }
        deliverMessage(message)
      }
      socket.onerror = () => {
        if (!disposed) {
          setConnection({ url, status: 'reconnecting', closeCode: null })
          disconnected()
        }
      }
      socket.onclose = (event) => {
        clearHeartbeat()
        if (disposed) return
        socketRef.current = null
        disconnected()
        if (event.code >= 4000 && event.code < 5000) {
          setConnection({ url, status: 'closed', closeCode: event.code })
          return
        }
        setConnection({ url, status: 'reconnecting', closeCode: event.code })
        retryTimer = setTimeout(connect, Math.min(500 * 2 ** attempts++, 10000))
      }
    }

    connect()
    return () => {
      disposed = true
      clearTimeout(retryTimer)
      clearHeartbeat()
      socket.onopen = socket.onmessage = socket.onerror = socket.onclose = null
      socket.close(1000)
      socketRef.current = null
    }
  }, [url])

  const send = useCallback((message) => {
    const socket = socketRef.current
    if (socket?.readyState !== WebSocket.OPEN) return false
    try {
      socket.send(JSON.stringify(message))
      return true
    } catch {
      return false
    }
  }, [])

  return { status, closeCode, send }
}
