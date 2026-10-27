export default function ConnectionBanner({ status, message }) {
  if (status === 'open' || status === 'idle') return null
  const reconnecting = status !== 'closed'
  return <div className="connection-banner" role="status"><span aria-hidden="true">{reconnecting ? '↻' : '!'}</span><span>{message || (status === 'connecting' ? 'Connecting to your game…' : reconnecting ? 'Reconnecting to your game. Hang tight.' : 'This connection has ended. Please rejoin the game.')}</span></div>
}
