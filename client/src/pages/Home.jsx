import { Link } from 'react-router-dom'
import { SiteHeader } from '../components/AppShell'

export default function Home() {
  return <div className="app-shell">
    <SiteHeader />
    <main className="home-main">
      <section className="hero">
        <div>
          <span className="hero-tag"><span aria-hidden="true">ϟ</span> Your notes. A little competition.</span>
          <h1>Make study<br />time <em>game time.</em></h1>
          <p className="hero-description">Turn your notes into a live quiz battle. Bring your friends, test what you know, and make it stick.</p>
          <div className="hero-actions"><Link to="/host" className="btn btn-primary">Host a quiz <span aria-hidden="true">↗</span></Link><Link to="/join" className="btn btn-secondary">Join a game <span aria-hidden="true">→</span></Link></div>
          <p className="hero-footnote"><span className="small-dot" /> No player accounts. Just a room code.</p>
        </div>
        <div className="hero-preview" aria-label="Example quiz preview">
          <div className="quiz-preview">
            <div className="preview-header"><span>Biology / Round 01</span><span className="preview-live">● Quiz preview</span></div>
            <h2>Which organelle powers<br />the cell?</h2>
            <div className="preview-options"><div className="preview-option answer-a"><strong>A</strong> Nucleus</div><div className="preview-option answer-b"><strong>B</strong> Mitochondria</div><div className="preview-option answer-c"><strong>C</strong> Ribosome</div><div className="preview-option answer-d"><strong>D</strong> Golgi body</div></div>
            <div className="preview-bottom"><span>Think fast. Learn together.</span><span aria-hidden="true">✦ ✦ ✦</span></div>
            <div className="score-pop"><span aria-hidden="true">ϟ</span> A little friendly rivalry.</div>
          </div>
          <p className="preview-caption">Your study material, with a competitive streak.</p>
        </div>
      </section>
      <section className="how-it-works" aria-labelledby="how-heading">
        <div className="section-topline"><h2 id="how-heading">From notes to “one more round.”</h2></div>
        <div className="steps-grid">
          <div className="how-step"><span className="step-icon">01</span><div><h3>Bring your notes</h3><p>Paste your study notes or upload a PDF. We’ll turn the key ideas into questions.</p></div></div>
          <div className="how-step"><span className="step-icon">02</span><div><h3>Gather your people</h3><p>Review your quiz, open a room, and share the code. Any browser can join.</p></div></div>
          <div className="how-step"><span className="step-icon">03</span><div><h3>Play to remember</h3><p>Race the clock, see why answers are right, and climb the leaderboard.</p></div></div>
        </div>
      </section>
    </main>
  </div>
}
