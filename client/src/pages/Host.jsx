import { Link } from 'react-router-dom'

function Host() {
  return (
    <div className="min-h-screen bg-slate-900 text-white px-4 py-10">
      <div className="max-w-2xl mx-auto">
        <Link to="/" className="text-slate-400 hover:text-white text-sm">
          &larr; Back
        </Link>
        <h1 className="text-3xl font-bold mt-4">Host a Quiz</h1>
        <p className="text-slate-400 mt-2">
          Upload notes, generate questions, and start a live room. (Coming next.)
        </p>
      </div>
    </div>
  )
}

export default Host
