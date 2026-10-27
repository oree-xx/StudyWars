import { Link } from 'react-router-dom'

export function SiteHeader({ roomCode }) {
  return (
    <header className="site-header">
      <Link className="brand" to="/" aria-label="StudyWars home"><span className="brand-mark" aria-hidden="true">ϟ</span><span>Study<span>Wars</span></span></Link>
      {roomCode ? <span className="room-tag">ROOM {roomCode}</span> : <nav className="header-links" aria-label="Main navigation"><Link className="nav-host" to="/host">Host a quiz</Link><Link className="nav-join" to="/join">Join a game <span aria-hidden="true">↗</span></Link></nav>}
    </header>
  )
}

export function SiteFooter() {
  return <footer className="site-footer"><span>Less cramming. More competing.</span><span className="footer-note"><span className="small-dot" /> Made for learning together</span></footer>
}

export default function AppShell({ children, compact = false, roomCode, label }) {
  return <div className="app-shell"><SiteHeader roomCode={roomCode} /><main className={`page-content${compact ? ' compact' : ''}`} aria-label={label}>{children}</main><SiteFooter /></div>
}
