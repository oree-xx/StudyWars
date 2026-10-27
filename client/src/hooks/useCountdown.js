import { useEffect, useState } from 'react'

// Deadlines are normalized from the server clock before reaching the UI.
// A missing deadline expires safely instead of granting extra answering time.
export function useCountdown(question) {
  const [now, setNow] = useState(Date.now)

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 100)
    return () => clearInterval(interval)
  }, [])

  const duration = (question.time_limit || 20) * 1000
  const remaining = Math.min(duration, Math.max(0, (question.deadline ?? 0) - now))
  return {
    seconds: Math.ceil(remaining / 1000),
    fraction: remaining / duration,
    expired: remaining <= 0,
  }
}
