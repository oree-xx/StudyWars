export default function QuestionReview({ questions, onBack, onCreateRoom, creatingRoom, error }) {
  return <div className="stack">
    <div>
      <div className="step-strip" aria-label="Quiz setup steps"><span>✓ Notes added</span><span className="step-line" /><span className="active">02 · Review</span><span className="step-line" /><span>03 · Go live</span></div>
      <div className="page-heading" style={{ marginBottom: 0 }}><p className="eyebrow">Your quiz is taking shape</p><h1>Give it a quick once-over.</h1><p className="muted">{questions.length} questions, ready for your group. Check the answers before you open the room.</p></div>
    </div>
    <ol className="review-list">{questions.map((question, index) => <li className="card" key={index}>
      <div className="review-title"><span className="question-number">{String(index + 1).padStart(2, '0')}</span><p>{question.question}</p></div>
      <ul className="review-options">{question.options.map((option, optionIndex) => <li key={optionIndex} className={optionIndex === question.correct_index ? 'correct' : ''}><span>{String.fromCharCode(65 + optionIndex)}</span><span>{option}{optionIndex === question.correct_index && <span> ✓<span className="sr-only"> Correct answer</span></span>}</span></li>)}</ul>
      <p className="review-explanation">{question.explanation}</p>
    </li>)}</ol>
    {error && <p className="error-notice" role="alert">{error}</p>}
    <div className="action-row"><button type="button" onClick={onBack} disabled={creatingRoom} className="btn btn-secondary">← Back to notes</button><button type="button" onClick={onCreateRoom} disabled={creatingRoom || questions.length === 0} className="btn btn-primary">{creatingRoom ? 'Opening your room…' : 'Open game room'} <span aria-hidden="true">→</span></button></div>
  </div>
}
