import { Link } from 'react-router-dom'

function Join() {
  return (
    <div className="min-h-screen bg-slate-900 text-white px-4 py-10">
      <div className="max-w-md mx-auto">
        <Link to="/" className="text-slate-400 hover:text-white text-sm">
          &larr; Back
        </Link>
        <h1 className="text-3xl font-bold mt-4">Join a Quiz</h1>
        <p className="text-slate-400 mt-2">
          Enter a room code and your name to join. (Coming next.)
        </p>
      </div>
    </div>
  )
}

export default Join
