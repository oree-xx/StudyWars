import { Link } from 'react-router-dom'

function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-10 bg-slate-900 text-white px-4">
      <div className="text-center">
        <h1 className="text-5xl font-extrabold tracking-tight">StudyWars</h1>
        <p className="mt-3 text-slate-400">Turn your notes into a live quiz battle.</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 w-full max-w-md">
        <Link
          to="/host"
          className="flex-1 text-center bg-indigo-500 hover:bg-indigo-400 transition-colors rounded-xl px-6 py-4 font-semibold text-lg"
        >
          Host a Quiz
        </Link>
        <Link
          to="/join"
          className="flex-1 text-center bg-slate-800 hover:bg-slate-700 transition-colors rounded-xl px-6 py-4 font-semibold text-lg"
        >
          Join a Quiz
        </Link>
      </div>
    </div>
  )
}

export default Home
